// Copyright 2024-present the vsag project
// SPDX-License-Identifier: Apache-2.0
#include <malloc.h>
#include <sys/resource.h>
#ifdef VSAG_BENCH_FULL
#include <vsag/factory.h>
#include <vsag/index.h>
#else
#include <vsag/lite/index.h>
#endif
#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <ctime>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <unordered_set>
#include <vector>

namespace {
void
require(bool value, const std::string& message) {
    if (not value) {
        throw std::runtime_error(message);
    }
}
uint64_t
number(const char* argument) {
    const std::string text(argument);
    require(
        not text.empty() and
            std::all_of(text.begin(), text.end(), [](char ch) { return ch >= '0' and ch <= '9'; }),
        "expected positive decimal integer");
    const auto value = std::stoull(text);
    require(value > 0, "expected positive decimal integer");
    return value;
}
uint64_t
rss(bool high_water = false) {
    std::ifstream input("/proc/self/status");
    std::string key;
    while (input >> key) {
        if (key == (high_water ? "VmHWM:" : "VmRSS:")) {
            uint64_t value = 0;
            std::string unit;
            input >> value >> unit;
            require(static_cast<bool>(input) and unit == "kB", "invalid VmRSS");
            return value;
        }
        std::string remainder;
        std::getline(input, remainder);
    }
    throw std::runtime_error("VmRSS unavailable");
}
#ifndef VSAG_BENCH_FULL
struct QualityResult {
    uint64_t queries{};
    uint64_t budget{};
    double recall{};
    double p50_us{};
    double p99_us{};
    double cpu_ms{};
};

QualityResult
quality(vsag::lite::Index& index, uint64_t dim, const char* query_path, const char* truth_path) {
    std::ifstream queries(query_path, std::ios::binary);
    std::ifstream truth(truth_path, std::ios::binary);
    require(static_cast<bool>(queries) and static_cast<bool>(truth), "quality input open failed");
    const char* selected = std::getenv("VSAG_LOAD_QUALITY_EF");
    const uint64_t budget = selected == nullptr ? 128 : number(selected);
    std::vector<float> query(dim);
    std::vector<double> latencies;
    uint64_t hits = 0;
    uint64_t expected_total = 0;
    const auto cpu_start = std::clock();
    while (queries.peek() != std::char_traits<char>::eof()) {
        int32_t width = 0;
        int32_t k = 0;
        queries.read(reinterpret_cast<char*>(&width), sizeof(width));
        truth.read(reinterpret_cast<char*>(&k), sizeof(k));
        require(static_cast<bool>(queries) and static_cast<bool>(truth) and width > 0 and
                    static_cast<uint64_t>(width) == dim and k > 0 and k <= 100,
                "invalid quality dimensions");
        queries.read(reinterpret_cast<char*>(query.data()),
                     static_cast<std::streamsize>(dim * sizeof(float)));
        std::vector<int32_t> ids(k);
        truth.read(reinterpret_cast<char*>(ids.data()),
                   static_cast<std::streamsize>(ids.size() * sizeof(int32_t)));
        require(static_cast<bool>(queries) and static_cast<bool>(truth),
                "truncated quality inputs");
        std::unordered_set<int64_t> expected(ids.begin(), ids.end());
        require(expected.size() == ids.size() and
                    std::all_of(ids.begin(),
                                ids.end(),
                                [&](int32_t id) {
                                    return id >= 0 and static_cast<uint64_t>(id) < index.Size();
                                }),
                "invalid quality truth IDs");
        const auto start = std::chrono::steady_clock::now();
        auto found = index.SearchWithOptions(query.data(), dim, k, {budget});
        latencies.push_back(
            std::chrono::duration<double, std::micro>(std::chrono::steady_clock::now() - start)
                .count());
        require(static_cast<bool>(found) and found->size() == ids.size(), "quality query failed");
        for (const auto& neighbor : *found) {
            hits += expected.count(neighbor.id);
        }
        expected_total += ids.size();
    }
    const auto cpu_ms = 1000.0 * static_cast<double>(std::clock() - cpu_start) / CLOCKS_PER_SEC;
    require(not latencies.empty() and truth.peek() == std::char_traits<char>::eof(),
            "quality input counts differ");
    std::sort(latencies.begin(), latencies.end());
    const auto rank = [&](double fraction) {
        const auto position =
            static_cast<uint64_t>(std::ceil(fraction * static_cast<double>(latencies.size())));
        return latencies[std::max<uint64_t>(1, position) - 1];
    };
    return {latencies.size(),
            budget,
            static_cast<double>(hits) / static_cast<double>(expected_total),
            rank(0.5),
            rank(0.99),
            cpu_ms};
}
#endif

int
run(const std::string& snapshot, uint64_t dim, uint64_t count, bool force_remove) {
    require(dim <= static_cast<uint64_t>(std::numeric_limits<int32_t>::max()) and
                count <= static_cast<uint64_t>(std::numeric_limits<int64_t>::max()),
            "dimensions or count out of range");
    const char* query_path = std::getenv("VSAG_LOAD_QUERY");
    const char* query_results = std::getenv("VSAG_LOAD_QUERY_RESULTS");
    const char* quality_truth = std::getenv("VSAG_LOAD_QUALITY_TRUTH");
    require(quality_truth == nullptr or query_path != nullptr,
            "quality truth requires query input");
#ifdef VSAG_BENCH_FULL
    require(query_path == nullptr, "optional first query is only available for Lite");
#endif
    require(query_results == nullptr or query_path != nullptr, "query output requires query input");
    require(query_results == nullptr or not std::filesystem::exists(query_results),
            "query output already exists");
    const auto bytes = std::filesystem::file_size(snapshot);
    malloc_trim(0);
    const auto before_create = rss();
#ifdef VSAG_BENCH_FULL
    const auto parameters =
        std::string(R"({"dtype":"float32","metric_type":"l2","dim":)") + std::to_string(dim) +
        R"(,"index_param":{"max_degree":16,"ef_construction":128,)" +
        (force_remove ? R"("graph_storage_type":"flat","support_force_remove":true,)"
                        R"("use_reverse_edges":true,)"
                      : R"("graph_storage_type":"compressed",)") +
        R"("base_quantization_type":"fp32",)"
        R"("store_raw_vector":true}})";
    auto created = vsag::Factory::CreateIndex("hgraph", parameters);
    require(static_cast<bool>(created), "Full index create failed");
    auto index = *created;
#endif
    malloc_trim(0);
    const auto before_load = rss();
    const auto start = std::chrono::steady_clock::now();
    {
        std::ifstream input(snapshot, std::ios::binary);
        require(static_cast<bool>(input), "snapshot open failed");
#ifdef VSAG_BENCH_FULL
        require(static_cast<bool>(index->Deserialize(input)), "Full load failed");
#else
        require(not force_remove, "force-remove profile is only available for Full");
        auto loaded = vsag::lite::Index::Load(input);
        require(static_cast<bool>(loaded), "Lite load failed");
        auto index = std::move(*loaded);
#endif
        const auto load_ms =
            std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - start)
                .count();
#ifdef VSAG_BENCH_FULL
        require(index->GetNumElements() == static_cast<int64_t>(count), "loaded count differs");
#else
        require(index->Size() == count and index->Dim() == dim, "loaded count/dimension differs");
#endif
        input.close();
        malloc_trim(0);
        const auto after_load = rss();
        const auto load_vm_hwm = query_path == nullptr ? 0 : rss(true);
        rusage usage{};
        require(getrusage(RUSAGE_SELF, &usage) == 0, "getrusage failed");
        double first_query_us = 0.0;
        uint64_t first_query_count = 0;
#ifndef VSAG_BENCH_FULL
        if (query_path != nullptr) {
            std::ifstream query_input(query_path, std::ios::binary);
            int32_t query_dim = 0;
            query_input.read(reinterpret_cast<char*>(&query_dim), sizeof(query_dim));
            require(static_cast<bool>(query_input) and query_dim > 0 and
                        static_cast<uint64_t>(query_dim) == dim,
                    "invalid first query dimension");
            std::vector<float> query(dim);
            require(dim <= static_cast<uint64_t>(std::numeric_limits<std::streamsize>::max()) /
                               sizeof(float),
                    "first query exceeds stream capacity");
            query_input.read(reinterpret_cast<char*>(query.data()),
                             static_cast<std::streamsize>(dim * sizeof(float)));
            require(static_cast<bool>(query_input), "truncated first query");
            const auto query_start = std::chrono::steady_clock::now();
            auto found = index->Search(query.data(), dim, std::min<uint64_t>(10, count));
            first_query_us = std::chrono::duration<double, std::micro>(
                                 std::chrono::steady_clock::now() - query_start)
                                 .count();
            require(static_cast<bool>(found), "first query failed");
            first_query_count = found->size();
            require(first_query_count == std::min<uint64_t>(10, count), "short first query");
            if (query_results != nullptr) {
                std::ofstream output(query_results);
                require(static_cast<bool>(output), "first query output failed");
                output << "rank,id,distance\n" << std::hexfloat;
                for (uint64_t rank = 0; rank < found->size(); ++rank) {
                    output << rank << ',' << (*found)[rank].id << ',' << (*found)[rank].distance
                           << '\n';
                }
                require(static_cast<bool>(output), "first query output write failed");
            }
        }
#endif
#ifndef VSAG_BENCH_FULL
        QualityResult quality_result;
        if (quality_truth != nullptr) {
            quality_result = quality(*index, dim, query_path, quality_truth);
        }
#endif
        std::cout << "dim,count,snapshot_bytes,load_ms,before_create_rss_kib,"
                     "before_load_rss_kib,loaded_rss_kib,process_peak_rss_kib,page_cache_control";
        if (query_path != nullptr) {
            std::cout << ",first_query_us,first_query_count,load_vm_hwm_kib";
        }
        if (quality_truth != nullptr) {
            std::cout << ",quality_queries,quality_ef,recall_at_k,search_p50_us,search_p99_us,"
                         "query_loop_cpu_ms";
        }
        std::cout << '\n';
        std::cout << dim << ',' << count << ',' << bytes << ',' << std::fixed
                  << std::setprecision(6) << load_ms << ',' << before_create << ',' << before_load
                  << ',' << after_load << ',' << usage.ru_maxrss << ",warm_uncontrolled";
        if (query_path != nullptr) {
            std::cout << ',' << first_query_us << ',' << first_query_count << ',' << load_vm_hwm;
        }
#ifndef VSAG_BENCH_FULL
        if (quality_truth != nullptr) {
            std::cout << ',' << quality_result.queries << ',' << quality_result.budget << ','
                      << quality_result.recall << ',' << quality_result.p50_us << ','
                      << quality_result.p99_us << ',' << quality_result.cpu_ms;
        }
#endif
        std::cout << '\n';
    }
    return 0;
}
}  // namespace
int
main(int argc, char** argv) {
    try {
        require(argc == 4 or argc == 5,
                "usage: load_memory SNAPSHOT DIM COUNT [compressed|force-remove]");
        const std::string profile = argc == 5 ? argv[4] : "compressed";
        require(profile == "compressed" or profile == "force-remove", "invalid load profile");
        return run(argv[1], number(argv[2]), number(argv[3]), profile == "force-remove");
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
