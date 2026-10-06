# Online FP32 diversity selection: experimental pilot

2026-10-06. ENABLE_DIVERSE_NEIGHBOR_EXPERIMENT is OFF by default. When enabled,
GraphBackend::nearest greedily prunes FP32 neighbors from its existing search
candidate pool using the alpha=1 pairwise occlusion comparison in Full's
src/impl/pruning_strategy.cpp. If the eligible pool is undersized, pruning is
skipped. This directly participates in BuildGraph's incremental Add, subsequent
Add and Update. FP16 selection, reverse link installation, deletion repair and
all public APIs remain unchanged. It does not call the Full module or pull its
dependency closure into Lite; it transfers the small comparison rule onto the
existing Lite distance functions and candidate ordering. This is not the earlier
offline outgoing/incoming-union reconstruction.

The snapshot format does not record the experimental selection policy. Initial
adjacency persists, but future mutations follow the receiving library's build
configuration. This is an experiment boundary, not a supported portable policy
configuration. Do not enable by default or update PR source branches yet.

GIST 10k/100k was constructed from the base vectors from scratch. Uniform
entries, max_degree=16, ef=128, CPU 0, 300 development queries (source rows
100..399) were used. These queries were already observed during the previous
failed gate; they are not a new blind test. Each row is one fresh process,
so time differences are descriptive pilot results, not repeated-run estimates.
The benchmark's churn uses 10 rounds x100 original-vector Update/Remove/Add
cycles (not large vector displacement). Save/Load must preserve all query IDs
and distances exactly. Build time includes initial insertion and BuildGraph.

| Scale | Mode | Cycles | Recall@10 | Build ms | Query P50 us | Snapshot bytes |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 100k | default | 0 | 0.675000 | 44250.987389 | 571.268000 | 398400064 |
| 100k | default | 1000 | 0.670000 | 43669.748392 | 558.476000 | 398400000 |
| 100k | diverse | 0 | 0.830333 | 51177.691453 | 657.836000 | 391896208 |
| 100k | diverse | 1000 | 0.830333 | 51159.910440 | 654.316000 | 392149984 |
| 10k | default | 0 | 0.893333 | 1691.097437 | 208.945000 | 39840064 |
| 10k | default | 1000 | 0.881667 | 1658.663982 | 205.686000 | 39840056 |
| 10k | diverse | 0 | 0.964667 | 1904.743535 | 261.404000 | 39282976 |
| 10k | diverse | 1000 | 0.957000 | 1862.862506 | 256.375000 | 39468288 |

The online candidate improves validation recall at the same ef but spends more
construction/query work. At 100k, initial recall improves 0.675 to 0.830333;
build time grows 44.25s to 51.18s and P50 571us to 658us. After 1,000 cycles,
candidate recall stays 0.830333 versus default 0.670. The 10k candidate reaches
0.964667 before churn and 0.957 after. The 100k candidate still fails the 0.90
quality gate, and equal ef is not an equal-quality cost comparison. No universal
speedup, long-run/concurrent safety, Full comparison or final adoption is claimed.
Rows 400..999 remain reserved for final assessment after configuration freezing.

Targeted tests confirm collinear pruning during Add/Update, intact incoming
metadata after removal, and unchanged FP16 neighbor-count behavior. Coverage
inspection motivated additional filter-allocation/capacity, stream-load failures,
FP16 rounding/overflow, malformed restore and CPU-feature dispatch regressions.
Fresh unit runs cover 958/1061 Lite source/internal-header lines (90.29%); .cpp
and public-header scope is 909/991 (91.73%). This is Lite-only line coverage,
not Full-library coverage or a branch-coverage claim. Coverage was collected
with ENABLE_COVERAGE=ON and the experimental option ON; performance measurements
used non-instrumented Release. The collector and per-file totals are included.

## Reproduction

```bash
cmake -S lite -B BUILD -G Ninja -DCMAKE_BUILD_TYPE=Release -DENABLE_TESTS=ON -DENABLE_BENCHMARKS=ON -DENABLE_DIVERSE_NEIGHBOR_EXPERIMENT=ON
cmake --build BUILD -j2
ctest --test-dir BUILD --output-on-failure
taskset -c 0 BUILD/lite_graph_crud_quality DATASET NEW_SNAPSHOT 0 100 NEW_HITS
taskset -c 0 BUILD/lite_graph_crud_quality DATASET NEW_SNAPSHOT 10 100 NEW_HITS
```

For coverage additionally enable ENABLE_COVERAGE, clear generated .gcda files
inside that build only, run the unit suite, then run collect_coverage.py after
adjusting its build path. Performance snapshot hashes and original commands are
included. The large snapshots remain on the host at
/home/ubuntu/project/vsag-lite-online-diverse-20261006. Dataset preparation and
provenance are in the previous held-out-query report. The dependency source cache
was reused after a Catch2 download timeout; the pinned version remains 3.7.1.
Default and experimental configurations use the same compiler/toolchain.


Final checks: experiment Release 3/3, default Release 4/4, experiment and default
ASan+UBSan 6/6 each, format/tidy15 passed. Default sanitizer build was restored
with the experiment OFF. Historical tidy logs show two test-style findings
corrected before final verification: use-auto and named parameters. The final
index-specific tidy log is clean; graph source/test diagnostics were already
clean in the combined pass. These historical logs are diagnostic history, not
unresolved failures. The private project handoff and server credentials are
excluded from the commit.
