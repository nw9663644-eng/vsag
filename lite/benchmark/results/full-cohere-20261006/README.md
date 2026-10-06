# Known-source Full Cohere FP32 reference (2026-10-06)

Rebuilt the existing Full shared-library target incrementally from clean tracked
source d18c82a1f1f23ff84362516e86af5f3cb2e34475, then installed into a separate
vsag-full-known-install-20261006 prefix and built a new benchmark runner.
Version header/build log, flags, ldd and library/binary SHA bind this measurement
to that source. This is not a fresh all-object rebuild or latest upstream claim;
unchanged cached objects/dependencies were reused. Only shared target was rebuilt;
installed static archive was not used and has no matching-version certification.

Official APIs used by the existing full_rabitq_dataset_main.cpp benchmark:
Factory::CreateIndex("hgraph"), Build, KnnSearch, Serialize and Deserialize.
FP32 squared-L2, degree16, construction/query ef128, compressed graph storage and
store_raw_vector=true. CPU affinity0; one warmup pass, one timed pass, three fresh
processes. Cohere prepared base100k/dim768, normalized FP32 with FP64 truth;
600 query rows[400,1000) were already observed in Lite and are not new blind data.
The same input manifest is recorded in protocol.json. No index code was changed.

## Results

| Metric | Median | Min | Max |
|---|---:|---:|---:|
| recall_at_k | 0.952000 | 0.952000 | 0.952000 |
| build_ms | 33940.856349 | 33899.969492 | 34026.834536 |
| search_p50_us | 323.242000 | 318.513000 | 324.483000 |
| search_p99_us | 379.081000 | 369.242000 | 381.291000 |
| query_loop_cpu_ms | 194.220000 | 191.298000 | 194.997000 |
| save_ms | 173.682623 | 172.968490 | 175.346686 |
| load_ms | 191.866919 | 190.262097 | 197.671555 |
| snapshot_bytes | 313616358.000000 | 313616358.000000 | 313616358.000000 |
| build_steady_rss_kib | 457592.000000 | 457580.000000 | 457800.000000 |
| final_steady_rss_kib | 456108.000000 | 455940.000000 | 456156.000000 |
| process_peak_rss_kib | 958556.000000 | 958548.000000 | 958772.000000 |

All three pass Recall@10>=.95. Save/Load verifies IDs exactly and distances within
1e-5 relative scale for all 600 queries per run. Raw 1800 timed-query counts and
nearest-rank P50/P99 were independently recomputed. RSS is whole process:
build_steady drops base input and trims allocator; final_steady is after reload and
result checks; peak includes preparation/build temporaries. File Load is warm
filesystem-cache measurement, not strict cold start. CPU loop includes vector
copy/search/scoring/bookkeeping and excludes warmup. P50/P99 time search+result copy.

## Interpretation

See cohere-matched-20261006 for prior Lite default768/candidate256 results. These
were measured in earlier processes, not interleaved with Full. Different quality
and index topology/storage mean timing ratios are descriptive reference points,
not exact equal-quality optimization or an adoption decision. No matching Lite RSS
measurement or Full mixed CRUD is included; Full/Lite memory or end-to-end CPU
benefit cannot yet be claimed. Snapshot sizes can be compared for these formats,
but a shared-library size alone is not a deployment-package size.

On the first run, Full logs preceded the CSV header on stdout. The collector's
CSV parser failed after the benchmark succeeded; parsing now preserves raw stdout
and extracts from the explicit header. Run0 was recovered, not remeasured/discarded.
No C++ source edits, new sanitizer/coverage results or concurrent CRUD claims.

## Reproduction and next work

commands.json and run.py contain actual host paths and parameters; use a fresh
output directory to remeasure. Large snapshots/binaries/datasets are excluded from
Git; snapshot hashes and linked-library/source provenance are retained. Build,
install and runner logs are included. Next: equivalent Lite memory lifecycle and
Full mixed CRUD, then a unified SIFT/GIST/Cohere report and policy decision.

## Prior Lite initial-query reference (not interleaved)

| Mode | Query ef | Recall | Median P50 us | Median P99 us | Median query CPU ms |
|---|---:|---:|---:|---:|---:|
| Lite default | 768 | 0.958000 | 2570.399 | 3082.429 | 1522.549 |
| Lite diverse | 256 | 0.961333 | 1073.785 | 1321.160 | 636.642 |

Uses three initial passes from the 1:4 group, before mutations. No mixed-query timings are substituted. Full and Lite CPU loop bookkeeping differ; this is a descriptive reference.
