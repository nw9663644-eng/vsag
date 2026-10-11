# RaBitQ three-lane tail using existing batch4, 2026-10-11

## Decision: insufficient consistent benefit; do not adopt

| Dataset | Control P50 us | Candidate P50 us | Change | Candidate P50 pair wins | Control P99 us | Candidate P99 us | Recall both |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| SIFT 10k | 202.764 | 201.604 | -0.57% | 6/7 | 247.204 | 237.483 | .987 |
| GIST 10k | 500.956 | 482.387 | -3.71% | 4/7 | 660.582 | 620.662 | .970 |
| Cohere 10k | 469.428 | 468.567 | -0.18% | 3/7 | 527.106 | 522.026 | .984 |
| GIST 100k | 1072.472 | 1077.841 | +0.50% | 4/7 | 1273.266 | 1297.675 | .859 |

No production source changed. Medians of seven per-process quantiles are not pooled quantiles. GIST10k paired P50 changes range roughly -15.93% to +9.61%; a favorable median is not a reliable improvement. P99 comes from only100 historical queries/process, nearest-rank index98, and is exploratory rather than final acceptance. Do not adopt or present this as a stable delivered speedup.

## Official reuse and minimal change

Lite already invokes the shared VSAG `RaBitQFloatThreeBitCenteredIPBatch4Impl` for complete four-neighbor batches, but remaining1-3 neighbors call the single-record kernel separately. The isolated graph_search_impl candidate uses the same existing batch4 when exactly3 remain: duplicate the last valid EncodedView into lane3, compute the four outputs, and process only the original3 lanes in their unchanged order. Count4 remains ordinary batch4; count1/2 remain scalar. No new SIMD kernel is introduced, and the extra fourth computation is part of the measured cost.

The exact sole transformation and native SIMD source are archived. No scoring formula, comparison, budget, model, entry, graph, layout, mutation, filter callback order, visited semantics, public API or snapshot change. Both candidate and control link the same pinned production static archive. Source/library/inputs/executable hashes recorded. Production remains f4abfa0; experiment began at personal HEAD ce201fa.

## Method and verification

Actual remote `/home/ubuntu/project/vsag-lite-baseline-v01`, server1.13.5.198/VM-0-10-ubuntu/HostKeyAlias119.45.24.226, personal experiment/lite-rabitq-next-20260926. CPU0/thread1 including BLAS, degree16/build128/query512/k10, initial RaBitQ8 snapshot/cell; seven alternating fresh-process pairs, one query warmup pass/process, no concurrent build/lint/test during timing. Internal MutableGraphState search timings, not public-API end-to-end or Full/CRUD/cold/durable I/O comparisons.

Independent verifier passed56 timed runs/5600 queries/56000 ordered neighbors/67 successful commands: all IDs/ranks/hex distances byte-exact to control/native, every query hit/visited/reranked count unchanged, truth intersections/quantiles/hashes and exact sole source replacement independently recomputed. Native builder Save/Load checks passed. Candidate mutation, Save, filtered queries, failure rollback, scalar-only ISA and sanitizer paths were not separately tested; adoption would still need them even with a favorable timing. Production Release/SAN/OFF/coverage is inherited, not freshly measured. Format15 overlay gate passed; no new full-header tidy claim.

First setup aborted before compilation/timing because the broad `if(count==4)` replacement marker matched both flush and batch-fill sites. The corrected marker includes the following estimate statement and is unique; retry r1 measured all four cells. No valid result was discarded. The original failed empty output directory remains on server.

## Replay and next work

Commit includes `lite/benchmark/run_rabitq_partial_batch3.py`, `lite/benchmark/verify_rabitq_partial_batch3.py`; runner refuses existing output paths. Pin identity libraries/sources/inputs/compiler flags and choose a fresh output path for replay. All raw timing/neighbor CSVs, query/truth inputs, source headers/probe/recipe and receipts are in raw.tar.gz with SHA256/size manifest; extract into a fresh directory and invoke the verifier there. Original plain raw, source, dataset and library files remain on server; only owned new RAM scratch expired. PR2904/2926 unchanged, project not complete.

Before another batch optimization, collect actual single/four/tail call shares and investigate where route scoring spends work. GIST100k quality and fresh native Full alignment/100k repetitions/interleaved true-value CRUD/larger query tails/complete deployment package remain unresolved.
