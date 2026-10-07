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
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>

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
rss() {
    std::ifstream input("/proc/self/status");
    std::string key;
    while (input >> key) {
        if (key == "VmRSS:") {
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
int
run(const std::string& snapshot, uint64_t dim, uint64_t count, bool force_remove) {
    require(dim <= static_cast<uint64_t>(std::numeric_limits<int32_t>::max()) and
                count <= static_cast<uint64_t>(std::numeric_limits<int64_t>::max()),
            "dimensions or count out of range");
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
        rusage usage{};
        require(getrusage(RUSAGE_SELF, &usage) == 0, "getrusage failed");
        std::cout << "dim,count,snapshot_bytes,load_ms,before_create_rss_kib,"
                     "before_load_rss_kib,loaded_rss_kib,process_peak_rss_kib,page_cache_control\n";
        std::cout << dim << ',' << count << ',' << bytes << ',' << std::fixed
                  << std::setprecision(6) << load_ms << ',' << before_create << ',' << before_load
                  << ',' << after_load << ',' << usage.ru_maxrss << ",warm_uncontrolled\n";
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
