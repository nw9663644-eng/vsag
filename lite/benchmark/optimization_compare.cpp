// Copyright 2024-present the vsag project
// SPDX-License-Identifier: Apache-2.0
#include <vsag/lite/index.h>

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
using Clock = std::chrono::steady_clock;
void
require(bool value) {
    if (not value) {
        throw std::runtime_error("benchmark operation failed");
    }
}
std::vector<float>
vector(uint64_t dim, uint64_t id) {
    std::vector<float> values(dim);
    for (uint64_t d = 0; d < dim; ++d) {
        values[d] = std::sin(static_cast<float>(id * 17 + d * 3) * 0.013F) +
                    std::cos(static_cast<float>(id * 7 + d) * 0.037F);
    }
    return values;
}
double
elapsed(Clock::time_point start) {
    return std::chrono::duration<double, std::micro>(Clock::now() - start).count();
}
}  // namespace
int
main(int argc, char** argv) {
    if (argc != 5) {
        return 2;
    }
    const std::string action(argv[1]);
    const uint64_t dim = std::stoull(argv[3]);
    const uint64_t mode = std::stoull(argv[4]);
    constexpr uint64_t count = 2048;
    if (action == "create") {
        auto made = vsag::lite::Index::Create(dim);
        require(static_cast<bool>(made));
        auto index = std::move(*made);
        for (uint64_t id = 0; id < count; ++id) {
            const auto values = vector(dim, id);
            require(static_cast<bool>(index->Add(static_cast<int64_t>(id), values.data(), dim)));
        }
        const auto start = Clock::now();
        require(static_cast<bool>(index->BuildGraph(mode == 2   ? vsag::lite::VectorStorage::RABITQ8
                                                    : mode == 1 ? vsag::lite::VectorStorage::FP16
                                                                : vsag::lite::VectorStorage::FP32,
                                                    16,
                                                    128)));
        const double build_us = elapsed(start);
        std::ofstream output(argv[2], std::ios::binary);
        require(static_cast<bool>(index->Save(output)));
        std::cout << "build_us=" << build_us << '\n';
        return 0;
    }
    std::ifstream input(argv[2], std::ios::binary);
    auto loaded = vsag::lite::Index::Load(input);
    require(static_cast<bool>(loaded));
    auto index = std::move(*loaded);
    if (action == "crud") {
        const auto start = Clock::now();
        for (uint64_t id = 0; id < 128; ++id) {
            const auto values = vector(dim, id + count);
            require(static_cast<bool>(index->Update(static_cast<int64_t>(id), values.data(), dim)));
            require(static_cast<bool>(
                index->Add(static_cast<int64_t>(id + count), values.data(), dim)));
            require(index->Remove(static_cast<int64_t>(id)));
        }
        std::cout << "crud_384_us=" << elapsed(start) << '\n';
        std::ofstream output(std::string(argv[2]) + "." + argv[4] + ".after", std::ios::binary);
        require(static_cast<bool>(index->Save(output)));
        return 0;
    }
    std::vector<std::vector<float>> queries;
    for (uint64_t id = 0; id < 256; ++id) {
        queries.push_back(vector(dim, id + count * 2));
    }
    for (const auto& query : queries) {
        require(static_cast<bool>(index->SearchWithOptions(query.data(), dim, 10, {128})));
    }
    std::vector<double> latencies;
    uint64_t hash = 1469598103934665603ULL;
    uint64_t id_hash = hash;
    const auto all_start = Clock::now();
    for (uint64_t repeat = 0; repeat < 4; ++repeat) {
        for (const auto& query : queries) {
            const auto start = Clock::now();
            auto found = index->SearchWithOptions(query.data(), dim, 10, {128});
            latencies.push_back(elapsed(start));
            require(static_cast<bool>(found));
            for (const auto& neighbor : *found) {
                uint32_t bits = 0;
                std::memcpy(&bits, &neighbor.distance, sizeof(bits));
                id_hash = (id_hash ^ static_cast<uint64_t>(neighbor.id)) * 1099511628211ULL;
                hash = (hash ^ static_cast<uint64_t>(neighbor.id)) * 1099511628211ULL;
                hash = (hash ^ bits) * 1099511628211ULL;
            }
        }
    }
    const double total_us = elapsed(all_start);
    std::sort(latencies.begin(), latencies.end());
    std::cout << "dim=" << dim << " mode=" << mode << " id_hash=" << id_hash << " hash=" << hash
              << " p50_us=" << latencies[latencies.size() / 2]
              << " p99_us=" << latencies[(latencies.size() * 99 + 99) / 100 - 1]
              << " total_us=" << total_us << '\n';
}
