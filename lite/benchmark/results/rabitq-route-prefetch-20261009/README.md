# RaBitQ routing filter prefetch experiment

Control: personal Lite commit 7bb52678788bafaea68573f828effc7ac339bdb7, exact frozen Release library. Candidate: same sources/configuration plus read-only adjacency-batch filter-plane and metadata prefetch. This is an old-Lite comparison, NOT native Full VSAG.

Source evidence: src/impl/searcher/hgraph_rabitq_searcher.cpp gathers unvisited batch IDs and calls PrefetchFusedFilter before scoring; src/datacell/hgraph_rabitq_fused_datacell.cpp prefetches node/filter records. Lite follows this strategy without importing Full graph/storage/allocator. Model, distance math, batch ordering, heap admission, entry points, degree/ef, filters and snapshot format are unchanged. Hinted addresses are inside the selected live record; hints allocate no shared scratch and never mutate the model.

Earlier phase instrumentation identified routing as dominant. Here timings are uninstrumented end-to-end measurements, not a new phase profile or hardware-counter cache-miss evidence.

Three alternating pairs per dataset. CPU0, degree16/construction128/k10; query ef128 for10k and ef512 for100k, same100 prepared queries, no warmup, single BLAS/OMP/MKL thread, non-isolated host, uncontrolled warm page cache. identity.json records binary/script/data hashes and parent diff. Test-only extensions and bilingual docs corrections followed timing; final production-library SHA is unchanged.

| Dataset | P50 control/candidate us | P50 change | P99 control/candidate us | Recall |
| --- | --- | --- | --- | --- |
| cohere10k | 162.527/159.387 | -1.93% | 267.014/249.194 | 0.961 |
| gist10k | 172.526/162.176 | -6.00% | 289.274/255.075 | 0.914 |
| sift10k | 80.419/77.338 | -3.83% | 133.637/125.248 | 0.978 |
| cohere100k | 1062.457/1048.117 | -1.35% | 1314.522/1259.414 | 0.937 |
| gist100k | 1106.466/1008.208 | -8.88% | 1491.568/1226.574 | 0.859 |

All15 pairs have equal snapshot SHA, ordered neighbor/distance CSV and truth-hit CSV. Builder/load processes validate persistence roundtrips. Large scratch snapshots are not retained: offline verification checks recorded SHA, not a fresh byte reread. Prepared query/groundtruth files are archived; base matrices remain in identity-recorded server datasets.

Only limited query-latency improvement is observed. SIFT10k pair1 candidate P50 is slower (82.059 vs80.419us) despite lower median: no universal per-query/per-trial gain. Cohere100k median build increases3.22% (30933.775/31930.135ms), GIST100k build increases0.14%; no build/load/package/memory speedup claim. Peak/loaded RSS and snapshot bytes are in rows/summary and broadly unchanged. Cohorts are small/non-isolated; no statistical significance or cold-start claim.

Final Release6/6, ASan/UBSan5/5, coverage5/5 and RaBitQ-OFF4/4 pass. Reference/prefetch-on/prefetch-off golden tests span dimensions1/17/128/768/960, ties/non-monotonic IDs, k1/10, multiple ef, allow/reject filters, before/after real-value Update/Remove/Add, matching visits/reorders/IDs/exact distances. clang-format/tidy15 pass (dependency warnings suppressed). Lite production lines2667/2805=95.08%; instantiated shared SIMD174/176, combined2841/2981=95.30%, not Full coverage. Existing allocation rollback tests pass; no new external6000-position fault scan is claimed. Node doc checker NOT run (runtime absent, branch lacks newer upstream script).

Run python3 lite/benchmark/results/rabitq-route-prefetch-20261009/verify.py to audit both folders: checksums/members, raw quantiles/medians,3000 truth intersections,90 loads, paired ordered outputs and fresh raw coverage. Rerun run_aligned_comparison.py using identity.arguments after producing exact control/candidate libraries; use a new output directory.

PR2904/2926 unchanged. Cohere100k Recall.937 and GIST100k.859 still miss research targets. Native-Full quality/SIMD alignment, larger query cohorts, cold loads, fresh package closure and long real whole-vector persistent CRUD remain pending.
