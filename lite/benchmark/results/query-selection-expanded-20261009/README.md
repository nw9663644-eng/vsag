# Adopted query-local retained-buffer selection

Control is previous Lite at 3361bd2 (production C++ at 3f27573), not native Full VSAG.
Fixed existing 600 observed queries per dataset, 10k GIST/Cohere, k10, degree16,
construction128, query ef512, CPU0, one BLAS/OMP thread, alternating process order.
No warmup; warm uncontrolled cache and noisy shared VM. Not blind acceptance.

| Dataset | Storage | Control P50 us | Candidate P50 us | P50 change | P99 change | Recall |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| cohere10k600 | fp16 | 448.339 | 405.621 | -9.53% | -11.06% | 0.987 |
| cohere10k600 | fp32 | 591.476 | 535.899 | -9.40% | -11.67% | 0.987333 |
| cohere10k600 | rabitq8 | 488.519 | 450.751 | -7.73% | -2.66% | 0.9835 |
| gist10k600 | fp16 | 486.949 | 443.969 | -8.83% | -3.04% | 0.9655 |
| gist10k600 | fp32 | 629.387 | 590.628 | -6.16% | -7.00% | 0.9655 |
| gist10k600 | rabitq8 | 492.01 | 466.291 | -5.23% | -0.24% | 0.961 |

Five paired trials, one independent load per builder: 30 pairs, 60 builders,
60 loads, 36000 truth intersections. Routing/admission unchanged. FP32/FP16
consume the owned heap buffer and select/sort only top-k. RaBitQ scores the
same retained coarse candidates directly; formula/count/final ranking unchanged.
Based on native DistanceHeap::GetData and HGraph RaBitQ BoundedResults access,
not a new quantization algorithm or a lower search budget.
All paired snapshots and ordered ID/hex-distance outputs are exactly equal.
Load/index-size/RSS are recorded, but no new footprint or Full speed win is claimed.
RaBitQ still slower than FP16 here. Tail improvement is small for GIST RaBitQ.
Fresh scoped coverage: Lite 2675/2813 (95.09%), shared SIMD174/176 (98.86%).
See validation.json for exact tests and exclusions; whole project remains incomplete.

Run python3 verify.py from this directory to audit both experiments.
Archive includes actual frozen query/truth bytes and all raw per-query records.
Base data provenance and reproduction arguments are in dataset/identity metadata.
Original base files are preserved on the server; temporary snapshots were
automatically removed by the driver after hashes/load tests due to disk limits.
New untracked header omitted by git diff is included in raw.tar.gz plus source hashes.
The paired invocation is recorded in identity.json; use run_aligned_comparison.py
with the pinned control library and frozen dataset prefixes to reproduce.
