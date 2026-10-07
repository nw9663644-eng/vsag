// Copyright 2024-present the vsag project
// SPDX-License-Identifier: Apache-2.0
#include <vsag/lite/index.h>

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <ctime>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <numeric>
#include <queue>
#include <sstream>
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

std::vector<int64_t>
zero_ids(const vsag::lite::detail::Backend& graph) {
    std::vector<int64_t> result;
    for (uint64_t slot = 0; slot < graph.Size(); ++slot) {
        if (graph.IncomingLinkCountAt(slot) == 0) {
            result.push_back(graph.IdAt(slot));
        }
    }
    std::sort(result.begin(), result.end());
    return result;
}
}  // namespace

int
main(int argc, char** argv) {
    try {
        require(argc == 2, "usage: phase_trace INITIAL_FP32_SNAPSHOT");
        auto source = load_snapshot(argv[1]);
        const auto ids = source.ids;
        const auto vectors = source.vectors;
        const uint64_t dim = source.dim;
        auto restored = vsag::lite::detail::restore_graph_backend(dim,
                                                                  source.max_degree,
                                                                  source.ef_search,
                                                                  std::move(source.ids),
                                                                  std::move(source.vectors),
                                                                  std::move(source.links));
        require(static_cast<bool>(restored), "restore failed");
        auto graph = std::move(*restored);
        std::cout << "cycle,id,phase,before_zero,after_zero,new_zero_id,old_"
                     "outgoing_target\n";
        for (uint64_t cycle = 0; cycle < ids.size(); ++cycle) {
            const uint64_t original = cycle * 8191ULL % ids.size();
            const int64_t id = ids[original];
            const float* vector = vectors.data() + original * dim;
            std::vector<int64_t> old_targets;
            for (uint64_t slot = 0; slot < graph->Size(); ++slot) {
                if (graph->IdAt(slot) == id) {
                    for (uint64_t edge = 0; edge < graph->LinkCountAt(slot); ++edge) {
                        old_targets.push_back(graph->IdAt(graph->LinkAt(slot, edge)));
                    }
                    break;
                }
            }
            for (const std::string phase : {"update", "remove", "add"}) {
                const auto before = zero_ids(*graph);
                if (phase == "update") {
                    require(static_cast<bool>(graph->Update(id, vector, dim)), "update failed");
                } else if (phase == "remove") {
                    require(graph->Remove(id), "remove failed");
                } else {
                    require(static_cast<bool>(graph->Add(id, vector, dim)), "add failed");
                }
                const auto after = zero_ids(*graph);
                std::vector<int64_t> introduced;
                std::set_difference(after.begin(),
                                    after.end(),
                                    before.begin(),
                                    before.end(),
                                    std::back_inserter(introduced));
                if (not introduced.empty()) {
                    for (const int64_t target : introduced) {
                        std::cout << cycle << ',' << id << ',' << phase << ',' << before.size()
                                  << ',' << after.size() << ',' << target << ','
                                  << (std::find(old_targets.begin(), old_targets.end(), target) !=
                                      old_targets.end())
                                  << '\n';
                    }
                    return 0;
                }
            }
        }
        std::cout << "no_new_zero_incoming\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
