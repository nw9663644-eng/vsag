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

An internal FP16 graph candidate is also covered by the graph test executable:

    VSAG_SIFT_DIR=/path/to/scale-100000 /path/to/lite_graph_tests '[lite-fp16-sift]'

It stores FP16 vectors and uses quantized query-to-node and node-to-node L2
for graph traversal and construction. It remains an internal factory: the
public Index API and v1/v2 snapshots do not expose it. On 2026-09-15, three
10k SIFT runs at degree 16 / ef 128 kept Recall@10 at 0.973; median build was
5.33 s and query P50 was 493 us, versus 1.32 s and 143 us for FP32 in the
same Release executable. One 100k run kept Recall@10 at 0.946, with 73.69 s
build and 711 us P50, versus 21.69 s and 303 us for FP32. FP16 vector code
bytes were 25.6 MB at 100k, while IDs and adjacency targets accounted for
another 0.8 MB and 12.8 MB; container and hash-map overhead are excluded.
A transformed 10k input scaled by 0.001 also measured Recall@10 of 0.973.
These results show no query or build speed advantage with the generic scalar
half kernel.

The first table above reports generic scalar exhaustive scans, separate from the Lite graph results.
The FP16 result is lossless on original integer-valued SIFT coordinates:
its reconstruction RMSE was zero. As an additional **transformed input**
check, multiplying the 10k SIFT base and queries by 0.001 produced nonzero
FP16 RMSE (0.000009) and Recall@10 1.000 against FP32 exact truth. This
transformed case is not a standard dataset result and does not establish
quality for general floating-point embeddings. The probe keeps all three
representations in memory; encoded bytes are not index RSS or snapshot size.

Before exposing a quantized graph through Index, measure its steady-state RSS,
choose or implement a faster distance kernel, and design a separately versioned
snapshot with complete CRUD, Save/Load and malformed-input coverage. The scalar
FP16 graph result does not justify public integration yet.
