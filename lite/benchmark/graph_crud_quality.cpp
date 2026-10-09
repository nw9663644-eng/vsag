// Copyright 2024-present the vsag project
// SPDX-License-Identifier: Apache-2.0
#include <vsag/lite/index.h>

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <tuple>
#include <unordered_set>
#include <vector>

namespace {
using Clock = std::chrono::steady_clock;

void
require(bool condition, const char* message) {
    if (not condition) {
        throw std::runtime_error(message);
    }
}

int32_t
read_dim(std::istream& input) {
    int32_t dim = 0;
    input.read(reinterpret_cast<char*>(&dim), sizeof(dim));
    require(static_cast<bool>(input) and dim > 0 and dim <= 4096, "invalid record dimension");
    return dim;
}

template <typename T>
std::vector<std::vector<T>>
read_records(const std::string& path, int32_t expected_dim) {
    std::ifstream input(path, std::ios::binary | std::ios::ate);
    require(static_cast<bool>(input), "input open failed");
    const auto size = input.tellg();
    require(size > 0 and size % (sizeof(int32_t) + sizeof(T) * expected_dim) == 0,
            "invalid input file length");
    const auto count = static_cast<uint64_t>(size / (sizeof(int32_t) + sizeof(T) * expected_dim));
    input.seekg(0);
    std::vector<std::vector<T>> records;
    records.reserve(count);
    for (uint64_t i = 0; i < count; ++i) {
        require(read_dim(input) == expected_dim, "inconsistent record dimension");
        std::vector<T> row(expected_dim);
        input.read(reinterpret_cast<char*>(row.data()), sizeof(T) * expected_dim);
        require(static_cast<bool>(input), "truncated record");
        records.push_back(std::move(row));
    }
    return records;
}

double
percentile(std::vector<double> values, double fraction) {
    if (values.empty() or not std::isfinite(fraction) or fraction < 0.0 or fraction > 1.0) {
        throw std::invalid_argument("invalid percentile input");
    }
    std::sort(values.begin(), values.end());
    const auto rank =
        std::max<uint64_t>(
            1, static_cast<uint64_t>(std::ceil(fraction * static_cast<double>(values.size())))) -
        1;
    return values[rank];
}

uint64_t
environment_number(const char* name, uint64_t fallback) {
    const char* text = std::getenv(name);
    if (text == nullptr) {
        return fallback;
    }
    const std::string value(text);
    require(
        not value.empty() and
            std::all_of(value.begin(), value.end(), [](char c) { return c >= '0' and c <= '9'; }),
        "invalid graph environment number");
    const auto result = std::stoull(value);
    require(result > 0, "graph environment number must be positive");
    return result;
}

int
run(const std::string& directory,
    const std::string& snapshot,
    uint64_t rounds,
    uint64_t crud_ops,
    const std::string& query_results) {
    const auto base_path = directory + "/base.fvecs";
    const auto query_path = directory + "/queries.fvecs";
    const auto truth_path = directory + "/groundtruth.ivecs";
    const int32_t dim = [&] {
        std::ifstream file(base_path, std::ios::binary);
        require(static_cast<bool>(file), "base open failed");
        return read_dim(file);
    }();
    const int32_t k = [&] {
        std::ifstream file(truth_path, std::ios::binary);
        require(static_cast<bool>(file), "groundtruth open failed");
        return read_dim(file);
    }();
    require(not std::filesystem::exists(snapshot), "snapshot path already exists");
    require(query_results.empty() or not std::filesystem::exists(query_results),
            "query results path already exists");

    require(query_results.empty() or not std::filesystem::exists(query_results + ".latencies.csv"),
            "latency results path already exists");
    require(query_results.empty() or not std::filesystem::exists(query_results + ".neighbors.csv"),
            "neighbor results path already exists");

    const char* replacement_path = std::getenv("VSAG_GRAPH_REPLACEMENTS");
    const bool persistent = replacement_path != nullptr;
    const char* selected_mode = std::getenv("VSAG_GRAPH_CRUD_MODE");
    const std::string mutation_mode = selected_mode == nullptr ? "all" : selected_mode;
    require(mutation_mode == "all" or mutation_mode == "update" or mutation_mode == "replace",
            "invalid CRUD replay mode");
    require(selected_mode == nullptr or persistent, "CRUD mode requires persistent replacements");
    require(not persistent or (rounds > 0 and not query_results.empty()),
            "replacement replay requires rounds and query evidence");
    if (persistent) {
        for (const auto& suffix :
             {".operations.csv", ".initial", ".initial.latencies.csv", ".initial.neighbors.csv"}) {
            require(not std::filesystem::exists(query_results + suffix),
                    "replacement evidence already exists");
        }
    }
    auto base = read_records<float>(base_path, dim);
    auto queries = read_records<float>(query_path, dim);
    auto truth = read_records<int32_t>(truth_path, k);
    auto initial_truth = truth;
    std::vector<std::vector<float>> replacements;
    if (persistent) {
        require(rounds <= std::numeric_limits<uint64_t>::max() / crud_ops,
                "replacement cycle count overflow");
        replacements = read_records<float>(replacement_path, dim);
        require(replacements.size() == rounds * crud_ops, "replacement count mismatch");
        std::vector<int64_t> previous(base.size(), -1);
        for (uint64_t cycle = 0; cycle < replacements.size(); ++cycle) {
            const uint64_t id =
                ((cycle / crud_ops) * 65537ULL + (cycle % crud_ops) * 8191ULL) % base.size();
            const auto& prior =
                previous[id] < 0 ? base[id] : replacements[static_cast<uint64_t>(previous[id])];
            require(std::all_of(replacements[cycle].begin(),
                                replacements[cycle].end(),
                                [](float value) { return std::isfinite(value); }) and
                        replacements[cycle] != prior,
                    "replacement must change a finite vector");
            previous[id] = static_cast<int64_t>(cycle);
        }
        truth = read_records<int32_t>(directory + "/changed-groundtruth.ivecs", k);
    }
    require(queries.size() == truth.size() and queries.size() == initial_truth.size(),
            "query and groundtruth count differ");
    require(not base.empty() and not queries.empty() and static_cast<uint64_t>(k) <= base.size(),
            "invalid dataset shape");
    for (const auto* set : {&initial_truth, &truth}) {
        for (const auto& expected : *set) {
            require(std::unordered_set<int32_t>(expected.begin(), expected.end()).size() ==
                        expected.size(),
                    "duplicate groundtruth ID");
            for (const int32_t id : expected) {
                require(id >= 0 and static_cast<uint64_t>(id) < base.size(),
                        "groundtruth ID outside base");
            }
        }
    }
    const char* diagnostic_text = std::getenv("VSAG_GRAPH_DIAGNOSTIC_EF");
    const uint64_t diagnostic_budget =
        diagnostic_text == nullptr ? 0 : environment_number("VSAG_GRAPH_DIAGNOSTIC_EF", 1);
    if (diagnostic_text != nullptr) {
        require(persistent and diagnostic_budget == base.size(),
                "diagnostic requires persistent replay and the full node count");
        for (const auto& suffix : {".diagnostic.initial", ".diagnostic.final"}) {
            for (const auto& sidecar : {"", ".latencies.csv", ".neighbors.csv"}) {
                require(not std::filesystem::exists(query_results + suffix + sidecar),
                        "diagnostic evidence already exists");
            }
        }
        require(not std::filesystem::exists(query_results + ".diagnostic.summary.csv"),
                "diagnostic summary already exists");
    }
    auto created = vsag::lite::Index::Create(dim);
    require(static_cast<bool>(created), "index create failed");
    auto index = std::move(*created);
    auto start = Clock::now();
    for (uint64_t i = 0; i < base.size(); ++i) {
        auto added = index->Add(static_cast<int64_t>(i), base[i].data(), dim);
        require(static_cast<bool>(added), "index add failed");
    }
    const char* selected = std::getenv("VSAG_GRAPH_STORAGE");
    const std::string storage = selected == nullptr ? "fp32" : selected;
    require(storage == "fp32" or storage == "fp16" or storage == "rabitq8",
            "invalid graph storage selection");
    const auto representation = storage == "fp16"      ? vsag::lite::VectorStorage::FP16
                                : storage == "rabitq8" ? vsag::lite::VectorStorage::RABITQ8
                                                       : vsag::lite::VectorStorage::FP32;
    const uint64_t degree = environment_number("VSAG_GRAPH_DEGREE", 16);
    const uint64_t ef = environment_number("VSAG_GRAPH_EF", 128);
    const vsag::lite::SearchOptions options{environment_number("VSAG_GRAPH_QUERY_EF", ef)};
    require(static_cast<bool>(index->BuildGraph(representation, degree, ef)), "graph build failed");
    const auto build_ms = std::chrono::duration<double, std::milli>(Clock::now() - start).count();
    const auto measure = [&](const auto& expected_truth,
                             const std::string& evidence,
                             const vsag::lite::SearchOptions& search_options) {
        uint64_t hits = 0;
        std::vector<double> latencies;
        std::vector<uint64_t> query_hits;
        std::vector<std::vector<vsag::lite::Neighbor>> before;
        for (uint64_t i = 0; i < queries.size(); ++i) {
            start = Clock::now();
            auto result = index->SearchWithOptions(queries[i].data(), dim, k, search_options);
            latencies.push_back(
                std::chrono::duration<double, std::micro>(Clock::now() - start).count());
            require(static_cast<bool>(result) and result->size() == static_cast<uint64_t>(k),
                    "search failed");
            std::unordered_set<int64_t> expected(expected_truth[i].begin(),
                                                 expected_truth[i].end());
            uint64_t current_hits = 0;
            for (const auto& neighbor : *result) {
                current_hits += expected.count(neighbor.id);
            }
            hits += current_hits;
            query_hits.push_back(current_hits);
            before.push_back(std::move(*result));
        }
        if (not evidence.empty()) {
            std::ofstream query_output(evidence);
            require(static_cast<bool>(query_output), "query results open failed");
            query_output << "query,hits,k,recall_at_k\n";
            for (uint64_t i = 0; i < query_hits.size(); ++i) {
                query_output << i << ',' << query_hits[i] << ',' << k << ','
                             << static_cast<double>(query_hits[i]) / k << '\n';
            }
            require(static_cast<bool>(query_output), "query results write failed");
            std::ofstream timings(evidence + ".latencies.csv");
            timings << "query,latency_us\n" << std::fixed << std::setprecision(6);
            for (uint64_t query = 0; query < latencies.size(); ++query) {
                timings << query << ',' << latencies[query] << '\n';
            }
            require(static_cast<bool>(timings), "latency results write failed");
            std::ofstream neighbors(evidence + ".neighbors.csv");
            require(static_cast<bool>(neighbors), "neighbor results open failed");
            neighbors << "query,rank,id,distance\n" << std::hexfloat;
            for (uint64_t query = 0; query < before.size(); ++query) {
                for (uint64_t rank = 0; rank < before[query].size(); ++rank) {
                    const auto& neighbor = before[query][rank];
                    neighbors << query << ',' << rank << ',' << neighbor.id << ','
                              << neighbor.distance << '\n';
                }
            }
            require(static_cast<bool>(neighbors), "neighbor results write failed");
        }
        return std::make_tuple(hits, std::move(latencies), std::move(before));
    };
    double initial_recall = 0;
    if (persistent) {
        const auto initial = measure(initial_truth, query_results + ".initial", options);
        initial_recall =
            static_cast<double>(std::get<0>(initial)) / static_cast<double>(queries.size() * k);
    }
    uint64_t diagnostic_initial_hits = 0;
    if (diagnostic_budget != 0) {
        diagnostic_initial_hits =
            std::get<0>(measure(initial_truth,
                                query_results + ".diagnostic.initial",
                                vsag::lite::SearchOptions{diagnostic_budget}));
    }
    std::vector<std::tuple<uint64_t, uint64_t, uint64_t, double>> operation_samples;
    if (persistent) {
        require(replacements.size() <= std::numeric_limits<uint64_t>::max() / 3,
                "operation sample count overflow");
        operation_samples.reserve(replacements.size() * 3);
    }
    const auto crud_start = Clock::now();
    for (uint64_t round = 0; round < rounds; ++round) {
        for (uint64_t operation = 0; operation < crud_ops; ++operation) {
            const uint64_t id = (round * 65537ULL + operation * 8191ULL) % base.size();
            const uint64_t cycle = round * crud_ops + operation;
            const float* vector = persistent ? replacements[cycle].data() : base[id].data();
            const auto timed = [&](uint64_t kind, const auto& action) {
                if (not persistent) {
                    action();
                    return;
                }
                const auto begin = Clock::now();
                action();
                if (persistent) {
                    const double latency =
                        std::chrono::duration<double, std::micro>(Clock::now() - begin).count();
                    operation_samples.emplace_back(cycle, id, kind, latency);
                }
            };
            if (mutation_mode != "replace") {
                timed(0, [&] {
                    require(static_cast<bool>(index->Update(static_cast<int64_t>(id), vector, dim)),
                            "update failed");
                });
            }
            if (mutation_mode != "update") {
                timed(1,
                      [&] { require(index->Remove(static_cast<int64_t>(id)), "remove failed"); });
                timed(2, [&] {
                    require(static_cast<bool>(index->Add(static_cast<int64_t>(id), vector, dim)),
                            "re-add failed");
                });
            }
        }
    }
    const auto crud_ms =
        std::chrono::duration<double, std::milli>(Clock::now() - crud_start).count();
    require(index->Size() == base.size(), "live count changed");
    auto [hits, latencies, before] = measure(truth, query_results, options);
    if (persistent) {
        std::ofstream samples(query_results + ".operations.csv");
        samples << "cycle,id,operation,latency_us\n" << std::setprecision(9);
        for (const auto& [cycle, id, operation, latency] : operation_samples) {
            samples << cycle << ',' << id << ',' << operation << ',' << latency << '\n';
        }
        require(static_cast<bool>(samples), "operation evidence write failed");
    }
    if (diagnostic_budget != 0) {
        const auto full = measure(truth,
                                  query_results + ".diagnostic.final",
                                  vsag::lite::SearchOptions{diagnostic_budget});
        std::ofstream diagnostic(query_results + ".diagnostic.summary.csv");
        diagnostic << "budget,initial_recall,final_recall\n"
                   << std::setprecision(9) << diagnostic_budget << ','
                   << static_cast<double>(diagnostic_initial_hits) /
                          static_cast<double>(queries.size() * k)
                   << ','
                   << static_cast<double>(std::get<0>(full)) /
                          static_cast<double>(queries.size() * k)
                   << '\n';
        require(static_cast<bool>(diagnostic), "diagnostic summary write failed");
    }
    start = Clock::now();
    std::ofstream output(snapshot, std::ios::binary);
    require(static_cast<bool>(output) and static_cast<bool>(index->Save(output)), "save failed");
    output.close();
    require(static_cast<bool>(output), "snapshot close failed");
    const auto save_ms = std::chrono::duration<double, std::milli>(Clock::now() - start).count();
    start = Clock::now();
    std::ifstream input(snapshot, std::ios::binary);
    auto loaded = vsag::lite::Index::Load(input);
    require(static_cast<bool>(loaded) and (*loaded)->Size() == base.size(), "load failed");
    const auto load_ms = std::chrono::duration<double, std::milli>(Clock::now() - start).count();
    for (uint64_t i = 0; i < queries.size(); ++i) {
        auto after = (*loaded)->SearchWithOptions(queries[i].data(), dim, k, options);
        require(static_cast<bool>(after) and after->size() == before[i].size(),
                "post-load search failed");
        for (uint64_t j = 0; j < before[i].size(); ++j) {
            require(
                (*after)[j].id == before[i][j].id and (*after)[j].distance == before[i][j].distance,
                "post-load result changed");
        }
    }
    std::cout << "base_count,query_count,dim,k,rounds,crud_ops,recall_at_k,build_ms,search_p50_us,"
                 "search_p99_us,save_ms,load_ms,snapshot_bytes,storage,max_degree,ef_search,crud_"
                 "ms,query_ef_search";
    if (persistent) {
        std::cout << ",persistent_replacements,initial_recall_at_k";
        if (selected_mode != nullptr) {
            std::cout << ",mutation_mode";
        }
    }
    std::cout << '\n';
    std::cout << base.size() << ',' << queries.size() << ',' << dim << ',' << k << ',' << rounds
              << ',' << crud_ops << ',' << std::fixed << std::setprecision(6)
              << static_cast<double>(hits) / static_cast<double>(queries.size() * k) << ','
              << build_ms << ',' << percentile(latencies, 0.50) << ','
              << percentile(latencies, 0.99) << ',' << save_ms << ',' << load_ms << ','
              << std::filesystem::file_size(snapshot) << ',' << storage << ',' << degree << ','
              << ef << ',' << crud_ms << ',' << options.ef_search;
    if (persistent) {
        std::cout << ',' << replacements.size() << ',' << initial_recall;
        if (selected_mode != nullptr) {
            std::cout << ',' << mutation_mode;
        }
    }
    std::cout << '\n';
    return 0;
}
}  // namespace

int
main(int argc, char** argv) {
    try {
        require(argc == 5 or argc == 6,
                "usage: lite_graph_crud_quality DATASET SNAPSHOT ROUNDS CRUD_OPS "
                "[QUERY_RESULTS]");
        const auto rounds = std::stoull(argv[3]);
        const auto crud_ops = std::stoull(argv[4]);
        require(crud_ops > 0, "CRUD_OPS must be positive");
        return run(argv[1], argv[2], rounds, crud_ops, argc == 6 ? argv[5] : "");
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
