# Reproducible Lite / native Full measurements

Build Lite in Release with tests, benchmark tools, FP16 SIMD and optional RaBitQ
enabled. Compile the native runners against the matching installed Full headers
and library, not against arbitrary newer headers:

```bash
c++ -O3 -DNDEBUG -std=c++17 -I "$FULL_PREFIX/include" \
  lite/benchmark/full_rabitq_dataset_main.cpp -L "$FULL_PREFIX/lib" \
  -Wl,-rpath,"$FULL_PREFIX/lib" -lvsag -o "$FULL_BUILDER"
c++ -O3 -DNDEBUG -std=c++17 -DVSAG_BENCH_FULL -I "$FULL_PREFIX/include" \
  lite/benchmark/load_memory.cpp -L "$FULL_PREFIX/lib" \
  -Wl,-rpath,"$FULL_PREFIX/lib" -lvsag -o "$FULL_LOADER"
python3 lite/benchmark/run_aligned_comparison.py \
  --lite-build "$LITE_BUILD" --full-library "$FULL_PREFIX/lib/libvsag.so" \
  --full-builder "$FULL_BUILDER" --full-loader "$FULL_LOADER" \
  --dataset sift10k="$SIFT_DATASET" --dataset gist10k="$GIST_DATASET" \
  --output "$NEW_OUTPUT" --trials 3 --loads 3 --ef 128 --cpu 0
```

Dataset directories contain base.fvecs, queries.fvecs and exact groundtruth.ivecs
with IDs corresponding to base row numbers. All inputs and library hashes are
recorded. The script refuses an existing output directory. Snapshots use
temporary scratch directories (default /dev/shm); raw logs, query samples,
neighbors, configs and snapshot hashes are copied to durable output first.

The Full opt-in `VSAG_FULL_PROFILE=small` uses native HGraph, degree16,
construction ef128, build_thread_count1, memory_io for base and precise storage,
compressed graph, and no redundant raw FP32 copy for floating representations.
FP16 is now available alongside FP32 and native RaBitQ3x5. Without the profile,
historical runner FP32 defaults remain unchanged. The loader accepts
`VSAG_LOAD_FULL_MODE=fp32|fp16|rabitq3x5` with the same profile. RaBitQ uses FHT,
32bit query values, error rate1.9 and reorder. Its randomized rotation can cause
run-to-run recall variation; all trial results must be retained.

Lite has degree16, construction/stored ef128 and explicit per-query ef.
`--ef` changes the query budget only, never construction. Optional
`--full-ef` declares a distinct Full query budget for quality-floor experiments;
different budgets must never be presented as equal-budget results. All runs pin
one CPU and explicitly constrain OpenBLAS, OMP and MKL thread counts to one.
ISA support and runtime dispatch logs are evidence, not proof of identical
floating-point reduction order between implementations.

For I/O regression, replace the Full arguments with
`--control-library /path/to/old/libvsag-lite.so`. The driver verifies the reported
storage and requires byte-identical snapshots and ordered neighbor CSVs for
each pair. The control must provide the existing Lite SearchWithOptions ABI.

```bash
python3 lite/benchmark/test_aligned_comparison.py "$LITE_BUILD" "$CONTROL_LIBRARY"
python3 lite/benchmark/test_full_query_options.py "$FULL_BUILDER"
VSAG_FULL_PROFILE=small python3 lite/benchmark/test_full_query_options.py "$FULL_BUILDER"
```

Measurements deliberately distinguish:

- build-process peak RSS, including input vectors and construction scratch;
- fresh loader total RSS, its before-create/before-load baseline and process peak;
- builder's in-process round-trip load from standalone fresh-process load;
- same-budget retrieval from quality-floor comparisons;
- raw shared-library size from equally stripped shared-library size.

Page cache is warm/uncontrolled; these are not cold-start measurements.
The driver runs zero CRUD rounds: it is not a real changed-vector long-term
CRUD acceptance test. Peak RSS and library size do not constitute a complete
deployment package with dependency closure. Default cohorts may have only
100 queries, making P99 an unstable tail estimate. Same degree/budget/ISA
capabilities do not make two graph topologies equivalent. Report recall,
limitations, configurations, Full revision provenance and all raw trials.
