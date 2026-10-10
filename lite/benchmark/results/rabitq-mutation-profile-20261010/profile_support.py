# Copyright 2024-present the vsag project
# SPDX-License-Identifier: Apache-2.0
PROFILER = "// Copyright 2024-present the vsag project\n// SPDX-License-Identifier: Apache-2.0\n#pragma once\n#include <array>\n#include <chrono>\n#include <cstdio>\n#include <ctime>\nnamespace vsag::lite::detail::rabitq::diagnostic {\nenum Stage { ADAPTER, NEAREST, DECODE, LINK, REPAIR, SCORE, SCAN, ENCODE, STAGES };\ninline const char* names[] = {\"adapter\", \"nearest\", \"decode\", \"link_other\", \"repair_other\",\n                              \"score_and_sort\", \"incoming_scan\", \"prepare_encoding\"};\ninline const char* ops[] = {\"add\", \"update\", \"remove\"};\ninline int operation = -1;\ninline double cpu_us() {\n    timespec ts{};\n    clock_gettime(CLOCK_PROCESS_CPUTIME_ID, &ts);\n    return ts.tv_sec * 1e6 + ts.tv_nsec / 1e3;\n}\ninline double wall_us() {\n    return std::chrono::duration<double, std::micro>(\n        std::chrono::steady_clock::now().time_since_epoch()).count();\n}\nstruct Value { unsigned long long calls{}; double cpu{}, wall{}, inclusive_cpu{}; };\nstruct Stats {\n    std::array<std::array<Value, STAGES>, 3> values{};\n    ~Stats() {\n        std::fprintf(stderr, \"\\nPROFILE_BEGIN\\nop,stage,calls,cpu_exclusive_us,wall_exclusive_us,cpu_inclusive_us\\n\");\n        for (int op = 0; op < 3; ++op) {\n            for (int stage = 0; stage < STAGES; ++stage) {\n                const auto& v = values[op][stage];\n                std::fprintf(stderr, \"%s,%s,%llu,%.6f,%.6f,%.6f\\n\",\n                    ops[op], names[stage], v.calls, v.cpu, v.wall, v.inclusive_cpu);\n            }\n        }\n        std::fprintf(stderr, \"PROFILE_END\\n\");\n    }\n};\ninline Stats stats;\nstruct Scope;\ninline Scope* current{};\nstruct Scope {\n    Stage stage;\n    int op;\n    Scope* parent{};\n    double cpu{}, wall{}, child_cpu{}, child_wall{};\n    bool done{};\n    explicit Scope(Stage s) : stage(s), op(operation) {\n        if (op < 0) return;\n        parent = current;\n        current = this;\n        wall = wall_us();\n        cpu = cpu_us();\n    }\n    void Finish() {\n        if (done || op < 0) return;\n        const double elapsed_cpu = cpu_us() - cpu;\n        const double elapsed_wall = wall_us() - wall;\n        auto& v = stats.values[op][stage];\n        ++v.calls;\n        v.cpu += elapsed_cpu - child_cpu;\n        v.wall += elapsed_wall - child_wall;\n        v.inclusive_cpu += elapsed_cpu;\n        if (parent) {\n            parent->child_cpu += elapsed_cpu;\n            parent->child_wall += elapsed_wall;\n        }\n        current = parent;\n        done = true;\n    }\n    ~Scope() { Finish(); }\n};\nstruct Operation {\n    int old;\n    Scope scope;\n    explicit Operation(int op) : old(operation), scope(Set(op)) {}\n    static Stage Set(int op) { operation = op; return ADAPTER; }\n    ~Operation() { scope.Finish(); operation = old; }\n};\n}\n"
def instrument(header, codec, adapter):
    header = header.replace('#include <array>', '#include "mutation-profile.h"\n#include <array>', 1)
    for signature, stage in (
        ("decode_query(uint64_t slot) const {", "DECODE"),
        ("nearest(const std::vector<float>& query, float query_norm, uint64_t excluded, uint64_t count) {", "NEAREST"),
        ("           const std::vector<uint64_t>& additional_candidates) {", "REPAIR"),
        ("link(uint64_t source, uint64_t target, std::vector<uint64_t>* displaced_targets = nullptr) {", "LINK")):
        assert header.count(signature) == 1, signature
        header = header.replace(signature, signature + "\n        diagnostic::Scope profile_scope(diagnostic::" + stage + ");", 1)
    marker = "const auto scan_start = measure_mutation_scans_ ? Clock::now() : Clock::time_point{};"
    assert header.count(marker) == 2
    header = header.replace(marker, "diagnostic::Scope profile_scan(diagnostic::SCAN);\n        " + marker)
    for member in ("update_wall_us", "remove_wall_us"):
        marker = "if (measure_mutation_scans_) {\n" + ("            " if member.startswith("update") else "                ") + "mutation_scan_timing_." + member
        assert header.count(marker) == 1, member
        header = header.replace(marker, "profile_scan.Finish();\n        " + marker, 1)
    for start in ("            for (const uint64_t candidate : additional_candidates) {",
                  "            for (uint64_t neighbor : neighbors) {"):
        assert header.count(start) >= 1
        a = header.rindex(start)
        end = "            std::sort(ranked.begin(), ranked.end(), better);"
        b = header.index(end, a) + len(end)
        header = header[:a] + "            { diagnostic::Scope profile_score(diagnostic::SCORE);\n" + header[a:b] + "\n            }" + header[b:]
    codec = codec.replace('#pragma once', '#pragma once\n#include "mutation-profile.h"', 1)
    signature = "prepare_encoding(const Model& model, const float* input) {"
    assert codec.count(signature) == 1
    codec = codec.replace(signature, signature + "\n    diagnostic::Scope profile_encode(diagnostic::ENCODE);")
    for signature, op in (("Add(int64_t id, const float* vector, uint64_t dim) override {", 0),
                          ("Update(int64_t id, const float* vector, uint64_t dim) override {", 1),
                          ("Remove(int64_t id) override {", 2)):
        assert adapter.count(signature) == 1
        adapter = adapter.replace(signature, signature + "\n        rabitq::diagnostic::Operation profile_operation(" + str(op) + ");")
    return header, codec, adapter
