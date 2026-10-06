#include <algorithm>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

template <typename T>
std::vector<std::vector<T>>
records(const std::string& path) {
    std::ifstream input(path, std::ios::binary);
    if (!input)
        throw std::runtime_error("input open failed");
    std::vector<std::vector<T>> rows;
    int32_t dim = 0;
    while (input.read(reinterpret_cast<char*>(&dim), 4)) {
        if (dim <= 0 || dim > 4096)
            throw std::runtime_error("invalid dimension");
        std::vector<T> row(dim);
        if (!input.read(reinterpret_cast<char*>(row.data()), dim * sizeof(T)))
            throw std::runtime_error("truncated record");
        rows.push_back(std::move(row));
    }
    return rows;
}
int
main(int argc, char** argv) {
    if (argc != 2)
        return 2;
    const std::string root = argv[1];
    const auto base = records<float>(root + "/base.fvecs");
    const auto queries = records<float>(root + "/queries.fvecs");
    const auto truth = records<int32_t>(root + "/groundtruth.ivecs");
    std::cout << "query,top10_set_equal\n";
    for (uint64_t query : {0, 85, 171, 256, 342, 428, 513, 599}) {
        std::vector<std::pair<double, uint64_t>> distances;
        for (uint64_t id = 0; id < base.size(); ++id) {
            double value = 0;
            for (uint64_t d = 0; d < queries.at(query).size(); ++d) {
                const double delta = double(base[id][d]) - double(queries[query][d]);
                value += delta * delta;
            }
            distances.emplace_back(value, id);
        }
        std::partial_sort(distances.begin(), distances.begin() + 10, distances.end());
        std::vector<uint64_t> exact;
        for (uint64_t i = 0; i < 10; ++i) exact.push_back(distances[i].second);
        std::vector<uint64_t> expected(truth.at(query).begin(), truth.at(query).end());
        std::sort(exact.begin(), exact.end());
        std::sort(expected.begin(), expected.end());
        std::cout << query << ',' << (exact == expected) << '\n';
        if (exact != expected)
            return 1;
    }
}
