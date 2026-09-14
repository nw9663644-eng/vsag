# SQ8 candidate probe (not an index backend)

This standalone executable evaluates one possible next Lite quantization format. It
does **not** change Index, graph traversal, the v1/v2 snapshot, or process
resident memory of the current Lite index. The measured `sq8_code_bytes`
counts only encoded vectors; the probe also keeps the FP32 base dataset and
training model in memory to calculate exact ground truth and reconstruction
error. Its process RSS is therefore not the memory use of an SQ8 index.

The probe reuses the repository's generic scalar SQ8 squared-L2 kernel and
`ClampScalarQuantizationDelta`. It trains **classic per-dimension minimum and
maximum bounds** on the selected base vectors, encodes one unsigned byte per
dimension, and searches all encoded vectors with FP32 queries. Full VSAG's
`ScalarQuantizer` normally uses a sampled/truncated-bound trainer and brings
additional allocator, parameter and SIMD-dispatch dependencies; this probe is
not bit-identical to that full training configuration.

Configure the independent Lite build and run a self-test:

    cmake -S lite -B /path/to/build-sq8 -G Ninja -DCMAKE_BUILD_TYPE=Release -DENABLE_QUANTIZATION_PROBE=ON
    cmake --build /path/to/build-sq8 --target lite_sq8_probe -j2
    /path/to/build-sq8/lite_sq8_probe --self-test

Run the prepared 10k or 100k SIFT-128 subset from the experiment workflow:

    /usr/bin/time -v -o /path/to/results/sq8-100k.time.txt /path/to/build-sq8/lite_sq8_probe /path/to/scale-100000 > /path/to/results/sq8-100k.csv 2> /path/to/results/sq8-100k.stderr.txt

The program checks that the FP32 exhaustive top-10 matches the supplied exact
ground truth on 100 independent queries, then reports SQ8 Recall@10, RMSE,
query P50/P99 and encoded byte count. Search times are exploratory, alternate
FP32/SQ8 execution order per query, and use the generic scalar kernel; they
are neither graph-search latency nor an optimized SIMD comparison. The tool
assumes Linux x86_64 little-endian fvecs/ivecs input. It rejects missing,
truncated, wrong-dimension, non-finite and inconsistent datasets.

On 2026-09-14, three 100k SIFT runs each yielded SQ8 Recall@10 0.988 and
12,800,000 encoded bytes versus 51,200,000 FP32 vector bytes. Median generic
scalar SQ8 exhaustive-search P50 was 33.33 ms, slower than this probe's
FP32 8.81 ms. These figures are candidate evidence only. Before adding an SQ8
backend, measure the combined graph+SQ8 Recall/latency, real index RSS, CRUD,
Save/Load and snapshot compatibility under a separately versioned format.
