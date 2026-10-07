// Copyright 2024-present the vsag project
// SPDX-License-Identifier: Apache-2.0

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <numeric>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <vector>

#include "lite/backend.h"

namespace {

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
    require(version == 2 and representation == 2, "mutation trace requires an FP32 graph snapshot");
    require(count > 0 and dim > 0 and dim <= 4096 and available >= 48 and
                payload == available - 48 and payload >= 16 and
                count <= (payload - 16) / (16 + dim * sizeof(float)),
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
using Edge = std::pair<int64_t, int64_t>;
std::vector<Edge>
edge_set(const vsag::lite::detail::Backend& graph, int64_t excluded) {
    std::vector<Edge> edges;
    for (uint64_t slot = 0; slot < graph.Size(); ++slot) {
        const auto source = graph.IdAt(slot);
        if (source == excluded) {
            continue;
        }
        for (uint64_t edge = 0; edge < graph.LinkCountAt(slot); ++edge) {
            const auto target = graph.IdAt(graph.LinkAt(slot, edge));
            if (target != excluded) {
                edges.emplace_back(source, target);
            }
        }
    }
    std::sort(edges.begin(), edges.end());
    require(std::adjacent_find(edges.begin(), edges.end()) == edges.end(), "duplicate edge");
    return edges;
}
uint64_t
common_edges(const std::vector<Edge>& left, const std::vector<Edge>& right) {
    uint64_t count = 0;
    auto a = left.begin();
    auto b = right.begin();
    while (a != left.end() and b != right.end()) {
        if (*a < *b) {
            ++a;
        } else if (*b < *a) {
            ++b;
        } else {
            ++count;
            ++a;
            ++b;
        }
    }
    return count;
}
uint64_t
score(const vsag::lite::detail::Backend& graph,
      const std::vector<std::vector<float>>& queries,
      const std::vector<std::vector<int32_t>>& truth,
      const std::vector<uint64_t>& selected,
      uint64_t k) {
    uint64_t hits = 0;
    for (const uint64_t query : selected) {
        const auto result = graph.Search(queries[query].data(), graph.Dim(), k);
        require(static_cast<bool>(result) and result->size() == k, "query failed");
        const std::unordered_set<int64_t> expected(truth[query].begin(), truth[query].end());
        for (const auto& neighbor : *result) {
            hits += expected.count(neighbor.id);
        }
    }
    return hits;
}
}  // namespace

int
main(int argc, char** argv) {
    try {
        require(argc == 3 or argc == 4,
                "usage: graph_mutation_trace INITIAL_FP32_SNAPSHOT DATASET [EVENT_CSV]");
        std::ofstream events;
        if (argc == 4) {
            require(not std::filesystem::exists(argv[3]), "event output already exists");
            events.open(argv[3]);
            require(events.good(), "event output open failed");
            events << "cycle,id,query,k,before_hits,remove_hits,add_hits\n";
        }
        auto source = load_snapshot(argv[1]);
        const auto ids = source.ids;
        const auto vectors = source.vectors;
        require(std::gcd(ids.size(), 8191ULL) == 1, "ID schedule is not a permutation");
        const uint64_t dim = source.dim;
        const auto queries =
            read_records<float>(std::string(argv[2]) + "/queries.fvecs", static_cast<int32_t>(dim));
        std::ifstream truth_file(std::string(argv[2]) + "/groundtruth.ivecs", std::ios::binary);
        require(static_cast<bool>(truth_file), "truth open failed");
        const auto k = read_dim(truth_file);
        const auto truth = read_records<int32_t>(std::string(argv[2]) + "/groundtruth.ivecs", k);
        require(not queries.empty() and queries.size() == truth.size() and
                    ids.size() > static_cast<uint64_t>(k),
                "invalid dataset shape");
        for (const auto& row : truth) {
            for (const int32_t id : row) {
                require(source.slots.count(id) != 0, "truth ID missing from initial snapshot");
            }
        }
        auto restored = vsag::lite::detail::restore_graph_backend(dim,
                                                                  source.max_degree,
                                                                  source.ef_search,
                                                                  std::move(source.ids),
                                                                  std::move(source.vectors),
                                                                  std::move(source.links));
        require(static_cast<bool>(restored), "restore failed");
        auto graph = std::move(*restored);
        std::cout << "cycle,id,common_queries,k,before_hits,remove_hits,add_hits,"
                     "before_edges,remove_edges,add_edges,remove_dropped,remove_added,"
                     "add_dropped,add_added\n";
        for (uint64_t cycle = 0; cycle < ids.size(); ++cycle) {
            const uint64_t original = cycle * 8191ULL % ids.size();
            const int64_t id = ids[original];
            const float* vector = vectors.data() + original * dim;
            require(static_cast<bool>(graph->Update(id, vector, dim)), "update failed");
            const bool checkpoint = cycle == 0 or cycle == 1 or cycle == 10 or cycle == 97 or
                                    cycle == 100 or cycle == 500 or cycle == 1000 or
                                    cycle == 2000 or cycle == 5000 or cycle + 1 == ids.size();
            std::vector<uint64_t> event_query;
            if (argc == 4) {
                for (uint64_t offset = 0; offset < queries.size(); ++offset) {
                    const uint64_t query = (cycle + offset) % queries.size();
                    if (std::find(truth[query].begin(), truth[query].end(), id) ==
                        truth[query].end()) {
                        event_query.push_back(query);
                        break;
                    }
                }
            }
            const auto event_before = score(*graph, queries, truth, event_query, k);
            std::vector<uint64_t> selected;
            std::vector<Edge> before;
            uint64_t before_hits = 0;
            if (checkpoint) {
                for (uint64_t query = 0; query < queries.size(); ++query) {
                    if (std::find(truth[query].begin(), truth[query].end(), id) ==
                        truth[query].end()) {
                        selected.push_back(query);
                    }
                }
                before = edge_set(*graph, id);
                before_hits = score(*graph, queries, truth, selected, static_cast<uint64_t>(k));
            }
            require(graph->Remove(id), "remove failed");
            require(graph->Size() + 1 == ids.size(), "remove count differs");
            const auto event_remove = score(*graph, queries, truth, event_query, k);
            std::vector<Edge> removed;
            uint64_t remove_hits = 0;
            if (checkpoint) {
                removed = edge_set(*graph, id);
                remove_hits = score(*graph, queries, truth, selected, static_cast<uint64_t>(k));
            }
            require(static_cast<bool>(graph->Add(id, vector, dim)), "add failed");
            require(graph->Size() == ids.size(), "add count differs");
            if (argc == 4) {
                const auto event_add = score(*graph, queries, truth, event_query, k);
                events << cycle << ',' << id << ',';
                if (event_query.empty()) {
                    events << -1;
                } else {
                    events << event_query.front();
                }
                events << ',' << k << ',' << event_before << ',' << event_remove << ',' << event_add
                       << '\n';
                require(events.good(), "event output write failed");
            }
            if (checkpoint) {
                const auto added = edge_set(*graph, id);
                const auto add_hits =
                    score(*graph, queries, truth, selected, static_cast<uint64_t>(k));
                const auto remove_common = common_edges(before, removed);
                const auto add_common = common_edges(removed, added);
                std::cout << cycle << ',' << id << ',' << selected.size() << ',' << k << ','
                          << before_hits << ',' << remove_hits << ',' << add_hits << ','
                          << before.size() << ',' << removed.size() << ',' << added.size() << ','
                          << before.size() - remove_common << ',' << removed.size() - remove_common
                          << ',' << removed.size() - add_common << ',' << added.size() - add_common
                          << '\n';
            }
        }
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
