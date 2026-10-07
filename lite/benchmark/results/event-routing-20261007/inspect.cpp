// Copyright 2024-present the vsag project
// SPDX-License-Identifier: Apache-2.0
#define main route_probe_main
#include "/home/ubuntu/project/vsag-lite-baseline-v01/lite/benchmark/graph_route_probe.cpp"
#undef main

int main(int argc, char **argv) {
  try {
    require(argc == 4, "usage: inspect SNAPSHOT ONE_QUERY_DATASET OUTPUT");
    require(not std::filesystem::exists(argv[3]), "output exists");
    auto graph = load_snapshot(argv[1]);
    const auto queries =
        read_records<float>(std::string(argv[2]) + "/queries.fvecs", graph.dim);
    const auto truth =
        read_records<int32_t>(std::string(argv[2]) + "/groundtruth.ivecs", 10);
    require(queries.size() == 1 and truth.size() == 1,
            "requires one top-10 query");
    const auto trace = search(graph, select_entries(graph, "uniform"),
                              "uniform", queries[0].data(), 10);
    std::ifstream input(argv[1], std::ios::binary);
    auto index = vsag::lite::Index::Load(input);
    require(static_cast<bool>(index), "public load failed");
    const auto native = (*index)->Search(queries[0].data(), graph.dim, 10);
    require(static_cast<bool>(native) and native->size() == 10,
            "public search failed");
    std::unordered_set<int64_t> scalar_ids;
    std::unordered_set<int64_t> native_ids;
    const std::unordered_set<int64_t> expected(truth[0].begin(),
                                               truth[0].end());
    for (const auto &result : trace.result) {
      scalar_ids.insert(graph.ids[result.slot]);
    }
    for (const auto &result : *native) {
      native_ids.insert(result.id);
    }
    require(scalar_ids == native_ids,
            "scalar and native result ID sets differ");
    std::ofstream output(argv[3]);
    output << "id,slot,visited,scalar_returned,native_returned,truth\n";
    for (uint64_t slot = 0; slot < graph.ids.size(); ++slot) {
      const auto id = graph.ids[slot];
      output << id << ',' << slot << ','
             << static_cast<uint64_t>(trace.visited[slot]) << ','
             << scalar_ids.count(id) << ',' << native_ids.count(id) << ','
             << expected.count(id) << '\n';
    }
    output.flush();
    require(output.good(), "output write failed");
    return 0;
  } catch (const std::exception &error) {
    std::cerr << error.what() << '\n';
    return 1;
  }
}
