// Copyright 2024-present the vsag project
// SPDX-License-Identifier: Apache-2.0
#include <sys/resource.h>
#include <unistd.h>

#include <chrono>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>

#include "lite/rabitq_snapshot.h"

uint64_t
resident_kib() {
    std::ifstream input("/proc/self/statm");
    uint64_t pages = 0;
    uint64_t resident = 0;
    if (not(input >> pages >> resident)) {
        throw std::runtime_error("cannot read resident pages");
    }
    return resident * static_cast<uint64_t>(sysconf(_SC_PAGESIZE)) / 1024;
}

int
main(int argc, char** argv) {
    try {
        if (argc != 2) {
            throw std::runtime_error("expected snapshot");
        }
        const auto baseline = resident_kib();
        std::ifstream input(argv[1], std::ios::binary);
        const auto start = std::chrono::steady_clock::now();
        auto state = vsag::lite::detail::rabitq::load_mutable_snapshot(input);
        const auto load_ms =
            std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - start)
                .count();
        const auto resident = resident_kib();
        rusage usage{};
        if (getrusage(RUSAGE_SELF, &usage) != 0) {
            throw std::runtime_error("cannot read peak resident");
        }
        const auto memory = state.GetMemoryUsage();
        const auto incoming = state.GetIncomingMemoryUsage();
        state.Validate();
        std::cout
            << "count,dim,edges,incoming_edges,incoming_logical_bytes,incoming_capacity_bytes,"
               "known_logical_bytes,known_capacity_bytes,slot_entries,slot_buckets,"
               "baseline_rss_kib,resident_rss_kib,peak_rss_kib,load_ms\n";
        std::cout << state.Size() << ',' << state.GetModel().dim << ',' << memory.adjacency_edges
                  << ',' << incoming.edges << ',' << incoming.logical_bytes << ','
                  << incoming.capacity_bytes << ',' << memory.KnownLogicalBytes() << ','
                  << memory.KnownCapacityBytes() << ',' << memory.slot_entries << ','
                  << memory.slot_buckets << ',' << baseline << ',' << resident << ','
                  << usage.ru_maxrss << ',' << std::fixed << std::setprecision(6) << load_ms
                  << '\n';
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
