// Copyright 2024-present the vsag project
// SPDX-License-Identifier: Apache-2.0
#include <vsag/lite/index.h>

#include <cstdlib>
#include <exception>
#include <iostream>
#include <new>
#include <sstream>
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
int
main() {
    int problems = 0;
    constexpr int modes =
#if defined(VSAG_LITE_HAS_RABITQ_BACKEND)
        3;
#else
        2;
#endif
    for (int mode = 0; mode < modes; ++mode) {
        for (int op = 0; op < 3; ++op) {
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
                if (!index->BuildGraph(mode == 2 ? vsag::lite::VectorStorage::RABITQ8
                                                 : (mode != 0 ? vsag::lite::VectorStorage::FP16
                                                              : vsag::lite::VectorStorage::FP32),
                                       3,
                                       16)) {
                    return 3;
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
                    } else {
                        failed = !index->Remove(3);
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
                                  : index->Remove(3);
                    if (not retried) {
                        ++invalid;
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
