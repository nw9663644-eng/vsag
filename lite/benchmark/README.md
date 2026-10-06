# VSAG Lite baseline experiment

This experimental tool records a deterministic standalone Lite BruteForce baseline. It does not claim a performance improvement.

See [FINAL_REPORT.md](FINAL_REPORT.md) for the consolidated current-head and historical evidence.
See [RABITQ_LITE_FEASIBILITY.md](RABITQ_LITE_FEASIBILITY.md) for the source-based boundary and next experimental gate.\

## Directory layout

- `lite/benchmark/main.cpp`, `dataset_main.cpp`, and `run_*.sh`:
  deterministic Lite baseline, CRUD, load, and SIFT runners.
- `lite/benchmark/full/`, `full_main.cpp`, and `full_dataset_main.cpp`:
  separate Full VSAG comparison consumers.
- `lite/benchmark/prepare_sift.py`: prepares the documented SIFT subsets.
- `lite/benchmark/quantization_probe.cpp`: opt-in SQ8/FP16 scan experiment.
- `lite/benchmark/rabitq_lite_layout_probe.cpp`: opt-in RaBitQ 3+5 bit-plane differential probe.
- `lite/benchmark/rabitq_lite_codec_probe.cpp`: deterministic FHT training, 3-bit lower-bound filtering, 5-bit supplement reranking, and filter-first graph traversal probe.
- `lite/benchmark/prepare_gist.cpp`: bounded GIST fbin-prefix converter that recomputes exact squared-L2 Top-10 ground truth for each selected scale.
- `src/lite/fp16_codec.h` and the internal FP16 factory/tests in
  `src/lite/graph_backend.cpp` and `src/lite/graph_backend_test.cpp`:
  candidate graph experiment, not a public `Index` backend.
- `lite/CMakeLists.txt`: `ENABLE_BENCHMARKS` and
  `ENABLE_QUANTIZATION_PROBE` opt-in build switches.

The public FP32 graph, filtering, CRUD, and snapshot implementation comes from
the Lite feature branch; this experiment branch adds measurements and internal
quantization candidates.

Build it with `-DENABLE_BENCHMARKS=ON`, then run:

```bash
lite/benchmark/run_baseline.sh build-lite-baseline/lite_benchmark baseline-results
```

The runner executes fixed 10k x 128 and 100k x 128 cases. Each case writes one CSV row, a Lite snapshot, and `/usr/bin/time -v` process measurements. It also records the commit, CPU, compiler, CMake version, OS, and benchmark binary checksum in `environment.txt`. The CSV includes build, CRUD, search, save/warm-load, snapshot-size, process peak-RSS, top-1 self-query recall, and a result checksum. The fixed seed makes generated vectors reproducible. In the baseline and Full/Lite comparison CSVs, `peak_rss_kib` is the process-lifetime peak reported by `getrusage(RUSAGE_SELF)`; it covers build, CRUD, search, save, and warm load, not just the load phase.

The same runner also executes a 20-round CRUD stability case. Every round performs 500 Update-Remove-Add cycles while preserving 10,000 live vectors, verifies exact self-query results before and after Save-Load, and records per-round latency, resident/peak RSS, snapshot size, recall, and checksum in `crud-stability.csv`. The snapshot is deliberately overwritten inside a newly created output directory so the experiment retains one verifiable final snapshot instead of twenty identical-size files.

The stability command can also be run directly:

```bash
lite_benchmark stability COUNT DIM ROUNDS CRUD_OPS QUERIES K SEED SNAPSHOT_DIRECTORY
lite_benchmark graph-stability COUNT DIM ROUNDS CRUD_OPS QUERIES K SEED MAX_DEGREE EF_SEARCH SNAPSHOT_DIRECTORY
```

The graph stability mode applies the same update-remove-readd cycle after an explicit
`BuildGraph`. It records the active count, v2 snapshot size, current and peak RSS, recall,
and round-trip checksum together with the graph parameters. The default runner uses a
2,000 x 32, 10-round configuration so this diagnostic remains practical despite physical
graph repair on every removal. Stable RSS and snapshot size show bounded behavior for that
recorded workload; they do not prove that the allocator returns memory to the operating
system or that all workloads are fragmentation-free.

At commit `66f2a18`, the Release runner completed the default graph case with 2,000
live 32-dimensional vectors, degree 12, ef_search 64, and 100 update-remove-readd
cycles per round. All 10 rounds retained 2,000 live IDs and passed Save/Load result
checks. The v2 snapshot stayed within 442,544–472,456 bytes rather than growing
monotonically. Current RSS was 4,300 KiB after round 1 and 5,044 KiB after round 10;
the process-lifetime peak remained 5,044 KiB. Top-1 self-query recall ranged from
0.875 to 1.000, so this run is storage/churn evidence rather than a graph-quality
target. The raw CSV, `/usr/bin/time -v` output, environment record, summary, and
SHA-256 hashes are retained outside Git with the experiment artifacts.

After generating the two baseline snapshots, the runner starts seven separate loader processes for each scale. Every loader reports snapshot size, `load_ms`, first-query latency, follow-up query P50/P99, current/peak RSS, result checksum, and final index size. The known ID 0 query uses variant 1 because the fixed baseline CRUD sequence updates that ID before saving. The loader repeats this same query for every follow-up search, so its `search_p50_us` and `search_p99_us` measure repeated-query latency rather than a distribution across distinct queries. Its `peak_rss_kib` covers the entire loader process.

The loader can also be run directly for a snapshot generated by this benchmark:

```bash
lite_benchmark load SNAPSHOT DIM QUERY_ID QUERY_VARIANT QUERIES K SEED
```

The loader is a fresh process, but the runner does not evict the snapshot from the operating-system page cache. Its CSV therefore records `page_cache_control=uncontrolled`, and the results must be described as fresh-process load measurements rather than strict cold-load measurements.

`warm_load_ms` is measured in the same process immediately after saving and must not be reported as cold-start latency. A strict cold-load experiment must additionally control and document the operating-system page cache.

### Batched snapshot-load comparison

Commit `fb36355` replaces per-value stream calls with bulk reads directly into the final
owned ID, FP32 vector, and adjacency containers. It keeps the v1/v2 little-endian formats
and converts payload values in place on non-little-endian hosts. This remains an
owned-memory load rather than mmap or zero-copy.

On 2026-09-20, the same Release executables alternated only the loaded shared library
between parent `64bbed5` and `fb36355`. The v1 generated 100k x 128 snapshot used seven
runs per version. The v2 graph case used five runs per version on the 100k SIFT snapshot
at degree 16 / ef 128; every run executed the existing `[lite-sift-load]` assertions and
100 queries. Page cache state was uncontrolled, so these are fresh-process comparisons,
not strict cold-load measurements.

| Snapshot | Before median Load (ms) | Batched median Load (ms) | Speedup | Result check |
| --- | ---: | ---: | ---: | --- |
| v1 BruteForce, 52,000,048 bytes | 192.956 | 22.436 | 8.60x | identical checksum and 100,000 IDs |
| v2 graph, 65,600,064 bytes | 250.835 | 34.652 | 7.24x | Recall@10 0.946 and all 611 assertions passed |

Median process RSS was effectively unchanged: 58,448 versus 58,428 KiB for v1 and
76,172 versus 76,140 KiB peak RSS for v2. The raw stdout, `/usr/bin/time -v` files,
commands, and exact-commit artifact directories are retained outside Git. The comparison
does not measure mmap, zero-copy loading, native big-endian execution, or strict cold I/O.

The runners check that their benchmark executables and library inputs exist before creating an output directory, and refuse to overwrite an existing output directory or snapshot. Run them on an otherwise idle machine and retain the compiler, commit SHA, CPU, and raw output with any report.

## Full/Lite comparison

`full_main.cpp` exercises the public Full VSAG BruteForce API with the same generated FP32 vectors, query sequence, dimensions, seed, and operation counts as the Lite baseline. Full removal explicitly uses `RemoveMode::FORCE_REMOVE`, matching Lite's immediate last-record-to-hole removal semantics; the default Full `MARK_REMOVE` behavior is not equivalent.

Build and install Full VSAG from the same commit, build `lite/benchmark/full` against that installation, and build the Lite benchmark with `ENABLE_BENCHMARKS=ON`. Then run:

```bash
lite/benchmark/run_comparison.sh \
  FULL_BENCHMARK LITE_BENCHMARK FULL_LIBVSAG_SO LITE_LIBVSAG_LITE_SO OUTPUT_DIRECTORY
```

The runner alternates Full/Lite execution order over seven repetitions for both 10k x 128 and 100k x 128 cases. It records raw and stripped shared-library sizes, binary and library checksums, per-process `/usr/bin/time -v` output, CSV measurements, and snapshots. It extracts the single CSV header/data pair from captured stdout and fails if the pair is missing, duplicated, or malformed; Full VSAG diagnostic logs remain in the raw stdout file. Results compare two exact FP32 squared-L2 BruteForce implementations; they do not establish graph-index performance or standard-dataset Recall@K.

## SIFT-128 subset Recall@10

