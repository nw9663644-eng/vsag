# RaBitQ best-heap reserve candidate, 2026-10-11

## Decision: do not adopt

Preallocating the bounded best heap did not provide a consistent latency benefit. All four cells won only 3/7 paired P50 comparisons. Do not select the apparently favorable Cohere median and present it as a production improvement. Production `src/` and `include/` remain unchanged at f4abfa0 (experiment HEAD 6aadc03).

| Dataset | Control P50 us | Candidate P50 us | Change | P50 pair wins | Control P99 us | Candidate P99 us | Recall both |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| SIFT 10k | 206.114 | 204.934 | -0.57% | 3/7 | 248.132 | 243.252 | .987 |
| GIST 10k | 496.025 | 496.545 | +0.10% | 3/7 | 667.231 | 712.799 | .970 |
| Cohere 10k | 481.597 | 463.186 | -3.82% | 3/7 | 594.052 | 565.934 | .984 |
| GIST 100k | 1140.337 | 1163.135 | +2.00% | 3/7 | 1341.290 | 1363.010 | .859 |

Numbers are medians of seven per-process quantiles, not pooled quantiles. Quantiles use nearest-rank over only 100 historical queries/process: P50 index49, P99 index98. They are exploratory, not final tail-latency acceptance. Individual paired changes are retained in audit.json; Cohere P50 paired changes ranged approximately -18.86% to +35.03%, demonstrating substantial noise. No statistical or universal performance claim is made.

## Source evidence and exact minimal change

`graph_search_impl` in `src/lite/rabitq_graph_state.h` creates a local best heap then pushes and pops to retain ef candidates. At ef512 an accepted push may transiently require 513 elements. `QueryHeap` inherits the standard vector-backed priority_queue constructor. The isolated overlay constructs a vector reserved to `ef + (ef < codes.Size())`, then moves it into the otherwise identical heap. When ef equals the entire population no extra transient element can be visited. No overflow-prone unconditional ef+1 or persistent cache was introduced.

Native `src/impl/heap/standard_heap.cpp` supports the continuous heap/push-pop comparison design, **but does not explicitly reserve capacity**. This candidate is not an existing native reserve optimization transplanted into Lite.

The source-only overlay is archived as candidate-rabitq_graph_state.h alongside its control and pinned supporting sources. The independent verifier checks the exact replacement. Candidate queue, scoring, filter behavior, entry points, ef/k, graph topology, model, seed, full-code reranking, and snapshot layout are unchanged. No production source, public API, CMake or PR was modified.

## Protocol and validation

- Actual remote repository `/home/ubuntu/project/vsag-lite-baseline-v01`, server 1.13.5.198, SSH alias119.45.24.226; individual branch experiment/lite-rabitq-next-20260926.
- CPU0, single thread including BLAS; degree16/build128/query512/k10; RaBitQ8. Seven fresh-process pairs/cell with cyclic control-first/candidate-first order; each process performs one query warmup pass. No concurrent build/lint/test workload during timed queries.
- One initial snapshot/cell prepared by the pinned current native builder, then both probes load the same snapshot. Snapshot hash/size and input hashes are recorded. No CRUD or cold/durable I/O claim.
- Control internal SearchWithOptions results were checked against public native Index::SearchWithOptions, including ordered IDs and exact float distance bits. Both internal probes have the same compiler flags, static archive and probe source except the candidate include overlay. Timings are **internal search**, not public API timings and not native Full comparisons.
- Independent verifier passed 56 timed runs, 5600 queries, 56000 ordered neighbors and 66 recorded successful commands; all ranks/IDs/hex distances are byte-exact to control/native. Per-query hits, visited counts and rerank counts are also exact. Native builders additionally perform Save/Load result checks. No claim that candidate Save/Load/CRUD paths were separately exercised.
- Existing probe unchanged; no new production Release/SAN/OFF/coverage claim. This isolated experiment does not establish whole-library coverage or allocation-count reduction measurements. All original sources, data, raw results and libraries were preserved; only owned new RAM scratch automatically expired.

Run from the remote repo: `python3 lite/benchmark/run_rabitq_best_reserve.py`, then `python3 lite/benchmark/verify_rabitq_best_reserve.py lite/benchmark/results/rabitq-best-reserve-20261011`. The runner refuses an existing output directory; move only your own output or choose a new output path before replay. Pin the identity's source/library/input hashes and compile flags before comparing any replay. Large RAM snapshots/executables are represented by hashes, not committed bytes. Actual runner/probe/header sources, commands, input queries/truth, per-query results, identities and audit remain here.

## Remaining work

Do not interpret the previous ordinary-new allocation count as proof that allocation dominates CPU. Prioritize source-backed route-score/data-access optimizations and GIST100k graph coverage. Fresh native Full configuration/SIMD/quality alignment, repeated 100k comparisons, genuinely interleaved changed-value CRUD, larger query tails and complete deployment-package evidence remain open. PR2904/2926 remain untouched; the overall project is not complete.
