// Copyright 2024-present the vsag project
// SPDX-License-Identifier: Apache-2.0
// Build only through build_rabitq_stage_probe.py: source overlay supplies timers.
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <vector>

#include "lite/rabitq_snapshot.h"

namespace rb = vsag::lite::detail::rabitq;
struct CountingFile : std::filebuf {
    uint64_t calls{0};
    std::streamsize
    xsgetn(char* data, std::streamsize count) override {
        ++calls;
        return std::filebuf::xsgetn(data, count);
    }
};

int
main(int argc, char** argv) {
    try {
        if (argc != 5 and argc != 6) {
            throw std::runtime_error(
                "usage: stage_probe SNAPSHOT QUERIES EF REPEATS [NEW_NEIGHBORS]");
        }
        CountingFile buffer;
        buffer.open(argv[1], std::ios::in | std::ios::binary);
        std::istream input(&buffer);
        auto state = rb::load_mutable_snapshot(input);
        std::ifstream queries(argv[2], std::ios::binary);
        std::vector<std::vector<float>> rows;
        while (true) {
            int32_t dim = 0;
            queries.read(reinterpret_cast<char*>(&dim), 4);
            if (queries.eof()) {
                break;
            }
            if (!queries || dim <= 0 || static_cast<uint64_t>(dim) != state.GetModel().dim) {
                throw std::runtime_error("invalid query dimension");
            }
            rows.emplace_back(dim);
            queries.read(reinterpret_cast<char*>(rows.back().data()),
                         static_cast<std::streamsize>(static_cast<uint64_t>(dim) * sizeof(float)));
            if (!queries) {
                throw std::runtime_error("truncated queries");
            }
        }
        const uint64_t ef = std::stoull(argv[3]);
        const uint64_t repeats = std::stoull(argv[4]);
        if (rows.empty() || ef == 0 || repeats == 0) {
            throw std::runtime_error("invalid query options");
        }
        std::ofstream neighbors;
        if (argc == 6) {
            if (std::filesystem::exists(argv[5])) {
                throw std::runtime_error("neighbor output exists");
            }
            neighbors.open(argv[5]);
            if (not neighbors) {
                throw std::runtime_error("neighbor output open failed");
            }
            neighbors << "query,rank,id,distance\n" << std::hexfloat;
        }
        rb::stage_query.fill(0.0);
        uint64_t visited = 0;
        uint64_t reordered = 0;
        uint64_t checksum = 0;
        for (uint64_t repeat = 0; repeat < repeats; ++repeat) {
            uint64_t query_id = 0;
            for (const auto& query : rows) {
                const auto result = state.SearchWithOptions(query.data(), 10, ef);
                visited += result.visited;
                reordered += result.reordered;
                if (argc == 6 and repeat == 0) {
                    for (uint64_t rank = 0; rank < result.neighbors.size(); ++rank) {
                        const auto& neighbor = result.neighbors[rank];
                        neighbors << query_id << ',' << rank << ',' << state.GetIds()[neighbor.id]
                                  << ',' << neighbor.distance << '\n';
                    }
                    if (not neighbors) {
                        throw std::runtime_error("neighbor output failed");
                    }
                }
                ++query_id;
                for (const auto& neighbor : result.neighbors) {
                    checksum += state.GetIds()[neighbor.id];
                }
            }
        }
        std::cout << std::fixed << std::setprecision(6);
        std::cout
            << "count,dim,stream_reads,payload_us,ids_us,topology_read_us,validate_us,construct_us,"
               "queries,transform_us,route_us,rerank_us,visited,reordered,checksum\n";
        std::cout << state.Size() << ',' << state.GetModel().dim << ',' << buffer.calls;
        for (double stage : rb::stage_load) {
            std::cout << ',' << stage;
        }
        std::cout << ',' << rows.size() * repeats;
        for (double stage : rb::stage_query) {
            std::cout << ',' << stage;
        }
        std::cout << ',' << visited << ',' << reordered << ',' << checksum << '\n';
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