The optional `lite_dataset_benchmark` evaluates independent queries from the public
[ANN-Benchmarks SIFT-128 Euclidean dataset](https://github.com/erikbern/ann-benchmarks).
Install Python `numpy` and `h5py` in an isolated environment, download the HDF5
file to a directory outside the repository, and prepare the two prefixes:

```bash
curl -fL -o /data/sift-128-euclidean.hdf5 https://ann-benchmarks.com/sift-128-euclidean.hdf5
python3 lite/benchmark/prepare_sift.py /data/sift-128-euclidean.hdf5 /data/sift-prepared
cmake -S lite -B build-lite-baseline -DCMAKE_BUILD_TYPE=Release -DENABLE_BENCHMARKS=ON
cmake --build build-lite-baseline --target lite_dataset_benchmark
lite/benchmark/run_sift.sh build-lite-baseline/lite_dataset_benchmark /data/sift-prepared /data/sift-results
```

The preparation script takes the first 10k and 100k training vectors and the
first 100 independent test queries. It recomputes squared-L2 exact Top-10
ground truth separately on each selected base prefix (ties by ascending ID).
The HDF5 file's original 1M-base neighbors must not be reused for a subset.
Each `manifest.json` records the source and converted-file SHA-256 hashes;
the output directory must be new. The runner records seven raw CSVs, process
measurements, environment and per-scale manifests. The executable verifies
each query's search result against the selected-prefix ground truth, then
checks exact result and distance equality after Save/Load. These measurements
cover standalone Lite exact BruteForce only; they do not compare Full on this
dataset, imply an ANN quality improvement, or measure strict cold loading.
The scripts require a little-endian host for the fvecs/ivecs interchange files.

To compare Full and Lite BruteForce on the same prepared SIFT subsets, build
the independent Full consumer against a Full VSAG installation from this
commit and run the alternating seven-round comparison:

```bash
cmake -S lite/benchmark/full -B build-full-dataset -DCMAKE_PREFIX_PATH=/path/to/full-install
cmake --build build-full-dataset --target full_dataset_benchmark
lite/benchmark/run_sift_comparison.sh build-full-dataset/full_dataset_benchmark \
  build-lite-baseline/lite_dataset_benchmark /path/to/full-install/lib/libvsag.so \
  build-lite-baseline/libvsag-lite.so /data/sift-prepared /data/sift-comparison
```

Each implementation gets the same base/query/ground-truth files and Top-10
definition. Full uses FP32 squared-L2 BruteForce and its own snapshot format;
it copies query values into an existing Dataset outside the timed search.
The runner retains raw process stdout, stderr, CSV, snapshots, environment,
and seven executions per scale per implementation. The Full library and Lite
library build identities should be recorded alongside the executable hashes
when reporting this comparison.

# SQ8 and FP16 candidate probe (not an index backend)

This standalone executable evaluates two possible Lite quantization formats. It
does **not** change Index, graph traversal, the v1/v2 snapshot, or process
resident memory of the current Lite index. The measured `sq8_code_bytes`
and `fp16_code_bytes` count only encoded vectors; the probe also keeps the
FP32 base dataset and training model in memory to calculate exact ground truth and reconstruction
error. Its process RSS is therefore not the memory use of a quantized index.

The probe reuses the repository's generic scalar SQ8 squared-L2 kernel and
`ClampScalarQuantizationDelta`. It trains **classic per-dimension minimum and
maximum bounds** on the selected base vectors, encodes one unsigned byte per
dimension, and searches all encoded vectors with FP32 queries. Full VSAG's
`ScalarQuantizer` normally uses a sampled/truncated-bound trainer and brings
additional allocator, parameter and SIMD-dispatch dependencies; this probe is
not bit-identical to that full training configuration.

FP16 uses a standalone portable IEEE binary16 encoder with round-to-nearest-even
and the repository's generic half-precision squared-L2 kernel. It rejects
values outside the finite FP16 range. The encoder is not Full VSAG's
`FloatToFP16` implementation; this probe does not test production format
compatibility. Both the base and query vectors are encoded for FP16 search.
The self-test includes positive and negative zero, a subnormal, a halfway
rounding case, the maximum finite value, and overflow rejection.

Configure the independent Lite build and run a self-test:

    cmake -S lite -B /path/to/build-quantization -G Ninja -DCMAKE_BUILD_TYPE=Release -DENABLE_QUANTIZATION_PROBE=ON
    cmake --build /path/to/build-quantization --target lite_quantization_probe -j2
    /path/to/build-quantization/lite_quantization_probe --self-test

Run the prepared 10k or 100k SIFT-128 subset from the experiment workflow:

    /usr/bin/time -v -o /path/to/results/quantization-100k.time.txt /path/to/build-quantization/lite_quantization_probe /path/to/scale-100000 > /path/to/results/quantization-100k.csv 2> /path/to/results/quantization-100k.stderr.txt

The program checks that the FP32 exhaustive top-10 matches the supplied exact
ground truth on 100 independent queries, then reports SQ8 and FP16
Recall@10, RMSE, query P50/P99 and encoded byte counts. Search times are
exploratory, rotate FP32/SQ8/FP16 order per query, and use generic scalar
kernels. They are neither graph-search latency nor an optimized SIMD
comparison. The tool assumes Linux x86_64 little-endian fvecs/ivecs input. It rejects missing,
truncated, wrong-dimension, non-finite and inconsistent datasets.

On 2026-09-14, three serial 100k SIFT-128 runs measured the following
candidate outcomes (median of each run's query P50):

| Scan | Recall@10 | P50 | Encoded vector bytes |
| --- | ---: | ---: | ---: |
| FP32 exact | 1.000 | 8.855 ms | 51,200,000 |
| SQ8 | 0.988 | 34.145 ms | 12,800,000 plus 1,024-byte model |
| FP16 | 1.000 | 47.474 ms | 25,600,000 |

These timings are from generic scalar exhaustive scans, not the Lite graph.
The FP16 result is lossless on original integer-valued SIFT coordinates:
its reconstruction RMSE was zero. As an additional **transformed input**
check, multiplying the 10k SIFT base and queries by 0.001 produced nonzero
FP16 RMSE (0.000009) and Recall@10 1.000 against FP32 exact truth. This
transformed case is not a standard dataset result and does not establish
quality for general floating-point embeddings. The probe keeps all three
representations in memory; encoded bytes are not index RSS or snapshot size.

The exhaustive scan remains an offline algorithm comparison. FP16 graph storage
is now exposed by the Lite API and uses the official SIMD-dispatched half
kernel plus the separately versioned v3 snapshot; SQ8 remains an offline
candidate.

## Public FP16 graph resident memory

The hidden `[lite-sift-rss]` probe builds either the default FP32 graph or
`VectorStorage::FP16` through the public Index API in a fresh process. It
releases the input base vectors, calls `malloc_trim(0)` on glibc, executes the
same 100 independent queries, and reads current `VmRSS` from
`/proc/self/status`. Queries and ground truth remain resident, so the result
is a same-process-layout comparison rather than an exact container byte count.

    VSAG_SIFT_DIR=/path/to/scale-100000 VSAG_SIFT_RSS_BACKEND=fp32 /path/to/lite_graph_tests '[lite-sift-rss]'
    VSAG_SIFT_DIR=/path/to/scale-100000 VSAG_SIFT_RSS_BACKEND=fp16 /path/to/lite_graph_tests '[lite-sift-rss]'

On 2026-09-20, one fresh process per backend produced:

| SIFT-128 subset | Storage | Recall@10 | Current RSS |
| --- | --- | ---: | ---: |
| 10k | FP32 | 0.973 | 12,036 KiB |
| 10k | FP16 | 0.973 | 9,492 KiB |
| 100k | FP32 | 0.946 | 77,424 KiB |
| 100k | FP16 | 0.946 | 52,236 KiB |

FP16 reduced current RSS by 21.1% at 10k and 32.5% at 100k in these single
runs while preserving measured Recall@10. The 100k FP16 graph also stores
25,600,000 vector-code bytes instead of 51,200,000 FP32 bytes; IDs, links,
containers, queries, ground truth, allocator behavior, and the process image
explain why total RSS does not fall by 50%. These are single-host, single-run
measurements and not a variance or cross-platform study.

## FP16 v3 snapshot size and fresh-process load

The hidden `[lite-sift]` probe accepts `VSAG_GRAPH_STORAGE=fp32|fp16`; omitting the variable preserves the FP32 default. It builds through the public API, writes a v2 FP32 or v3 FP16 snapshot, reloads it, verifies the active storage, and checks exact result and distance equality across the round trip. The `[lite-sift-load]` probe discovers the stored representation after loading and reports first-query latency separately from follow-up-query P50/P99, together with current and process-lifetime peak RSS.

At commit `bcd2388`, one snapshot per storage and scale was generated and each snapshot was loaded in seven fresh processes with alternating FP32/FP16 execution order. The table reports the single build/save observation and the median of seven load processes. Page cache state was uncontrolled, so Load is a fresh-process metric rather than strict cold I/O.

| SIFT-128 subset | Storage | Snapshot bytes | Recall@10 | Build (ms) | Save (ms) | Load median (ms) | First query median (us) | Follow-up P50/P99 median (us) | Steady RSS median (KiB) | Peak RSS median (KiB) |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 10k | FP32 v2 | 6,560,064 | 0.973 | 864.663 | 26.526 | 3.373 | 129.207 | 100.097 / 128.808 | 11,724 | 11,764 |
| 10k | FP16 v3 | 4,000,064 | 0.973 | 843.392 | 24.027 | 27.149 | 175.937 | 108.498 / 156.537 | 9,260 | 14,064 |
| 100k | FP32 v2 | 65,600,064 | 0.946 | 20,178.9 | 276.240 | 34.874 | 459.440 | 337.664 / 462.920 | 75,808 | 75,908 |
| 100k | FP16 v3 | 40,000,064 | 0.946 | 17,230.1 | 243.660 | 270.980 | 455.701 | 308.394 / 432.701 | 50,752 | 100,600 |

The v3 snapshot is 39.0% smaller at both scales. Its median steady RSS is 21.0% lower at 10k and 33.1% lower at 100k, with unchanged measured Recall@10. The current v3 Load path is 8.05x slower at 10k and 7.77x slower at 100k, and its process peak RSS is higher. `Index::Load` currently reads every binary16 value through a per-value stream operation into a temporary FP32 vector; `GraphBackend::Restore` then encodes that FP32 vector back into final FP16 storage. This double conversion explains the observed load-time and transient-memory bottleneck and identifies a targeted follow-up optimization. Query latency differences are mixed and should not be generalized from one snapshot generation.

Raw stdout, stderr, `/usr/bin/time -v`, environment metadata, snapshot SHA-256 values, and the generated summary are retained in `/home/ubuntu/project/vsag-lite-fp16-v3-load-validation-20260920-bcd2388` on the measured host. The experiment does not measure mmap, zero-copy loading, strict cold I/O, native big-endian execution, or cross-host variance.

### Direct v3 restore follow-up

Feature commit `5ac36ef` removes the FP32 staging copy. `Index::Load` bulk-reads portable binary16 values into a `uint16_t` container, byte-swaps in place when required, rejects non-finite exponent patterns without decoding to float, and moves the container directly into the FP16 graph backend. Versions 1 and 2 and the v3 bytes remain unchanged.

The comparison reused the exact `[lite-sift-load]` executable from probe commit `bcd2388` (rebased as `73f78a3`), the same v3 snapshot per scale, and switched only `LD_LIBRARY_PATH` between feature baseline `73f9c4c` and `5ac36ef`. Each version ran in seven fresh processes with alternating order. Values below are medians; page cache state remained uncontrolled.

| SIFT-128 subset | Library | Load (ms) | First query (us) | Follow-up P50/P99 (us) | Steady RSS (KiB) | Peak RSS (KiB) | Recall@10 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 10k | Before | 27.089 | 169.066 | 107.697 / 152.277 | 9,204 | 14,012 | 0.973 |
| 10k | Direct restore | 2.580 | 124.417 | 95.097 / 123.678 | 9,200 | 9,240 | 0.973 |
| 100k | Before | 270.248 | 441.151 | 297.024 / 406.631 | 50,752 | 100,600 | 0.946 |
| 100k | Direct restore | 26.168 | 397.111 | 283.013 / 381.693 | 50,748 | 50,848 | 0.946 |

Direct restore improved median v3 Load by 10.50x at 10k and 10.33x at 100k. Median process peak RSS fell by 34.1% and 49.5%; steady RSS, snapshot bytes, snapshot SHA-256, and Recall@10 remained unchanged. Query timings were not the optimization target and show no regression in these runs. The result demonstrates removal of the measured conversion bottleneck, while retaining the owned-memory, non-mmap load design and the same strict-cold-I/O limitation.

All 28 loader processes passed their assertions with empty stderr. Raw stdout, stderr, `/usr/bin/time -v`, environment and binary hashes, snapshot hashes, and summaries are retained in `/home/ubuntu/project/vsag-lite-fp16-v3-load-compare-20260920-5ac36ef`.

## Full HGraph RaBitQ reference probe

`full_rabitq_dataset_benchmark` is an opt-in Full VSAG consumer used to evaluate
official RaBitQ behavior before proposing a Lite storage format. It compares the
same public HGraph implementation at degree 16 and `ef_search=128` in three modes:

- `fp32`: FP32 base storage.
- `rabitq1`: one-bit RaBitQ traversal with FP32 reorder, the documented safe default.
- `rabitq3x5`: three filter bits plus five supplement bits in split storage.

The probe uses public `Factory`, `Index::Build`, search, Serialize, and Deserialize
APIs. It reports Recall@10, build and query latency, snapshot size, and process RSS,
and requires identical results after round-trip loading. It does not copy or expose
the internal RaBitQ quantizer in Lite.

Build the independent Full consumer and run seven alternating repetitions:

```bash
cmake -S lite/benchmark/full -B build-full-rabitq \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_PREFIX_PATH=/path/to/full-vsag-install
cmake --build build-full-rabitq --target full_rabitq_dataset_benchmark
lite/benchmark/run_rabitq_reference.sh \
  build-full-rabitq/full_rabitq_dataset_benchmark \
  /path/to/full-vsag-install/lib/libvsag.so \
  /path/to/prepared-sift /new/output-directory
```

This is a Full HGraph reference, not a Lite graph benchmark. It is suitable for
checking achievable quality, storage, and dependency cost, but algorithm-level
differences prevent attributing Full-versus-Lite differences solely to quantization.

### Measured RaBitQ reference results

At experiment commit `844790629e57bcd89809dbba58b260f8a74d74e1`,
the runner executed seven fresh processes per scale and mode, rotating the mode
order on each repetition. All 42 processes passed the serialize/deserialize
identity checks and produced empty stderr. Values below are medians; brackets
show the observed Recall@10 or P99 range where it materially affects
interpretation.

| SIFT-128 subset | Mode | Recall@10 median [range] | Build (ms) | Query P50/P99 median (us) | Snapshot bytes | Final RSS (KiB) | Peak RSS (KiB) |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 10k | FP32 | 0.997 [0.971, 1.000] | 258.890 | 90.148 / 141.856 | 5,765,755 | 169,320 | 177,052 |
| 10k | RaBitQ 1-bit + FP32 reorder | 0.987 [0.921, 0.990] | 304.969 | 93.278 / 124.655 | 6,013,051 | 300,676 | 308,660 |
| 10k | RaBitQ 3+5 split | 0.983 [0.919, 0.995] | 328.196 | 121.757 / 153.896 | 2,202,806 | 301,480 | 308,896 |
| 100k | FP32 | 0.997 [0.996, 0.998] | 3,227.986 | 190.635 / 265.864 | 57,157,546 | 190,456 | 315,288 |
| 100k | RaBitQ 1-bit + FP32 reorder | 0.915 [0.901, 0.928] | 3,389.983 | 181.305 / 238.453 | 59,567,366 | 321,404 | 446,720 |
| 100k | RaBitQ 3+5 split | 0.986 [0.984, 0.989] | 3,605.873 | 221.003 / 326.071 [290.072, 2,891.121] | 22,235,021 | 322,544 | 461,840 |

At 100k, the 3+5 split snapshot is 61.1% smaller than the FP32 HGraph
snapshot, with an absolute Recall@10 median change of -0.011. Its median query
P50 is 15.9% slower, build is 11.7% slower, and load is 20.3% slower
(79.451 ms versus 66.044 ms). One 3+5 run produced a 2.891 ms P99 outlier, so
the tail result is not yet stable. The 1-bit mode is not a storage candidate
for the Lite objective in this configuration: its FP32 reorder payload makes
the snapshot 4.2% larger than FP32, while Recall@10 is lower and resident
memory is substantially higher.

The Full process retains transform models and Full VSAG dependencies, so its
RSS is evidence about integration cost rather than a projection of a future
Lite backend. These measurements also compare three Full HGraph
configurations; they must not be combined with the separate Lite graph
measurements to claim a quantization-only speed or memory change. The next
bounded step is therefore a Lite-specific 3+5 storage-layout and dependency
audit. No RaBitQ code or API should be added to the feature PR until that
design identifies an independently testable minimal subset.

Raw CSV, stdout, stderr, `/usr/bin/time -v`, snapshots, manifests, environment
metadata, and binary/library hashes are retained outside Git at:

```text
/home/ubuntu/project/vsag-lite-rabitq-reference-20260921-8447906
```

The measured benchmark executable SHA-256 is
`b50d34d3cc4e46a9b38564d930c3ae05fb38565a23407ac94d49b3bd7d7feba6`;
the Full VSAG shared library SHA-256 is
`4d245bfcde3969ecd18b338b68d7cd8b3a8f4c47d39eeba71045b9aafadb7505`.

## Lite RaBitQ 3+5 search probe

The opt-in codec probe follows the Full RaBitQ L2 split-search equations without changing the public Lite API or snapshots. It trains a deterministic four-round FHT model, encodes an 8-bit CAQ scalar code, stores the high 3 bits in filter planes and the low 5 bits in supplement planes, and records the norm/error metadata needed by the official lower-bound formula. Search scans the filter payload first and reads the supplement payload only when the lower bound can still enter the current Top-K heap.

Run its deterministic self-test or the prepared SIFT-10k smoke with:

```bash
build-lite-rabitq-codec-run/lite_rabitq_codec_probe --self-test
build-lite-rabitq-codec-run/lite_rabitq_codec_probe /path/to/scale-10000
```

The 2026-09-21 SIFT-10k smoke produced 0.994 Recall@10 for both the full 8-bit split scan and lower-bound-filtered search. The filtered result matched the full-code Top-10 exactly and reordered a mean 136.43 of 10,000 candidates (1.3643%). Its 480,000 filter bytes, 800,000 supplement bytes, and 240,000 metadata bytes describe encoded payloads only; the standalone process also retains source vectors, queries, model state, and C++ container overhead. The single run is a functional smoke, not a stable latency benchmark or evidence for a public Lite backend.

On 2026-09-22, seven fresh processes repeated the prepared SIFT-100k case at commit `a99b0e6`. Every run produced 0.985 Recall@10 for both the full 8-bit split scan and lower-bound-filtered search, with exact Top-10 agreement between those two paths. A mean 227.26 of 100,000 candidates (0.2273%) read the 5-bit supplement. Median build-and-encode time was 406.992 ms, filtered-search query P50 was 14,216.053 us, and process peak RSS was 78,456 KiB. The process retains the input vectors and per-record C++ allocations, so RSS is not the encoded payload size. Dataset page-cache state was uncontrolled, and this probe uses scalar plane decoding; the timing is experimental evidence rather than an optimized search claim. Raw CSV, `/usr/bin/time -v`, environment, hashes, and summary are retained outside Git at `/home/ubuntu/project/vsag-lite-rabitq-search-100k-20260922-a99b0e6`.

The next probe revision adds an independent little-endian `VSLRBQ01` v1 snapshot for the FHT model, split payloads, and distance metadata. Its self-test verifies byte round-trip search equality and rejects truncation, a bad magic value, non-finite or invalid metadata, excessive dimensions/counts, and trailing bytes. This remains an experiment-only format and does not alter public Lite snapshot versions v1/v2/v3.

### Contiguous RaBitQ record storage

The next probe revision replaces one `filter` and one `supplement` allocation per record with three owned contiguous arrays: all filter planes, all supplement planes, and fixed-size metadata. The scalar 8-bit code remains a temporary encoding buffer and is not retained. The self-test verifies record strides and byte-identical snapshot output after load/save. Single fresh-process checks retained the same 10k/100k Recall@10, filtered/full agreement, and reorder counts. The 100k process peak was 69,048 KiB versus the earlier seven-run median of 78,456 KiB (12.0% lower), but that comparison is directional because the new value is a single run and both processes retain source vectors. Raw output and `/usr/bin/time -v` evidence are in `/home/ubuntu/project/vsag-lite-rabitq-contiguous-validation-20260922`.

### RaBitQ filter-first graph traversal

The graph adapter reuses the existing Lite FP32 graph builder to produce a controlled topology, exports that topology into contiguous CSR offsets and neighbors, and then searches it using only the RaBitQ 3-bit filter distance. After traversal, it reads the 5-bit supplement for at most `ef_search=128` candidates and returns the full-code Top-10. This isolates traversal and reorder behavior without introducing another graph-construction algorithm. The probe now links `vsag::lite` only to build the reference topology; its RaBitQ model, records, traversal, and distance path remain experiment-local.

Single fresh-process SIFT results with degree 16 and `ef_search=128` were:

| Scale | Full RaBitQ Recall@10 | Graph Recall@10 | Mean visited | Supplement reorder | Full-scan P50 (us) | Graph P50 (us) | CSR bytes |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 10k | 0.994 | 0.966 | 829.15 | 128 | 1,461.610 | 281.383 | 1,360,008 |
| 100k | 0.985 | 0.940 | 1,150.83 | 128 | 14,266.271 | 406.009 | 13,600,008 |

The 100k graph traversal is 35.1x faster than this probe's scalar full scan, while Recall@10 is 0.006 below the separately measured public Lite FP32 graph result of 0.946. This is a functional gate, not a stable performance comparison: each scale ran once, the scalar filter kernel is not SIMD-dispatched, and process peak RSS includes the input dataset plus temporary BruteForce and FP32 graph instances used to build/export the topology. Raw CSV, stderr, and `/usr/bin/time -v` evidence are in `/home/ubuntu/project/vsag-lite-rabitq-graph-validation-20260922-final`.

## GIST-960 RaBitQ validation

The RaBitQ codec probe accepts non-power-of-two dimensions using the same four-round transform shape as `FHTKacRotator`: alternating front/back floor-power-of-two FHT blocks, sign masks, Kac mixing, and final scaling. Its self-test covers dimensions 768 and 960, norm preservation, deterministic encoding, layout sizes, and snapshot round trips.

Prepare a documented prefix from the public ANN_GIST1M `fbin` files outside the repository. The converter requires 960-dimensional inputs, rejects truncated or non-finite payloads, and recomputes exact Top-10 independently for the 10k and 100k prefixes:

```bash
cmake -S lite -B build-lite-rabitq -DCMAKE_BUILD_TYPE=Release \
  -DENABLE_RABITQ_LITE_PROBE=ON -DENABLE_TESTS=ON
cmake --build build-lite-rabitq --target lite_prepare_gist lite_rabitq_codec_probe
build-lite-rabitq/lite_prepare_gist base.fbin query.fbin /data/gist-prepared 100000 100
build-lite-rabitq/lite_rabitq_codec_probe /data/gist-prepared/scale-10000 32 512
build-lite-rabitq/lite_rabitq_codec_probe /data/gist-prepared/scale-100000 32 512
```

On the recorded 100-query prefixes, exhaustive full-code and lower-bound-filtered Recall@10 were both 0.997 at 10k and 100k. With `max_degree=32` and `ef_search=512`, graph Recall@10 was 0.984 at 10k and 0.949 at 100k; graph-search P50 was 5.408 ms and 9.139 ms. The 100k run encoded in 2.715 s, built the temporary FP32-derived graph in 180.568 s, used 1,408,628 KiB process peak RSS, and stored 36.0 MB filter payload, 60.0 MB supplement payload, 2.4 MB metadata, and 26.4 MB CSR topology (decimal bytes).

These are single-run experiment results, not a public-backend or SIMD performance claim. The scalar full scan keeps source vectors and a temporary FP32 graph backend resident, and the GIST subsets are prefix-specific datasets with recomputed ground truth. Full GIST1M is optional stress testing rather than a Lite acceptance requirement; high dimensionality is covered here without redefining Lite as a million-scale index.

## RaBitQ CSR snapshot experiment

The experiment-only `VSLRBQ01` format keeps its existing version 1 model/code payload unchanged. Version 2 appends the CSR graph as little-endian offset and neighbor arrays. Loading validates the offset count, zero origin, monotonic and bounded adjacency ranges, maximum degree 64, final edge count, neighbor range, self-loops, duplicate neighbors, truncation, and trailing bytes before graph search can run.

Use separate processes to save and restore a prepared dataset:

```bash
build-lite-rabitq/lite_rabitq_codec_probe --save \
  /data/sift-prepared/scale-10000 /data/sift-10k-rabitq-v2.bin 16 128
build-lite-rabitq/lite_rabitq_codec_probe --load \
  /data/sift-prepared/scale-10000 /data/sift-10k-rabitq-v2.bin 128
```

Recorded SIFT-10k and SIFT-100k snapshots were 2,880,648 and 28,800,648 bytes. Fresh-process load took 6.817 and 66.843 ms, and restored graph Recall@10 remained exactly 0.966 and 0.940. Mean visited/reordered counts also remained 829.15/128 and 1,150.83/128. The 100k loader used 32,176 KiB process peak RSS. These are single-run fresh-process measurements with uncontrolled page cache; they validate independent persistence and result stability rather than strict cold-load performance.

Version 2 is local to the opt-in probe. It does not change public Lite v1/v2/v3 snapshots or expose RaBitQ through `VectorStorage`.


### RaBitQ fixed-model CRUD experiment

The experiment now has a correctness-oriented mutable graph state. Add and Update encode with the existing trained centroid and FHT masks; the model is never retrained. Remove uses last-slot compaction, repairs every reference to the removed and moved slots, and preserves the external-ID-to-slot map. The mutation path expands persisted CSR into adjacency vectors and uses exhaustive full-code neighbor selection, so it is not a mutation-performance result.

VSLRBQ01 version 3 persists the fixed model, contiguous split records, external IDs, graph options, and CSR topology. Versions 1 and 2 remain unchanged. The self-test runs 180 deterministic mixed Add/Update/Remove operations, checks structural invariants after every operation, and requires byte-stable persistence plus identical graph-search results after a fresh restore.

This remains local to lite_rabitq_codec_probe; it does not change the public Lite API or public snapshot formats. Pairwise degree pruning currently reconstructs an approximate query from the stored 8-bit code, and SIMD filter dispatch is still open.


### RaBitQ fixed-model CRUD stability mode

The codec probe can measure the experiment-only mutable state with a fixed trained model:

    lite_rabitq_codec_probe --crud DATASET_DIR SNAPSHOT ROUNDS CRUD_OPS QUERIES MAX_DEGREE EF_SEARCH

Each operation updates one external ID, removes it, and adds the same ID and updated vector again, keeping the active count fixed. Full structural validation runs after each mutation batch rather than inside the timed operations. Each CSV row reports Update/Remove/Add P50 and P99, adjacency-to-CSR compaction, graph-search latency, exhaustive full-code and graph self-query Top-1, graph/full agreement, traversal work, snapshot save/load, snapshot bytes, RSS, and a deterministic result checksum.

The loader must reproduce every measured graph result and distance exactly. The reported state RSS is sampled before loading; round-trip RSS includes both the original and restored states. Process peak RSS also includes source vectors and the temporary FP32 graph used to create the initial reference topology. Mutation neighbor discovery reuses the filter-first graph traversal with the official exploration-depth rule and falls back to exhaustive full-code selection if it cannot return enough unique non-self neighbors. The CSV reports these fallbacks explicitly. This remains an experiment-only scalar path, so the numbers must not be presented as production update throughput.

At commit cf7a0f08, SIFT-10k ran five rounds of 50 CRUD cycles and SIFT-100k ran three rounds of 20 cycles, with 100 control queries per round, degree 16, and ef_search 128. Every round preserved its active count, produced empty stderr, and restored exactly the same graph result IDs and distances.

| Scale | Update P50 median | Remove P50 median | Add P50 median | Graph search P50 median | Full self Top-1 | Graph self Top-1 median | Graph/full Top-1 median | Snapshot median | State RSS median |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 10k | 4,117.827 us | 446.159 us | 4,027.419 us | 305.802 us | 1.000 | 0.960 | 0.960 | 2,949,520 B | 23,268 KiB |
| 100k | 39,843.379 us | 4,449.088 us | 39,208.362 us | 535.205 us | 1.000 | 0.920 | 0.920 | 29,597,472 B | 156,672 KiB |

The roughly 10x Update/Add increase from 10k to 100k identifies exhaustive full-code neighbor selection as the dominant mutation bottleneck. Remove also scales about 10x because it intentionally scans all possibly asymmetric adjacency lists. The first 100k round had a 16.254 ms Remove P99 outlier; later round P99 values were 4.595/4.544 ms. Graph/full positional Top-10 agreement ranged from 0.899 to 0.946 at 10k and 0.789 to 0.834 at 100k, while full-code self Top-1 stayed 1.000. This supports optimizing mutation neighbor discovery next, while retaining the exhaustive path as a differential oracle. Raw CSV, stderr, /usr/bin/time -v, environment, binary hash, summary, snapshots, and verified SHA-256 manifest are in /home/ubuntu/project/vsag-lite-rabitq-crud-validation-20260923-cf7a0f0.

Commit e2f096b9 replaced exhaustive mutation selection with the existing filter-first graph traversal and removed per-row sort/unique work from the correctness-required all-adjacency Remove scan. The exact same matrices produced zero exhaustive fallbacks and empty stderr:

| Scale | Update P50 median | Speedup | Remove P50 median | Speedup | Add P50 median | Speedup | Graph self Top-1 median | Graph/full positional median |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 10k | 617.175 us | 6.67x | 101.256 us | 4.41x | 514.037 us | 7.83x | 0.960 | 0.932 |
| 100k | 2,917.346 us | 13.66x | 921.936 us | 4.83x | 2,204.874 us | 17.78x | 0.920 | 0.800 |

Full-code self Top-1 remained 1.000. The optimized 10k/100k medians for snapshot bytes, state RSS, and graph-search P50 were effectively unchanged from the control matrix; 100k values were 29,597,472 B, 156,796 KiB, and 552.096 us. The matched quality medians and zero fallbacks show that the speedup came from bounded graph candidate discovery and removal of redundant list sorting in this workload. They do not prove that fallback is impossible on other graph shapes or that mutation is production-ready. Raw evidence and a machine-readable old/new comparison are in /home/ubuntu/project/vsag-lite-rabitq-graph-mutation-validation-20260923-e2f096b.

### RaBitQ filter SIMD experiment

Commit `214630d4` reuses the official `RaBitQFloatThreeBitCenteredIPImpl` kernel and AVX2/AVX512 traits in probe-only translation units. Runtime selection follows the existing Lite CPU-feature pattern and falls back to the portable scalar implementation. The probe still links only `libvsag-lite`; it does not add Full VSAG as a dependency. The self-test compares all 64 encoded records against the scalar formula before using the dispatched path.

The same fixed-count CRUD matrices produced the following medians relative to the graph-selected scalar control:

| Scale | Update P50 | Speedup | Add P50 | Speedup | Graph search P50 | Speedup | Graph self Top-1 | Graph/full positional |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 10k | 478.638 us | 1.29x | 390.099 us | 1.32x | 190.924 us | 1.57x | 0.960 | 0.932 |
| 100k | 2,693.471 us | 1.08x | 2,008.118 us | 1.10x | 387.919 us | 1.42x | 0.920 | 0.800 |

Every round kept full-code self Top-1 at 1.000, used zero exhaustive mutation fallbacks, restored identical result IDs/distances, and produced empty stderr. Remove does not use the filter inner-product kernel; its 0.97x/0.93x ratios are run-to-run variation rather than a SIMD result. Snapshot bytes and state RSS were effectively unchanged.

The measured host selected AVX512 and supports AVX2 fallback. Release and ASan+UBSan CTest passed 6/6; clang-format-15, clang-tidy-15, and the standalone dependency check passed. Raw CSV, snapshots, time output, CPU metadata, binary/source hashes, and a verified SHA-256 manifest are in `/home/ubuntu/project/vsag-lite-rabitq-simd-validation-20260923`. These results close the bounded scalar-filter performance risk on this x86 host. ARM SIMD, batch-four full scans, mutable adjacency memory, and the public backend contract remain separate work.

### Isolated mutable RaBitQ memory

The version 3 mutable snapshot can be loaded in a fresh process without retaining
the source dataset or the temporary FP32 graph builder:

    lite_rabitq_codec_probe --mutable-rss SNAPSHOT

The command reports logical and capacity bytes for the model, split-code storage,
external IDs, and adjacency, together with adjacency edge count, ID-map entry and
bucket counts, load time, current RSS, and peak RSS. `known_capacity_bytes` does
not include `std::unordered_map` node or bucket allocations, so the entry and
bucket counts are reported separately rather than estimated as portable bytes.

Seven fresh processes per scale loaded the SIMD-stage SIFT snapshots. The
following values are medians:

| Scale | Snapshot | Load | Known owned capacity | Adjacency edges | Adjacency capacity | ID-map entries / buckets | Current RSS | Peak RSS |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 10k | 2,943,408 B | 10.257 ms | 3,103,312 B | 157,842 | 1,502,736 B | 10,000 / 10,273 | 7,792 KiB | 14,508 KiB |
| 100k | 29,595,936 B | 101.869 ms | 31,195,840 B | 1,599,408 | 15,195,264 B | 100,000 / 172,933 | 43,556 KiB | 57,948 KiB |

Adjacency capacity exactly matched adjacency logical bytes after snapshot load
at both scales. The 100k owned-capacity total consists mainly of 15.2 MB split
codes, 0.8 MB IDs, and 15.2 MB adjacency storage; the remaining gap to RSS also
contains the ID map, allocator/process overhead, and shared runtime pages. This
fresh-process result shows that the earlier roughly 156.8 MiB CRUD `state_rss`
was dominated by retained source data and temporary graph-building state. It
does not identify adjacency reserved capacity or fragmentation as the next
bottleneck, so a flat-adjacency rewrite is not justified by the current
evidence.

Release and ASan+UBSan CTest passed 6/6, and clang-format-15,
clang-tidy-15, stderr checks, and the SHA-256 manifest passed. Raw per-process
JSON, stderr, source/environment metadata, summary, and the verified manifest
are in
`/home/ubuntu/project/vsag-lite-rabitq-mutable-rss-validation-20260923`.
This remains probe-only evidence and does not change the public Lite API or
snapshot formats.

The proposed public API, fixed-model lifecycle, version 4 snapshot boundary, and
promotion gates are documented in [`RABITQ_LITE_BACKEND_DESIGN.md`](RABITQ_LITE_BACKEND_DESIGN.md).

### Single-core CPU and CRUD runner

The probe reports both monotonic wall time and process CPU time from
`getrusage(RUSAGE_SELF)` for encoding, graph construction, Update, Remove,
Add, and graph search. Per-operation fields use the same P50/P99 aggregation
for both clocks. Process CPU time includes user and system time for the process;
it is not a hardware-counter measurement, and the `getrusage` calls add a
small fixed cost to microsecond-scale operations.

Run the fixed-affinity experiment on prepared 10k and 100k prefixes with:

```bash
lite/benchmark/run_rabitq_single_core.sh \
  build-lite-rabitq/lite_rabitq_codec_probe \
  /data/prepared-dataset /new/output-directory 0
```

The runner starts each repetition in a fresh process, binds it to one logical
CPU with `taskset`, and sets common BLAS/OpenMP thread-count variables to one.
It records the inherited CPU affinity, topology, commit, binary checksum, raw
CSV, `/usr/bin/time -v`, dataset manifests, snapshots, and a verified SHA-256
manifest. If a working `perf stat` is available, it also records task-clock,
cycles, instructions, branches, cache events, context switches, migrations, and
page faults; otherwise the run remains valid with process CPU time and
`/usr/bin/time -v` evidence.

This runner measures the experiment-only fixed-model RaBitQ state. It does not
make the public Lite backend single-threaded by contract, establish
cross-machine performance, or replace Recall@10 validation on independent
queries. SIFT, GIST, and Cohere should be reported as separate datasets rather
than pooled; a missing dataset must be recorded instead of substituted.

#### Recorded single-core SIFT and GIST results

At code commit `835eab3f75cf9c2a4393392daa097393cb2dd00c`, all runs were bound to logical CPU 0. A working kernel-compatible `perf stat` was unavailable, so the evidence uses phase-level process CPU time plus `/usr/bin/time -v`. CPU time closely matched wall time and whole-process utilization was 99% in every independent-query quality run.

| Dataset | Scale | Degree / ef | Full / filtered Recall@10 | Graph Recall@10 | Encode wall / CPU | Graph build wall / CPU | Graph query P50 wall / CPU | Peak RSS |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| SIFT-128 | 10k | 16 / 128 | 0.994 / 0.994 | 0.966 | 41.072 / 41.071 ms | 857.759 / 857.666 ms | 170.998 / 171 us | 28,888 KiB |
| SIFT-128 | 100k | 16 / 128 | 0.985 / 0.985 | 0.940 | 412.683 / 412.652 ms | 20,795.175 / 20,794.270 ms | 288.355 / 289 us | 222,492 KiB |
| GIST-960 | 10k | 32 / 512 | 0.997 / 0.997 | 0.984 | 274.384 / 274.345 ms | 6,813.658 / 6,813.344 ms | 1,888.441 / 1,889 us | 188,160 KiB |
| GIST-960 | 100k | 32 / 512 | 0.997 / 0.997 | 0.949 | 2,719.856 / 2,719.694 ms | 177,230.169 / 177,221.877 ms | 3,239.007 / 3,240 us | 1,408,812 KiB |

The quality rows use 100 independent queries and separately recomputed prefix ground truth. They are deterministic quality controls and single-run latency observations, not stable latency medians.

The fixed-count CRUD runner used seven fresh processes per dataset and scale at degree 16 and `ef_search=128`. Values below are medians; every run had zero exhaustive mutation fallbacks and passed exact result-and-distance checks after Save/Load.

| Dataset | Scale | Process CPU | Update P50 | Remove P50 | Add P50 | Graph search P50 | Graph self Top-1 | Graph/full positional |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| SIFT-128 | 10k | 100% | 447.992 us | 93.978 us | 374.833 us | 178.967 us | 0.960 | 0.943 |
| SIFT-128 | 100k | 99% | 2,430.080 us | 1,047.621 us | 1,792.649 us | 365.354 us | 0.930 | 0.831 |
| GIST-960 | 10k | 99% | 2,003.082 us | 95.509 us | 1,834.524 us | 598.172 us | 0.580 | 0.510 |
| GIST-960 | 100k | 99% | 4,157.985 us | 963.585 us | 3,434.265 us | 881.308 us | 0.370 | 0.208 |

The CRUD self-query columns are post-mutation reachability diagnostics, not standard Recall@10. A GIST-100k parameter sweep showed that `16/256`, `32/128`, `32/256`, and `64/256` raised Graph self Top-1 from the default 0.37 to 0.42, 0.56, 0.60, and 0.78. The `64/256` point increased graph build from 39.6 to 182.0 seconds, Update P50 from 4.13 to 40.77 ms, Add P50 from 3.41 to 38.09 ms, and snapshot size from 112.8 to 151.2 MB. This rules out simply maximizing graph parameters when single-insert efficiency matters; independent-query quality should use the documented GIST `32/512` configuration, while CRUD quality needs a separate graph-repair investigation.

Raw evidence and verified SHA-256 manifests are in `/home/ubuntu/project/vsag-lite-rabitq-single-core-{sift,gist}-20260926-835eab3`, `/home/ubuntu/project/vsag-lite-rabitq-single-core-{sift,gist}-quality-20260926-835eab3`, and `/home/ubuntu/project/vsag-lite-rabitq-gist-tuning-20260926-835eab3`. Cohere was not present on the measured server and is therefore recorded as pending rather than replaced with another dataset.

### CRUD rebuilt-topology differential control

Use the control mode to distinguish incremental graph-maintenance effects from
the quality of the selected graph parameters:

```bash
lite_rabitq_codec_probe --crud-control \
  DATASET_DIR SNAPSHOT ROUNDS CRUD_OPS QUERIES MAX_DEGREE EF_SEARCH
```

The command performs the same timed Update-Remove-Add sequence as `--crud`.
After each batch, it orders the current raw vectors by the mutable state's slot
mapping and invokes the existing FP32 Lite graph builder with the same degree
and `ef_search`. Incremental and rebuilt topologies then search the same
RaBitQ codes and queries. The extra CSV fields report rebuild wall/process CPU
time, rebuilt search P50 wall/process CPU time, rebuilt self-query and
full-code agreement, incremental/rebuilt Top-1 agreement, direct edge
counts for both topologies, and P50 wall/process CPU time spent in the full
adjacency scan inside Update and Remove. These scan fields are diagnostic
segments of the corresponding total mutation timers, not additional work.

The rebuild and slot-ordered FP32 copy are diagnostic work outside the mutation
timers. They intentionally increase runtime, transient memory, and process peak
RSS, so control-mode resource values must not be reported as the mutable
backend's steady footprint. The original `--crud` schema and runner remain
unchanged.

At commit `ae9a1d37ededb79942ed1ced6fbfa2dae9ca50fe`, one CPU-0
control run per GIST scale used 20 Update-Remove-Add cycles, 100 self queries,
degree 16, and `ef_search=128`:

| Scale | Incremental self Top-1 | Rebuilt self Top-1 | Incremental / rebuilt Top-1 agreement | Incremental / rebuilt positional agreement | Initial / control rebuild |
| --- | ---: | ---: | ---: | ---: | ---: |
| 10k | 0.580 | 0.570 | 0.990 | 0.510 / 0.512 | 1.783 / 1.746 s |
| 100k | 0.370 | 0.370 | 0.990 | 0.208 / 0.208 | 39.216 / 39.412 s |

Both processes used 99-100% of one logical CPU, had zero mutation fallbacks,
produced empty stderr, passed Save/Load identity checks, and have verified
SHA-256 manifests. The rebuilt topology did not recover the low default-parameter
GIST self-query score. For this bounded 20-operation workload, there is no
evidence that incremental CRUD repair caused the quality gap; the dominant
factor is the `16/128` graph/search configuration. This result does not prove
equivalence after long churn or adversarial updates. Raw evidence is in
`/home/ubuntu/project/vsag-lite-rabitq-gist-crud-control-20260926-ae9a1d3`.

### Long-churn adjacency repair

At commit `dafc2778502dfee06816c7546ad3023def06dc89`, the mutable
RaBitQ graph and the public Lite graph repair adjacency entries removed by
Update and Remove. Repair preserves surviving links and fills only vacated
degree slots from the affected local neighborhood. This follows the bounded
repair scope used by Full HGraph force removal while avoiding whole-graph
rebuilds and broad topology replacement.

A CPU-0 GIST control used the same `16/128` configuration as the earlier
long-churn diagnostic. The 10k run performed 10 rounds of 100 CRUD operations;
the 100k run performed 3 rounds of 100 operations. Each round used 100
self-query diagnostics and a freshly rebuilt topology control.

| Scale | Incremental edges | Rebuilt edges | Final incremental / rebuilt Top-1 | Median incremental self Top-1 | Median rebuilt self Top-1 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 10k | 159,972-160,000 | 160,000 | 0.930 | 0.645 | 0.645 |
| 100k | 1,599,997-1,599,999 | 1,600,000 | 0.960 | 0.360 | 0.340 |

Before repair, snapshot deltas showed losses of 13,569 adjacency entries after
the 10k workload and 3,892 after the 100k workload. After repair, the maximum
observed deficits were 28 and 3 entries, respectively, and the 10k run ended
at the full 160,000 edges. The repair does not make the incremental topology
identical to a rebuild, but it removes the monotonic sparsification failure
without changing median self-query quality at either scale.

Commit `a26a05238783e2f10bee59e02347f686ac632d57` then caches the
decoded source record while pruning each full reverse-neighbor list. Compared
with `dafc277`, all per-round result checksums, edge counts, snapshots, and
quality fields were identical. Observed mutation P50 medians changed as
follows:

| Scale | Update P50 | Add P50 | Remove P50 |
| --- | ---: | ---: | ---: |
| 10k | 2,364.776 -> 1,392.641 us (-41.1%) | 2,078.101 -> 1,198.701 us (-42.3%) | 238.556 -> 249.374 us (+4.5%) |
| 100k | 4,817.310 -> 3,640.397 us (-24.4%) | 3,811.256 -> 2,769.428 us (-27.3%) | 1,199.740 -> 1,409.153 us (+17.5%) |

These are paired deterministic single-process observations, not a statistical
latency distribution. Search timing also changed even though the search path
did not, so it is not attributed to the source-decode optimization. Both runs
used 99% of one logical CPU, produced empty stderr, passed exact Save/Load
result checks, and have verified SHA-256 manifests. Raw evidence is in
`/home/ubuntu/project/vsag-lite-rabitq-gist-crud-repair-20260926-dafc277`
and
`/home/ubuntu/project/vsag-lite-rabitq-link-cache-validation-20260926-a26a052`.

### Mutable adjacency scan cost

Commit `c6bb0a640f097b1d89b3300cda88e68498979331` adds opt-in
phase timing to `--crud-control` without changing the original `--crud`
schema or enabling timing calls in that path. The timed region is only the
full adjacency scan that removes incoming references during Update or removes
and remaps references during Remove.

The same deterministic CPU-0 GIST workloads used above produced these medians:

| Scale | Update total | Update scan | Update scan share | Remove total | Remove scan | Remove scan share |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 10k | 1,388.615 us | 68.029 us | 4.9% | 212.380 us | 110.243 us | 51.9% |
| 100k | 3,550.243 us | 504.576 us | 14.2% | 924.748 us | 918.888 us | 99.4% |

Process CPU ratios were 4.9% and 14.2% for Update, and 52.1% and 99.4% for
Remove, closely matching wall time. All quality fields, topology edge counts,
and result checksums were identical to the `a26a052` runs. Both stderr files
were empty and the SHA-256 manifest verifies all evidence.

Use the fresh-process memory diagnostic before integrating an incoming-edge
index into mutation paths:

```bash
lite_rabitq_codec_probe --incoming-rss MUTABLE_SNAPSHOT
```

It loads the mutable snapshot, constructs an exact
`vector<vector<uint64_t>>` incoming adjacency with counted reservations, and
reports build wall/process CPU, incoming logical/capacity bytes, combined known
state bytes, and RSS. The snapshot and CRUD behavior remain unchanged.

At commit `c7d192c05326c7c19fe65ca11b65b0f4f1766127`, seven
fresh processes per scale compared `--incoming-rss` with the existing
`--mutable-rss` baseline on the same long-churn snapshots:

| Scale | Edges | Incoming build wall / CPU | Incoming capacity | Capacity over known state | Baseline / incoming RSS |
| --- | ---: | ---: | ---: | ---: | ---: |
| 10k | 160,000 | 0.565 / 0.566 ms | 1,520,000 B | 13.28% | 15,964 / 16,992 KiB |
| 100k | 1,599,997 | 10.456 / 10.455 ms | 15,199,976 B | 13.29% | 124,980 / 137,792 KiB |

Every incoming edge count equaled the outgoing edge count. All 28 formal
processes produced empty stderr, and the evidence manifest verifies all inputs
and outputs. The measured capacity is exact for this counted-reservation
layout; RSS deltas include allocator and process effects. Raw evidence is in
`/home/ubuntu/project/vsag-lite-rabitq-incoming-rss-20260926-c7d192c`.

Use the opt-in mutation prototype to compare local incoming-edge maintenance
with the original full-scan path:

\`\`\`bash
lite_rabitq_codec_probe --crud-incoming \
  DATASET_DIR SNAPSHOT ROUNDS CRUD_OPS QUERIES MAX_DEGREE EF_SEARCH
\`\`\`

The mode rebuilds the incoming table from the initial topology, maintains it
through Add, Update, Remove, reverse-link pruning, local repair, and last-slot
compaction, and validates it against a fresh reconstruction at every batch
boundary. It adds incoming edge/logical/capacity columns to the regular CRUD
schema. The saved v3 snapshot stays unchanged and reconstructs incoming state
when this opt-in mode is selected after loading.

The 100k result justifies evaluating a lightweight incoming-edge index for
Remove. It does not by itself justify importing Full HGraph's hash-map,
per-node dynamic-vector, and synchronization structure into Lite. The next
experiment must measure the incoming index's logical and capacity bytes
alongside mutation latency before adoption. Raw evidence is in
`/home/ubuntu/project/vsag-lite-rabitq-scan-timing-20260926-c6bb0a6`.

### Opt-in incoming-edge mutation prototype

At commit `16d3aab2d74b2c67dd4ae95833acf1b4f4cefb2b`, the
experiment-only mutable graph can maintain an incoming adjacency through Add,
Update, Remove, reverse-link pruning, local repair, and last-slot compaction.
Batch validation reconstructs the incoming table from outgoing adjacency and
requires exact set equality. The v3 snapshot remains unchanged.

A paired CPU-0 GIST run compared `--crud` and `--crud-incoming` with
identical deterministic workloads:

| Scale | Workload | Update baseline / incoming | Remove baseline / incoming | Add baseline / incoming | Remove speedup |
| --- | ---: | ---: | ---: | ---: | ---: |
| 10k | 10 x 100 CRUD | 1,583.204 / 1,518.999 us | 222.214 / 122.257 us | 1,377.448 / 1,375.283 us | 1.82x |
| 100k | 3 x 100 CRUD | 3,831.412 / 3,130.365 us | 1,048.965 / 9.350 us | 2,944.942 / 2,940.789 us | 112.19x |

All per-round fallback, quality, visited/reordered, snapshot-size, and result
checksum fields were identical. Both paths passed exact Save/Load result
checks and produced empty stderr. Incoming edge counts tracked outgoing counts:
159,972-160,000 at 10k and 1,599,997-1,599,999 at 100k.

Dynamic vector capacity after long churn ranged from 1,858,728 to 2,243,040
bytes at 10k and 16,284,952 to 17,515,088 bytes at 100k. This is higher than
the exact initial construction and is the relevant memory range for the
prototype. The strong 100k Remove result supports continued evaluation, but
the dynamic capacity overhead must remain visible in any adoption decision.
Raw evidence and a verified manifest are in
`/home/ubuntu/project/vsag-lite-rabitq-incoming-crud-20260926-16d3aab`.

To measure whether periodic capacity recovery is worthwhile, use the separate
batch-boundary experiment:

```bash
lite_rabitq_codec_probe --crud-incoming-compact \
  DATASET_DIR SNAPSHOT ROUNDS CRUD_OPS QUERIES MAX_DEGREE EF_SEARCH
```

This mode performs the same incoming-edge CRUD workload, then replaces each
incoming list with an exact-size copy after the batch. It reports compaction
wall/process CPU time and incoming capacity before/after compaction. The
compaction runs after mutation latency sampling and exact incoming validation,
so its cost is visible separately. This is an experiment-only policy; regular
`--crud-incoming`, snapshots, and the Lite public API remain unchanged.

Use the threshold policy to compact only when reserved incoming capacity is
more than 125% of its logical bytes:

```bash
lite_rabitq_codec_probe --crud-incoming-threshold \
  DATASET_DIR SNAPSHOT ROUNDS CRUD_OPS QUERIES MAX_DEGREE EF_SEARCH
```

The output adds a per-batch trigger field to the same compaction measurements.
The 125% boundary is an experiment constant chosen from the long-churn
capacity trace; it is not a public setting or an adopted production policy.

Use `--crud-incoming-profile` or
`--crud-incoming-threshold-profile` with the same positional arguments to
append node-level layout diagnostics. The profile reports zero-degree and
cumulative degree buckets, degree/capacity percentiles and maxima, nodes and
entries with reserved slack, outer vector bytes, logical edge bytes, and
reserved edge bytes. Profiling runs after mutation/search timing and does not
change snapshots or the regular experiment schemas.

To model chunked incoming-adjacency layouts from an existing mutable snapshot
without rerunning CRUD, use:

```bash
lite_rabitq_codec_probe --incoming-layout-profile MUTABLE_SNAPSHOT
```

The output reports exact block counts and payload slack for block sizes 4, 8,
16, 32, and 64. `total_bytes` is an explicit model with one 64-bit head per
node, one 64-bit next pointer per block, and 64-bit source IDs. It excludes
allocator metadata and alignment, and is therefore a layout comparison rather
than a process-RSS measurement. The same output includes ideal static CSR and
the current vector-of-vectors logical byte counts as reference bounds.

### Incoming capacity compaction result

At commit `33232fce3fabfb15661bded92f90b0b0b724d532`, a paired
CPU-0 GIST run compared `--crud-incoming` with
`--crud-incoming-compact`. Compaction ran after every batch, outside the
per-operation latency samples:

| Scale | Workload | Capacity before compaction | Capacity after compaction | Median bytes recovered | Compact wall / CPU |
| --- | ---: | ---: | ---: | ---: | ---: |
| 10k | 10 x 100 CRUD | 1,724,944-1,858,728 B | 1,519,776-1,520,000 B | 240,164 B | 0.147 / 0.147 ms |
| 100k | 3 x 100 CRUD | 16,284,952-16,376,496 B | 15,199,976-15,199,992 B | 1,107,320 B | 0.701 / 0.701 ms |

The median p50 mutation results were:

| Scale | Update incoming / compact | Remove incoming / compact | Add incoming / compact |
| --- | ---: | ---: | ---: |
| 10k | 1,333.677 / 1,340.623 us | 106.093 / 106.563 us | 1,201.355 / 1,208.035 us |
| 100k | 3,028.645 / 3,090.134 us | 9.800 / 9.680 us | 2,826.181 / 2,878.930 us |

All per-round fallback, quality, visited/reordered, incoming edge/logical byte,
snapshot-size, and result-checksum fields were identical. The final snapshots
also had identical SHA-256 hashes for each scale, all stderr files were empty,
and the evidence manifest verifies the raw artifacts.

Unconditional compaction after every 100 CRUD cycles is not recommended as a
default policy: at 100k it recovered a median 1.11 MB while adding a separate
0.70 ms batch cost and coinciding with about 2% higher Update/Add medians in
this run. If capacity recovery is adopted later, it should be threshold-driven
and evaluated over longer churn instead of running after every batch. Raw
evidence is in
`/home/ubuntu/project/vsag-lite-rabitq-incoming-compact-20260926-33232fc`.

### Long-churn incoming capacity policy

At commit `b6fe3f060b8fadc337d3524b893ed37e9cc33b36`, a CPU-0
GIST-100k run extended the deterministic workload to 50 batches of 100
Update-Remove-Add cycles with 20 diagnostics per batch. The unmodified
full-scan and incoming-edge paths matched in every per-round fallback, quality,
visited/reordered, snapshot-size, and result-checksum field. Their final
snapshots also had identical SHA-256 hashes. Incoming maintenance therefore
remained semantically equivalent through 5,000 cycles while reducing median
Update from 5,734.170 to 4,163.219 us and Remove from 2,343.615 to 67.124 us.
Add medians were 3,861.078 and 3,989.944 us.

Without recovery, incoming capacity grew from 16,284,952 to 21,383,776 bytes
while logical bytes stayed near 15.20 MB. The capacity/logical ratio reached
1.407, and the final ten rounds still had a positive capacity slope. A separate
ten-round rebuilt-topology control took a median 50.789 seconds per rebuild,
but its self-query and full-code agreement ranges matched the incremental
topology and their Top-1 agreement median was 1.0. This extends the earlier
finding that the low `16/128` GIST self-query diagnostic is not repaired by
rebuilding the topology; independent-query validation continues to use the
documented `32/512` configuration.

The 125% threshold policy triggered only at rounds 10, 23, and 40:

| Metric | No recovery | 125% threshold |
| --- | ---: | ---: |
| Capacity range | 16,284,952-21,383,776 B | 15,958,016-19,135,896 B before policy |
| Final capacity | 21,383,776 B | 17,898,928 B |
| Compaction count / total wall time | 0 / 0 ms | 3 / 11.503 ms |
| Update P50 median | 4,163.219 us | 4,080.248 us |
| Remove P50 median | 67.124 us | 66.104 us |
| Add P50 median | 3,989.944 us | 3,900.404 us |

Each trigger recovered 3.86-3.94 MB and returned capacity to the exact logical
size. All 50 semantic rows and the final snapshot hash matched the no-recovery
baseline. The latency differences are single paired observations and are not
claimed as speedups; the result only shows no measured regression in this run.
Process peak RSS was identical because source data and graph construction
dominated the process peak, so the capacity figures are the exact evidence for
this policy rather than an RSS claim.

This experiment supports a sparse threshold policy over per-batch compaction
if incoming adjacency is adopted. It does not make threshold compaction or the
incoming prototype part of the public Lite implementation. Raw evidence and
verified manifests are in
`/home/ubuntu/project/vsag-lite-rabitq-incoming-long-churn-20260927-7bae1a9`
and
`/home/ubuntu/project/vsag-lite-rabitq-incoming-threshold-20260927-b6fe3f0`.

### Incoming degree distribution and chunk-layout decision

At profiler commit `7e1982cb2d4217a78f08fc6904a80c3e64d44d13` and layout-model
commit `6a9fa3e0550f706ac368ddfc86bc27e96844fff1`, paired CPU-0 runs
measured 50 batches of 100 Update-Remove-Add cycles and 20 diagnostic
queries per batch. Both 10k and 100k pairs matched all semantic rows and final
snapshot SHA-256 hashes; all stderr files were empty.

| Scale | Zero degree | Degree <= 16 | Degree > 64 | Degree P50/P90/P95/P99/max |
| --- | ---: | ---: | ---: | --- |
| 10k | 23.770% | 71.780% | 5.040% | 6 / 41 / 65 / 125 / 676 |
| 100k | 50.134% | 79.194% | 6.246% | 0 / 42 / 77 / 212 / 2706 |

The distribution is sparse and long-tailed. A fixed 16-, 32-, or 64-entry
inline allocation would waste storage on zero- and low-degree nodes while
still requiring overflow handling. The explicit chunk model found 8 entries
per block to be the smallest of the tested 4/8/16/32/64 layouts:

| Scale | Vector plus threshold | 8-entry chunk model | Chunk difference |
| --- | ---: | ---: | ---: |
| 10k | 1,519,968 B | 1,789,208 B | 269,240 B larger (17.714%) |
| 100k | 17,898,928 B | 16,995,248 B | 903,680 B smaller (5.049%) |

The chunk totals include an 8-byte node head, an 8-byte next pointer per
block, and 8-byte source IDs, but exclude allocator metadata and alignment.
They are modeled layout bytes rather than measured RSS. The 100k saving over
the thresholded vector layout is only 5.049%, while 10k regresses and chunk
traversal would add pointer chasing. A chunked backend prototype is therefore
not justified by this evidence.

The 125% threshold reduced final vector capacity by 36.375% at 10k and
16.297% at 100k. It triggered 25 times for 7.803 ms total at 10k and three
times (rounds 10, 23, and 40) for 11.699 ms total at 100k. The frequent 10k
triggers did not change semantic results or materially shift paired latency
medians, but a production policy should still evaluate size-aware hysteresis
before adoption. The current experiment decision is to retain dynamic vectors,
keep sparse threshold compaction as the candidate, and avoid a block-layout
implementation.

Raw CSVs, snapshots, the analyzer, SHA-256 manifest, and `summary.json` are
in
`/home/ubuntu/project/vsag-lite-rabitq-incoming-profile-20260929-7e1982c`.

### GIST-500k high-dimensional incoming validation

At commit `57aaa59201d3bf3457f32eb61f8432d1b3e7fc93`, a CPU-0
GIST-500k run repeated the no-recovery and 125% threshold profiles for 50
batches of 100 Update-Remove-Add cycles, with 20 self-query diagnostics per
batch, `max_degree=16`, and `ef_search=128`. The prepared input contains
500,000 960-dimensional vectors (1,922,000,000 bytes, SHA-256
`840447f2014c69dcd66c5296738f2a8147cf9296bbdc649b8374ab5466c16a1c`).

Both profiles completed all 50 rounds with empty stderr and zero mutation
fallbacks. Every paired semantic field and result checksum matched. Their
final snapshots were byte-identical with SHA-256
`6b17bc1b86c8a0017dbecf153971fd268185110e89e20e1dc6afae556c667545`.
The timed commands exited zero and reached 6,308,528 KiB and 6,308,552 KiB
maximum RSS respectively; source vectors and graph construction dominate this
process peak.

The final incoming graph contained 7,999,985 edges. Of 500,000 nodes, 319,611
(63.9222%) had zero incoming degree. Degree P50/P90/P95/P99/max was
`0 / 36 / 78 / 269 / 7326`, confirming a sparse, long-tailed distribution at
the larger and higher-dimensional scale.

| Metric | No recovery | 125% threshold |
| --- | ---: | ---: |
| Final incoming capacity | 95,452,888 B | 80,549,456 B |
| Final slack entries | 2,431,626 | 568,697 |
| Capacity saved | - | 14,903,432 B (15.613%) |
| Compaction triggers | 0 | 1 (round 47) |

The round-47 trigger reduced incoming capacity from 95,095,744 to 75,999,872
bytes in 16.697 ms wall time. The best tested chunk model again used 8-entry
blocks, but required 82,528,456 bytes: 1,979,000 bytes (2.457%) more than the
final thresholded vector layout. This larger-scale result strengthens the
decision to retain vector incoming adjacency with sparse 125% capacity recovery
and not implement a chunk backend.

Update, Remove, Add, search, Save, and Load medians are recorded in
`summary.json`, but this is one sequential paired run and is not evidence of
a latency speedup. The self-query diagnostics are mutation and round-trip
checks; this subset has no independent-query ground truth and therefore makes
no recall claim. One earlier threshold attempt ended when its remote execution
channel closed during the round-18 snapshot write; it is preserved separately,
excluded from the paired result, and had empty stderr with no OOM or segfault
kernel record.

Raw CSVs, snapshots, timing logs, commands, validation checks, SHA-256
manifest, and `summary.json` are in
`/home/ubuntu/project/vsag-lite-rabitq-gist500k-profile-20260929-57aaa59`.

### Public GraphBackend incoming-adjacency candidate

At commit `ec4410a6be37645f997b11aad3318a56b5da3d6b`, the private
`GraphBackend` maintains an incoming adjacency alongside its existing
outgoing links. Add, Update, Remove, degree pruning, repair, last-slot moves,
and FP32/FP16 restore keep both views synchronized. Snapshots and the public
Lite API are unchanged; Load reconstructs incoming links from the serialized
outgoing graph.

Tests independently rebuild incoming links from `LinkAt()` and require exact
set equality after construction, restored asymmetric links, FP32 and FP16
CRUD, and 200 Update-Remove-Add cycles. Release and ASan/UBSan CTest each
passed 6/6. clang-format-15, clang-tidy-15 with warnings-as-errors, and
`git diff --check` also passed.

A CPU-0 deterministic public-backend comparison used the parent commit's
full-scan Update/Remove path and the incoming candidate with identical seeds:

| Scale | Workload | Update P50 parent / incoming | Remove P50 parent / incoming | Re-add P50 parent / incoming |
| --- | ---: | ---: | ---: | ---: |
| 10k x 64D | 10 x 100 CRUD | 307.096 / 233.214 us | 140.006 / 7.970 us | 207.051 / 172.301 us |
| 100k x 64D | 3 x 100 CRUD | 5,025.578 / 543.905 us | 6,397.743 / 9.840 us | 717.400 / 311.092 us |

Every paired round matched count, snapshot bytes, Top-1 self recall, result
checksum, backend options, and final snapshot SHA-256. Both stderr streams were
empty. Peak RSS was 13,232/17,272 KiB at 10k and 98,540/138,192 KiB at 100k
(parent/incoming). Median Load rose from 1.691 to 2.573 ms at 10k and from
20.882 to 34.194 ms at 100k because incoming links are reconstructed.

These are single sequential paired observations, so the ratios are candidate
evidence rather than speedup claims. The next separate change should apply the
already profiled 125% sparse-capacity recovery policy and measure its effect on
this public backend; it should not change snapshot bytes or public API.

Raw CSVs, timing logs, snapshots, environment, summaries, and the verified
SHA-256 manifest are in
`/home/ubuntu/project/vsag-lite-public-incoming-20260930-ec4410a`.

### Public GraphBackend sparse incoming-capacity recovery

At commit `bd062b1`, the public-backend incoming candidate checks reserved
incoming-adjacency capacity after each 100 successful Remove operations. It
compacts only when capacity exceeds logical bytes by more than 25%. Compaction
is best-effort: an allocation failure cannot turn a successful Remove into an
API error. Snapshots and the public Lite API remain unchanged.

The 256-node repeated-CRUD test now requires the policy to trigger and verifies
that remaining capacity slack is within the 25% boundary, allowing one
`uint64_t` of implementation-level `shrink_to_fit` slack. Release and
ASan/UBSan CTest each passed 6/6. clang-format-15, clang-tidy-15 with
warnings-as-errors, and `git diff --check` also passed.

A deterministic private inspection probe used the same CPU-0 100k x 64D graph
and 50 batches of 100 Update-Remove-Add cycles as the public benchmark. The
logical incoming state remained 15,200,000 bytes. Initial capacity/slack was
21,824,808/6,624,808 bytes; final capacity/slack was
18,745,048/3,545,048 bytes. The policy compacted 25 times. Thus final slack was
46.5% below initial slack, while remaining below the 25% logical-byte boundary.
This probe reads internal counters solely for validation and adds no public API.

A sequential paired public-backend run compared incoming maintenance without
recovery to the threshold candidate:

| Metric | Incoming only | 125% threshold |
| --- | ---: | ---: |
| Update P50 | 474.906 us | 493.506 us |
| Remove P50 / P99 | 9.590 / 15.224 us | 8.100 / 17.115 us |
| Re-add P50 | 274.705 us | 296.465 us |
| Search P50 | 429.457 us | 471.201 us |
| Peak RSS | 138,688 KiB | 132,996 KiB |
| Whole-run wall time | 45.66 s | 53.28 s |

All 50 paired rows matched count, CRUD count, snapshot bytes, Top-1 self
recall, result checksum, backend options, and final snapshot SHA-256. Stderr
was empty. The lower process peak RSS is consistent with capacity recovery, but
this is one sequential paired run. The latency and wall-time differences include
run-order and host noise and are not attributed to compaction. The workload is
a self-query mutation and round-trip diagnostic without independent-query
ground truth, so it makes no ANN recall claim.

Raw CSVs, timing logs, the private probe source and output, validation logs,
summary, and SHA-256 manifest are in
`/home/ubuntu/project/vsag-lite-public-threshold-20260930-bd062b1`.

### Scale-aware public incoming-capacity checks

At commit `47b2475`, the capacity policy keeps the 100-remove minimum check
interval for small graphs and scales the interval to approximately 1% of the
current graph size. This prevents every 100 removals from causing an O(n)
capacity scan on larger indices while retaining the same 125% compaction
threshold and best-effort failure behavior.

On the same CPU-0 100k x 64D, 50 x 100 CRUD workload, the scale-aware policy
checked at approximately 1,000 removals and compacted at rounds 10, 20, 30, 40,
and 50. Incoming logical bytes remained 15,200,000. Final capacity/slack was
17,675,144/2,475,144 bytes, compared with 18,745,048/3,545,048 bytes for the
fixed-100 candidate. Whole-run wall time was 46.42 seconds, compared with 53.28
seconds for fixed-100 and 45.66 seconds without recovery. The process peak was
138,704 KiB because the first compaction occurs after 10 rounds; peak RSS is
therefore not reduced in this workload even though final retained capacity is.

All 50 rows again matched the no-recovery run's semantic fields and checksum,
and the final snapshot SHA-256 was identical. Release and ASan/UBSan CTest each
passed 6/6; clang-format-15, clang-tidy-15 with warnings-as-errors, and
`git diff --check` passed. These timings remain single sequential observations,
so the result supports a lower-overhead policy choice but is not a general
latency claim.

Raw evidence is in
`/home/ubuntu/project/vsag-lite-public-scaled-interval-20260930-47b2475`.

### Multi-scale long-churn capacity boundary

At commit `71675f1`, the scale-aware policy raises its minimum inspection
interval from 100 to 1,000 successful Remove operations. The larger floor avoids
small-graph compaction thrash while the existing `Size() / 100` term continues
to scale the interval for large graphs. The repeated-CRUD test now covers 2,000
cycles and checks the 125% boundary immediately when a compaction occurs, before
a subsequent Add can reserve new incoming capacity.

A CPU-0 private capacity probe ran 10k x 64D for 200 x 100 CRUD operations and
100k x 64D for 100 x 100 operations:

| Scale | Old / new compactions | Final logical / capacity / slack | Probe wall |
| --- | ---: | ---: | ---: |
| 10k | 200 / 20 | 1,520,000 / 1,766,608 / 246,608 B | 8.99 s |
| 100k | 10 / 10 | 15,200,000 / 17,604,672 / 2,404,672 B | 36.92 s |

The 10k compactions now occur every 10 rounds instead of every round. The 100k
schedule remains every 10 rounds. Public Save/Load stability runs completed all
200 and 100 rows respectively with constant count, snapshot bytes, and empty
stderr. For the first 50 100k rounds, semantic fields and result checksums were
identical to the preceding scale-aware candidate; final snapshots also loaded
successfully.

The longer run exposes a separate graph-quality limitation. Top-1 self-query
recall had a first-block/last-block median of 0.950/0.875 at 10k and 0.700/0.675
at 100k; observed minima were 0.600 and 0.400. The block medians do not show
a monotonic decline, but their low and variable values expose a graph
repair/reachability limit. Capacity compaction does not change graph links, and
the checksum match confirms this is separate from capacity-policy semantics. The next graph task must address repair quality and validate with
independent queries; self-query recall is only a reachability diagnostic.

Release and ASan/UBSan CTest each passed 6/6. clang-format-15,
clang-tidy-15 with warnings-as-errors, and `git diff --check` passed. Raw
evidence is in
`/home/ubuntu/project/vsag-lite-scaled-churn-min1000-20260930-71675f1`.

### Incoming-reachability-preserving graph links

At commit `69cd411`, graph degree pruning avoids removing a node's only incoming
edge when another candidate edge can be removed safely. If a newly added or
updated node is still unreachable after reciprocal link attempts, the backend
rewires the farthest safe edge from one of its nearest neighbors. The displaced
node must retain another incoming edge. Maximum degree, search parameters,
public API, and snapshot format are unchanged.

The 2,000-cycle CRUD regression now requires every re-added node to receive an
incoming link and requires Add not to increase the number of zero-incoming
nodes. Exact incoming/outgoing consistency is still checked after every cycle.

A private CPU-0 topology probe measured the baseline and candidate with the same
synthetic 64D data and CRUD sequence:

| Scale / checkpoint | Zero incoming baseline / candidate | Entry-directed reachable baseline / candidate | Self Top-1 baseline / candidate |
| --- | ---: | ---: | ---: |
| 10k initial | 301 / 0 | 9,684 / 9,982 | 1.000 / 1.000 |
| 10k after 200 x 100 CRUD | 686 / 489 | 9,223 / 9,430 | 0.750 / 0.800 |
| 100k initial | 9,373 / 0 | 90,294 / 99,120 | 0.650 / 0.750 |
| 100k after 100 x 100 CRUD | 10,266 / 1,391 | 89,275 / 97,602 | 0.600 / 0.700 |

Both candidates retained exactly 16 outgoing edges per node and one weakly
connected component throughout. This isolates the relevant failure mode as
directed reachability from graph entry points rather than edge-count loss or
weak disconnection. Remove/repair can still create zero-incoming nodes, so the
candidate reduces but does not eliminate long-churn reachability loss.

The matching public stability workloads produced these medians:

| Scale | Metric | Baseline | Candidate |
| --- | --- | ---: | ---: |
| 10k, 200 rounds | Update / Remove / Re-add P50 | 208.211 / 7.770 / 168.307 us | 198.892 / 7.445 / 166.882 us |
| 10k, 200 rounds | Search P50 / whole run | 173.902 us / 15.16 s | 170.063 us / 14.65 s |
| 100k, 100 rounds | Update / Remove / Re-add P50 | 473.972 / 9.045 / 278.475 us | 460.608 / 9.049 / 272.466 us |
| 100k, 100 rounds | Search P50 / whole run | 429.718 us / 65.28 s | 408.179 us / 64.27 s |

The candidate's self-query first/last-block medians were 0.950/0.900 at 10k and
0.825/0.800 at 100k, versus 0.950/0.875 and 0.700/0.675 for the baseline.
Candidate stderr was empty. Peak RSS changed from 19,688 to 19,948 KiB at 10k
and 138,780 to 139,356 KiB at 100k. These are single sequential runs and do not
establish a general latency improvement. Self-query Top-1 is a reachability
diagnostic, not independent-query ANN recall; independent SIFT/GIST quality
validation remains required.

Release and ASan/UBSan CTest each passed 6/6. clang-format-15,
clang-tidy-15 with warnings-as-errors, and `git diff --check` passed. Raw probe,
CSV, timing, and validation evidence is in
`/home/ubuntu/project/vsag-lite-graph-topology-20260930-69cd411`.

### Remove-repair incoming reachability

At commit `c25f8a8`, graph removal repairs the outgoing adjacency of affected
nodes and then applies the existing safe incoming-edge repair to those same
nodes. This targets the remaining removal-induced zero-incoming nodes without a
full-graph scan. Maximum degree, search parameters, public API, and snapshot
format are unchanged. The repeated-CRUD regression now also requires Remove not
to increase the zero-incoming count.

The CPU-0 topology probe compared `c25f8a8` with the preceding `69cd411`
candidate under identical synthetic 64D workloads:

| Scale / checkpoint | Zero incoming before / after | Entry-directed reachable before / after | Self Top-1 before / after |
| --- | ---: | ---: | ---: |
| 10k after 200 x 100 CRUD | 489 / 6 | 9,430 / 9,906 | 0.800 / 0.800 |
| 100k after 100 x 100 CRUD | 1,391 / 15 | 97,602 / 98,961 | 0.700 / 0.700 |

Both variants retained exactly 16 outgoing edges per node and one weakly
connected component. Public stability final Top-1 changed from 0.950 to 0.950 at
10k and from 0.700 to 0.750 at 100k; observed minima changed from 0.650 to 0.700
and remained 0.550 respectively. Candidate median Update/Remove/Re-add/Search
latencies were 201.306/7.410/168.197/170.712 us at 10k and
474.387/9.010/282.981/423.367 us at 100k. Compared with `69cd411`, the 100k
Update, Re-add, and Search medians increased by about 3-4%, while final RSS and
snapshot size were unchanged. These are single sequential runs, so the timing
values are observations rather than universal speed claims.

Release and ASan/UBSan CTest each passed 6/6. clang-format-15,
clang-tidy-15 with warnings-as-errors, and `git diff --check` passed. Raw probe,
CSV, timing, commands, and checksums are in
`/home/ubuntu/project/vsag-lite-graph-repair-incoming-20260930-c25f8a8`.

### Independent-query graph quality after CRUD (2026-10-05)

The opt-in `lite_graph_crud_quality` target measures public FP32 Lite graph Search
on the prepared SIFT-128 and GIST-960 prefixes. It reads the same 100 independent
queries and prefix-specific exact squared-L2 Top-10 truth as `dataset_main.cpp`.
The deterministic Update-Remove-Add sequence writes the original vector back to
each selected ID, so the exact truth remains valid across all rounds. After the
search it saves a snapshot, reloads it, and requires every returned ID and
distance to match. Use it as follows:

```bash
cmake -S lite -B build-lite-quality -DCMAKE_BUILD_TYPE=Release -DENABLE_BENCHMARKS=ON
cmake --build build-lite-quality --target lite_graph_crud_quality
lite_graph_crud_quality DATASET_DIR NEW_SNAPSHOT_PATH ROUNDS CRUD_OPS
```

The same executable was linked at runtime against `7ff27f8` (before the local
incoming repair) and `c25f8a8` (after). Runs were sequential on CPU 0 with
`max_degree=16`, `ef_search=128`, 100 independent queries, and 100 CRUD cycles
per round. The current library's zero-round initial Recall@10 is included to
separate build quality from churn. It is identical across the two code versions
because the changed repair path is not called during BuildGraph.

| Dataset / scale | Initial | Short before / after | Long before / after |
| --- | ---: | ---: | ---: |
| SIFT 10k | 0.985 | 0.984 / 0.986 (20 rounds) | 0.975 / 0.976 (200 rounds) |
| SIFT 100k | 0.956 | 0.952 / 0.952 (10 rounds) | 0.949 / 0.949 (100 rounds) |
| GIST 10k | 0.916 | 0.892 / 0.896 (20 rounds) | 0.814 / 0.811 (200 rounds) |
| GIST 100k | 0.742 | 0.748 / 0.748 (10 rounds) | 0.733 / 0.729 (100 rounds) |

The incoming repair greatly reduced zero-incoming nodes in the separate topology
probe, but did not produce a clear independent-query benefit. In the longer GIST
runs, Recall@10 was lower by 0.003 and 0.004 respectively. These are single
sequential runs with 100 queries each, so the small differences are not a claim
of statistical significance. The repair remains an experimental graph-quality
candidate; further work should inspect entry traversal and local neighbor
selection before promotion. The measurements include no FP16 or RaBitQ quality
claim. Raw CSV, time, stderr, snapshots, binary/library hashes, and commands are
under `/home/ubuntu/project/vsag-lite-independent-crud-quality-20261005`.

The optional fifth output argument records per-query hits without changing the
existing aggregate CSV:

```bash
lite_graph_crud_quality DATASET_DIR SNAPSHOT ROUNDS CRUD_OPS QUERY_RESULTS
```

A paired rerun used the same executable, mutations, queries, and truth while
switching only the pre/post-repair shared library. For GIST 10k, 19 queries
improved, 14 regressed, and 67 were unchanged. The aggregate delta was -0.003,
the deterministic paired bootstrap 95% interval was [-0.021, 0.013], and the
two-sided sign-test p-value was 0.487. For GIST 100k, 0 queries improved, 3
regressed, and 97 were unchanged. The aggregate delta was -0.004, the bootstrap
interval was [-0.009, 0], and the sign-test p-value was 0.25.

The 10k result varies in both directions across queries, while the 100k loss is
concentrated in three queries. Neither scale establishes a statistically clear
quality change with only 100 queries. Snapshot inspection also found that
changed-edge median squared-L2 was essentially unchanged at 10k and 5.5% higher
after repair at 100k; sampled neighbor spread did not decrease. The next
diagnostic should therefore measure routing/visited candidates or expand the
independent query set rather than infer quality from zero-incoming counts alone.
Paired raw evidence is under
`/home/ubuntu/project/vsag-lite-query-paired-20261005`.

#### Routing-coverage diagnostic

The opt-in `lite_graph_route_probe` parses a v2 FP32 graph snapshot and
reproduces the current scalar graph traversal while recording visited nodes. It
is an experiment tool, not a production search implementation or public API.
The output separates exact Top-10 truth nodes that were never visited from truth
nodes that were visited but omitted from the final Top-k:

```bash
cmake --build build-lite-quality --target lite_graph_route_probe
lite_graph_route_probe SNAPSHOT DATASET_DIR NEW_QUERY_CSV [EF_SEARCH [ENTRY_MODE]]
```

The optional `EF_SEARCH` value overrides the value stored in the snapshot for
sensitivity analysis; it does not modify the snapshot. `ENTRY_MODE` defaults to
`uniform`, which exactly reproduces the production entry slots. The diagnostic
`in_degree` mode instead chooses up to eight nodes with the greatest incoming
degree (ties by slot). On all four GIST
before/after snapshots, the default probe's per-query hit counts exactly matched
`lite_graph_crud_quality`. Every missed truth node was unvisited and
`visited_not_returned` was zero, so the observed Recall@10 loss is routing
coverage rather than final heap pruning.

| GIST scale / snapshot | ef=128 Recall / mean visited | ef=256 Recall / mean visited | ef=512 Recall / mean visited |
| --- | ---: | ---: | ---: |
| 10k before | 0.814 / 821.18 | 0.866 / 1,333.61 | 0.903 / 2,173.65 |
| 10k after | 0.811 / 829.95 | 0.865 / 1,350.14 | 0.909 / 2,209.59 |
| 100k before | 0.733 / 1,262.21 | 0.798 / 2,126.18 | 0.851 / 3,603.40 |
| 100k after | 0.729 / 1,264.34 | 0.801 / 2,131.47 | 0.850 / 3,618.33 |

Higher search budgets recover more exact neighbors, but increase mean visited
nodes by roughly 1.6-1.7x at `ef=256` and 2.7-2.9x at `ef=512` relative to
`ef=128`. The repair delta changes sign across scale and budget, so these 100
queries do not support a stable recall improvement claim. The evidence narrows
the next algorithmic work to entry routing and neighbor selection, with recall
and visited-node cost reported together. Raw route CSV and summaries are in
`/home/ubuntu/project/vsag-lite-query-paired-20261005`.


##### Static high-in-degree entries

The `in_degree` entry mode tests whether static graph hubs are better starting
points than the production uniform slots. It keeps the entry count and all
subsequent traversal logic unchanged. The table reports paired differences from
`uniform`: Recall@10 and mean visited nodes.

| GIST scale / snapshot | ef=128 delta | ef=256 delta | ef=512 delta |
| --- | ---: | ---: | ---: |
| 10k before | 0.000 / -6.59 | -0.001 / -6.32 | 0.000 / -5.04 |
| 10k after | -0.001 / -6.74 | -0.001 / -5.86 | 0.000 / -5.10 |
| 100k before | +0.002 / -6.06 | 0.000 / -9.12 | 0.000 / -8.95 |
| 100k after | +0.002 / -8.55 | -0.001 / -11.11 | 0.000 / -9.23 |

At `ef=128`, only one or two queries changed per run. At `ef=256`, two runs
lost one hit and the other two were unchanged; all `ef=512` result sets had
the same hit counts. Saving roughly 5-11 visited nodes out of 815-3,618 is less
than one percent and does not establish a useful quality/cost improvement.
Static high-in-degree entries therefore remain a rejected diagnostic candidate,
not a production change.


##### Query-directed greedy routing

The diagnostic `greedy` mode starts from the production uniform entries,
chooses the query-nearest seed, and follows ring and outgoing graph neighbors
while distance strictly improves. It then runs the unchanged bottom search from
the local minimum. This approximates the direction of Full HGraph's query-aware
routing, but deliberately does not claim equivalence to its separate sparse
route levels. The CSV reports `route_nodes` and `distance_evaluations`; route
work is included rather than hidden.

The table reports the paired Recall@10 change from `uniform` and the mean
additional distance evaluations per query:

| GIST scale / snapshot | ef=128 delta / extra evals | ef=256 delta / extra evals | ef=512 delta / extra evals |
| --- | ---: | ---: | ---: |
| 10k before | 0.000 / 37.93 | -0.001 / 40.82 | 0.000 / 44.40 |
| 10k after | -0.001 / 37.93 | -0.001 / 41.70 | 0.000 / 44.95 |
| 100k before | +0.002 / 42.23 | +0.001 / 40.36 | 0.000 / 42.77 |
| 100k after | +0.002 / 41.82 | +0.001 / 40.10 | 0.000 / 42.72 |

At 10k the route was neutral or lost one hit; at 100k it gained at most two
hits at the lower budget, and the difference disappeared at `ef=512`. Two
10k runs each scored one truth node during routing that the final Top-10 did not
return. The small, scale-dependent changes do not justify the added work or a
production entry-policy change. A future routing candidate needs a separately
constructed sparse route structure or improved neighbor selection rather than
greedy descent over the same bottom graph.


##### Offline neighbor-selection experiment (2026-10-05)

The route probe accepts an additional optional argument:

```text
lite_graph_route_probe SNAPSHOT DATASET OUTPUT [EF_SEARCH [ENTRY_MODE [NEIGHBOR_MODE]]]
```

`preserve` is the default and leaves stored edges unchanged. `symmetric` pools
original outgoing and incoming neighbors, removes duplicates, then keeps the
nearest `max_degree` candidates. Only the candidate pool is symmetric: the
resulting directed graph need not be. `diverse` uses the same pool and the
alpha=1 occlusion comparison from `src/impl/pruning_strategy.cpp`:
a candidate is rejected if it is closer to an already selected neighbor than
to the source. Selection is synchronous over the original snapshot and does
not refill rejected edges. This is not an exact Full HGraph transplant: Full
keeps undersized candidate pools unchanged and has separate candidate discovery
and reverse-edge installation. The probe prunes undersized pools too, performs
no online mutation maintenance, and never writes the transformed snapshot.

All results below use uniform entries, ef=128, degree limit 16 and 100 independent
Top-10 queries per dataset/scale. Both `before` and `after` snapshots are taken
AFTER long CRUD; these labels distinguish the incoming-repair implementation,
not before/after CRUD. The table shows the repaired (`after`) snapshots.
Topology measures stored directed edges only, excluding the implicit ring used
by search. Zero in-degree and reachability are diagnostics, not a proof of
strong connectivity or query quality.

| Dataset | Mode | Recall@10 | Mean visited | Mean degree | Zero in-degree | Reachable from slot 0 |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| SIFT 10k | preserve | 0.976000 | 798.410000 | 16.000000 | 0 | 9900 |
| SIFT 10k | symmetric | 0.977000 | 805.310000 | 16.000000 | 122 | 9814 |
| SIFT 10k | diverse | 0.997000 | 871.390000 | 7.071900 | 0 | 10000 |
| SIFT 100k | preserve | 0.949000 | 1137.560000 | 16.000000 | 9 | 99283 |
| SIFT 100k | symmetric | 0.953000 | 1136.150000 | 16.000000 | 1198 | 98147 |
| SIFT 100k | diverse | 0.989000 | 1148.070000 | 8.203820 | 9 | 99991 |
| GIST 10k | preserve | 0.811000 | 829.950000 | 16.000000 | 28 | 8483 |
| GIST 10k | symmetric | 0.830000 | 806.350000 | 16.000000 | 1392 | 6917 |
| GIST 10k | diverse | 0.962000 | 1085.120000 | 5.492800 | 214 | 9768 |
| GIST 100k | preserve | 0.729000 | 1264.340000 | 15.999010 | 433 | 88344 |
| GIST 100k | symmetric | 0.771000 | 1217.450000 | 15.999310 | 17738 | 63769 |
| GIST 100k | diverse | 0.896000 | 1413.600000 | 5.678810 | 2647 | 97019 |

Diversity substantially improves recall in these samples, but is not ready for
production adoption: GIST 100k zero in-degree increases from 433 to 2,647 despite
higher reachability and recall. GIST 10k increases from 28 to 214. Nearest-only
selection over the symmetric candidate pool degrades topology still further.
A subsequent online candidate must preserve or repair incoming connectivity
and measure single-core Add/Update/Remove cost, query latency, and memory.
The lower mean degree does not itself establish a production memory saving.

At ef=256/512, diverse GIST recall is 0.986/0.994 (10k) and 0.932/0.961 (100k)
on repaired snapshots. These gains spend more search work: ef=128 mean visited
nodes are 1,085/1,414 versus 830/1,264 for preserve. Results from 100 queries
and an offline whole-graph transformation do not prove online CRUD stability,
production speed, or optimality. The recorded process time includes loading,
transformation and every query; it is not isolated build or search latency.

Evidence directories on the experiment host:
`/home/ubuntu/project/vsag-lite-neighbor-selection-20261005` (24 topology runs)
and `/home/ubuntu/project/vsag-lite-query-paired-20261005` (GIST budget sweeps).
`topology-*-summary.csv` includes degree, zero-in/out and directed reachability;
per-query CSVs retain their existing schema. Default mode reproduced all 400
GIST public-baseline query hit counts. The Release suite passed 4/4 and the
ASan+UBSan suite 6/6. Small collinear, incoming-only and singleton fixtures,
invalid mode and empty-snapshot rejection passed with both probe builds:

```bash
python3 lite/benchmark/test_graph_route_probe.py build-lite-fragment-release/lite_graph_route_probe
python3 lite/benchmark/test_graph_route_probe.py build-lite-baseline-asan/lite_graph_route_probe
```

Only the standalone experiment and its documentation change. Production graph
construction, CRUD, public API and snapshot format remain unchanged.


##### Diversity followed by safe incoming repair (2026-10-05)

The optional `NEIGHBOR_MODE=diverse_repair` applies the preceding diversity
selection, then visits zero-in-degree targets in slot order. It first appends
a reverse edge from the first outgoing neighbor with spare degree. If no such
neighbor exists, it follows `GraphBackend::ensure_incoming` in
`src/lite/graph_backend.cpp`: replace the farthest eligible edge from an outgoing
neighbor only when the displaced target retains at least one other incoming
edge. If neither operation is possible, the target is left unresolved. No
self edges, duplicate edges or degree overflow are introduced. This experiment
adds spare-capacity handling because diversity often leaves partially filled
rows; the production helper uses replacement. It is still a single offline
pass, not a guarantee of connectivity or an online CRUD implementation.

Eight SIFT/GIST snapshots were evaluated on CPU 0, uniform entries, ef=128,
degree limit 16 and 100 independent queries. All eight ended with zero
zero-in-degree nodes. Repaired-implementation (`after`) snapshots:

| Dataset | Diverse Recall | Diverse+repair Recall | Mean visited | Mean degree | Reachable from slot 0 |
| --- | ---: | ---: | ---: | ---: | ---: |
| SIFT 10k | 0.997000 | 0.997000 | 871.390000 | 7.071900 | 10000 |
| SIFT 100k | 0.989000 | 0.989000 | 1148.100000 | 8.203910 | 100000 |
| GIST 10k | 0.962000 | 0.963000 | 1086.600000 | 5.506300 | 9978 |
| GIST 100k | 0.896000 | 0.891000 | 1415.220000 | 5.693380 | 99625 |

GIST 100k recall decreases from 0.896 to 0.891 versus pure diversity but remains
above preserve (0.729). Reachability improves from 97,019 to 99,625, while
zero-in-degree drops from 2,647 to zero. GIST 10k recall increases from 0.962
to 0.963, with reachability 9,978 and zero-in-degree zero. Neither graph is
fully reachable along stored edges. The synthetic saturated-degree fixture
also demonstrates that zero-in-degree zero can leave disconnected components.

The candidate merits online evaluation, not automatic adoption. CPU pinning
controls placement; no isolated timing was collected in this matrix, so this
is not evidence of single-core speedup. Next evaluate connectivity preservation
and online construction/CRUD cost, CPU time, query latency and memory before
changing the production selection policy. The fixed 100 queries remain a
sampling limitation; Cohere is not covered by this experiment.

Release 4/4 and ASan+UBSan 6/6 passed. Both probe builds passed spare-capacity,
safe saturated replacement, impossible-repair and singleton regression fixtures.
The ASan GIST 10k run matched Release per-query CSV exactly. Existing preserve
and diverse GIST 10k outputs were byte-identical to the preceding experiment.
Format/tidy version 15 and diff checks passed. Raw results and commands are in
`/home/ubuntu/project/vsag-lite-diverse-repair-20261005`; production code and
PR branches are unchanged.


##### Directed versus weak connectivity (2026-10-05)

The summary additionally reports `reverse_reachable_from_zero`,
`weak_components` and `largest_weak_component`. Reverse reachability counts
nodes that can reach slot zero along stored directed edges. Weak components
ignore edge direction. These linear-time diagnostics exclude implicit search
ring edges and require an auxiliary reverse adjacency list; their memory and
time must not be attributed to the production index or search.

All 12 combinations of SIFT/GIST 10k/100k repaired-implementation snapshots
and preserve/diverse/diverse_repair have one weak component containing every
node. Thus the observed reachability deficit is directed, not disconnected
weak components. For diverse_repair:

| Dataset | Reachable from 0 | Can reach 0 | Weak components | Largest component |
| --- | ---: | ---: | ---: | ---: |
| SIFT 10k | 10000 | 10000 | 1 | 10000 |
| SIFT 100k | 100000 | 100000 | 1 | 100000 |
| GIST 10k | 9978 | 10000 | 1 | 10000 |
| GIST 100k | 99625 | 99955 | 1 | 100000 |

Both SIFT snapshots are strongly connected: every node reaches zero and zero
reaches every node. GIST is not: the 100k graph has 375 nodes unreachable from
zero and 45 unable to reach zero (these sets need not be disjoint). The 45-node
reverse deficit already exists in preserve and pure diverse. A subsequent
candidate should examine directed edge installation/retention and safe reverse
links, rather than assuming zero in-degree repair guarantees connectivity.
These diagnostics do not prove that every missed query is due to connectivity;
budget-limited exploration remains a separate source of recall loss.

All 1,200 per-query output rows are byte-identical to the previous corresponding
runs. Release 4/4, ASan+UBSan 6/6, both-build small-graph fixtures, format/tidy15
and diff checks passed. Fixtures distinguish a one-way connected chain from two
independent cycles. Commands and raw evidence are in
`/home/ubuntu/project/vsag-lite-connectivity-20261005`. No production policy or
PR branch is changed by this diagnostic increment.


##### Append-only reverse-edge candidate (2026-10-05)

`NEIGHBOR_MODE=diverse_reverse` runs diverse_repair then considers each existing
edge in source-slot order, appending its missing reverse only when the target
row has spare degree. Candidate edges are copied before the pass, so newly
added edges cannot affect iteration. This references Lite Add/Update's reverse
`link(neighbor, slot)` operation, but intentionally omits eviction. It never
removes edges and preserves the configured degree limit; saturated rows may
leave asymmetric edges. The temporary adjacency copy is experiment overhead,
not evidence of production memory cost.

Eight before/after incoming-repair snapshots (all after long CRUD) were tested
on CPU 0 with uniform entries, ef=128 and 100 independent Top-10 queries.
The repaired-implementation snapshots give:

| Dataset | Recall@10 | Mean visited | Mean degree | Reachable from 0 | Can reach 0 |
| --- | ---: | ---: | ---: | ---: | ---: |
| SIFT 10k | 1.000000 | 930.870000 | 8.945800 | 10000 | 10000 |
| SIFT 100k | 0.993000 | 1240.440000 | 10.129540 | 100000 | 100000 |
| GIST 10k | 0.972000 | 1136.500000 | 7.616700 | 9991 | 10000 |
| GIST 100k | 0.903000 | 1484.010000 | 7.750910 | 99789 | 99955 |

Compared with diverse_repair, GIST 100k recall improves 0.891 to 0.903,
mean visited grows 1,415.22 to 1,484.01 (about 4.9%), and mean degree grows
5.69338 to 7.75091 (about 36%). Unreachable-from-zero nodes fall from 375 to
211, while the 45 nodes unable to reach zero remain. GIST 10k recall improves
0.963 to 0.972 but nine nodes remain unreachable. SIFT remains strongly
connected and reaches recall 1.000/0.993 at 10k/100k. These are sample results,
not guaranteed perfect recall or measured latency improvements.

The candidate remains offline: full connectivity is not achieved on GIST and
extra adjacency/search work must be weighed against quality. Next inspect
saturated boundary rows before proposing edge replacement, and validate online
construction/CRUD behavior and single-core timings before production adoption.
Do not infer that eliminating the reachability deficit alone will eliminate
all recall loss under a finite search budget.

Release 4/4, ASan+UBSan 6/6 and both-build fixtures passed, including an
asymmetric four-node graph that exercises actual reverse addition and saturated
cycles that cannot be connected by this pass. ASan GIST 10k per-query output
matches Release; the previous diverse_repair output is unchanged. Format/tidy15
and diff checks passed. Raw evidence and commands:
`/home/ubuntu/project/vsag-lite-reverse-fill-20261005`. No production code or
PR source branch is changed.


##### Two-hop-witness reverse replacement: not adopted (2026-10-05)

`NEIGHBOR_MODE=diverse_reverse_safe` extends diverse_reverse with a second
reverse-edge pass. For a saturated row u, an existing edge u->v is eligible for
replacement only if a current u->w->v path exists with w different from v.
The farthest eligible edge is replaced by the missing reverse. The witness is
checked against the current graph for each mutation, so deleting that edge
preserves prior reachability through the two-hop path. This is stricter than
production `GraphBackend::link`'s incoming-count guard, but it is not an exact
transplant and does not preserve path lengths or finite-budget search quality.
Candidates are snapshotted, all changes respect the existing degree limit,
and no public API, production CRUD or snapshot format changes.

Eight SIFT/GIST snapshots were evaluated with CPU 0, ef=128, uniform entries
and 100 independent queries. Repaired-implementation snapshots:

| Dataset | Append-only Recall | Replacement Recall | Mean visited | From 0 | To 0 |
| --- | ---: | ---: | ---: | ---: | ---: |
| SIFT 10k | 1.000000 | 1.000000 | 932.740000 | 10000 | 10000 |
| SIFT 100k | 0.993000 | 0.992000 | 1244.700000 | 100000 | 100000 |
| GIST 10k | 0.972000 | 0.972000 | 1146.560000 | 9996 | 10000 |
| GIST 100k | 0.903000 | 0.900000 | 1498.170000 | 99802 | 100000 |

All measured forward/reverse reachability counts are nondecreasing and average
degree is unchanged. In GIST 100k, all 100,000 nodes can now reach zero, but
198 remain unreachable from zero. Recall drops 0.903 to 0.900 and mean visited
increases 1,484.01 to 1,498.17. SIFT 100k loses 0.001 recall, and GIST 10k is
unchanged after repair (the before snapshot loses 0.003). No tested combination
improves recall over append-only reversal. With only 100 queries these small
differences are not a statistical regression claim, but there is no observed
quality/work advantage to justify adoption. The candidate stays opt-in and
will not be added to production. Stop extending this topology-only sequence;
next measure the simpler diversity/append-only alternatives under matched
recall and actual single-core build, query and CRUD costs.

The probe's `--self-test` checks an actual saturated replacement and all-pairs
reachability preservation for that fixture, plus refusal without a witness.
The Python fixture runner invokes it and covers degree-one disconnected cycles.
Release 4/4, ASan+UBSan 6/6 and both-build fixtures passed; ASan GIST 10k output
matches Release and the previous diverse_reverse output remains identical.
Format/tidy15 and diff checks passed. Raw results, commands and source/binary
hashes are in `/home/ubuntu/project/vsag-lite-reverse-safe-20261005`.


##### Actual Lite API timing for offline candidates

The optional `API_REPEATS` argument measures the actual Lite API:

```text
lite_graph_route_probe SNAPSHOT DATASET OUTPUT [EF_SEARCH [ENTRY_MODE [NEIGHBOR_MODE [API_REPEATS]]]]
```

API_REPEATS must be 1..1000 and requires uniform ENTRY_MODE. The probe now links
vsag::lite. It serializes the selected graph into the existing v2 FP32 format,
loads it with Index::Load, performs one full warmup/quality pass, then times
Index::Search calls. The `.api.csv` summary and `.api.csv.latencies.csv` raw
samples are additional outputs; previous diagnostic commands remain valid.
Existing output paths are rejected. Query-loop CPU time includes the full loop;
Load is from an in-memory stream and excludes serialization/graph transformation.

The five-process GIST100k comparison and raw samples are published in
[results/api-latency-20261005](results/api-latency-20261005/README.md).
At the selected Recall>=0.90 gate, preserve ef1536 scores 0.902 with median
process P50 4035.594us; diverse_reverse ef128 scores 0.903 with P50 618.959us.
This loaded-index warm-query result is promising, but does not measure online
construction/CRUD, independent holdout quality or cold-start performance.


##### Loaded-candidate CRUD validation

An optional `CRUD_CYCLES` argument after API_REPEATS runs serial Update changed,
Update original, Remove and Add original cycles through the loaded Lite API.
It requires 1..100000 cycles. The original external ID and vector are restored
on every cycle; success and live count are checked. Post-CRUD queries are scored
against the same truth, then Save/Load must preserve all result IDs/distances.
Additional `.api.csv.crud.csv` and `.samples.csv` outputs contain post-CRUD quality,
loop CPU time and every operation latency. Query timing remains pre-CRUD.

[The GIST two-scale, three-process results](results/api-crud-20261006/README.md)
show preserved candidate recall advantage, with mutation loop CPU overhead about
33.4% at 10k and 19.5% at 100k at equal ef=128. This measures existing CRUD on an
offline-transformed graph; online diversity building, long churn and concurrency
remain to be validated. It must not be combined into a net speedup with the
previous differently tuned query comparison.


##### Independent-query acceptance gate (2026-10-06)

The fixed tuning-set configurations failed Recall>=0.90 on GIST source rows
[100,400), disjoint from prior rows [0,100): preserve ef1536 scores 0.867667,
diverse ef160 0.837000, diverse_reverse ef128 0.836667. The previously recorded
6.52x loaded-query ratio is limited to the tuning split and is not a validated
equal-quality speedup on independent queries. No retuning was performed.
[Raw evidence, preparation and acceptance limits](results/gist-holdout-20261006/README.md).
The wrapper prepare_gist_holdout.py reuses the existing precise truth preparer;
reserve unused query rows for final assessment after any further tuning.


##### Input and scoring investigation (2026-10-06)

[The failed-gate investigation](results/input-audit-20261006/README.md) found
all 100,000 snapshot vectors byte-identical to prepared base vectors by external
ID. Eight sampled truth sets match independent double-precision exhaustive scans;
all three aggregate scalar/API recalls match. No sampled input/scoring error was
found, so the independent-query gate remains failed and parameter selection must
be validated more broadly before any adoption claim.


##### Online neighbor-diversity experiment

The standalone Lite CMake option ENABLE_DIVERSE_NEIGHBOR_EXPERIMENT defaults OFF.
It enables FP32 alpha=1 diversity pruning inside GraphBackend::nearest, so actual
BuildGraph/Add/Update select neighbors online. Undersized pools and FP16 keep
existing selection. Reverse link and Remove repair still use the existing policy.
[Online construction results and boundaries](results/online-diverse-20261006/README.md)
show higher validation recall with increased construction/query cost; the 100k
configuration remains below the 0.90 quality gate. Keep the option experimental.


##### Frozen online-graph budgets and final-query acceptance

[Final GIST100k study](results/online-final-20261006/README.md) freezes budgets
on development rows [100,400) then tests unseen rows [400,1000). The loaded
post-1,000-CRUD default graph at ef8192 scores Recall0.954/P50 17.303ms; the online
diversity graph at ef512 scores 0.950/2.057ms (three-process medians). Both pass
Recall>=0.90. The 8.41x selected-point ratio is conditional on a coarse budget
grid, warm single-core loaded querying and this dataset; it is not a universal
or globally optimal speedup. Construction was at ef128. Query-budget overrides
are experimental; an independent public query-budget interface and broader
workload validation remain to be implemented. All 1,000 GIST queries are now
observed and cannot serve as a new blind set after more tuning.


##### Native per-query options

The API timing mode now calls SearchWithOptions and preserves the snapshot's
configured budget. API CSV adds configured_ef_search and query_ef_search.
Query overrides no longer change CRUD's stored budget; post-CRUD quality uses
the requested query budget. [Verification and migration boundary](results/query-options-20261006/README.md).
Historical high-budget mutation measurements that altered the snapshot option
have different semantics and must not be relabeled as this native API path.


##### Serial mixed workloads

An optional QUERY_EVERY argument after CRUD_CYCLES interleaves one query after
that many complete modified-update/restore/remove/re-add cycles. It must be
1..CRUD_CYCLES; omission preserves grouped mutation. Query budget remains
per-call and maintenance budget remains the snapshot's configured value.
New .mixed.csv records query latency and row; appended summary fields separate
mutation CPU, query CPU and total mixed-loop CPU. In this mode crud_loop_cpu_ms
means summed mutation-phase CPU; in grouped mode it retains full mutation-loop
CPU semantics. [GIST100k pilot and exact definitions](results/mixed-20261006/README.md)
show nearly equal end quality and a 1.87x mixed-CPU ratio for the selected
mutation-heavy workload, with 9% higher maintenance CPU. One run per mode is
not a repeated-run estimate or a universal workload speedup.
