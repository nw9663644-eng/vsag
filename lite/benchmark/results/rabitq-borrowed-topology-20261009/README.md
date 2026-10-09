# RaBitQ build-only graph reads source vectors

Control HEAD410a889, library SHA28bbe034658e0dfc29c635946348986c80162314d829b0da767cf3f20e409096 (independently rebuilt from HEAD, byte-identical to the previously published row-training candidate). Candidate source is recorded in validation.json and the identity dirty patch; all three experiments bind the same final production library SHA. Test-only style corrections and an invalid-row regression were added after timing without changing that library.

## Source evidence and minimal change

OSPP G3/G5/P8/P10: reduce construction memory/copies while keeping graph quality and failure atomicity. Official FlattenDataCell::ComputePairVectors uses two layout leases rather than copying the vector store. Lite Backend::VectorAt supplies source-owned rows or caller-owned scratch. Index::BuildGraph retains the original backend until successful publication.

The existing GraphBackend algorithm is reused, not replaced with a new ANN policy. A synchronous build-only source skips its FP32 reserve/append. Distance-to-query consumes a row immediately; pair distances use distinct scratch buffers. build_graph_topology returns only owned adjacency, never a borrowed backend or row pointer. Temporary state is destroyed inside the factory. The ordinary owning FP32/FP16 path remains; source rows, IDs, SIMD distance kernels, graph selection, degree/ef, quantization seed47/model/codes, API and snapshot format are unchanged. No concurrent build contract is added. Invalid rows/errors discard the temporary graph and leave the source intact.

## Paired real measurements

Same public runner, CPU0, degree16/constructionef128, k10, 100 historical observed queries, no warmup, single BLAS/OMP/MKL threads. Three alternating pairs per dataset. Queryef128 at10k and512 at100k; three fresh loaders each. Old Lite is a regression control, NOT native Full VSAG. The host is not isolated and cache is warm/uncontrolled; 100queries are not robust P99 evidence.

| Dataset | Peak RSS control/candidate KiB | Change | Build ms control/candidate | Query P50 us control/candidate | Recall@10 |
| --- | ---: | ---: | ---: | ---: | ---: |
| cohere10k | 110496 / 83824 | -24.14% | 1601.816 / 1558.848 | 163.616 / 162.877 | 0.961 |
| gist10k | 134724 / 103784 | -22.97% | 1727.519 / 1758.647 | 173.167 / 191.875 | 0.914 |
| sift10k | 28900 / 23636 | -18.21% | 620.198 / 618.074 | 85.867 / 80.648 | 0.978 |
| cohere100k | 1063632 / 759516 | -28.59% | 31598.878 / 31762.858 | 1136.385 / 1042.268 | 0.937 |
| gist100k | 1307484 / 928404 | -28.99% | 33787.858 / 35422.717 | 1173.405 / 1256.422 | 0.859 |

Construction peak decreases18.2-29.0%. This is whole builder RSS including input/staging, not deployment/load-only memory. Construction is not uniformly faster: GIST100k build+4.84%. Query implementation is unchanged but timing is mixed: GIST10k P50+10.80%, GIST100k+7.08%; Cohere100k-8.28%. Allocation layout/cache/code placement and host variability may affect these observations; no universal query-speed or build-speed gain is claimed. Both100k high-dimensional fixed-budget recalls remain below the prior research floors. Snapshot sizes and loadedRSS are effectively unchanged; full metrics/P99/load values remain in summary.json, with raw samples retained.

The [100k experiment](../rabitq-borrowed-topology-100k-20261009/README.md) and [floating regression](../rabitq-borrowed-topology-float-regression-20261009/README.md) share the same candidate/control libraries. Floating storage has18 extra pairs: all snapshots/ordered neighbors/Recall agree; P50 differences -1.35% to+5.02% are reported in full summaries, not sold as improvements.

## Validation and evidence

Release6/6, ASan/UBSan with leak detection5/5, fresh coverage5/5, RaBitQ-OFF4/4. Borrowed/owning topology equality covers dimensions1/17/128/768, duplicate vectors, non-monotonic IDs, scratch-backed rows, source destruction, invalid options/graph source/NaN and empty source. Existing6000 fault positions cover three storages/four operations: all changed_after_failure/invalid_snapshot/escaped counters zero; Build actual failures128/143/192. This is a bounded allocation-failure model, not proof for all allocators. Production Lite2659/2801=94.9304%; with instantiated shared SIMD2833/2977=95.1629%. Scope files and raw gcov JSON are retained; not Full repository coverage.

format15/tidy15/diffcheck passed. Initial tidy exposed eight test-only diagnostics, including a pre-existing explicit float type; fixed without changing measured production. Failed and final logs both remain in raw.tar.gz. Newly fetched upstream documentation rule requests a Node checker; the server has no Node runtime and the working branch does not contain that checker, so it was not run. No PR update or Full-suite success is claimed.

Run python3 verify.py to audit all33 pairs, raw quantiles, truth intersections, medians,126 load records, hashes, coverage and faults without extracting tar paths. Large scratch snapshots were disposable and only their size/SHA/round-trip checks survive; base datasets remain in the recorded host cache. The verifier recomputes intersections against archived prepared groundtruth, not exhaustive base distances or cold I/O.

Reproduce with lite/benchmark/run_aligned_comparison.py using identity.json arguments and matching libraries. It uses existing cached inputs, stores snapshots in /dev/shm, and archives small evidence before session end. Full final quality alignment, long persistent whole-vector mixed CRUD, larger query cohorts, cold loading, fresh Full/package closure and route-query optimization remain pending. Existing native Full comparisons still show slower Lite queries. This is one construction-memory optimization, not complete OSPP acceptance.

Architecture: [English](../../../../docs/docs/en/src/development/lite_rabitq_design.md), [Chinese](../../../../docs/docs/zh/src/development/lite_rabitq_design.md).
