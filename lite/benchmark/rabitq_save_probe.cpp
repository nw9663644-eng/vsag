// Copyright 2024-present the vsag project
// SPDX-License-Identifier: Apache-2.0
#include <vsag/lite/index.h>

#include <chrono>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>

namespace {
uint64_t
status(const std::string& key) {
    std::ifstream input("/proc/self/status");
    std::string current;
    while (input >> current) {
        if (current == key) {
            uint64_t value = 0;
            input >> value;
            return value;
        }
        std::string line;
        std::getline(input, line);
    }
    throw std::runtime_error("memory status unavailable");
}
}  // namespace

int
main(int argc, char** argv) {
    try {
        if (argc != 3 or std::filesystem::exists(argv[2])) {
            throw std::runtime_error("usage: rabitq_save_probe INPUT NEW_OUTPUT");
        }
        std::ifstream input(argv[1], std::ios::binary);
        auto loaded = vsag::lite::Index::Load(input);
        if (not loaded) {
            throw std::runtime_error("load failed");
        }
        const auto before_rss = status("VmRSS:");
        const auto before_hwm = status("VmHWM:");
        const auto start = std::chrono::steady_clock::now();
        std::ofstream output(argv[2], std::ios::binary);
        if (not output or not(*loaded)->Save(output)) {
            throw std::runtime_error("save failed");
        }
        output.close();
        if (not output) {
            throw std::runtime_error("save close failed");
        }
        const auto elapsed =
            std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - start)
                .count();
        std::cout
            << "count,dim,save_ms,before_rss_kib,before_hwm_kib,after_rss_kib,after_hwm_kib,bytes\n"
            << (*loaded)->Size() << ',' << (*loaded)->Dim() << ',' << std::setprecision(12)
            << elapsed << ',' << before_rss << ',' << before_hwm << ',' << status("VmRSS:") << ','
            << status("VmHWM:") << ',' << std::filesystem::file_size(argv[2]) << '\n';
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
