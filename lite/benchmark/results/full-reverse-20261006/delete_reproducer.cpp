// Copyright 2024-present the vsag project
// SPDX-License-Identifier: Apache-2.0
#include <vsag/dataset.h>
#include <vsag/factory.h>
#include <vsag/index.h>

#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

int main(int argc, char **argv) {
  try {
    const std::string mode = argc == 2 ? argv[1] : "remove";
    if (mode != "remove" and mode != "update-remove" and
        mode != "last-remove" and mode != "restored") {
      throw std::invalid_argument("invalid mode");
    }
    auto created = vsag::Factory::CreateIndex(
        "hgraph",
        R"({"dtype":"float32","metric_type":"l2","dim":16,"index_param":{)"
        R"("max_degree":16,"ef_construction":128,"support_force_remove":true,"use_reverse_edges":true,)"
        R"("graph_storage_type":"flat","base_quantization_type":"fp32",)"
        R"("store_raw_vector":true}})");
    if (not created) {
      throw std::runtime_error("create failed");
    }
    auto index = *created;
    std::vector<float> base(8 * 16, 0.0F);
    std::vector<int64_t> ids;
    for (int64_t i = 0; i < 8; ++i) {
      base[i * 16 + i] = 1.0F;
      ids.push_back(i);
    }
    auto data = vsag::Dataset::Make()
                    ->NumElements(8)
                    ->Dim(16)
                    ->Ids(ids.data())
                    ->Float32Vectors(base.data())
                    ->Owner(false);
    auto built = index->Build(data);
    if (not built or not built->empty()) {
      throw std::runtime_error("build failed");
    }
    int64_t id = mode == "last-remove" ? 7 : 0;
    auto single = vsag::Dataset::Make()
                      ->NumElements(1)
                      ->Dim(16)
                      ->Ids(&id)
                      ->Float32Vectors(base.data() + id * 16)
                      ->Owner(false);
    if (mode == "update-remove") {
      auto changed = base;
      changed[0] += 0.125F;
      single->Float32Vectors(changed.data());
      auto updated = index->UpdateVector(id, single, true);
      single->Float32Vectors(base.data());
      auto restored = index->UpdateVector(id, single, true);
      if (not updated or not *updated or not restored or not *restored) {
        throw std::runtime_error("update failed");
      }
    }
    auto removed = index->Remove(id, vsag::RemoveMode::FORCE_REMOVE);
    if (not removed or *removed != 1 or index->GetNumElements() != 7) {
      throw std::runtime_error("remove failed");
    }
    if (mode == "restored") {
      auto added = index->Add(single);
      if (not added or not added->empty() or index->GetNumElements() != 8) {
        throw std::runtime_error("add failed");
      }
    }
    auto query = vsag::Dataset::Make()
                     ->NumElements(1)
                     ->Dim(16)
                     ->Float32Vectors(base.data())
                     ->Owner(false);
    std::cerr << "before query: mode=" << mode
              << " count=" << index->GetNumElements() << std::endl;
    auto result = index->KnnSearch(query, 1, R"({"hgraph":{"ef_search":128}})");
    if (not result) {
      throw std::runtime_error("query API failed");
    }
    std::cout << "returned=" << (*result)->GetDim() << '\n';
    return 0;
  } catch (const std::exception &error) {
    std::cerr << error.what() << '\n';
    return 1;
  }
}
