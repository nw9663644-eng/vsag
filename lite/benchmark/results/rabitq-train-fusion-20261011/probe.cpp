// Copyright 2024-present the vsag project
// SPDX-License-Identifier: Apache-2.0
#include "lite/rabitq_codec.h"
#include <chrono>
#include <cstring>
#include <iomanip>
#include <iostream>
#include <limits>

int main() {
  namespace codec = vsag::lite::detail::rabitq;
  for (uint64_t dim : {128ULL, 768ULL, 960ULL}) {
    const uint64_t count = 100000;
    std::vector<float> data(count * dim);
    for (uint64_t i = 0; i < data.size(); ++i) {
      data[i] =
          static_cast<float>(static_cast<int64_t>(i % 1999) - 999) / 1024.0F;
    }
    for (uint64_t trial = 0; trial < 6; ++trial) {
      uint64_t calls = 0;
      const auto start = std::chrono::steady_clock::now();
      auto model = codec::train_rows(count, dim, 47, [&](uint64_t row) {
        ++calls;
        return data.data() + row * dim;
      });
      const double elapsed = std::chrono::duration<double, std::milli>(
                                 std::chrono::steady_clock::now() - start)
                                 .count();
      uint64_t hash = 14695981039346656037ULL;
      for (float value : model.centroid) {
        uint32_t bits{};
        std::memcpy(&bits, &value, sizeof(bits));
        hash = (hash ^ bits) * 1099511628211ULL;
      }
      for (uint8_t value : model.flips) {
        hash = (hash ^ value) * 1099511628211ULL;
      }
      std::cout << dim << ',' << trial << ',' << std::setprecision(12)
                << elapsed << ',' << calls << ',' << hash << '\n';
    }
  }
  // Source rows may share one scratch buffer; no row pointer may escape a call.
  std::vector<float> scratch(17);
  const auto scratch_model = codec::train_rows(3, 17, 47, [&](uint64_t row) {
    std::fill(scratch.begin(), scratch.end(), static_cast<float>(row));
    return scratch.data();
  });
  const std::vector<float> matrix(51, 1.0F);
  const auto reference = codec::train(matrix, 3, 17, 47);
  if (scratch_model.centroid != reference.centroid or
      scratch_model.flips != reference.flips) {
    return 1;
  }
  for (float invalid : {std::numeric_limits<float>::infinity(),
                        std::numeric_limits<float>::quiet_NaN()}) {
    std::vector<float> broken(51, 1.0F);
    broken.back() = invalid;
    bool rejected = false;
    try {
      (void)codec::train(broken, 3, 17, 47);
    } catch (const std::exception &) {
      rejected = true;
    }
    if (not rejected) {
      return 2;
    }
  }
  return 0;
}
