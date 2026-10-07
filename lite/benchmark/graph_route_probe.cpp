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
replace_redundant_reverse_edges(GraphSnapshot& graph) {
    const auto original = graph.links;
    for (uint64_t source = 0; source < original.size(); ++source) {
        for (const uint64_t target : original[source]) {
            auto& neighbors = graph.links[target];
            if (std::find(neighbors.begin(), neighbors.end(), source) != neighbors.end()) {
                continue;
            }
            if (neighbors.size() < graph.max_degree) {
                neighbors.push_back(source);
                continue;
            }
            uint64_t selected = neighbors.size();
            float farthest = -1.0F;
            for (uint64_t edge = 0; edge < neighbors.size(); ++edge) {
                const uint64_t displaced = neighbors[edge];
                bool alternate = false;
                for (const uint64_t via : neighbors) {
                    if (via != displaced and
                        std::find(graph.links[via].begin(), graph.links[via].end(), displaced) !=
                            graph.links[via].end()) {
                        alternate = true;
                        break;
                    }
                }
                if (alternate) {
                    const float value =
                        distance(graph, graph.vectors.data() + target * graph.dim, displaced);
                    if (selected == neighbors.size() or value > farthest) {
                        selected = edge;
                        farthest = value;
                    }
                }
            }
            // Recheck against the current graph for every replacement. The two-hop
            // witness excludes the removed edge, preserving existing reachability.
            if (selected != neighbors.size()) {
                neighbors[selected] = source;
            }
        }
    }
}

void
test_reverse_replacement() {
    GraphSnapshot graph;
    graph.dim = 1;
    graph.max_degree = 2;
    graph.ids = {0, 1, 2, 3};
    graph.vectors = {0, 1, 2, 3};
    graph.links = {{1, 2}, {2}, {0}, {0}};
    const auto reachable = [](const GraphSnapshot& value, uint64_t seed) {
        std::vector<uint8_t> seen(value.links.size(), 0);
        std::vector<uint64_t> pending{seed};
        seen[seed] = 1;
        for (uint64_t i = 0; i < pending.size(); ++i) {
            for (const uint64_t next : value.links[pending[i]]) {
                if (seen[next] == 0) {
                    seen[next] = 1;
                    pending.push_back(next);
                }
            }
        }
        return seen;
    };
    const GraphSnapshot before = graph;
    replace_redundant_reverse_edges(graph);
    require(graph.links[0] == std::vector<uint64_t>({1, 3}), "expected redundant edge replacement");
    for (uint64_t source = 0; source < graph.links.size(); ++source) {
        const auto old_reachable = reachable(before, source);
        const auto new_reachable = reachable(graph, source);
        require(graph.links[source].size() <= graph.max_degree, "replacement exceeds degree");
        for (uint64_t target = 0; target < graph.links.size(); ++target) {
            require(old_reachable[target] == 0 or new_reachable[target] != 0,
                    "replacement lost existing reachability");
        }
    }
    graph.max_degree = 1;
    graph.links = {{1}, {0}, {0}, {2}};
    const auto saturated = graph.links;
    replace_redundant_reverse_edges(graph);
    require(graph.links == saturated, "replacement removed an edge without a witness");
}

