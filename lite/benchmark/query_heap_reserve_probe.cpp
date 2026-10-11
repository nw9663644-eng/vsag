// Copyright 2024-present the vsag project
// SPDX-License-Identifier: Apache-2.0
#include <vsag/lite/index.h>

#include <chrono>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

int
main(int argc, char** argv) {
    try {
        if (argc != 5) {
            throw std::runtime_error("usage: probe SNAPSHOT QUERIES METRICS NEIGHBORS");
        }
        std::ifstream input(argv[1], std::ios::binary);
        auto loaded = vsag::lite::Index::Load(input);
        if (not loaded) {
            throw std::runtime_error("load failed");
        }
        const uint64_t dim = (*loaded)->Dim();
        std::ifstream queries(argv[2], std::ios::binary);
        if (not queries) {
            throw std::runtime_error("queries open failed");
        }
        std::vector<std::vector<float>> rows;
        while (queries.peek() != std::char_traits<char>::eof()) {
            int32_t width{};
            queries.read(reinterpret_cast<char*>(&width), sizeof(width));
            if (width <= 0 or static_cast<uint64_t>(width) != dim) {
                throw std::runtime_error("query width");
            }
            rows.emplace_back(dim);
            queries.read(reinterpret_cast<char*>(rows.back().data()),
                         static_cast<std::streamsize>(dim * sizeof(float)));
            if (not queries) {
                throw std::runtime_error("query payload");
            }
        }
        if (rows.empty()) {
            throw std::runtime_error("no queries");
        }
        for (const auto& query : rows) {
            const auto found = (*loaded)->SearchWithOptions(query.data(), dim, 10, {512});
            if (not found or found->size() != 10) {
                throw std::runtime_error("warmup failed");
            }
        }
        std::ofstream metrics(argv[3]);
        std::ofstream neighbors(argv[4]);
        metrics << "query,latency_us\n" << std::setprecision(12);
        neighbors << "query,rank,id,distance\n";
        for (uint64_t q = 0; q < rows.size(); ++q) {
            const auto start = std::chrono::steady_clock::now();
            const auto result = (*loaded)->SearchWithOptions(rows[q].data(), dim, 10, {512});
            const double elapsed =
                std::chrono::duration<double, std::micro>(std::chrono::steady_clock::now() - start)
                    .count();
            if (not result or result->size() != 10) {
                throw std::runtime_error("query failed");
            }
            metrics << q << ',' << elapsed << '\n';
            for (uint64_t rank = 0; rank < result->size(); ++rank) {
                neighbors << q << ',' << rank << ',' << (*result)[rank].id << ',' << std::hexfloat
                          << (*result)[rank].distance << std::defaultfloat << '\n';
            }
        }
        if (not metrics or not neighbors) {
            throw std::runtime_error("output failed");
        }
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
