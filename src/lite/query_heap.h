// Copyright 2024-present the vsag project
// SPDX-License-Identifier: Apache-2.0
#pragma once

#include <queue>
#include <utility>
#include <vector>

namespace vsag::lite::detail {

// Same ranking/admission as priority_queue; owned data can be consumed once routing ends.
// Native DistanceHeap::GetData likewise exposes retained candidates without popping them.
template <typename T, typename Compare>
class QueryHeap : public std::priority_queue<T, std::vector<T>, Compare> {
    using Base = std::priority_queue<T, std::vector<T>, Compare>;

public:
    using Base::Base;

    [[nodiscard]] const std::vector<T>&
    GetData() const {
        return this->c;
    }

    [[nodiscard]] std::vector<T>
    TakeData() {
        return std::move(this->c);
    }
};

}  // namespace vsag::lite::detail
