// Copyright 2024-present the vsag project
// SPDX-License-Identifier: Apache-2.0
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <numeric>
#include <queue>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <vector>

namespace {

struct Candidate {
    uint64_t slot;
    float distance;
};

bool
closer(const Candidate& left, const Candidate& right) {
    return left.distance < right.distance or
           (left.distance == right.distance and left.slot < right.slot);
}

bool
farther(const Candidate& left, const Candidate& right) {
    return left.distance > right.distance or
           (left.distance == right.distance and left.slot > right.slot);
}

void
require(bool condition, const char* message) {
    if (not condition) {
        throw std::runtime_error(message);
    }
}

template <typename T>
T
read(std::istream& input) {
    T value{};
    input.read(reinterpret_cast<char*>(&value), sizeof(value));
    require(static_cast<bool>(input), "truncated input");
    return value;
}

int32_t
read_dim(std::istream& input) {
    const auto dim = read<int32_t>(input);
    require(dim > 0 and dim <= 4096, "invalid record dimension");
    return dim;
}

template <typename T>
std::vector<std::vector<T>>
read_records(const std::string& path, int32_t expected_dim) {
    std::ifstream input(path, std::ios::binary | std::ios::ate);
    require(static_cast<bool>(input), "dataset open failed");
    const auto size = input.tellg();
    require(size > 0 and size % (sizeof(int32_t) + sizeof(T) * expected_dim) == 0,
            "invalid dataset length");
    const auto count = static_cast<uint64_t>(size / (sizeof(int32_t) + sizeof(T) * expected_dim));
    input.seekg(0);
    std::vector<std::vector<T>> records;
    records.reserve(count);
    for (uint64_t i = 0; i < count; ++i) {
        require(read_dim(input) == expected_dim, "inconsistent record dimension");
        std::vector<T> row(expected_dim);
        input.read(reinterpret_cast<char*>(row.data()), sizeof(T) * expected_dim);
        require(static_cast<bool>(input), "truncated dataset record");
        records.push_back(std::move(row));
    }
    return records;
}

struct GraphSnapshot {
    uint64_t dim{};
    uint64_t max_degree{};
    uint64_t ef_search{};
    std::vector<int64_t> ids;
    std::vector<float> vectors;
    std::vector<std::vector<uint64_t>> links;
    std::unordered_map<int64_t, uint64_t> slots;
};

GraphSnapshot
load_snapshot(const std::string& path) {
    std::ifstream input(path, std::ios::binary | std::ios::ate);
    require(static_cast<bool>(input), "snapshot open failed");
    const uint64_t available = static_cast<uint64_t>(input.tellg());
    input.seekg(0);
    char magic[8];
    input.read(magic, sizeof(magic));
    require(static_cast<bool>(input) and std::memcmp(magic, "VSAGLT01", 8) == 0,
            "invalid snapshot magic");
    const auto version = read<uint64_t>(input);
    const auto dim = read<uint64_t>(input);
    const auto count = read<uint64_t>(input);
    const auto payload = read<uint64_t>(input);
    const auto representation = read<uint64_t>(input);
    require(version == 2 and representation == 2, "route probe requires an FP32 graph snapshot");
    require(count > 0 and dim > 0 and dim <= 4096 and payload + 48 == available,
            "invalid snapshot layout");
    const auto degree = read<uint64_t>(input);
    const auto ef_search = read<uint64_t>(input);
    require(degree > 0 and degree <= 64 and ef_search > 0, "invalid graph options");

    GraphSnapshot graph;
    graph.dim = dim;
    graph.max_degree = degree;
    graph.ef_search = ef_search;
    graph.ids.resize(count);
    graph.vectors.resize(count * dim);
    graph.links.reserve(count);
    for (uint64_t slot = 0; slot < count; ++slot) {
        graph.ids[slot] = static_cast<int64_t>(read<uint64_t>(input));
        require(graph.slots.emplace(graph.ids[slot], slot).second, "duplicate snapshot ID");
    }
    input.read(reinterpret_cast<char*>(graph.vectors.data()),
               static_cast<std::streamsize>(graph.vectors.size() * sizeof(float)));
    require(static_cast<bool>(input), "truncated snapshot vectors");
    for (const float value : graph.vectors) {
        require(std::isfinite(value), "non-finite snapshot vector");
    }
    for (uint64_t slot = 0; slot < count; ++slot) {
        const auto size = read<uint64_t>(input);
        require(size <= degree, "invalid link count");
        std::vector<uint64_t> row(size);
        input.read(reinterpret_cast<char*>(row.data()),
                   static_cast<std::streamsize>(row.size() * sizeof(uint64_t)));
        require(static_cast<bool>(input), "truncated snapshot links");
        std::unordered_set<uint64_t> unique;
        for (const uint64_t neighbor : row) {
            require(neighbor < count and neighbor != slot and unique.insert(neighbor).second,
                    "invalid snapshot neighbor");
        }
        graph.links.push_back(std::move(row));
    }
    require(static_cast<uint64_t>(input.tellg()) == available, "snapshot trailing bytes");
    return graph;
}

float
distance(const GraphSnapshot& graph, const float* query, uint64_t slot) {
    const float* vector = graph.vectors.data() + slot * graph.dim;
    float result = 0.0F;
    for (uint64_t i = 0; i < graph.dim; ++i) {
        const float delta = query[i] - vector[i];
        result += delta * delta;
    }
    return result;
}

std::vector<uint64_t>
select_entries(const GraphSnapshot& graph, const std::string& mode) {
    constexpr uint64_t k_entry_points = 8;
    if (mode == "uniform" or mode == "greedy") {
        std::vector<uint64_t> entries{0};
        const uint64_t last = graph.ids.size() - 1;
        if (last != 0) {
            entries.push_back(last);
        }
        constexpr uint64_t k_extra_entry_points = k_entry_points - 2;
        for (uint64_t i = 1; i <= k_extra_entry_points; ++i) {
            const uint64_t entry = i * last / (k_extra_entry_points + 1);
            if (entry != 0 and entry != last) {
                entries.push_back(entry);
            }
        }
        return entries;
    }
    require(mode == "in_degree", "ENTRY_MODE must be uniform, in_degree, or greedy");
    std::vector<uint64_t> in_degree(graph.ids.size(), 0);
    for (const auto& neighbors : graph.links) {
        for (const uint64_t neighbor : neighbors) {
            ++in_degree[neighbor];
        }
    }
    std::vector<uint64_t> entries(graph.ids.size());
    std::iota(entries.begin(), entries.end(), 0);
    const auto count = std::min<uint64_t>(k_entry_points, entries.size());
    std::partial_sort(entries.begin(),
                      entries.begin() + static_cast<std::ptrdiff_t>(count),
                      entries.end(),
                      [&in_degree](uint64_t left, uint64_t right) {
                          return in_degree[left] > in_degree[right] or
                                 (in_degree[left] == in_degree[right] and left < right);
                      });
    entries.resize(count);
    return entries;
}

void
repair_incoming(GraphSnapshot& graph) {
    std::vector<uint64_t> incoming(graph.links.size(), 0);
    for (const auto& row : graph.links) {
        for (const uint64_t target : row) {
            ++incoming[target];
        }
    }
    for (uint64_t target = 0; target < graph.links.size(); ++target) {
        if (incoming[target] != 0) {
            continue;
        }
        bool appended = false;
        for (const uint64_t source : graph.links[target]) {
            if (graph.links[source].size() < graph.max_degree) {
                graph.links[source].push_back(target);
                ++incoming[target];
                appended = true;
                break;
            }
        }
        if (appended) {
            continue;
        }
        // Follow GraphBackend::ensure_incoming: never remove a sole incoming edge.
        uint64_t selected_source = graph.links.size();
        uint64_t selected_edge = 0;
        float farthest = -1.0F;
        for (const uint64_t source : graph.links[target]) {
            for (uint64_t edge = 0; edge < graph.links[source].size(); ++edge) {
                const uint64_t displaced = graph.links[source][edge];
                if (incoming[displaced] <= 1) {
                    continue;
                }
                const float value =
                    distance(graph, graph.vectors.data() + source * graph.dim, displaced);
                if (selected_source == graph.links.size() or value > farthest) {
                    selected_source = source;
                    selected_edge = edge;
                    farthest = value;
                }
            }
        }
        if (selected_source != graph.links.size()) {
            auto& displaced = graph.links[selected_source][selected_edge];
            --incoming[displaced];
            displaced = target;
            ++incoming[target];
        }
    }
}

void
append_reverse_edges(GraphSnapshot& graph) {
    // Snapshot the candidate edges: additions must not change iteration order.
    const auto original = graph.links;
    for (uint64_t source = 0; source < original.size(); ++source) {
        for (const uint64_t target : original[source]) {
            auto& neighbors = graph.links[target];
            if (neighbors.size() < graph.max_degree and
                std::find(neighbors.begin(), neighbors.end(), source) == neighbors.end()) {
                neighbors.push_back(source);
            }
        }
    }
}

void
apply_neighbor_mode(GraphSnapshot& graph, const std::string& mode) {
    if (mode == "preserve") {
        return;
    }
    require(
        mode == "diverse" or mode == "symmetric" or mode == "diverse_repair" or
            mode == "diverse_reverse",
        "NEIGHBOR_MODE must be preserve, symmetric, diverse, diverse_repair, or diverse_reverse");
    std::vector<std::vector<uint64_t>> incoming(graph.ids.size());
    for (uint64_t source = 0; source < graph.links.size(); ++source) {
        for (const uint64_t target : graph.links[source]) {
            incoming[target].push_back(source);
        }
    }
    std::vector<std::vector<uint64_t>> diversified(graph.ids.size());
    for (uint64_t source = 0; source < graph.links.size(); ++source) {
        std::vector<uint64_t> candidates = graph.links[source];
        candidates.insert(candidates.end(), incoming[source].begin(), incoming[source].end());
        std::sort(candidates.begin(), candidates.end());
        candidates.erase(std::unique(candidates.begin(), candidates.end()), candidates.end());
        candidates.erase(std::remove(candidates.begin(), candidates.end(), source),
                         candidates.end());
        std::vector<Candidate> ranked;
        ranked.reserve(candidates.size());
        for (const uint64_t candidate : candidates) {
            ranked.push_back(
                {candidate, distance(graph, graph.vectors.data() + source * graph.dim, candidate)});
        }
        std::sort(ranked.begin(), ranked.end(), closer);
        auto& selected = diversified[source];
        selected.reserve(std::min<uint64_t>(graph.max_degree, ranked.size()));
        if (mode == "symmetric") {
            for (uint64_t i = 0; i < std::min<uint64_t>(graph.max_degree, ranked.size()); ++i) {
                selected.push_back(ranked[i].slot);
            }
            continue;
        }
        for (const Candidate& candidate : ranked) {
            bool good = true;
            for (const uint64_t previous : selected) {
                if (distance(graph, graph.vectors.data() + previous * graph.dim, candidate.slot) <
                    candidate.distance) {
                    good = false;
                    break;
                }
            }
            if (good) {
                selected.push_back(candidate.slot);
                if (selected.size() == graph.max_degree) {
                    break;
                }
            }
        }
    }
    graph.links = std::move(diversified);
    if (mode == "diverse_repair" or mode == "diverse_reverse") {
        repair_incoming(graph);
    }
    if (mode == "diverse_reverse") {
        append_reverse_edges(graph);
    }
}

double
mean_degree(const GraphSnapshot& graph) {
    uint64_t edges = 0;
    for (const auto& neighbors : graph.links) {
        edges += neighbors.size();
    }
    return static_cast<double>(edges) / static_cast<double>(graph.links.size());
}

struct TopologyStats {
    uint64_t zero_out{};
    uint64_t zero_in{};
    uint64_t reachable{};
    uint64_t reverse_reachable{};
    uint64_t weak_components{};
    uint64_t largest_weak_component{};
};

TopologyStats
topology_stats(const GraphSnapshot& graph) {
    TopologyStats stats;
    std::vector<std::vector<uint64_t>> reverse(graph.links.size());
    std::vector<uint64_t> incoming(graph.links.size(), 0);
    for (uint64_t source = 0; source < graph.links.size(); ++source) {
        const auto& neighbors = graph.links[source];
        require(neighbors.size() <= graph.max_degree, "transformed degree exceeds limit");
        stats.zero_out += static_cast<uint64_t>(neighbors.empty());
        std::unordered_set<uint64_t> unique;
        for (const uint64_t neighbor : neighbors) {
            require(neighbor < graph.links.size() and neighbor != source and
                        unique.insert(neighbor).second,
                    "invalid transformed edge");
            ++incoming[neighbor];
            reverse[neighbor].push_back(source);
        }
    }
    stats.zero_in = static_cast<uint64_t>(std::count(incoming.begin(), incoming.end(), 0));
    if (graph.links.empty()) {
        return stats;
    }
    std::vector<uint8_t> visited(graph.links.size(), 0);
    std::vector<uint64_t> pending{0};
    visited[0] = 1;
    for (uint64_t i = 0; i < pending.size(); ++i) {
        for (const uint64_t neighbor : graph.links[pending[i]]) {
            if (visited[neighbor] == 0) {
                visited[neighbor] = 1;
                pending.push_back(neighbor);
            }
        }
    }
    stats.reachable = pending.size();
    std::fill(visited.begin(), visited.end(), 0);
    pending = {0};
    visited[0] = 1;
    for (uint64_t i = 0; i < pending.size(); ++i) {
        for (const uint64_t neighbor : reverse[pending[i]]) {
            if (visited[neighbor] == 0) {
                visited[neighbor] = 1;
                pending.push_back(neighbor);
            }
        }
    }
    stats.reverse_reachable = pending.size();
    std::fill(visited.begin(), visited.end(), 0);
    for (uint64_t seed = 0; seed < graph.links.size(); ++seed) {
        if (visited[seed] != 0) {
            continue;
        }
        ++stats.weak_components;
        pending = {seed};
        visited[seed] = 1;
        for (uint64_t i = 0; i < pending.size(); ++i) {
            const uint64_t source = pending[i];
            const auto visit = [&](const std::vector<uint64_t>& neighbors) {
                for (const uint64_t neighbor : neighbors) {
                    if (visited[neighbor] == 0) {
                        visited[neighbor] = 1;
                        pending.push_back(neighbor);
                    }
                }
            };
            visit(graph.links[source]);
            visit(reverse[source]);
        }
        stats.largest_weak_component =
            std::max<uint64_t>(stats.largest_weak_component, pending.size());
    }
    return stats;
}

struct SearchTrace {
    std::vector<Candidate> result;
    std::vector<uint8_t> visited;
    uint64_t expanded{};
    uint64_t route_nodes{};
    uint64_t distance_evaluations{};
    bool early_stop{};
};

SearchTrace
search(const GraphSnapshot& graph,
       const std::vector<uint64_t>& entries,
       const std::string& entry_mode,
       const float* query,
       uint64_t k) {
    k = std::min<uint64_t>(k, graph.ids.size());
    SearchTrace trace;
    trace.visited.resize(graph.ids.size(), 0);
    if (k == 0) {
        return trace;
    }
    std::vector<uint64_t> active_entries = entries;
    std::vector<uint8_t> route_visited(graph.ids.size(), 0);
    if (entry_mode == "greedy") {
        std::vector<float> route_distances(graph.ids.size(), 0.0F);
        auto route_score = [&](uint64_t slot) {
            if (route_visited[slot] == 0) {
                route_visited[slot] = 1;
                route_distances[slot] = distance(graph, query, slot);
                ++trace.distance_evaluations;
            }
            return Candidate{slot, route_distances[slot]};
        };
        Candidate current = route_score(entries.front());
        for (const uint64_t entry : entries) {
            const Candidate candidate = route_score(entry);
            if (closer(candidate, current)) {
                current = candidate;
            }
        }
        while (true) {
            Candidate next = current;
            auto consider = [&](uint64_t slot) {
                const Candidate candidate = route_score(slot);
                if (closer(candidate, next)) {
                    next = candidate;
                }
            };
            if (graph.ids.size() > 1) {
                consider((current.slot + graph.ids.size() - 1) % graph.ids.size());
                consider((current.slot + 1) % graph.ids.size());
            }
            for (const uint64_t neighbor : graph.links[current.slot]) {
                consider(neighbor);
            }
            if (next.slot == current.slot) {
                break;
            }
            current = next;
        }
        active_entries.assign(1, current.slot);
        trace.route_nodes =
            static_cast<uint64_t>(std::count(route_visited.begin(), route_visited.end(), 1));
    }
    const uint64_t ef = std::min<uint64_t>(graph.ids.size(), std::max(k, graph.ef_search));
    std::priority_queue<Candidate, std::vector<Candidate>, decltype(&closer)> best(&closer);
    std::priority_queue<Candidate, std::vector<Candidate>, decltype(&farther)> candidates(&farther);
    auto visit = [&](uint64_t slot) {
        if (trace.visited[slot] != 0) {
            return;
        }
        trace.visited[slot] = 1;
        ++trace.distance_evaluations;
        const Candidate next{slot, distance(graph, query, slot)};
        candidates.push(next);
        best.push(next);
        if (best.size() > ef) {
            best.pop();
        }
    };

    for (const uint64_t entry : active_entries) {
        visit(entry);
    }
    while (not candidates.empty()) {
        const Candidate current = candidates.top();
        candidates.pop();
        if (best.size() == ef and closer(best.top(), current)) {
            trace.early_stop = true;
            break;
        }
        ++trace.expanded;
        if (graph.ids.size() > 1) {
            visit((current.slot + graph.ids.size() - 1) % graph.ids.size());
            visit((current.slot + 1) % graph.ids.size());
        }
        for (const uint64_t neighbor : graph.links[current.slot]) {
            visit(neighbor);
        }
    }
    trace.result.resize(best.size());
    for (uint64_t i = trace.result.size(); i > 0; --i) {
        trace.result[i - 1] = best.top();
        best.pop();
    }
    trace.result.resize(std::min<uint64_t>(k, trace.result.size()));
    for (uint64_t slot = 0; slot < route_visited.size(); ++slot) {
        if (route_visited[slot] != 0) {
            trace.visited[slot] = 1;
        }
    }
    return trace;
}

int
run(const std::string& snapshot,
    const std::string& directory,
    const std::string& output_path,
    uint64_t ef_search,
    const std::string& entry_mode,
    const std::string& neighbor_mode) {
    require(not std::filesystem::exists(output_path), "output path already exists");
    GraphSnapshot graph = load_snapshot(snapshot);
    if (ef_search != 0) {
        graph.ef_search = ef_search;
    }
    apply_neighbor_mode(graph, neighbor_mode);
    const auto topology = topology_stats(graph);
    const auto entries = select_entries(graph, entry_mode);
    const auto queries =
        read_records<float>(directory + "/queries.fvecs", static_cast<int32_t>(graph.dim));
    std::ifstream truth_input(directory + "/groundtruth.ivecs", std::ios::binary);
    require(static_cast<bool>(truth_input), "groundtruth open failed");
    const int32_t k = read_dim(truth_input);
    truth_input.close();
    const auto truth = read_records<int32_t>(directory + "/groundtruth.ivecs", k);
    require(queries.size() == truth.size(), "query and truth count differ");

    std::ofstream output(output_path);
    require(static_cast<bool>(output), "output open failed");
    output << "query,hits,truth_visited,truth_not_visited,visited_not_returned,"
              "visited_nodes,expanded_nodes,route_nodes,distance_evaluations,early_stop\n";
    uint64_t total_hits = 0;
    uint64_t total_truth_visited = 0;
    uint64_t total_visited = 0;
    uint64_t total_expanded = 0;
    uint64_t total_route_nodes = 0;
    uint64_t total_distance_evaluations = 0;
    for (uint64_t i = 0; i < queries.size(); ++i) {
        const SearchTrace trace =
            search(graph, entries, entry_mode, queries[i].data(), static_cast<uint64_t>(k));
        std::unordered_set<int64_t> expected(truth[i].begin(), truth[i].end());
        uint64_t hits = 0;
        for (const Candidate& candidate : trace.result) {
            hits += expected.count(graph.ids[candidate.slot]);
        }
        uint64_t truth_visited = 0;
        for (const int32_t id : truth[i]) {
            const auto found = graph.slots.find(id);
            require(found != graph.slots.end(), "truth ID missing from snapshot");
            truth_visited += static_cast<uint64_t>(trace.visited[found->second] != 0);
        }
        const auto visited_nodes =
            static_cast<uint64_t>(std::count(trace.visited.begin(), trace.visited.end(), 1));
        total_hits += hits;
        total_truth_visited += truth_visited;
        total_visited += visited_nodes;
        total_expanded += trace.expanded;
        total_route_nodes += trace.route_nodes;
        total_distance_evaluations += trace.distance_evaluations;
        output << i << ',' << hits << ',' << truth_visited << ',' << k - truth_visited << ','
               << truth_visited - hits << ',' << visited_nodes << ',' << trace.expanded << ','
               << trace.route_nodes << ',' << trace.distance_evaluations << ',' << trace.early_stop
               << '\n';
    }
    require(static_cast<bool>(output), "output write failed");
    std::cout << "query_count,k,recall_at_k,truth_visit_rate,mean_visited_nodes,"
                 "mean_expanded_nodes,mean_route_nodes,mean_distance_evaluations,mean_graph_degree,"
                 "zero_out,zero_in,edge_reachable_from_zero,reverse_reachable_from_zero,weak_"
                 "components,largest_weak_component\n";
    std::cout << queries.size() << ',' << k << ',' << std::fixed << std::setprecision(6)
              << static_cast<double>(total_hits) / static_cast<double>(queries.size() * k) << ','
              << static_cast<double>(total_truth_visited) / static_cast<double>(queries.size() * k)
              << ',' << static_cast<double>(total_visited) / static_cast<double>(queries.size())
              << ',' << static_cast<double>(total_expanded) / static_cast<double>(queries.size())
              << ',' << static_cast<double>(total_route_nodes) / static_cast<double>(queries.size())
              << ','
              << static_cast<double>(total_distance_evaluations) /
                     static_cast<double>(queries.size())
              << ',' << mean_degree(graph) << ',' << topology.zero_out << ',' << topology.zero_in
              << ',' << topology.reachable << ',' << topology.reverse_reachable << ','
              << topology.weak_components << ',' << topology.largest_weak_component << '\n';
    return 0;
}

}  // namespace

int
main(int argc, char** argv) {
    try {
        require(argc >= 4 and argc <= 7,
                "usage: lite_graph_route_probe SNAPSHOT DATASET OUTPUT "
                "[EF_SEARCH [ENTRY_MODE [NEIGHBOR_MODE]]]");
        const uint64_t ef_search = argc >= 5 ? std::stoull(argv[4]) : 0;
        require(argc == 4 or ef_search > 0, "EF_SEARCH must be positive");
        const std::string entry_mode = argc >= 6 ? argv[5] : "uniform";
        const std::string neighbor_mode = argc == 7 ? argv[6] : "preserve";
        return run(argv[1], argv[2], argv[3], ef_search, entry_mode, neighbor_mode);
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
