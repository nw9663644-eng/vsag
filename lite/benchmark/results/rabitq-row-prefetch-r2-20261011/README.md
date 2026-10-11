# RaBitQ row-ahead prefetch candidate, 2026-10-11

## Rejected: extra neighbor walk regresses query latency

| Dataset | Control P50 us | Candidate P50 us | Change | Candidate P50 pair wins | Control P99 us | Candidate P99 us | Recall both |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| SIFT 10k | 200.376 | 217.764 | +8.68% | 0/7 | 239.453 | 266.622 | .987 |
| GIST 10k | 499.136 | 530.046 | +6.19% | 1/7 | 627.933 | 700.951 | .970 |
| Cohere 10k | 471.527 | 515.407 | +9.31% | 0/7 | 531.556 | 580.684 | .984 |
| GIST 100k | 1078.611 | 1146.729 | +6.32% | 0/7 | 1288.544 | 1313.664 | .859 |

Production is not modified. These medians of seven process quantiles describe this isolated experiment, not universal CPU causality or Full performance. P99 uses only100 historical queries/process and is not final acceptance. The additional visited checks/row traversal are a plausible cost, not a measured attribution of the whole regression. Do not repeat or adopt the same candidate.

## Source evidence and exact change

Current Lite `graph_search_impl` prefetches the filter and metadata for unvisited neighbors just before collecting batches of four, then immediately computes a complete batch. Official `src/impl/searcher/basic_searcher.cpp` uses ahead-of-computation `flatten->Prefetch` and visited-list prefetching. The isolated candidate moves Lite's existing same filter-cache-line and metadata prefetch instructions into a separate pass over the current adjacency row, before its unchanged ordered visit/batch pass. This is a scoped adaptation of a native prefetch idea, not a direct transplant of native graph or SIMD behavior.

No code/model layout, score formula, comparator, graph edge, parameter, entry point, mutation, snapshot or public API changed. It does not replace existing three-bit SIMD kernels or batch4 scoring. Candidate/control headers and exact source transformation are archived, and the independent verifier checks that this is the sole overlay change. The experiments use unchanged production src/include at f4abfa0, personal HEAD ce201fa.

## Measurements and checks

Remote1.13.5.198/VM-0-10-ubuntu/HostKeyAlias119.45.24.226; `/home/ubuntu/project/vsag-lite-baseline-v01`, branch experiment/lite-rabitq-next-20260926. CPU0/thread1 including BLAS, degree16/build128/query512/k10, initial RaBitQ8 snapshots. Seven alternating fresh-process pairs/cell, one warmup query pass/process, no build/lint/test overlap with timing. Both variants measure internal MutableGraphState::SearchWithOptions; not public call latency, native Full, CRUD or cold/durable I/O.

Control is independently checked against public native Index ordered results/float bits; all56 timed runs/5600 queries/56000 ordered neighbors match native/control byte-for-byte. Per-query hits, visited and rerank counts unchanged. Independent verification recomputes truth intersections, quantiles and all source/input hashes;67 commands successful. Current native builder Save/Load checks passed; candidate mutation/Save/filtered/failure paths and fresh production SAN/coverage were not separately run. Existing probe and production library are unchanged. Header format15 uses explicit repository .clang-format; no new complete-header tidy or whole-library coverage claim.

Initial runner setup failed before compiling/timing due to an omitted body variable. Retry r1 failed the format gate because a RAM file inherited default formatting instead of the repository config; its format log/commands are preserved as startup-r1 files. Explicit `-style=file:<repo>/.clang-format` fixed this before r2's complete measurement. An early verifier invocation before100k completion also failed its completeness assertion; post-completion verification passed. These are tooling/preparation failures, not product failures or discarded unfavorable timings.

## Reproducibility and retention

Runner `lite/benchmark/run_rabitq_row_prefetch.py` and verifier `lite/benchmark/verify_rabitq_row_prefetch.py` are committed. Runner refuses an existing output directory; choose a new output path on replay and pin identity sources/libraries/inputs/flags. Raw snapshots and temporary executables are hash/size receipts, not committed large binaries. Every raw result/header/query/truth/recipe file is in raw.tar.gz with SHA256/size manifest; extract into a fresh directory and run the verifier on that directory. Plain original raw data, old sources/data/libraries remain on server. Only owned new RAM scratch expired. PR2904/2926 unchanged; overall project unfinished.

Next measure single/batch4/tail scoring call counts before designing additional SIMD or layout changes; allocation and prefetch guesses are not CPU profiles. Fresh native Full alignment, 100k repetitions, GIST graph quality, interleaved changed-value CRUD, larger query tails and deployment-package closure remain open.
