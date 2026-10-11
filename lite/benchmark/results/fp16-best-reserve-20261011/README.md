# FP16 best-heap reserve candidate, 2026-10-11

## Decision: do not adopt

No consistent improvement was observed. Production `src/` and `include/` remain unchanged at f4abfa0 (experiment HEAD 6aadc03). This report is a rejected structural candidate, not a delivered query speedup.

| Dataset | Control P50 us | Candidate P50 us | Change | P50 pair wins | Control P99 us | Candidate P99 us | Recall both |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| SIFT 10k | 185.474 | 185.194 | -0.15% | 3/7 | 247.754 | 248.753 | .993 |
| GIST 10k | 600.102 | 601.232 | +0.19% | 3/7 | 805.977 | 815.906 | .971 |
| Cohere 10k | 627.083 | 626.342 | -0.12% | 4/7 | 741.338 | 728.759 | .985 |
| GIST 100k | 1273.604 | 1280.893 | +0.57% | 4/7 | 1574.215 | 1588.345 | .865 |

Numbers are medians of seven process quantiles, not pooled quantiles. Each process measures only 100 historical queries after one warmup pass; nearest-rank P50/P99 indices49/98. Small or inconsistent differences and the per-pair variation in audit.json do not establish a general speedup or final P99 acceptance.

## Minimal structural candidate and isolation

Current `GraphBackend::SearchImpl` constructs a vector-backed QueryHeap and retains at most ef elements by push then pop. An accepted push at ef512 may temporarily require513. The sole overlay change constructs an initially empty vector reserved to `ef + (ef < Size())`, then moves it into `QueryHeap<Candidate, Closer>` using its inherited priority_queue constructor. The comparator and operation sequence remain unchanged. No candidate-queue, visited, encoding, distance, budget, graph, mutation, public API or snapshot change.

The runner copies the pinned static archive into new RAM scratch, compiles only the overlay graph_backend.cpp with the recorded original compile_commands.json entry (same flags, new source/output), and replaces its single graph_backend.cpp.o archive member. It links control and candidate public-API probes using the original and scratch archives respectively. Actual compile entry, commands, archive membership, executable/archive hashes and exact source overlay are retained. The original archive hash is checked again after all measurements; production sources and libraries are never overwritten.

Official StandardHeap's push-pop/vector pattern was consulted but does not contain explicit reserve; do not describe the reserve itself as reused official code. FP16 is measured through **public** Index::SearchWithOptions, while the companion RaBitQ reserve experiment measures **internal** MutableGraphState search. Do not combine the two tables into a valid FP16-vs-RaBitQ comparison.

## Protocol and checks

Remote `/home/ubuntu/project/vsag-lite-baseline-v01`,1.13.5.198/HostKeyAlias119.45.24.226, personal experiment/lite-rabitq-next-20260926. CPU0/single thread/degree16/build128/query512/k10, initial FP16 snapshot per cell. Seven alternating fresh process pairs; one warmup query pass per process. No build/lint/test overlap with timed queries. This is not CRUD, cold I/O, a Full comparison or end-to-end latency.

Independent verification passed56 timed runs/5600 queries/56000 ordered neighbors/66 successful commands: all control/candidate ranks, IDs and hex distances byte-exact to native builder; groundtruth intersections and quantiles independently recomputed; input/source hashes and exact sole source replacement checked. Native builder Save/Load checks passed. The candidate only reads snapshots and queries; candidate mutation, Save, failure rollback and filtered queries were not separately validated, so adoption would still require those tests even if latency improved.

New public probe was formatted with clang-format15 before measurement. Source-only clang-tidy15 passed afterward with27102 non-user dependency warnings suppressed, not a complete header lint. No new production Release/SAN/OFF/coverage run is claimed. Raw inputs/results/sources/libraries preserved; only owned new RAM scratch expired. Large snapshots and executables retained by SHA/size/provenance, not bytes.

Replay from remote repo: `python3 lite/benchmark/run_fp16_best_reserve.py`, then `python3 lite/benchmark/verify_fp16_best_reserve.py lite/benchmark/results/fp16-best-reserve-20261011`. Runner refuses existing output; choose a new output path for replay and pin identity sources/archive/inputs/compiler flags. Actual runner, probe, controls/overlays, input queries/truth, raw timings/neighbors, compile recipe and audit are archived.

## Next work

Do not adopt this candidate or repeat the same reserve experiment. Investigate route distance scoring and accessed-record layout rather than treating allocation counts as a CPU profile. GIST100k quality, final fresh native Full comparisons, interleaved true-value CRUD, larger query tails and deployment-package closure remain unfulfilled. PR2904/2926 untouched; overall project not complete.
