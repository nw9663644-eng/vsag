// Copyright 2024-present the vsag project
// SPDX-License-Identifier: Apache-2.0
#define main mutation_trace_main
#include "/home/ubuntu/project/vsag-lite-baseline-v01/lite/benchmark/graph_mutation_trace.cpp"
#undef main

namespace {
void save_graph(const vsag::lite::detail::Backend &graph,
                const std::string &path) {
  require(not std::filesystem::exists(path), "snapshot output exists");
  std::ofstream output(path, std::ios::binary);
  auto write = [&](uint64_t value) {
    output.write(reinterpret_cast<const char *>(&value), sizeof(value));
  };
  uint64_t edges = 0;
  for (uint64_t slot = 0; slot < graph.Size(); ++slot) {
    edges += graph.LinkCountAt(slot);
  }
  output.write("VSAGLT01", 8);
  write(2);
  write(graph.Dim());
  write(graph.Size());
  write(16 + graph.Size() * (16 + 4 * graph.Dim()) + 8 * edges);
  write(2);
  write(graph.MaxDegree());
  write(graph.EfSearch());
  for (uint64_t slot = 0; slot < graph.Size(); ++slot) {
    write(static_cast<uint64_t>(graph.IdAt(slot)));
  }
  std::vector<float> scratch;
  for (uint64_t slot = 0; slot < graph.Size(); ++slot) {
    output.write(reinterpret_cast<const char *>(graph.VectorAt(slot, scratch)),
                 static_cast<std::streamsize>(4 * graph.Dim()));
  }
  for (uint64_t slot = 0; slot < graph.Size(); ++slot) {
    write(graph.LinkCountAt(slot));
    for (uint64_t edge = 0; edge < graph.LinkCountAt(slot); ++edge) {
      write(graph.LinkAt(slot, edge));
    }
  }
  output.flush();
  require(output.good(), "snapshot write failed");
}
} // namespace

int main(int argc, char **argv) {
  try {
    require(argc == 3, "usage: replay INITIAL_SNAPSHOT OUTPUT_DIRECTORY");
    auto source = load_snapshot(argv[1]);
    const auto ids = source.ids;
    const auto vectors = source.vectors;
    const auto dim = source.dim;
    auto restored = vsag::lite::detail::restore_graph_backend(
        dim, source.max_degree, source.ef_search, std::move(source.ids),
        std::move(source.vectors), std::move(source.links));
    require(static_cast<bool>(restored), "restore failed");
    auto graph = std::move(*restored);
    for (uint64_t cycle = 0; cycle <= 7112; ++cycle) {
      const uint64_t original = cycle * 8191ULL % ids.size();
      const auto id = ids[original];
      const auto *vector = vectors.data() + original * dim;
      require(static_cast<bool>(graph->Update(id, vector, dim)),
              "update failed");
      const bool selected = cycle == 1099 or cycle == 3000 or cycle == 7112;
      const auto prefix =
          std::string(argv[2]) + "/cycle-" + std::to_string(cycle);
      if (selected) {
        save_graph(*graph, prefix + "-before.snapshot");
      }
      require(graph->Remove(id), "remove failed");
      if (selected) {
        save_graph(*graph, prefix + "-remove.snapshot");
      }
      require(static_cast<bool>(graph->Add(id, vector, dim)), "add failed");
      if (selected) {
        save_graph(*graph, prefix + "-add.snapshot");
        std::cout << cycle << ',' << id << '\n';
      }
    }
    return 0;
  } catch (const std::exception &error) {
    std::cerr << error.what() << '\n';
    return 1;
  }
}
