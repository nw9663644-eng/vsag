// Copyright 2024-present the vsag project
// SPDX-License-Identifier: Apache-2.0
#include <vsag/lite/index.h>

#include <cmath>
#include <fstream>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <vector>

namespace {
void
require(bool value) {
    if (not value) {
        throw std::runtime_error("boundary fixture failed");
    }
}
}  // namespace

int
main(int argc, char** argv) {
    try {
        require(argc == 2);
        std::ofstream ledger(argv[1], std::ios::binary);
        auto created = vsag::lite::Index::Create(1);
        require(static_cast<bool>(created));
        auto index = std::move(*created);
        constexpr uint64_t count = 65537;
        for (uint64_t i = 0; i < count; ++i) {
            const float value = std::sin(static_cast<float>(i) * .01F);
            require(static_cast<bool>(index->Add(static_cast<int64_t>(i), &value, 1)));
        }
        require(static_cast<bool>(index->BuildGraph(vsag::lite::VectorStorage::RABITQ8, 4, 16)));
        for (uint64_t epoch = 0; epoch < 5; ++epoch) {
            if (epoch == 1 or epoch == 2) {
                require(index->Remove(static_cast<int64_t>(count - epoch)));
            }
            if (epoch == 3 or epoch == 4) {
                const float changed = epoch == 3 ? .375F : -.625F;
                const auto id = static_cast<int64_t>(count - (epoch == 3 ? 2 : 1));
                require(static_cast<bool>(index->Add(id, &changed, 1)));
                require(static_cast<bool>(index->Update(64, &changed, 1)));
            }
            std::stringstream snapshot;
            require(static_cast<bool>(index->Save(snapshot)));
            const auto bytes = snapshot.str();
            const uint64_t size = bytes.size();
            ledger.write(reinterpret_cast<const char*>(&size), sizeof(size));
            ledger.write(bytes.data(), static_cast<std::streamsize>(bytes.size()));
            auto loaded = vsag::lite::Index::Load(snapshot);
            require(static_cast<bool>(loaded));
            for (uint64_t q = 0; q < 4; ++q) {
                const float query = static_cast<float>(q) * .375F - .5F;
                for (uint64_t mode = 0; mode < 4; ++mode) {
                    vsag::lite::IdFilter filter;
                    if (mode != 0) {
                        filter = [mode](int64_t id) {
                            return mode == 1 or (mode == 2 and id % 2 == 0);
                        };
                    }
                    for (const auto* current : {index.get(), loaded->get()}) {
                        const auto result =
                            current->SearchWithOptions(&query, 1, 10, {512}, filter);
                        require(static_cast<bool>(result));
                        require(mode != 3 or result->empty());
                        std::cout << epoch << ',' << current->Size() << ',' << q << ',' << mode;
                        for (const auto& neighbor : *result) {
                            std::cout << ',' << neighbor.id << ':' << std::hexfloat
                                      << neighbor.distance << std::defaultfloat;
                        }
                        std::cout << '\n';
                    }
                }
            }
        }
        require(static_cast<bool>(ledger));
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
