#!/usr/bin/env python3
# Copyright 2024-present the vsag project
# SPDX-License-Identifier: Apache-2.0
"""Generate a diagnostic header overlay, never change production headers.

Clock probes alter timing. This estimates phase shares only, not product latency.
Instrumented files and compiler command remain in the caller's new scratch folder.
No hardware counters or privileged kernel settings are required.
"""
import argparse
import json
from pathlib import Path
import subprocess


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise RuntimeError("stage marker changed: " + old[:80])
    return text.replace(old, new, 1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("new_directory")
    parser.add_argument("static_library")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    output = Path(args.new_directory).resolve()
    (output/"lite").mkdir(parents=True, exist_ok=False)
    graph = (root/"src/lite/rabitq_graph_state.h").read_text()
    graph = replace_once(graph, "using Clock = std::chrono::steady_clock;",
                         "using Clock = std::chrono::steady_clock;\n"
                         "inline std::array<double, 3> stage_query{};\n"
                         "inline std::array<double, 5> stage_load{};")
    begin = graph.index("inline GraphSearchResult\ngraph_search_impl(")
    end = graph.index("inline GraphSearchResult\ngraph_search(", begin)
    prefix, suffix = graph[:begin], graph[end:]
    graph = graph[begin:end]
    graph = replace_once(graph, "    const float query_sum = std::accumulate(query.begin(), query.end(), 0.0F);",
                         "    const auto stage_start = Clock::now();\n"
                         "    const float query_sum = std::accumulate(query.begin(), query.end(), 0.0F);")
    graph = replace_once(graph, "    const uint64_t reorder_count = best.size();",
                         "    const auto stage_boundary = Clock::now();\n"
                         "    stage_query[1] += microseconds(stage_start, stage_boundary);\n"
                         "    const uint64_t reorder_count = best.size();")
    graph = replace_once(graph, "    return {std::move(result), visited_count, reorder_count};",
                         "    stage_query[2] += microseconds(stage_boundary, Clock::now());\n"
                         "    return {std::move(result), visited_count, reorder_count};")
    graph = prefix + graph + suffix
    marker = "        const auto normalized = normalize(model_, query, query_norm);"
    # SearchWithOptions only; plain Search is intentionally untouched.
    pos = graph.index("    SearchWithOptions(const float* query,")
    before, after = graph[:pos], graph[pos:]
    after = replace_once(after, marker, "        const auto transform_start = Clock::now();\n" +
                         marker + "\n        stage_query[0] += microseconds(transform_start, Clock::now());")
    graph = before + after
    snapshot = (root/"src/lite/rabitq_snapshot.h").read_text()
    snapshot = replace_once(snapshot, "    auto loaded = load_snapshot_payload(input, 1);",
                            "    auto stage_start = Clock::now();\n"
                            "    auto loaded = load_snapshot_payload(input, 1);\n"
                            "    stage_load[0] = microseconds(stage_start, Clock::now());\n"
                            "    stage_start = Clock::now();")
    for marker, index in [("    const uint64_t offset_count = read_u64(input);", 1),
                          ("    validate_graph_topology(graph, loaded.codes.Size());", 2),
                          ("    return {std::move(loaded.model),", 3)]:
        snapshot = replace_once(snapshot, marker,
            f"    stage_load[{index}] = microseconds(stage_start, Clock::now());\n"
            "    stage_start = Clock::now();\n" + marker)
    snapshot = replace_once(snapshot, "    return {std::move(loaded.model),",
                            "    MutableGraphState result{std::move(loaded.model),")
    snapshot = replace_once(snapshot, "            ef_search};",
                            "            ef_search};\n"
                            "    stage_load[4] = microseconds(stage_start, Clock::now());\n"
                            "    return result;")
    (output/"lite/rabitq_graph_state.h").write_text(graph)
    (output/"lite/rabitq_snapshot.h").write_text(snapshot)
    command = ["c++", "-O3", "-DNDEBUG", "-std=c++17", "-DVSAG_LITE_RABITQ_X86_SIMD",
               "-I"+str(output), "-I"+str(root/"src"), "-I"+str(root/"include"),
               str(root/"lite/benchmark/rabitq_stage_probe.cpp"),
               str(Path(args.static_library).resolve()), "-o", str(output/"stage_probe")]
    (output/"compile.json").write_text(json.dumps(command)+"\n")
    subprocess.run(command, check=True)


if __name__ == "__main__":
    main()
