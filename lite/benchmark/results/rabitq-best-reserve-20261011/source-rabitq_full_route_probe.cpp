// Copyright 2024-present the vsag project
// SPDX-License-Identifier: Apache-2.0
#include <vsag/lite/index.h>

#include <chrono>
#include <cstring>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>

#include "lite/rabitq_snapshot.h"

namespace {
void
require(bool value, const char* message) {
    if (not value) {
        throw std::runtime_error(message);
    }
}

template <typename T>
std::vector<std::vector<T>>
records(const char* path, uint64_t dim) {
    std::ifstream input(path, std::ios::binary);
    require(static_cast<bool>(input), "input open");
    std::vector<std::vector<T>> result;
    while (input.peek() != std::char_traits<char>::eof()) {
        int32_t width{};
        input.read(reinterpret_cast<char*>(&width), sizeof(width));
        require(input and width > 0 and static_cast<uint64_t>(width) == dim, "input width");
        std::vector<T> row(dim);
        input.read(reinterpret_cast<char*>(row.data()),
                   static_cast<std::streamsize>(dim * sizeof(T)));
        require(static_cast<bool>(input), "input payload");
        result.push_back(std::move(row));
    }
    return result;
}
}  // namespace

int
main(int argc, char** argv) {
    try {
        require(argc == 6, "usage: probe SNAPSHOT QUERIES TRUTH PREFIX NATIVE_CHECK_0_OR_1");
        namespace codec = vsag::lite::detail::rabitq;
        std::ifstream input(argv[1], std::ios::binary);
        auto state = codec::load_mutable_snapshot(input, true);
        const auto queries = records<float>(argv[2], state.GetModel().dim);
        const auto truth = records<int32_t>(argv[3], 10);
        require(queries.size() == truth.size() and not queries.empty(), "query counts");
        const std::string check(argv[5]);
        require(check == "0" or check == "1", "native-check flag");
#ifndef VSAG_LITE_EXPERIMENT_FULL_ROUTE
        if (check == "1") {
            std::ifstream original(argv[1], std::ios::binary);
            auto native = vsag::lite::Index::Load(original);
            require(static_cast<bool>(native), "native load");
            for (const auto& query : queries) {
                const auto actual = state.SearchWithOptions(query.data(), 10, 512);
                const auto expected =
                    native.value()->SearchWithOptions(query.data(), query.size(), 10, {512});
                require(expected and expected->size() == actual.neighbors.size(), "native count");
                for (uint64_t rank = 0; rank < actual.neighbors.size(); ++rank) {
                    uint32_t left{};
                    uint32_t right{};
                    std::memcpy(&left, &actual.neighbors[rank].distance, sizeof(left));
                    std::memcpy(&right, &(*expected)[rank].distance, sizeof(right));
                    require(state.GetIds()[actual.neighbors[rank].id] == (*expected)[rank].id and
                                left == right,
                            "native ordered distance-bit parity");
                }
            }
        }
#else
        require(check == "0", "candidate cannot claim native result parity");
#endif
        for (const auto& query : queries) {
            (void)state.SearchWithOptions(query.data(), 10, 512);
        }
        std::ofstream output(std::string(argv[4]) + ".queries.csv");
        std::ofstream neighbors(std::string(argv[4]) + ".neighbors.csv");
        output << "query,hits,latency_us,visited,reordered\n" << std::setprecision(12);
        neighbors << "query,rank,id,distance\n";
        for (uint64_t q = 0; q < queries.size(); ++q) {
            const auto start = std::chrono::steady_clock::now();
            const auto found = state.SearchWithOptions(queries[q].data(), 10, 512);
            const double elapsed =
                std::chrono::duration<double, std::micro>(std::chrono::steady_clock::now() - start)
                    .count();
            require(found.neighbors.size() == 10, "result count");
            uint64_t hits = 0;
            for (uint64_t rank = 0; rank < found.neighbors.size(); ++rank) {
                const auto& neighbor = found.neighbors[rank];
                const auto id = state.GetIds()[neighbor.id];
                hits += static_cast<uint64_t>(std::find(truth[q].begin(), truth[q].end(), id) !=
                                              truth[q].end());
                neighbors << q << ',' << rank << ',' << id << ',' << std::hexfloat
                          << neighbor.distance << std::defaultfloat << '\n';
            }
            output << q << ',' << hits << ',' << elapsed << ',' << found.visited << ','
                   << found.reordered << '\n';
        }
        require(output and neighbors, "evidence output");
        std::cout << "queries=" << queries.size() << " native_check=" << check << '\n';
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
