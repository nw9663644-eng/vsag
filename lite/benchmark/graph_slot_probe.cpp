// Copyright 2024-present the vsag project
// SPDX-License-Identifier: Apache-2.0
// Reuse the existing snapshot reader, distance calculation and routing loop.
#define VSAG_LITE_ROUTE_PROBE_MAIN graph_route_probe_main
#include "graph_route_probe.cpp"  // NOLINT(bugprone-suspicious-include): share diagnostic code.
#undef VSAG_LITE_ROUTE_PROBE_MAIN

namespace {
std::vector<uint64_t>
reference_order(const GraphSnapshot& graph, const GraphSnapshot& reference) {
    require(graph.dim == reference.dim, "reference dimension mismatch");
    std::vector<uint64_t> order;
    order.reserve(graph.ids.size());
    for (const int64_t id : reference.ids) {
        const auto found = graph.slots.find(id);
        if (found != graph.slots.end()) {
            order.push_back(found->second);
        }
    }
    require(order.size() == graph.ids.size(), "reference does not cover all current ids");
    return order;
}

SlotRouting
make_routing(const std::vector<uint64_t>& order) {
    SlotRouting routing;
    routing.previous.resize(order.size());
    routing.next.resize(order.size());
    routing.tie_rank.resize(order.size());
    for (uint64_t i = 0; i < order.size(); ++i) {
        const uint64_t slot = order[i];
        routing.previous[slot] = order[(i + order.size() - 1) % order.size()];
        routing.next[slot] = order[(i + 1) % order.size()];
        routing.tie_rank[slot] = i;
    }
    return routing;
}

std::vector<uint64_t>
reference_entries(const std::vector<uint64_t>& order) {
    std::vector<uint64_t> entries{order.front()};
    const uint64_t last = order.size() - 1;
    if (last != 0) {
        entries.push_back(order[last]);
    }
    for (uint64_t i = 1; i <= 6; ++i) {
        const uint64_t rank = i * last / 7;
        if (rank != 0 and rank != last) {
            entries.push_back(order[rank]);
        }
    }
    return entries;
}
}  // namespace

int
main(int argc, char** argv) {
    try {
        require(argc == 5, "usage: slot_probe SNAPSHOT REFERENCE DATASET OUTPUT.csv");
        const std::string path = argv[4];
        require(not std::filesystem::exists(path) and
                    not std::filesystem::exists(path + ".neighbors.csv"),
                "output already exists");
        const auto graph = load_snapshot(argv[1]);
        const auto reference = load_snapshot(argv[2]);
        const auto order = reference_order(graph, reference);
        auto routing = make_routing(order);
        const auto physical_entries = select_entries(graph, "uniform");
        const auto logical_entries = reference_entries(order);
        const auto queries = read_records<float>(std::string(argv[3]) + "/queries.fvecs",
                                                 static_cast<int32_t>(graph.dim));
        std::ifstream truth_input(std::string(argv[3]) + "/groundtruth.ivecs", std::ios::binary);
        require(static_cast<bool>(truth_input), "truth open failed");
        const int32_t k = read_dim(truth_input);
        const auto truth = read_records<int32_t>(std::string(argv[3]) + "/groundtruth.ivecs", k);
        require(queries.size() == truth.size(), "query/truth count mismatch");
        for (const auto& row : truth) {
            require(std::unordered_set<int32_t>(row.begin(), row.end()).size() == row.size(),
                    "duplicate truth ids");
        }
        std::ifstream snapshot(argv[1], std::ios::binary);
        auto native = vsag::lite::Index::Load(snapshot);
        require(static_cast<bool>(native), "native load failed");
        std::ofstream output(path);
        std::ofstream neighbors(path + ".neighbors.csv");
        output << "query,mask,eligible,k,hits,truth_visited,visited_nodes,expanded_nodes,"
                  "distance_evaluations,tie_comparisons,baseline_native_ids_equal\n";
        neighbors << "query,mask,rank,id,distance\n";
        require(output.good() and neighbors.good(), "output open failed");
        for (uint64_t query = 0; query < queries.size(); ++query) {
            const bool eligible =
                std::all_of(truth[query].begin(), truth[query].end(), [&](int32_t id) {
                    return graph.slots.count(id) != 0;
                });
            if (not eligible) {
                for (uint64_t mask = 0; mask < 8; ++mask) {
                    output << query << ',' << mask << ",0," << k << ",0,0,0,0,0,0,0\n";
                }
                continue;
            }
            const auto actual = (*native)->SearchWithOptions(
                queries[query].data(), graph.dim, static_cast<uint64_t>(k), {graph.ef_search});
            require(static_cast<bool>(actual), "native search failed");
            std::unordered_set<int64_t> native_ids;
            for (const auto& neighbor : *actual) {
                native_ids.insert(neighbor.id);
            }
            const std::unordered_set<int64_t> expected(truth[query].begin(), truth[query].end());
            for (uint64_t mask = 0; mask < 8; ++mask) {
                routing.restore_ring = (mask & 2) != 0;
                routing.restore_ties = (mask & 4) != 0;
                const auto& entries = (mask & 1) != 0 ? logical_entries : physical_entries;
                const auto trace = search(graph,
                                          entries,
                                          "uniform",
                                          queries[query].data(),
                                          static_cast<uint64_t>(k),
                                          &routing);
                uint64_t hits = 0;
                uint64_t truth_visited = 0;
                std::unordered_set<int64_t> result_ids;
                for (uint64_t rank = 0; rank < trace.result.size(); ++rank) {
                    const auto candidate = trace.result[rank];
                    const int64_t id = graph.ids[candidate.slot];
                    result_ids.insert(id);
                    hits += expected.count(id);
                    neighbors << query << ',' << mask << ',' << rank << ',' << id << ','
                              << std::hexfloat << candidate.distance << std::defaultfloat << '\n';
                }
                for (const auto id : expected) {
                    truth_visited += trace.visited[graph.slots.at(id)];
                }
                const bool baseline_match = mask == 0 and result_ids == native_ids;
                require(mask != 0 or baseline_match, "scalar baseline differs from native ids");
                output << query << ',' << mask << ",1," << k << ',' << hits << ',' << truth_visited
                       << ',' << std::count(trace.visited.begin(), trace.visited.end(), 1) << ','
                       << trace.expanded << ',' << trace.distance_evaluations << ','
                       << trace.tie_comparisons << ',' << baseline_match << '\n';
            }
        }
        output.close();
        neighbors.close();
        require(static_cast<bool>(output) and static_cast<bool>(neighbors), "output write failed");
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
