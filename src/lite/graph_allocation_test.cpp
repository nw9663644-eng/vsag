// Copyright 2024-present the vsag project
// SPDX-License-Identifier: Apache-2.0
#include <vsag/lite/index.h>

#include <cstdlib>
#include <exception>
#include <iostream>
#include <new>
#include <sstream>

#if defined(VSAG_LITE_HAS_RABITQ_BACKEND)
#include "lite/rabitq_snapshot.h"
#endif
static long remaining = -1;
void*
operator new(std::size_t n) {
    if (remaining >= 0 && remaining-- == 0) {
        remaining = -1;
        throw std::bad_alloc();
    }
    if (void* p = std::malloc(n != 0U ? n : 1)) {
        return p;
    }
    throw std::bad_alloc();
}
void
operator delete(void* p) noexcept {
    std::free(p);
}
void
operator delete(void* p, std::size_t /*unused*/) noexcept {
    std::free(p);
}
void*
operator new[](std::size_t n) {
    return ::operator new(n);
}
void
operator delete[](void* p) noexcept {
    ::operator delete(p);
}
void
operator delete[](void* p, std::size_t /*unused*/) noexcept {
    ::operator delete(p);
}
std::string
save(vsag::lite::Index& i) {
    std::ostringstream o;
    auto r = i.Save(o);
    if (!r) {
        return "SAVE_ERROR";
    }
    return o.str();
}

#if defined(VSAG_LITE_HAS_RABITQ_BACKEND)
int
check_reverse_update_allocation() {
    namespace codec = vsag::lite::detail::rabitq;
    constexpr uint64_t count = 16;
    constexpr uint64_t dim = 17;
    std::vector<float> base(count * dim);
    std::vector<int64_t> ids(count);
    codec::GraphTopology graph;
    graph.offsets.push_back(0);
    for (uint64_t row = 0; row < count; ++row) {
        ids[row] = static_cast<int64_t>(row);
        for (uint64_t d = 0; d < dim; ++d) {
            base[row * dim + d] = std::sin(static_cast<float>(row * 7 + d) * 0.17F);
        }
        for (uint64_t step : {uint64_t{1}, uint64_t{3}, uint64_t{7}}) {
            graph.neighbors.push_back((row + step) % count);
        }
        graph.offsets.push_back(graph.neighbors.size());
    }
    const auto model = codec::train(base, count, dim, 47);
    codec::EncodedRecords codes(dim);
    for (uint64_t row = 0; row < count; ++row) {
        codes.Append(codec::encode(model, base.data() + row * dim));
    }
    std::vector<float> replacement(dim);
    for (uint64_t d = 0; d < dim; ++d) {
        replacement[d] = std::cos(static_cast<float>(d) * 0.31F);
    }
    int problems = 0;
    for (int policy = 0; policy < 4; ++policy) {
        codec::MutableGraphState initial(model, codes, graph, ids, 4, 16, false, true);
        initial.ConfigureIncomingProtection(
            policy == 0 ? codec::IncomingProtection::NONE
                        : (policy == 1 ? codec::IncomingProtection::RECOUNT
                                       : codec::IncomingProtection::CACHED));
        if (policy == 3 and not initial.UpdateTransactional(
                                0, codec::prepare_encoding(model, replacement.data()))) {
            return 1;
        }
        std::ostringstream before_stream;
        codec::save_mutable_snapshot(before_stream, initial);
        const auto before = before_stream.str();
        const auto rebuilds = initial.IncomingCountRebuilds();
        auto golden = initial;
        if (not golden.UpdatePrepared(3, codec::prepare_encoding(model, replacement.data()))) {
            return 1;
        }
        std::ostringstream golden_stream;
        codec::save_mutable_snapshot(golden_stream, golden);
        int failures = 0;
        int successes = 0;
        for (int limit = 0; limit < 500; ++limit) {
            auto state = initial;
            auto prepared = codec::prepare_encoding(model, replacement.data());
            bool failed = false;
            remaining = limit;
            try {
                if (not state.UpdateTransactional(3, std::move(prepared))) {
                    ++problems;
                }
            } catch (const std::bad_alloc&) {
                failed = true;
            } catch (...) {
                remaining = -1;
                ++problems;
                failed = true;
            }
            remaining = -1;
            state.Validate();
            std::ostringstream after_stream;
            codec::save_mutable_snapshot(after_stream, state);
            if (failed) {
                ++failures;
                if (after_stream.str() != before or state.IncomingCountRebuilds() != rebuilds) {
                    ++problems;
                }
                if (not state.UpdateTransactional(
                        3, codec::prepare_encoding(model, replacement.data()))) {
                    ++problems;
                }
                state.Validate();
                std::ostringstream retry_stream;
                codec::save_mutable_snapshot(retry_stream, state);
                if (retry_stream.str() != golden_stream.str() or
                    state.IncomingCountRebuilds() != golden.IncomingCountRebuilds()) {
                    ++problems;
                }
            } else {
                ++successes;
                if (after_stream.str() != golden_stream.str() or
                    state.IncomingCountRebuilds() != golden.IncomingCountRebuilds()) {
                    ++problems;
                }
            }
            const auto memory = state.GetMemoryUsage();
            const auto incoming = state.GetIncomingMemoryUsage();
            if (memory.incoming_adjacency_logical_bytes != incoming.logical_bytes or
                memory.incoming_adjacency_capacity_bytes != incoming.capacity_bytes) {
                ++problems;
            }
        }
        if (failures == 0 or successes == 0) {
            ++problems;
        }
        std::cout << "REVERSE_UPDATE policy=" << policy << " failures=" << failures
                  << " successes=" << successes << " cumulative_problems=" << problems << "\n";
    }
    return problems;
}
#endif