void
apply_neighbor_mode(GraphSnapshot& graph, const std::string& mode) {
    if (mode == "preserve") {
        return;
    }
    require(mode == "diverse" or mode == "symmetric" or mode == "diverse_repair" or
                mode == "diverse_reverse" or mode == "diverse_reverse_safe",
            "NEIGHBOR_MODE must be preserve, symmetric, diverse, diverse_repair, diverse_reverse, "
            "or diverse_reverse_safe");
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
    if (mode == "diverse_repair" or mode == "diverse_reverse" or mode == "diverse_reverse_safe") {
        repair_incoming(graph);
    }
    if (mode == "diverse_reverse" or mode == "diverse_reverse_safe") {
        append_reverse_edges(graph);
    }
    if (mode == "diverse_reverse_safe") {
        replace_redundant_reverse_edges(graph);
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
    uint64_t tie_comparisons{};
};

// Diagnostic overrides only: production routing remains in GraphBackend.
struct SlotRouting {
    std::vector<uint64_t> previous;
    std::vector<uint64_t> next;
    std::vector<uint64_t> tie_rank;
    bool restore_ring{};
    bool restore_ties{};
};

SearchTrace
search(const GraphSnapshot& graph,
       const std::vector<uint64_t>& entries,
       const std::string& entry_mode,
       const float* query,
       uint64_t k,
       const SlotRouting* routing = nullptr) {
    require(routing == nullptr or
                (entry_mode == "uniform" and routing->previous.size() == graph.ids.size() and
                 routing->next.size() == graph.ids.size() and
                 routing->tie_rank.size() == graph.ids.size()),
            "invalid slot routing override");
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
    const auto candidate_closer = [&](const Candidate& left, const Candidate& right) {
        if (left.distance == right.distance and left.slot != right.slot) {
            ++trace.tie_comparisons;
            if (routing != nullptr and routing->restore_ties) {
                return routing->tie_rank[left.slot] < routing->tie_rank[right.slot];
            }
        }
        return closer(left, right);
    };
    const auto candidate_farther = [&](const Candidate& left, const Candidate& right) {
        if (left.distance == right.distance and left.slot != right.slot) {
            ++trace.tie_comparisons;
            if (routing != nullptr and routing->restore_ties) {
                return routing->tie_rank[left.slot] > routing->tie_rank[right.slot];
            }
        }
        return farther(left, right);
    };
    std::priority_queue<Candidate, std::vector<Candidate>, decltype(candidate_closer)> best(
        candidate_closer);
    std::priority_queue<Candidate, std::vector<Candidate>, decltype(candidate_farther)> candidates(
        candidate_farther);
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
        if (best.size() == ef and candidate_closer(best.top(), current)) {
            trace.early_stop = true;
            break;
        }
        ++trace.expanded;
        if (graph.ids.size() > 1) {
            if (routing != nullptr and routing->restore_ring) {
                visit(routing->previous[current.slot]);
                visit(routing->next[current.slot]);
            } else {
                visit((current.slot + graph.ids.size() - 1) % graph.ids.size());
                visit((current.slot + 1) % graph.ids.size());
            }
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

void
measure_crud(vsag::lite::Index& index,
             const GraphSnapshot& graph,
             const std::vector<std::vector<float>>& queries,
             const std::vector<std::vector<int32_t>>& truth,
             uint64_t cycles,
             uint64_t query_budget,
             uint64_t query_every,
             const std::string& path) {
    using Clock = std::chrono::steady_clock;
    std::vector<std::vector<double>> times(4);
    std::vector<double> mixed_latencies;
    uint64_t mixed_hits = 0;
    double mutation_cpu_ms = 0;
    double query_cpu_ms = 0;
    const uint64_t k = truth.front().size();
    const auto timed = [&](uint64_t operation, const auto& action) {
        const auto start = Clock::now();
        require(action(), "API CRUD operation failed");
        const auto end = Clock::now();
        times[operation].push_back(std::chrono::duration<double, std::micro>(end - start).count());
    };
    const auto cpu_start = std::clock();
    for (uint64_t i = 0; i < cycles; ++i) {
        const auto mutation_start = std::clock();
        const uint64_t slot = (i * 8191ULL) % graph.ids.size();
        const int64_t id = graph.ids[slot];
        const float* original = graph.vectors.data() + slot * graph.dim;
        std::vector<float> changed(original, original + graph.dim);
        changed[0] += 0.125F;
        timed(0, [&] { return static_cast<bool>(index.Update(id, changed.data(), graph.dim)); });
        timed(1, [&] { return static_cast<bool>(index.Update(id, original, graph.dim)); });
        timed(2, [&] { return index.Remove(id); });
        timed(3, [&] { return static_cast<bool>(index.Add(id, original, graph.dim)); });
        require(index.Size() == graph.ids.size(), "API CRUD changed live count");
        mutation_cpu_ms +=
            1000.0 * static_cast<double>(std::clock() - mutation_start) / CLOCKS_PER_SEC;
        if (query_every != 0 and (i + 1) % query_every == 0) {
            const uint64_t query = mixed_latencies.size() % queries.size();
            const auto query_start = std::clock();
            const auto start = Clock::now();
            auto result =
                index.SearchWithOptions(queries[query].data(), graph.dim, k, {query_budget});
            const auto end = Clock::now();
            query_cpu_ms +=
                1000.0 * static_cast<double>(std::clock() - query_start) / CLOCKS_PER_SEC;
            require(static_cast<bool>(result) and result->size() == k, "API mixed search failed");
            mixed_latencies.push_back(
                std::chrono::duration<double, std::micro>(end - start).count());
            std::unordered_set<int64_t> expected(truth[query].begin(), truth[query].end());
            for (const auto& neighbor : *result) {
                mixed_hits += expected.count(neighbor.id);
            }
        }
    }
    const double cpu_ms = 1000.0 * static_cast<double>(std::clock() - cpu_start) / CLOCKS_PER_SEC;
    uint64_t hits = 0;
    std::vector<std::vector<vsag::lite::Neighbor>> results;
    for (uint64_t i = 0; i < queries.size(); ++i) {
        auto result = index.SearchWithOptions(queries[i].data(), graph.dim, k, {query_budget});
        require(static_cast<bool>(result) and result->size() == k, "API post-CRUD search failed");
        std::unordered_set<int64_t> expected(truth[i].begin(), truth[i].end());
        for (const auto& neighbor : *result) {
            hits += expected.count(neighbor.id);
        }
        results.push_back(std::move(*result));
    }
    std::stringstream saved(std::ios::in | std::ios::out | std::ios::binary);
    auto start = Clock::now();
    require(static_cast<bool>(index.Save(saved)), "API post-CRUD save failed");
    const auto save_ms = std::chrono::duration<double, std::milli>(Clock::now() - start).count();
    const auto snapshot_bytes = static_cast<uint64_t>(saved.tellp());
    saved.seekg(0);
    start = Clock::now();
    auto reloaded = vsag::lite::Index::Load(saved);
    const auto reload_ms = std::chrono::duration<double, std::milli>(Clock::now() - start).count();
    require(static_cast<bool>(reloaded) and (*reloaded)->Size() == index.Size(),
            "API post-CRUD reload failed");
    for (uint64_t i = 0; i < queries.size(); ++i) {
        auto after =
            (*reloaded)->SearchWithOptions(queries[i].data(), graph.dim, k, {query_budget});
        require(static_cast<bool>(after) and after->size() == results[i].size(),
                "API post-CRUD reload search failed");
        for (uint64_t j = 0; j < after->size(); ++j) {
            require((*after)[j].id == results[i][j].id and
                        (*after)[j].distance == results[i][j].distance,
                    "API post-CRUD reload changed result");
        }
    }
    std::ofstream samples(path + ".samples.csv");
    samples << "cycle,update_changed_us,restore_us,remove_us,readd_us\n";
    for (uint64_t i = 0; i < cycles; ++i) {
        samples << i;
        for (const auto& values : times) {
            samples << ',' << std::fixed << std::setprecision(6) << values[i];
        }
        samples << '\n';
    }
    samples.close();
    require(static_cast<bool>(samples), "API CRUD samples write failed");
    std::ofstream mixed_output(path + ".mixed.csv");
    mixed_output << "query_event,query,latency_us\n";
    for (uint64_t i = 0; i < mixed_latencies.size(); ++i) {
        mixed_output << i << ',' << i % queries.size() << ',' << std::fixed << std::setprecision(6)
                     << mixed_latencies[i] << '\n';
    }
    mixed_output.close();
    require(static_cast<bool>(mixed_output), "API mixed samples write failed");
    const auto mixed_percentile = [&](double fraction) {
        if (mixed_latencies.empty()) {
            return 0.0;
        }
        auto sorted = mixed_latencies;
        std::sort(sorted.begin(), sorted.end());
        return sorted[static_cast<uint64_t>(
                          std::ceil(fraction * static_cast<double>(sorted.size()))) -
                      1];
    };
    std::ofstream output(path);
    output << "cycles,recall_at_k,crud_loop_cpu_ms,update_changed_p50_us,restore_p50_us,"
              "remove_p50_us,readd_p50_us,save_ms,reload_ms,snapshot_bytes,query_every,mixed_"
              "queries,mixed_recall_at_k,mixed_search_p50_us,mixed_search_p99_us,mixed_query_cpu_"
              "ms,mixed_loop_cpu_ms\n";
    output << cycles << ',' << std::fixed << std::setprecision(6)
           << static_cast<double>(hits) / static_cast<double>(queries.size() * k) << ','
           << (query_every == 0 ? cpu_ms : mutation_cpu_ms);
    for (auto& values : times) {
        std::sort(values.begin(), values.end());
        output << ',' << values[(values.size() - 1) / 2];
    }
    const double mixed_recall =
        mixed_latencies.empty()
            ? 0.0
            : static_cast<double>(mixed_hits) / static_cast<double>(mixed_latencies.size() * k);
    output << ',' << save_ms << ',' << reload_ms << ',' << snapshot_bytes << ',' << query_every
           << ',' << mixed_latencies.size() << ',' << mixed_recall << ',' << mixed_percentile(0.50)
           << ',' << mixed_percentile(0.99) << ',' << query_cpu_ms << ',' << cpu_ms << '\n';
    output.close();
    require(static_cast<bool>(output), "API CRUD summary write failed");
}

void
measure_api(const GraphSnapshot& graph,
            const std::vector<std::vector<float>>& queries,
            const std::vector<std::vector<int32_t>>& truth,
            uint64_t repeats,
            uint64_t configured_budget,
            uint64_t crud_cycles,
            uint64_t query_every,
            const std::string& path) {
    require(not std::filesystem::exists(path), "API output path already exists");
    // Match Index::Save's v2 FP32 layout; serialization is outside Load timing.
    std::stringstream snapshot(std::ios::in | std::ios::out | std::ios::binary);
    const auto write = [&](uint64_t value, uint64_t bytes = 8) {
        for (uint64_t i = 0; i < bytes; ++i) {
            snapshot.put(static_cast<char>((value >> (8 * i)) & 0xff));
        }
    };
    uint64_t payload = 16 + graph.ids.size() * 16 + graph.vectors.size() * 4;
    for (const auto& row : graph.links) {
        payload += row.size() * 8;
    }
    snapshot.write("VSAGLT01", 8);
    for (const uint64_t value : {uint64_t{2},
                                 graph.dim,
                                 static_cast<uint64_t>(graph.ids.size()),
                                 payload,
                                 uint64_t{2},
                                 graph.max_degree,
                                 configured_budget}) {
        write(value);
    }
    for (const int64_t id : graph.ids) {
        write(static_cast<uint64_t>(id));
    }
    for (const float value : graph.vectors) {
        uint32_t bits = 0;
        std::memcpy(&bits, &value, sizeof(bits));
        write(bits, 4);
    }
    for (const auto& row : graph.links) {
        write(row.size());
        for (const uint64_t target : row) {
            write(target);
        }
    }
    require(static_cast<bool>(snapshot), "API snapshot serialization failed");
    snapshot.seekg(0);
    using Clock = std::chrono::steady_clock;
    auto start = Clock::now();
    auto loaded = vsag::lite::Index::Load(snapshot);
    const double load_ms = std::chrono::duration<double, std::milli>(Clock::now() - start).count();
    require(static_cast<bool>(loaded), "API snapshot load failed");
    const uint64_t k = truth.front().size();
    uint64_t hits = 0;
    // One full warmup pass also measures quality outside the timed query loop.
    for (uint64_t i = 0; i < queries.size(); ++i) {
        auto result =
            (*loaded)->SearchWithOptions(queries[i].data(), graph.dim, k, {graph.ef_search});
        require(static_cast<bool>(result) and result->size() == k, "API warmup failed");
        std::unordered_set<int64_t> expected(truth[i].begin(), truth[i].end());
        for (const auto& neighbor : *result) {
            hits += expected.count(neighbor.id);
        }
    }
    std::vector<double> latencies;
    latencies.reserve(queries.size() * repeats);
    const auto cpu_start = std::clock();
    for (uint64_t round = 0; round < repeats; ++round) {
        for (const auto& query : queries) {
            start = Clock::now();
            auto result =
                (*loaded)->SearchWithOptions(query.data(), graph.dim, k, {graph.ef_search});
            const auto end = Clock::now();
            require(static_cast<bool>(result) and result->size() == k, "API timed search failed");
            latencies.push_back(std::chrono::duration<double, std::micro>(end - start).count());
        }
    }
    const double cpu_ms = 1000.0 * static_cast<double>(std::clock() - cpu_start) / CLOCKS_PER_SEC;
    std::ofstream samples(path + ".latencies.csv");
    require(static_cast<bool>(samples), "API latency output open failed");
    samples << "round,query,latency_us\n" << std::fixed << std::setprecision(6);
    for (uint64_t i = 0; i < latencies.size(); ++i) {
        samples << i / queries.size() << ',' << i % queries.size() << ',' << latencies[i] << '\n';
    }
    samples.close();
    require(static_cast<bool>(samples), "API latency output write failed");
    std::sort(latencies.begin(), latencies.end());
    const auto percentile = [&](double fraction) {
        return latencies[static_cast<uint64_t>(
                             std::ceil(fraction * static_cast<double>(latencies.size()))) -
                         1];
    };
    std::ofstream output(path);
    require(static_cast<bool>(output), "API output open failed");
    output << "query_count,repeats,recall_at_k,search_p50_us,search_p99_us,query_loop_cpu_ms,load_"
              "ms,configured_ef_search,query_ef_search\n";
    output << queries.size() << ',' << repeats << ',' << std::fixed << std::setprecision(6)
           << static_cast<double>(hits) / static_cast<double>(queries.size() * k) << ','
           << percentile(0.50) << ',' << percentile(0.99) << ',' << cpu_ms << ',' << load_ms << ','
           << configured_budget << ',' << graph.ef_search << '\n';
    output.close();
    require(static_cast<bool>(output), "API output write failed");
    if (crud_cycles != 0) {
        measure_crud(**loaded,
                     graph,
                     queries,
                     truth,
                     crud_cycles,
                     graph.ef_search,
                     query_every,
                     path + ".crud.csv");
    }
}

int
run(const std::string& snapshot,
    const std::string& directory,
    const std::string& output_path,
    uint64_t ef_search,
    const std::string& entry_mode,
    const std::string& neighbor_mode,
    uint64_t api_repeats,
    uint64_t crud_cycles,
    uint64_t query_every) {
    require(not std::filesystem::exists(output_path), "output path already exists");
    require(api_repeats == 0 or not std::filesystem::exists(output_path + ".api.csv.latencies.csv"),
            "API latency output path already exists");
    require(api_repeats == 0 or entry_mode == "uniform",
            "API measurement requires uniform ENTRY_MODE");
    require(api_repeats == 0 or not std::filesystem::exists(output_path + ".api.csv"),
            "API output path already exists");
    require(crud_cycles == 0 or
                (not std::filesystem::exists(output_path + ".api.csv.crud.csv") and
                 not std::filesystem::exists(output_path + ".api.csv.crud.csv.samples.csv")),
            "API CRUD output path already exists");
    require(crud_cycles == 0 or
                not std::filesystem::exists(output_path + ".api.csv.crud.csv.mixed.csv"),
            "API mixed output path already exists");
    GraphSnapshot graph = load_snapshot(snapshot);
    const uint64_t configured_budget = graph.ef_search;
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
    if (api_repeats != 0) {
        measure_api(graph,
                    queries,
                    truth,
                    api_repeats,
                    configured_budget,
                    crud_cycles,
                    query_every,
                    output_path + ".api.csv");
    }
    return 0;
}

}  // namespace

// The slot-factor diagnostic reuses this translation unit with a distinct entry point.
#ifndef VSAG_LITE_ROUTE_PROBE_MAIN
#define VSAG_LITE_ROUTE_PROBE_MAIN main
#endif
int
VSAG_LITE_ROUTE_PROBE_MAIN(int argc, char** argv) {
    try {
        if (argc == 2 and std::string(argv[1]) == "--self-test") {
            test_reverse_replacement();
            std::cout << "Reverse replacement fixtures passed\n";
            return 0;
        }
        require(
            argc >= 4 and argc <= 10,
            "usage: lite_graph_route_probe SNAPSHOT DATASET OUTPUT "
            "[EF_SEARCH [ENTRY_MODE [NEIGHBOR_MODE [API_REPEATS [CRUD_CYCLES [QUERY_EVERY]]]]]]");
        const uint64_t ef_search = argc >= 5 ? std::stoull(argv[4]) : 0;
        require(argc == 4 or ef_search > 0, "EF_SEARCH must be positive");
        const std::string entry_mode = argc >= 6 ? argv[5] : "uniform";
        const std::string neighbor_mode = argc >= 7 ? argv[6] : "preserve";
        const uint64_t api_repeats = argc >= 8 ? std::stoull(argv[7]) : 0;
        require(argc < 8 or (api_repeats > 0 and api_repeats <= 1000),
                "API_REPEATS must be in [1, 1000]");
        const uint64_t crud_cycles = argc >= 9 ? std::stoull(argv[8]) : 0;
        require(argc < 9 or (crud_cycles > 0 and crud_cycles <= 100000),
                "CRUD_CYCLES must be in [1, 100000]");
        const uint64_t query_every = argc == 10 ? std::stoull(argv[9]) : 0;
        require(argc != 10 or (query_every > 0 and query_every <= crud_cycles),
                "QUERY_EVERY must be in [1, CRUD_CYCLES]");
        return run(argv[1],
                   argv[2],
                   argv[3],
                   ef_search,
                   entry_mode,
                   neighbor_mode,
                   api_repeats,
                   crud_cycles,
                   query_every);
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
