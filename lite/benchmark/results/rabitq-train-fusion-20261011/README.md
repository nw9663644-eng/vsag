# RaBitQ training row-local validation/accumulation, 2026-10-11

Production change: `train_rows` validates then accumulates each row before requesting the next one, instead of validating the entire matrix and then requesting every row again. Accumulation order within each centroid coordinate, seed47, transformed centroid, finite-value and overflow checks are preserved. Source publication/rollback, graph topology, quantization, query, API and snapshot layout do not change. Official source reference: `src/quantization/rabitq_quantization/rabitq_quantizer.cpp::TrainImpl` accumulates the centroid from source rows; this change retains Lite validation rather than removing it.

This is a small training-stage locality improvement, not a whole-build memory optimization. Do not infer query speedup, reduced peak RSS, improved recall, or Full VSAG superiority.

## Microbenchmark

CPU0, O3/NDEBUG C++17, synthetic deterministic100000-row FP32 matrices, dimensions128/768/960. Control process runs first, candidate second; each has one initial pass and five reported passes. Both executables compiled before timing. No statistical claim or dataset generalization is made. Raw files retain all six rows/dimension. Every model fingerprint agrees, source row callback count changes200000→100000. The fingerprint is a non-cryptographic diagnostic; independent historical-model fixtures provide stronger encoded-output comparison on small cases.

| Dimension | Control median ms | Candidate median ms | Reduction |
| --- | ---: | ---: | ---: |
| 128 | 6.473584 | 5.078371 | 21.55% |
| 768 | 34.797508 | 29.473575 | 15.30% |
| 960 | 42.714655 | 36.489364 | 14.58% |

These tens of milliseconds are a small fraction of complete high-dimensional builds taking tens of seconds. No new full100k end-to-end experiment is claimed. Source retention and incoming-adjacency construction still affect build peak; those acceptance gaps remain.

`probe.cpp` reproduces matrix initialization, callback accounting, fingerprint and scratch/invalid-value fixtures. Compile once with control header overlay and once with candidate header overlay, using recorded flags. It outputs dimension,trial,elapsed_ms,row_calls,model_fingerprint. Archived control/candidate headers pin the exact change; root source/header hashes and validation logs are retained. No large matrix or binary is committed.

## Validation and discovered build regression

Release6/6 and coverage-build6/6 pass after the production change. `test_rabitq_codec_module.py` normal and sanitized runs pass28 exact records over7dimensions, including historical centroid/flips/filter/supplement/scalar/metadata parity, multiple translation units and inverse/decode ownership. Existing reusable-row unit test now asserts exactly N calls, while retaining model/encoding and non-finite rejection assertions.

The first complete sanitizer build failed in an unchanged historical benchmark: the32-bit incoming adjacency could not bind to `estimate_chunk_layout`'s64-bit nested-vector parameter. The estimator now templates the ID type; degree-based hypothetical64-bit chunk accounting remains unchanged (not a new actual-storage claim). Failed log is retained, and the corrected complete sanitizer build/test results are archived separately. Formatting uses clang-format15. This report does not claim fresh whole-project coverage or full lint. Existing coverage counters were not reset before this run, so they are not a fresh isolated coverage union.

No PR2904/2926 update. Only the personal experiment branch receives this change. Latest native Full comparison, GIST100k RaBitQ quality, large-query tail statistics, interleaved long changed-value CRUD and deployment-package closure still require acceptance.
