# Persistent whole-row CRUD: quality failure evidence

Production is pinned to 2fea8f9; only the acceptance tool changes. Not a Full VSAG comparison.
GIST/Cohere10k, 600 historically observed queries, k10, degree16, construction128, query512, CPU0, BLAS/OMP1.
Three full-ID passes per run, 30000 changed Update/Remove/re-add cycles; six runs, 540000 mutations.
Replacement recipe: FP32 .875*current+.125*original donor; Cohere renormalized via FP64 then FP32.
All new rows persist. Initial and final exact truth use FP64 direct differences, not original truth reused after mutations.
No queries between mutations: not per-operation mixed read/write. One run per case, no statistical speed claim.
All 12 builders passed exact Save/Load ordered ID/distance checks. Independent raw audit covers10800 query states.
Snapshots were hashed then removed only inside verified newly created RAM scratch; original source/base/raw preserved.
Raw replacement matrices and final bases are reconstructible from preserved base, recipe and generator;
their checksums/row counts are recorded, not claimed to be archived here. Actual queries/truth are in raw.tar.gz.

| Dataset/storage | Initial recall | Maintained recall | Fresh-final recall | Update/Remove/Add P50 us |
| --- | ---: | ---: | ---: | --- |
| gist10k600/fp32 | 0.965500 | 0.898167 | 0.949833 | 213.724/12.490/141.867 |
| gist10k600/fp16 | 0.965500 | 0.898667 | 0.949833 | 199.377/11.698/147.617 |
| gist10k600/rabitq8 | 0.961000 | 0.811167 | 0.948500 | 403.852/250.185/282.463 |
| cohere10k600/fp32 | 0.987333 | 0.951167 | 0.965000 | 181.757/13.570/133.657 |
| cohere10k600/fp16 | 0.987000 | 0.951167 | 0.964667 | 167.517/13.179/134.517 |
| cohere10k600/rabitq8 | 0.983500 | 0.908167 | 0.961833 | 345.202/257.244/248.465 |

Final-data FP32/FP16 controls use identical vector content, degree and budgets. Their higher quality
shows final distribution alone is insufficient to explain the maintained loss. RaBitQ fresh construction
also trains a new model, so its difference combines graph and model effects; do not assign sole causality.
Maintained GIST floating modes and both RaBitQ cases fail historical study floors (GIST.90/Cohere.95).
These are study thresholds, not official OSPP numerical requirements. Stable-quality acceptance remains unmet.
Lower post-CRUD query latency is not a valid speed win at degraded recall.
RaBitQ Remove is much slower than floating modes; full-edge scanning is a source-backed target, not yet optimized.
verified-summary.json includes raw-derived API throughput, P50/P99, query QPS, CRUD-block throughput, save/load/size/whole-process RSS.
API throughput=count/sum timed API wall latencies; CRUD-block throughput includes bookkeeping but excludes query/I/O.
Whole-process peak includes original/replacement matrices, staging, index and load; not steady deployment RSS.

Reproduce on the recorded host: set OPENBLAS_NUM_THREADS=OMP_NUM_THREADS=MKL_NUM_THREADS=1 and cached NumPy PYTHONPATH.
Run prepare_persistent_crud.py NEW_RAM_DIRECTORY query-selection-expanded-20261009/raw.tar.gz.
For each generated dataset, set VSAG_GRAPH_REPLACEMENTS to replacement.fvecs and storage/degree/ef/query_ef as above;
run taskset -c0 lite_graph_crud_quality DATASET NEW_SNAPSHOT 3 10000 NEW_QUERY_RESULTS.
Commands and environment are frozen per case in raw.tar.gz. For fresh controls, assign the last10000 replacement
rows to IDs from round2 schedule and build with rounds0; final-base digests and derivation receipts are archived.
Run python3 verify.py here to recompute all query hits, operation schedules, quantiles, throughput and hashes.
Measured source is included in raw; later only initial-truth shape validation changed, with final fixtures rerun.
See validation.json for exclusions. Next: maintenance-quality isolation and transactional removal optimization;
do not retune observed queries or declare project acceptance complete.
