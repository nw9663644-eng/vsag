// Copyright 2024-present the vsag project
// SPDX-License-Identifier: Apache-2.0
#include <vsag/lite/index.h>

#include <algorithm>
#include <cstring>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <numeric>
#include <stdexcept>

#include "lite/rabitq_snapshot.h"

namespace {
void
require(bool condition, const char* message) {
    if (not condition) {
        throw std::runtime_error(message);
    }
}

template <typename T>
std::vector<T>
record(std::istream& input, uint64_t dim) {
    int32_t width{};
    input.read(reinterpret_cast<char*>(&width), sizeof(width));
    require(input and width > 0 and static_cast<uint64_t>(width) == dim, "record width");
    std::vector<T> values(dim);
    input.read(reinterpret_cast<char*>(values.data()),
               static_cast<std::streamsize>(dim * sizeof(T)));
    require(static_cast<bool>(input), "record payload");
    return values;
}
}  // namespace

int
main(int argc, char** argv) {
    try {
        require(argc == 5, "usage: probe SNAPSHOT QUERIES TRUTH OUTPUT_PREFIX");
        namespace codec = vsag::lite::detail::rabitq;
        std::ifstream encoded(argv[1], std::ios::binary);
        auto state = codec::load_mutable_snapshot(encoded, true);
        std::ifstream native_input(argv[1], std::ios::binary);
        auto native = vsag::lite::Index::Load(native_input);
        require(static_cast<bool>(native), "native load");
        for (uint64_t slot = 0; slot < state.Size(); ++slot) {
            require(state.GetIds()[slot] == static_cast<int64_t>(slot),
                    "initial ordinal IDs required");
        }
        std::ifstream queries(argv[2], std::ios::binary);
        std::ifstream truth(argv[3], std::ios::binary);
        std::ofstream summary(std::string(argv[4]) + ".queries.csv");
        std::ofstream evidence(std::string(argv[4]) + ".truth.csv");
        summary
            << "query,formal_hits,visited_truth,visited_nodes,visited_rerank_hits,all_codes_hits\n";
        evidence << "query,id,visited,formal,visited_rerank,all_codes\n";
        uint64_t query_id = 0;
        while (queries.peek() != std::char_traits<char>::eof()) {
            const auto query = record<float>(queries, state.GetModel().dim);
            const auto expected = record<int32_t>(truth, 10);
            const auto result =
                native.value()->SearchWithOptions(query.data(), query.size(), 10, {512});
            require(static_cast<bool>(result), "native query");
            const auto formal = state.SearchWithOptions(query.data(), 10, 512);
            require(formal.neighbors.size() == result->size(), "native count parity");
            for (uint64_t rank = 0; rank < formal.neighbors.size(); ++rank) {
                require(static_cast<int64_t>(formal.neighbors[rank].id) == (*result)[rank].id and
                            std::memcmp(&formal.neighbors[rank].distance,
                                        &(*result)[rank].distance,
                                        sizeof(float)) == 0,
                        "native ordered result parity");
            }
            std::vector<uint8_t> visited(state.Size());
            const auto traced = state.SearchWithOptions(query.data(), 10, 512, [&](int64_t id) {
                visited[static_cast<uint64_t>(id)] = 1;
                return true;
            });
            require(traced.visited == formal.visited and
                        static_cast<uint64_t>(std::count(visited.begin(), visited.end(), 1)) ==
                            formal.visited,
                    "trace visit count parity");
            float norm{};
            const auto normalized = codec::normalize(state.GetModel(), query.data(), norm);
            const float sum = std::accumulate(normalized.begin(), normalized.end(), 0.0F);
            const auto complete = codec::top_k(state.Size(), 10, [&](uint64_t slot) {
                const auto code = state.GetCodes().At(slot);
                const auto coarse = codec::filter_estimate(normalized, norm, code);
                return codec::full_distance(normalized, norm, code, coarse.centered_ip, sum);
            });
            const auto contains = [](const auto& candidates, uint64_t id) {
                return std::any_of(candidates.begin(),
                                   candidates.end(),
                                   [id](const auto& candidate) { return candidate.id == id; });
            };
            uint64_t hits{}, visited_hits{}, traced_hits{}, complete_hits{};
            for (const int32_t id : expected) {
                require(id >= 0 and static_cast<uint64_t>(id) < state.Size(), "truth ID");
                const bool a = contains(formal.neighbors, id);
                const bool b = contains(traced.neighbors, id);
                const bool c = contains(complete, id);
                hits += a;
                visited_hits += visited[id];
                traced_hits += b;
                complete_hits += c;
                evidence << query_id << ',' << id << ',' << static_cast<uint64_t>(visited[id])
                         << ',' << a << ',' << b << ',' << c << '\n';
            }
            summary << query_id << ',' << hits << ',' << visited_hits << ',' << formal.visited
                    << ',' << traced_hits << ',' << complete_hits << '\n';
            ++query_id;
        }
        require(query_id == 100 and truth.peek() == std::char_traits<char>::eof(), "query count");
        require(summary and evidence, "output write");
        std::cout << "queries=" << query_id << " native_and_visit_parity=pass\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
