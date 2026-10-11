// Copyright 2024-present the vsag project
// SPDX-License-Identifier: Apache-2.0
#include <vsag/lite/index.h>

#include <cstdlib>
#include <fstream>
#include <iostream>
#include <new>
#include <stdexcept>
#include <string>

namespace {
thread_local bool recording = false;
thread_local uint64_t allocations = 0;
thread_local uint64_t requested_bytes = 0;
thread_local uint64_t count_sized_requests = 0;
thread_local uint64_t index_count = 0;
}  // namespace

void*
operator new(std::size_t bytes) {
    if (void* pointer = std::malloc(bytes == 0 ? 1 : bytes)) {
        if (recording) {
            ++allocations;
            requested_bytes += bytes;
            count_sized_requests += static_cast<uint64_t>(bytes == index_count);
        }
        return pointer;
    }
    throw std::bad_alloc();
}
void
operator delete(void* pointer) noexcept {
    std::free(pointer);
}
void
operator delete(void* pointer, std::size_t) noexcept {
    std::free(pointer);
}
void*
operator new[](std::size_t bytes) {
    return ::operator new(bytes);
}
void
operator delete[](void* pointer) noexcept {
    ::operator delete(pointer);
}
void
operator delete[](void* pointer, std::size_t) noexcept {
    ::operator delete(pointer);
}

int
main(int argc, char** argv) {
    try {
        if (argc != 5) {
            throw std::runtime_error("usage: probe SNAPSHOT QUERIES NEW_METRICS NEW_NEIGHBORS");
        }
        std::ifstream input(argv[1], std::ios::binary);
        auto loaded = vsag::lite::Index::Load(input);
        if (not loaded) {
            throw std::runtime_error("load failed");
        }
        index_count = (*loaded)->Size();
        const uint64_t dim = (*loaded)->Dim();
        std::ifstream queries(argv[2], std::ios::binary);
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
            if (not(*loaded)->SearchWithOptions(query.data(), dim, 10, {512})) {
                throw std::runtime_error("warmup failed");
            }
        }
        std::ofstream metrics(argv[3]);
        std::ofstream neighbors(argv[4]);
        metrics << "query,ordinary_new_requests,ordinary_new_bytes,count_sized_requests\n";
        neighbors << "query,rank,id,distance\n";
        for (uint64_t q = 0; q < rows.size(); ++q) {
            allocations = requested_bytes = count_sized_requests = 0;
            recording = true;
            const auto result = (*loaded)->SearchWithOptions(rows[q].data(), dim, 10, {512});
            recording = false;
            if (not result or result->size() != 10 or allocations == 0) {
                throw std::runtime_error("query or interception failed");
            }
            metrics << q << ',' << allocations << ',' << requested_bytes << ','
                    << count_sized_requests << '\n';
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
        recording = false;
        std::cerr << error.what() << '\n';
        return 1;
    }
}