int
main() {
    int problems = 0;
#if defined(VSAG_LITE_HAS_RABITQ_BACKEND)
    try {
        problems += check_reverse_update_allocation();
    } catch (const std::exception& error) {
        remaining = -1;
        std::cerr << "Reverse Update fixture failed: " << error.what() << "\n";
        return 1;
    } catch (...) {
        remaining = -1;
        return 1;
    }
#endif
    constexpr int modes =
#if defined(VSAG_LITE_HAS_RABITQ_BACKEND)
        3;
#else
        2;
#endif
    for (int mode = 0; mode < modes; ++mode) {
        for (int op = 0; op < 4; ++op) {
            int failures = 0;
            int changed = 0;
            int invalid = 0;
            int escaped = 0;
            for (int limit = 0; limit < 500; ++limit) {
                auto made = vsag::lite::Index::Create(2);
                auto index = std::move(*made);
                for (int id = 0; id < 8; ++id) {
                    float v[2] = {float(id), float(id % 3)};
                    if (!index->Add(id, v, 2)) {
                        return 2;
                    }
                }
                const auto storage = mode == 2 ? vsag::lite::VectorStorage::RABITQ8
                                               : (mode != 0 ? vsag::lite::VectorStorage::FP16
                                                            : vsag::lite::VectorStorage::FP32);
                if (op != 3 and not index->BuildGraph(storage, 3, 16)) {
                    return 3;
                }
                // Warm experimental incoming counts before mutation fault injection.
                // The default adapter keeps the same unprotected public behavior.
                if (mode == 2 and op != 3) {
                    const float warm[2] = {-7, 2};
                    if (not index->Update(0, warm, 2)) {
                        return 4;
                    }
                }
                const auto before = save(*index);
                bool failed = false;
                remaining = limit;
                try {
                    float v[2] = {23, 5};
                    if (op == 0) {
                        failed = !index->Add(20, v, 2);
                    } else if (op == 1) {
                        failed = !index->Update(3, v, 2);
                    } else if (op == 2) {
                        failed = !index->Remove(3);
                    } else {
                        failed = !index->BuildGraph(storage, 3, 16);
                    }
                } catch (const std::exception&) {
                    failed = true;
                    ++escaped;
                }
                remaining = -1;
                if (failed) {
                    ++failures;
                    auto after = save(*index);
                    if (after != before) {
                        ++changed;
                        if (changed == 1) {
                            std::cout << "FIRST_CHANGED mode=" << mode << " op=" << op
                                      << " allocation=" << limit << " size=" << index->Size()
                                      << "\n";
                        }
                    }
                    std::istringstream in(after);
                    if (!vsag::lite::Index::Load(in)) {
                        ++invalid;
                    }
                    const float retry_vector[2] = {23, 5};
                    const bool retried =
                        op == 0   ? static_cast<bool>(index->Add(20, retry_vector, 2))
                        : op == 1 ? static_cast<bool>(index->Update(3, retry_vector, 2))
                        : op == 2 ? index->Remove(3)
                                  : static_cast<bool>(index->BuildGraph(storage, 3, 16));
                    if (not retried) {
                        ++invalid;
                    }
                    if (mode == 2 and op != 3 and retried) {
                        const float continued[2] = {-6, 3};
                        if (not index->Update(1, continued, 2)) {
                            ++invalid;
                        }
                        std::istringstream retried_snapshot(save(*index));
                        if (not vsag::lite::Index::Load(retried_snapshot)) {
                            ++invalid;
                        }
                    }
                }
            }
            problems += changed + invalid + escaped;
            std::cout << "SUMMARY mode=" << mode << " op=" << op << " failures=" << failures
                      << " changed_after_failure=" << changed << " invalid_snapshot=" << invalid
                      << " escaped=" << escaped << "\n";
        }
    }
    return problems == 0 ? 0 : 1;
}
