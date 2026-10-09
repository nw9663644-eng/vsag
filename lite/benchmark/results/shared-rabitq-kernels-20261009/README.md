# Shared native RaBitQ kernels and mutation rollback (2026-10-09)

## Source and change

Baseline: `a38b44717e553fddfb760c9245ebe98f6dc23fd9` on the personal experimental branch. Candidate: accompanying source changes; exact measured libraries and inputs are pinned by SHA256 in identity.json. This is old Lite versus modified Lite, **not Full VSAG parity**.

Lite now calls the existing `RaBitQFloatSupplementCodeIPImpl` in `src/simd/kernels/rabitq_compute.h` through runtime AVX2/AVX512 dispatch. Full and Lite scalar paths share the extracted original scalar function. Full's vector accumulation and reduction remain unchanged. Query sums are cached per query, and final reranking reuses the previously computed filter inner product. No graph budget, encoding layout or snapshot format changes. Native FMA/vector reduction can change distance rounding relative to the old scalar path.

FP32/FP16 public graph mutations now journal affected rows and overwritten records for allocation-failure rollback. Private bulk construction bypasses journaling until publication, avoiding redundant backups. This intentionally adds some mutation overhead in exchange for consistent error semantics.

## Fixed real-data comparison

One CPU (taskset CPU0), Release GCC11.4, 10,000 base vectors, 100 historical queries, k10, degree16, ef128; three alternating fresh-process trials per cell, 54 runs. Each process builds, searches, saves and loads. Table cells are medians of three runs. Page cache is uncontrolled, so load is **not cold I/O**. Rounds=0: these real-data runs do **not measure CRUD performance**. The overlapping preliminary run was discarded; only the isolated sequential batch is reported.

| Dataset | Storage | P50 old → new (us) | P99 old → new (us) | Recall old → new | P50 change |
| --- | --- | --- | --- | --- | --- |
| sift | fp32 | 79.048 → 80.777 | 102.248 → 105.288 | 0.985 → 0.985 | +2.2% |
| sift | fp16 | 77.228 → 77.908 | 101.537 → 101.100 | 0.985 → 0.985 | +0.9% |
| sift | rabitq8 | 163.546 → 134.206 | 231.934 → 210.585 | 0.978 → 0.978 | -17.9% |
| gist | fp32 | 232.055 → 206.886 | 352.161 → 325.233 | 0.916 → 0.916 | -10.8% |
| gist | fp16 | 189.876 → 172.316 | 297.913 → 251.965 | 0.915 → 0.915 | -9.2% |
| gist | rabitq8 | 468.390 → 231.125 | 625.196 → 395.612 | 0.914 → 0.914 | -50.7% |
| cohere | fp32 | 202.516 → 195.666 | 260.634 → 249.295 | 0.960 → 0.960 | -3.4% |
| cohere | fp16 | 176.875 → 176.916 | 222.935 → 217.735 | 0.960 → 0.960 | +0.0% |
| cohere | rabitq8 | 422.981 → 237.605 | 542.228 → 360.822 | 0.961 → 0.961 | -43.8% |

CPU process time, whole-process peak RSS (including base matrix and build), snapshot bytes, build and warm load medians are in summary.json; do not interpret these peaks as loaded-only index memory. Raw stdout, time -v, argv and every query/neighbor are in raw.tar.gz. neighbor-audit.json compares rank/IDs and distance bits across all paired runs. All paired initial snapshot SHA256 values match. Numerical changes are expected from native SIMD; matching recall alone does not prove all IDs identical.

## Synthetic mutation and warmed query check

`optimization_compare.cpp`: 2,048 deterministic vectors, dimensions128/768/960, degree16/ef128, 256 warmed queries repeated four times, three alternating trials. Build and 128 whole-vector Update/Add/Remove cycles (384 operations) are measured separately. synthetic.jsonl includes separate ID and distance hashes plus before/after snapshot hashes. Synthetic timing is not a real-data long-CRUD acceptance result.

## Limits and next decisions

RaBitQ still has query transformation, rotation, coarse filtering and full reranking costs. This improvement does not establish that it beats FP16/FP32, or native Full with aligned configuration. FP32/FP16 query regressions are reported rather than hidden. No equal-recall tuning, cold-load claim, 100k repeated final validation or blind query claim is made. Next: profile transformation/routing/reranking separately; compare native Full and Lite with aligned graph/search/ISA configuration; perform changed-vector long CRUD on real distributions. Do not change public defaults based on these 100 observed queries.

## Reproduction

Configure the baseline and candidate with Release and VSAG_LITE_ENABLE_RABITQ_BACKEND=ON. Run `python3 lite/benchmark/run_optimization_compare.py BASE_BUILD CANDIDATE_BUILD NEW_OUTPUT --sift SIFT_DIR --gist GIST_DIR --cohere COHERE_DIR`. Each input directory contains base.fvecs, queries.fvecs and groundtruth.ivecs. CPU0 and three repeats are default. Do not run other timed jobs concurrently or modify either measured library during the batch.

## Validation

Release 5/5, ASan+UBSan with leak detection 5/5, default RaBitQ-OFF 4/4 and coverage-enabled 5/5 passed. Instrumented production Lite and instantiated shared kernel line coverage: 2568/2704 (94.97%); this is not full repository coverage. 4,500 allocation positions over three storages and three operations produced no changed-on-failure records, invalid snapshots or escaped exceptions; retries succeed. The modified native Generic/AVX512 translation units compile, and the native kernel retains its original bitwise outputs in 840 cases under both O3 and Ofast. The Full repository test suite has not been rerun. Test logs and validation.json record this scope.
