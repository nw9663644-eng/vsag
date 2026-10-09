// Copyright 2024-present the vsag project
// SPDX-License-Identifier: Apache-2.0
#include <vsag/lite/index.h>

#include <cmath>
#include <cstdlib>
#include <iostream>
#include <new>
#include <stdexcept>
#include <string>

namespace {
bool recording = false;
uint64_t allocations = 0;
uint64_t requested_bytes = 0;
uint64_t matrix_requests = 0;
uint64_t matrix_bytes = 0;
}  // namespace

void*
operator new(std::size_t bytes) {
    if (void* pointer = std::malloc(bytes == 0 ? 1 : bytes)) {
        if (recording) {
            ++allocations;
            requested_bytes += bytes;
            matrix_requests += static_cast<uint64_t>(bytes == matrix_bytes);
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
operator delete(void* pointer, std::size_t /*unused*/) noexcept {
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
operator delete[](void* pointer, std::size_t /*unused*/) noexcept {
    ::operator delete(pointer);
}

int
main(int argc, char** argv) {
    try {
        if (argc != 3) {
            throw std::runtime_error("usage: rabitq_build_allocation_probe count dim");
        }
        const uint64_t count = std::stoull(argv[1]);
        const uint64_t dim = std::stoull(argv[2]);
        if (count < 16 or count > 100000 or dim == 0 or dim > 1024) {
            throw std::runtime_error("invalid bounded diagnostic shape");
        }
        auto created = vsag::lite::Index::Create(dim);
        if (not created) {
            throw std::runtime_error("create failed");
        }
        auto index = std::move(*created);
        std::vector<float> row(dim);
        for (uint64_t id = 0; id < count; ++id) {
            for (uint64_t d = 0; d < dim; ++d) {
                row[d] = std::sin(static_cast<float>(id * 7 + d) * .17F);
            }
            if (not index->Add(static_cast<int64_t>(id), row.data(), dim)) {
                throw std::runtime_error("add failed");
            }
        }
        matrix_bytes = count * dim * sizeof(float);
        recording = true;
        const auto result = index->BuildGraph(vsag::lite::VectorStorage::RABITQ8, 16, 128);
        recording = false;
        if (not result) {
            throw std::runtime_error("build failed");
        }
        std::cout
            << "count,dim,matrix_bytes,ordinary_new_requests,ordinary_new_bytes,matrix_requests\n"
            << count << ',' << dim << ',' << matrix_bytes << ',' << allocations << ','
            << requested_bytes << ',' << matrix_requests << '\n';
        return 0;
    } catch (const std::exception& error) {
        recording = false;
        std::cerr << error.what() << '\n';
        return 1;
    }
}
