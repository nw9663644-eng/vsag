// Copyright 2024-present the vsag project
// SPDX-License-Identifier: Apache-2.0
#include <vsag/lite/index.h>

#include <cmath>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
void
require(bool value, const char* message) {
    if (not value) {
        throw std::runtime_error(message);
    }
}
}  // namespace

int
main(int argc, char** argv) {
    try {
        require(argc == 3, "usage: graph_heap_regression fp32|fp16|rabitq8 NEW_SNAPSHOT_LEDGER");
        const std::string storage = argv[1];
        require(storage == "fp32" or storage == "fp16" or storage == "rabitq8", "invalid storage");
        const auto representation = storage == "fp16"      ? vsag::lite::VectorStorage::FP16
                                    : storage == "rabitq8" ? vsag::lite::VectorStorage::RABITQ8
                                                           : vsag::lite::VectorStorage::FP32;
        require(not std::filesystem::exists(argv[2]), "snapshot ledger exists");
        std::ofstream ledger(argv[2], std::ios::binary);
        require(static_cast<bool>(ledger), "snapshot ledger open failed");
        constexpr uint64_t count = 96;
        std::cout << "dim,epoch,query,ef,k,filter,rank,id,distance\n" << std::hexfloat;
        for (uint64_t dim : {uint64_t{1}, uint64_t{17}, uint64_t{128}}) {
            auto created = vsag::lite::Index::Create(dim);
            require(static_cast<bool>(created), "create failed");
            auto index = std::move(*created);
            std::vector<int64_t> ids(count);
            std::vector<std::vector<float>> values(count, std::vector<float>(dim));
            for (uint64_t row = 0; row < count; ++row) {
                ids[row] = row == 0 ? INT64_MIN : 6000 - static_cast<int64_t>(row * 77);
                for (uint64_t d = 0; d < dim; ++d) {
                    values[row][d] = std::sin(static_cast<float>((row % 16) * 7 + d) * .17F);
                }
                require(static_cast<bool>(index->Add(ids[row], values[row].data(), dim)),
                        "add failed");
            }
            require(static_cast<bool>(index->BuildGraph(representation, 4, 16)), "build failed");
            for (uint64_t epoch = 0; epoch <= 16; ++epoch) {
                if (epoch != 0) {
                    for (uint64_t operation = 0; operation < 4; ++operation) {
                        const uint64_t row = (epoch * 13 + operation * 17) % count;
                        for (uint64_t d = 0; d < dim; ++d) {
                            values[row][d] =
                                std::sin(static_cast<float>(epoch * (row + 3) + d) * .17F) +
                                static_cast<float>(epoch) * .05F;
                        }
                        require(static_cast<bool>(index->Update(ids[row], values[row].data(), dim)),
                                "changed update failed");
                    }
                    const uint64_t row = epoch * 29 % count;
                    require(index->Remove(ids[row]), "remove failed");
                    require(static_cast<bool>(index->Add(ids[row], values[row].data(), dim)),
                            "readd failed");
                }
                std::stringstream snapshot;
                require(static_cast<bool>(index->Save(snapshot)), "save failed");
                const auto bytes = snapshot.str();
                const uint64_t size = bytes.size();
                ledger.write(reinterpret_cast<const char*>(&size), sizeof(size));
                ledger.write(bytes.data(), static_cast<std::streamsize>(size));
                require(static_cast<bool>(ledger), "snapshot ledger failed");
                auto restored = vsag::lite::Index::Load(snapshot);
                require(static_cast<bool>(restored), "restore failed");
                for (uint64_t query_id = 0; query_id < 8; ++query_id) {
                    std::vector<float> query(dim);
                    for (uint64_t d = 0; d < dim; ++d) {
                        query[d] = std::sin(static_cast<float>(query_id * 7 + d) * .17F);
                    }
                    for (uint64_t ef : {uint64_t{4}, uint64_t{16}, count}) {
                        const vsag::lite::SearchOptions options{ef};
                        for (uint64_t k : {uint64_t{1}, uint64_t{10}}) {
                            for (uint64_t mode = 0; mode < 3; ++mode) {
                                vsag::lite::IdFilter filter;
                                if (mode != 0) {
                                    filter = [mode](int64_t id) {
                                        return mode == 1 and id % 3 == 0;
                                    };
                                }
                                auto before =
                                    index->SearchWithOptions(query.data(), dim, k, options, filter);
                                auto after = (*restored)->SearchWithOptions(
                                    query.data(), dim, k, options, filter);
                                require(static_cast<bool>(before) and static_cast<bool>(after),
                                        "query failed");
                                require(before->size() == after->size(),
                                        "reload result count changed");
                                // Empty filtered results must also have an explicit ledger row.
                                if (before->empty()) {
                                    std::cout << dim << ',' << epoch << ',' << query_id << ',' << ef
                                              << ',' << k << ',' << mode << ",empty,0,0\n";
                                }
                                for (uint64_t rank = 0; rank < before->size(); ++rank) {
                                    require((*before)[rank].id == (*after)[rank].id and
                                                (*before)[rank].distance == (*after)[rank].distance,
                                            "reload ordered result changed");
                                    std::cout << dim << ',' << epoch << ',' << query_id << ',' << ef
                                              << ',' << k << ',' << mode << ',' << rank << ','
                                              << (*before)[rank].id << ','
                                              << (*before)[rank].distance << '\n';
                                }
                            }
                        }
                    }
                }
            }
        }
        require(static_cast<bool>(std::cout), "result output failed");
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
