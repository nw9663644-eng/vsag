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
    require(dim > 0 and dim <= 4096 and payload + 48 == available, "invalid snapshot layout");
    const auto degree = read<uint64_t>(input);
    const auto ef_search = read<uint64_t>(input);
    require(degree > 0 and degree <= 64 and ef_search > 0, "invalid graph options");

    GraphSnapshot graph;
    graph.dim = dim;
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

struct SearchTrace {
    std::vector<Candidate> result;
    std::vector<uint8_t> visited;
    uint64_t expanded{};
    bool early_stop{};
};

SearchTrace
search(const GraphSnapshot& graph, const float* query, uint64_t k) {
    k = std::min<uint64_t>(k, graph.ids.size());
    SearchTrace trace;
    trace.visited.resize(graph.ids.size(), 0);
    if (k == 0) {
        return trace;
    }
    const uint64_t ef = std::min<uint64_t>(graph.ids.size(), std::max(k, graph.ef_search));
    std::priority_queue<Candidate, std::vector<Candidate>, decltype(&closer)> best(&closer);
    std::priority_queue<Candidate, std::vector<Candidate>, decltype(&farther)> candidates(&farther);
    auto visit = [&](uint64_t slot) {
        if (trace.visited[slot] != 0) {
            return;
        }
        trace.visited[slot] = 1;
        const Candidate next{slot, distance(graph, query, slot)};
        candidates.push(next);
        best.push(next);
        if (best.size() > ef) {
            best.pop();
        }
    };

    visit(0);
    const uint64_t last = graph.ids.size() - 1;
    if (last != 0) {
        visit(last);
    }
    constexpr uint64_t k_extra_entry_points = 6;
    for (uint64_t i = 1; i <= k_extra_entry_points; ++i) {
        const uint64_t entry = i * last / (k_extra_entry_points + 1);
        if (entry != 0 and entry != last) {
            visit(entry);
        }
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
    return trace;
}

int
run(const std::string& snapshot,
    const std::string& directory,
    const std::string& output_path,
    uint64_t ef_search) {
    require(not std::filesystem::exists(output_path), "output path already exists");
    GraphSnapshot graph = load_snapshot(snapshot);
    if (ef_search != 0) {
        graph.ef_search = ef_search;
    }
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
              "visited_nodes,expanded_nodes,early_stop\n";
    uint64_t total_hits = 0;
    uint64_t total_truth_visited = 0;
    uint64_t total_visited = 0;
    uint64_t total_expanded = 0;
    for (uint64_t i = 0; i < queries.size(); ++i) {
        const SearchTrace trace = search(graph, queries[i].data(), static_cast<uint64_t>(k));
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
        output << i << ',' << hits << ',' << truth_visited << ',' << k - truth_visited << ','
               << truth_visited - hits << ',' << visited_nodes << ',' << trace.expanded << ','
               << trace.early_stop << '\n';
    }
    require(static_cast<bool>(output), "output write failed");
    std::cout << "query_count,k,recall_at_k,truth_visit_rate,mean_visited_nodes,"
                 "mean_expanded_nodes\n";
    std::cout << queries.size() << ',' << k << ',' << std::fixed << std::setprecision(6)
              << static_cast<double>(total_hits) / static_cast<double>(queries.size() * k) << ','
              << static_cast<double>(total_truth_visited) / static_cast<double>(queries.size() * k)
              << ',' << static_cast<double>(total_visited) / static_cast<double>(queries.size())
              << ',' << static_cast<double>(total_expanded) / static_cast<double>(queries.size())
              << '\n';
    return 0;
}

}  // namespace

int
main(int argc, char** argv) {
    try {
        require(argc == 4 or argc == 5,
                "usage: lite_graph_route_probe SNAPSHOT DATASET OUTPUT [EF_SEARCH]");
        const uint64_t ef_search = argc == 5 ? std::stoull(argv[4]) : 0;
        require(argc == 4 or ef_search > 0, "EF_SEARCH must be positive");
        return run(argv[1], argv[2], argv[3], ef_search);
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
