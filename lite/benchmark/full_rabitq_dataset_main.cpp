// Copyright 2024-present the vsag project
// SPDX-License-Identifier: Apache-2.0
#include <malloc.h>
#include <sys/resource.h>
#include <vsag/dataset.h>
#include <vsag/factory.h>
#include <vsag/index.h>

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <ctime>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <string>
#include <unordered_set>
#include <vector>

namespace {
using Clock = std::chrono::steady_clock;

struct Neighbor {
    int64_t id;
    float distance;
};

template <typename T>
struct Matrix {
    int32_t dim{0};
    uint64_t count{0};
    std::vector<T> values;
};

void
require(bool condition, const std::string& message) {
    if (not condition) {
        throw std::runtime_error(message);
    }
}

template <typename T>
Matrix<T>
read_matrix(const std::string& path, int32_t expected_dim = 0) {
    std::ifstream input(path, std::ios::binary);
    require(static_cast<bool>(input), "input open failed: " + path);
    Matrix<T> matrix;
    while (true) {
        int32_t dim = 0;
        input.read(reinterpret_cast<char*>(&dim), sizeof(dim));
        if (input.eof()) {
            break;
        }
        require(static_cast<bool>(input) and dim > 0 and dim <= 4096, "invalid record dimension");
        if (matrix.dim == 0) {
            matrix.dim = dim;
        }
        require(dim == matrix.dim and (expected_dim == 0 or dim == expected_dim),
                "inconsistent record dimension");
        const auto offset = matrix.values.size();
        matrix.values.resize(offset + static_cast<uint64_t>(dim));
        input.read(reinterpret_cast<char*>(matrix.values.data() + offset), sizeof(T) * dim);
        require(static_cast<bool>(input), "truncated record");
        ++matrix.count;
    }
    require(matrix.count > 0, "empty input");
    return matrix;
}

double
percentile(std::vector<double> values, double fraction) {
    require(not values.empty() and std::isfinite(fraction) and fraction >= 0.0 and fraction <= 1.0,
            "invalid percentile input");
    std::sort(values.begin(), values.end());
    const auto rank =
        std::max<uint64_t>(
            1, static_cast<uint64_t>(std::ceil(fraction * static_cast<double>(values.size())))) -
        1;
    return values[rank];
}

uint64_t
parse_number(const char* value) {
    const std::string text(value);
    require(
        not text.empty() and
            std::all_of(text.begin(), text.end(), [](char ch) { return ch >= '0' and ch <= '9'; }),
        "expected a nonnegative integer");
    return std::stoull(text);
}

uint64_t
current_rss_kib() {
    std::ifstream status("/proc/self/status");
    std::string key;
    while (status >> key) {
        if (key == "VmRSS:") {
            uint64_t value = 0;
            std::string unit;
            status >> value >> unit;
            require(unit == "kB", "unexpected VmRSS unit");
            return value;
        }
        std::string remainder;
        std::getline(status, remainder);
    }
    throw std::runtime_error("VmRSS is unavailable");
}

std::string
create_parameters(int32_t dim, const std::string& mode, bool force_remove = false) {
    const std::string prefix =
        std::string(R"({"dtype":"float32","metric_type":"l2","dim":)") + std::to_string(dim) +
        R"(,"index_param":{"max_degree":16,"ef_construction":128,)" +
        (force_remove ? R"("support_force_remove":true,"use_reverse_edges":true,)" : "") +
        (force_remove ? R"("graph_storage_type":"flat",)"
                      : R"("graph_storage_type":"compressed",)");
    if (mode == "fp32") {
        return prefix + R"("base_quantization_type":"fp32","store_raw_vector":true}})";
    }
    if (mode == "rabitq1") {
        return prefix + R"("base_quantization_type":"rabitq","precise_quantization_type":"fp32",)"
                        R"("use_reorder":true,"store_raw_vector":true,"rabitq_use_fht":true,)"
                        R"("rabitq_bits_per_dim_query":32,"rabitq_bits_per_dim_base":1}})";
    }
    if (mode == "rabitq3x5") {
        return prefix +
               R"("base_quantization_type":"rabitq","precise_quantization_type":"rabitq",)"
               R"("use_reorder":true,"rabitq_use_fht":true,"rabitq_bits_per_dim_query":32,)"
               R"("rabitq_bits_per_dim_base":3,"rabitq_bits_per_dim_precise":5,)"
               R"("rabitq_error_rate":1.9}})";
    }
    throw std::invalid_argument("mode must be fp32, rabitq1, or rabitq3x5");
}

std::string
search_parameters(const std::string& mode, uint64_t ef_search) {
    return std::string(R"({"hgraph":{"ef_search":)") + std::to_string(ef_search) +
           R"(,"rabitq_one_bit_search":)" + (mode == "fp32" ? "false" : "true") + "}}";
}

std::shared_ptr<vsag::Index>
create_index(int32_t dim, const std::string& mode, bool force_remove = false) {
    auto created = vsag::Factory::CreateIndex("hgraph", create_parameters(dim, mode, force_remove));
    require(static_cast<bool>(created), "index create failed");
    return *created;
}

std::vector<Neighbor>
search(const std::shared_ptr<vsag::Index>& index,
       const vsag::DatasetPtr& query,
       int32_t k,
       const std::string& parameters,
       bool allow_short = false) {
    auto result = index->KnnSearch(query, k, parameters);
    require(static_cast<bool>(result), "search API failed");
    const auto count = (*result)->GetDim();
    require(count >= 0 and count <= k and (allow_short or count == k), "search size differs");
    std::vector<Neighbor> neighbors;
    neighbors.reserve(k);
    for (int64_t i = 0; i < count; ++i) {
        neighbors.push_back({(*result)->GetIds()[i], (*result)->GetDistances()[i]});
    }
    return neighbors;
}

void
measure_mixed(const std::shared_ptr<vsag::Index>& index,
              const std::string& directory,
              const std::string& snapshot,
              const Matrix<float>& queries,
              const Matrix<int32_t>& truth,
              const std::string& parameters,
              uint64_t cycles,
              uint64_t every,
              bool diagnose) {
    const auto base = read_matrix<float>(directory + "/base.fvecs", queries.dim);
    std::vector<double> mutation_us[4];
    std::vector<double> query_us;
    std::vector<uint64_t> query_hits;
    std::vector<uint64_t> query_counts;
    std::vector<std::string> diagnostics;
    double mutation_cpu_ms = 0;
    double query_cpu_ms = 0;
    std::vector<float> changed(base.dim);
    int64_t id = 0;
    auto mutation = vsag::Dataset::Make()->NumElements(1)->Dim(base.dim)->Ids(&id)->Owner(false);
    auto query = vsag::Dataset::Make()->NumElements(1)->Dim(base.dim)->Owner(false);
    const auto cpu_start = std::clock();
    for (uint64_t i = 0; i < cycles; ++i) {
        const auto mutation_start = std::clock();
        id = static_cast<int64_t>((i * 8191ULL) % base.count);
        const auto* original = base.values.data() + static_cast<uint64_t>(id) * base.dim;
        std::copy_n(original, base.dim, changed.data());
        changed[0] += 0.125F;
        const auto timed = [&](uint64_t operation, const auto& action) {
            const auto start = Clock::now();
            require(action(), "Full mixed mutation failed");
            mutation_us[operation].push_back(
                std::chrono::duration<double, std::micro>(Clock::now() - start).count());
        };
        mutation->Float32Vectors(changed.data());
        timed(0, [&] {
            auto result = index->UpdateVector(id, mutation, true);
            return result and *result;
        });
        mutation->Float32Vectors(original);
        timed(1, [&] {
            auto result = index->UpdateVector(id, mutation, true);
            return result and *result;
        });
        timed(2, [&] {
            auto result = index->Remove(id, vsag::RemoveMode::FORCE_REMOVE);
            return result and *result == 1;
        });
        require(index->GetNumElements() == static_cast<int64_t>(base.count - 1),
                "Full remove live count differs");
        timed(3, [&] {
            auto result = index->Add(mutation);
            return result and result->empty();
        });
        require(index->GetNumElements() == static_cast<int64_t>(base.count),
                "Full readd live count differs");
        mutation_cpu_ms +=
            1000.0 * static_cast<double>(std::clock() - mutation_start) / CLOCKS_PER_SEC;
        if ((i + 1) % every == 0) {
            const uint64_t row = query_us.size() % queries.count;
            query->Float32Vectors(queries.values.data() + row * queries.dim);
            const auto query_start = std::clock();
            const auto start = Clock::now();
            const auto result = search(index, query, truth.dim, parameters, true);
            query_us.push_back(
                std::chrono::duration<double, std::micro>(Clock::now() - start).count());
            query_cpu_ms +=
                1000.0 * static_cast<double>(std::clock() - query_start) / CLOCKS_PER_SEC;
            const auto* expected = truth.values.data() + row * truth.dim;
            std::unordered_set<int32_t> valid(expected, expected + truth.dim);
            uint64_t hits = 0;
            for (const auto& neighbor : result) {
                hits += valid.count(static_cast<int32_t>(neighbor.id));
            }
            query_hits.push_back(hits);
            query_counts.push_back(result.size());
            if (diagnose and result.size() < static_cast<uint64_t>(truth.dim)) {
                // Diagnostic-only reruns alter the whole-loop timer; never use it as a benchmark.
                for (const uint64_t budget : {128ULL, 512ULL, 100000ULL}) {
                    const auto retry =
                        search(index, query, truth.dim, search_parameters("fp32", budget), true);
                    uint64_t retry_hits = 0;
                    for (const auto& neighbor : retry) {
                        retry_hits += valid.count(static_cast<int32_t>(neighbor.id));
                    }
                    diagnostics.push_back(
                        std::to_string(i + 1) + "," + std::to_string(row) + "," +
                        std::to_string(budget) + "," + std::to_string(retry.size()) + "," +
                        std::to_string(retry_hits) + "," +
                        (retry.empty() ? "-1" : std::to_string(retry.front().id)));
                }
            }
        }
    }
    const auto total_cpu_ms =
        1000.0 * static_cast<double>(std::clock() - cpu_start) / CLOCKS_PER_SEC;
    uint64_t end_hits = 0;
    for (uint64_t row = 0; row < queries.count; ++row) {
        query->Float32Vectors(queries.values.data() + row * queries.dim);
        const auto result = search(index, query, truth.dim, parameters, true);
        const auto* expected = truth.values.data() + row * truth.dim;
        std::unordered_set<int32_t> valid(expected, expected + truth.dim);
        for (const auto& neighbor : result) {
            end_hits += valid.count(static_cast<int32_t>(neighbor.id));
        }
    }
    if (diagnose) {
        std::ofstream diagnostic(snapshot + ".diagnostic.csv");
        diagnostic << "cycle,query,ef_search,returned_count,hits,first_id\n";
        for (const auto& row : diagnostics) {
            diagnostic << row << '\n';
        }
        diagnostic.close();
        require(static_cast<bool>(diagnostic), "Full diagnostic samples write failed");
    }
    std::ofstream samples(snapshot + ".crud.samples.csv");
    samples << "cycle,update_us,restore_us,remove_us,readd_us\n"
            << std::fixed << std::setprecision(6);
    for (uint64_t i = 0; i < cycles; ++i) {
        samples << i;
        for (const auto& operation : mutation_us) {
            samples << ',' << operation[i];
        }
        samples << '\n';
    }
    samples.close();
    require(static_cast<bool>(samples), "Full mutation samples write failed");
    std::ofstream mixed(snapshot + ".mixed.csv");
    mixed << "query_event,query,latency_us,hits,returned_count\n"
          << std::fixed << std::setprecision(6);
    uint64_t mixed_hits = 0;
    for (uint64_t i = 0; i < query_us.size(); ++i) {
        mixed << i << ',' << i % queries.count << ',' << query_us[i] << ',' << query_hits[i] << ','
              << query_counts[i] << '\n';
        mixed_hits += query_hits[i];
    }
    mixed.close();
    require(static_cast<bool>(mixed), "Full query samples write failed");
    std::ofstream output(snapshot + ".crud.csv");
    output << "cycles,query_every,mixed_queries,end_recall_at_k,mixed_recall_at_k,"
              "mutation_cpu_ms,query_cpu_ms,mixed_loop_cpu_ms,mixed_p50_us,mixed_p99_us\n";
    output << std::fixed << std::setprecision(6) << cycles << ',' << every << ',' << query_us.size()
           << ',' << static_cast<double>(end_hits) / static_cast<double>(queries.count * truth.dim)
           << ','
           << static_cast<double>(mixed_hits) / static_cast<double>(query_us.size() * truth.dim)
           << ',' << mutation_cpu_ms << ',' << query_cpu_ms << ',' << total_cpu_ms << ','
           << percentile(query_us, 0.5) << ',' << percentile(query_us, 0.99) << '\n';
    output.close();
    require(static_cast<bool>(output), "Full mixed summary write failed");
}

int
run(const std::string& directory,
    const std::string& snapshot,
    const std::string& mode,
    uint64_t ef_search,
    uint64_t warmup_rounds,
    uint64_t crud_cycles,
    uint64_t query_every,
    bool diagnose) {
    require(not std::filesystem::exists(snapshot), "snapshot path already exists");
    auto base = read_matrix<float>(directory + "/base.fvecs");
    const auto queries = read_matrix<float>(directory + "/queries.fvecs", base.dim);
    const auto truth = read_matrix<int32_t>(directory + "/groundtruth.ivecs");
    require(queries.count == truth.count and truth.dim > 0, "query and truth shape differ");
    require(static_cast<uint64_t>(truth.dim) <= base.count, "invalid Top-K");

    std::vector<int64_t> ids(base.count);
    for (uint64_t i = 0; i < base.count; ++i) {
        ids[i] = static_cast<int64_t>(i);
    }
    auto base_dataset = vsag::Dataset::Make()
                            ->NumElements(static_cast<int64_t>(base.count))
                            ->Dim(base.dim)
                            ->Ids(ids.data())
                            ->Float32Vectors(base.values.data())
                            ->Owner(false);
    auto index = create_index(base.dim, mode, crud_cycles != 0);
    auto start = Clock::now();
    auto built = index->Build(base_dataset);
    require(static_cast<bool>(built) and built->empty(), "index build failed");
    const auto build_ms = std::chrono::duration<double, std::milli>(Clock::now() - start).count();

    base_dataset.reset();
    std::vector<float>().swap(base.values);
    std::vector<int64_t>().swap(ids);
    malloc_trim(0);
    const auto build_steady_rss_kib = current_rss_kib();

    std::vector<float> query_vector(base.dim);
    auto query_dataset = vsag::Dataset::Make()
                             ->NumElements(1)
                             ->Dim(base.dim)
                             ->Float32Vectors(query_vector.data())
                             ->Owner(false);
    const auto parameters = search_parameters(mode, ef_search);
    for (uint64_t round = 0; round < warmup_rounds; ++round) {
        for (uint64_t i = 0; i < queries.count; ++i) {
            std::copy_n(queries.values.data() + i * static_cast<uint64_t>(base.dim),
                        base.dim,
                        query_vector.data());
            search(index, query_dataset, truth.dim, parameters);
        }
    }
    uint64_t hits = 0;
    std::vector<double> latencies;
    std::vector<std::vector<Neighbor>> before;
    before.reserve(queries.count);
    const auto query_cpu_start = std::clock();
    for (uint64_t i = 0; i < queries.count; ++i) {
        std::copy_n(queries.values.data() + i * static_cast<uint64_t>(base.dim),
                    base.dim,
                    query_vector.data());
        start = Clock::now();
        auto result = search(index, query_dataset, truth.dim, parameters);
        latencies.push_back(
            std::chrono::duration<double, std::micro>(Clock::now() - start).count());
        const auto* expected_begin = truth.values.data() + i * static_cast<uint64_t>(truth.dim);
        const std::unordered_set<int64_t> expected(expected_begin, expected_begin + truth.dim);
        for (const auto& neighbor : result) {
            hits += expected.count(neighbor.id);
        }
        before.push_back(std::move(result));
    }

    const auto query_cpu_ms =
        1000.0 * static_cast<double>(std::clock() - query_cpu_start) / CLOCKS_PER_SEC;
    std::ofstream samples(snapshot + ".latencies.csv");
    samples << "query,latency_us\n" << std::fixed << std::setprecision(6);
    for (uint64_t i = 0; i < latencies.size(); ++i) {
        samples << i << ',' << latencies[i] << '\n';
    }
    samples.close();
    require(static_cast<bool>(samples), "query samples write failed");

    if (crud_cycles != 0) {
        measure_mixed(index,
                      directory,
                      snapshot,
                      queries,
                      truth,
                      parameters,
                      crud_cycles,
                      query_every,
                      diagnose);
        before.clear();
        for (uint64_t i = 0; i < queries.count; ++i) {
            std::copy_n(queries.values.data() + i * static_cast<uint64_t>(base.dim),
                        base.dim,
                        query_vector.data());
            before.push_back(search(index, query_dataset, truth.dim, parameters, true));
        }
    }

    start = Clock::now();
    std::ofstream output(snapshot, std::ios::binary);
    require(static_cast<bool>(output) and static_cast<bool>(index->Serialize(output)),
            "save failed");
    output.close();
    require(static_cast<bool>(output), "snapshot close failed");
    const auto save_ms = std::chrono::duration<double, std::milli>(Clock::now() - start).count();

    index.reset();
    malloc_trim(0);
    auto loaded = create_index(base.dim, mode, crud_cycles != 0);
    start = Clock::now();
    std::ifstream input(snapshot, std::ios::binary);
    require(static_cast<bool>(input) and static_cast<bool>(loaded->Deserialize(input)),
            "load failed");
    const auto load_ms = std::chrono::duration<double, std::milli>(Clock::now() - start).count();
    require(loaded->GetNumElements() == static_cast<int64_t>(base.count),
            "loaded index size differs");

    for (uint64_t i = 0; i < queries.count; ++i) {
        std::copy_n(queries.values.data() + i * static_cast<uint64_t>(base.dim),
                    base.dim,
                    query_vector.data());
        const auto after = search(loaded, query_dataset, truth.dim, parameters, crud_cycles != 0);
        require(after.size() == before[i].size(), "post-load result size changed");
        for (uint64_t j = 0; j < after.size(); ++j) {
            require(after[j].id == before[i][j].id, "post-load result ID changed");
            const auto scale =
                std::max({1.0F, std::abs(after[j].distance), std::abs(before[i][j].distance)});
            require(std::abs(after[j].distance - before[i][j].distance) <= 1e-5F * scale,
                    "post-load distance changed");
        }
    }

    malloc_trim(0);
    rusage usage{};
    require(getrusage(RUSAGE_SELF, &usage) == 0, "getrusage failed");
    std::cout << "mode,base_count,query_count,dim,k,recall_at_k,build_ms,search_p50_us,"
                 "search_p99_us,save_ms,load_ms,snapshot_bytes,build_steady_rss_kib,"
                 "final_steady_rss_kib,process_peak_rss_kib,query_ef_search,warmup_rounds,"
                 "query_loop_cpu_ms\n";
    std::cout << mode << ',' << base.count << ',' << queries.count << ',' << base.dim << ','
              << truth.dim << ',' << std::fixed << std::setprecision(6)
              << static_cast<double>(hits) / static_cast<double>(queries.count * truth.dim) << ','
              << build_ms << ',' << percentile(latencies, 0.50) << ','
              << percentile(latencies, 0.99) << ',' << save_ms << ',' << load_ms << ','
              << std::filesystem::file_size(snapshot) << ',' << build_steady_rss_kib << ','
              << current_rss_kib() << ',' << usage.ru_maxrss << ',' << ef_search << ','
              << warmup_rounds << ',' << query_cpu_ms << '\n';
    return 0;
}

}  // namespace

