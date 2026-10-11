# RaBitQ full-code routing candidate, 2026-10-11

Decision: reject this candidate as a default change. It does not improve recall on any of the three measured initial graphs. Production sources, API, graph edges, codec and persistence remain unchanged.

## Protocol and evidence

Remote VM-0-10-ubuntu, CPU0/thread1, initial 100k graphs, degree16/build128/query512/k10, 100 existing queries per dataset. Five alternating fresh control/candidate process pairs per dataset; one complete query warmup pass per process. Timing covers internal `MutableGraphState::SearchWithOptions`, not the public API wrapper. SIFT/GIST use their existing subsets; Cohere uses the existing normalized subset. No tuning, new ground-truth generation, CRUD, cold I/O, Full VSAG comparison or whole-project acceptance is claimed.

| Dataset | Control Recall@10 | Candidate Recall@10 | Control P50 us | Candidate P50 us | Control P99 us | Candidate P99 us |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| SIFT100k | .975 | .974 | 477.448 | 822.809 | 635.473 | 1167.489 |
| GIST100k | .859 | .859 | 1039.344 | 2570.895 | 1284.658 | 3247.317 |
| Cohere100k | .937 | .936 | 1083.992 | 2370.879 | 1242.948 | 2935.785 |

Values are medians of five run-level statistics. Each run has only 100 historical queries: P99 is exploratory, not a stable tail estimate or blind evaluation. All five runs per variant return identical ordered IDs and distance values. Candidate mean visited counts are 3447.17/3689.90/3945.92 versus control 3487.09/3696.15/3948.60.

## Minimal isolated change and limitations

`run_rabitq_full_route.py` creates a temporary header overlay, replacing exactly one routing `Candidate` score inside `graph_search_impl`: coarse `estimate.distance` becomes the existing codec `full_distance`, reusing centered inner product and query sum. No production header is overwritten. Candidate compilation excludes public API parity calls to avoid mixing candidate header code with the production backend. Control results match public API ordered IDs and float bits for all 100 queries per dataset in separate untimed invocations.

The existing unfiltered final rerank remains unchanged. Thus the candidate computes full distance for every visited node and again for the final 512 retained nodes; no full-score cache is implemented. The filter-only accepted heap is inactive in this experiment. Measured slowdown describes this exact candidate, not an optimal full-code routing implementation. Even eliminating those redundant final calls cannot change its observed lack of recall gain. No claim is made that routing approximation is universally harmless or graph topology is the only possible cause.

Source evidence: `src/lite/rabitq_graph_state.h::graph_search_impl` separates coarse routing and complete-code reranking, and `src/impl/searcher/basic_searcher.cpp` provides the official visited-neighbor traversal reference. The candidate reuses existing Lite/native-backed distance kernels, not a transplanted Full search algorithm. The earlier GIST diagnostic found 140 of 141 missed truths unvisited; this candidate shows that merely changing routing scores does not resolve that coverage gap at fixed budget.

## Verification, failures and reproduction

Run the runner from the repository root on the pinned environment; it refuses an existing output directory. Snapshot SHA/size, input SHA, library/archive/executable/source SHA, commands and stdout/stderr are archived in this directory. RAM snapshots are temporary and not retained; original datasets and sources are preserved. Run:

```sh
python3 lite/benchmark/run_rabitq_full_route.py
python3 lite/benchmark/verify_rabitq_full_route.py lite/benchmark/results/rabitq-full-route-retry-20261011
```

The independent verifier passed 30 runs/3000 queries/30000 neighbor rows, recomputed truth intersections and quantiles, checked repeated result determinism, native parity output equivalence, source hashes and the exact single-site overlay. `audit.json` contains the recomputed summary. Formatting used clang-format15 before measurement. Source-only clang-tidy15 reported no user-code warnings; 35857 dependency/header warnings were suppressed. Its run overlapped the overall experiment after SIFT completed; stage timestamps were not captured, so strict absence of lint/preparation overlap is not claimed. No fresh production Release/SAN/OFF/coverage result is claimed: production C++ is unchanged.

First attempt failed before measurement because the candidate binary output collided with the overlay directory. Failure logs are preserved separately in `../rabitq-full-route-20261011`; the retry used `candidate-headers` and a fresh output directory. After all measurements completed, SSH temporarily became unreachable, delaying verification; it recovered on the following continuation. This was not a product correctness failure.

Next: inspect official graph neighbor-selection/connectivity logic and evaluate a narrowly scoped, fixed-budget graph-construction candidate in isolation. Do not repeat this full-score routing candidate or silently raise ef/degree. Latest native Full/SIMD/quality-aligned comparison and interleaved changed-value CRUD remain outstanding.