int
main(int argc, char** argv) {
    try {
        require((argc >= 4 and argc <= 6) or argc == 8 or argc == 9,
                "usage: full_rabitq_dataset_benchmark DATASET_DIRECTORY SNAPSHOT_PATH "
                "MODE(fp32|rabitq1|rabitq3x5) [EF_SEARCH [WARMUP_ROUNDS [CRUD_CYCLES QUERY_EVERY "
                "[diagnose]]]]");
        const auto ef_search = argc >= 5 ? parse_number(argv[4]) : 128;
        const auto warmup_rounds = argc >= 6 ? parse_number(argv[5]) : 0;
        require(ef_search > 0 and ef_search <= 1000000, "invalid query budget");
        require(warmup_rounds <= 100, "invalid warmup count");
        const auto cycles = argc >= 8 ? parse_number(argv[6]) : 0;
        const auto every = argc >= 8 ? parse_number(argv[7]) : 0;
        require(argc < 8 or (std::string(argv[3]) == "fp32" and cycles > 0 and cycles <= 100000 and
                             every > 0 and every <= cycles),
                "invalid FP32 mixed protocol");
        require(argc != 9 or std::string(argv[8]) == "diagnose", "invalid diagnostic mode");
        if (argc == 9) {
            std::cerr << "DIAGNOSTIC ONLY: whole-loop CPU includes retry queries; "
                         "exclude this run from performance comparisons\n";
        }
        return run(argv[1], argv[2], argv[3], ef_search, warmup_rounds, cycles, every, argc == 9);
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
