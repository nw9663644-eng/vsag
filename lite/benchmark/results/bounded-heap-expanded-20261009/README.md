# Rejected single-sift bounded heap prototype

Control is previous Lite at 3361bd2 (production C++ at 3f27573), not native Full VSAG.
Fixed existing 600 observed queries per dataset, 10k GIST/Cohere, k10, degree16,
construction128, query ef512, CPU0, one BLAS/OMP thread, alternating process order.
No warmup; warm uncontrolled cache and noisy shared VM. Not blind acceptance.

| Dataset | Storage | Control P50 us | Candidate P50 us | P50 change | P99 change | Recall |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| cohere10k600 | fp16 | 423.7 | 423.041 | -0.16% | +14.30% | 0.987 |
| cohere10k600 | fp32 | 550.209 | 529.138 | -3.83% | +7.65% | 0.987333 |
| cohere10k600 | rabitq8 | 469.671 | 466.849 | -0.60% | +7.71% | 0.9835 |
| gist10k600 | fp16 | 435.471 | 469.779 | +7.88% | +4.96% | 0.9655 |
| gist10k600 | fp32 | 515.228 | 516.338 | +0.22% | +0.31% | 0.9655 |
| gist10k600 | rabitq8 | 554.988 | 541.818 | -2.37% | -1.33% | 0.961 |

Three paired trials, three loads per builder: 18 pairs, 36 builders,
108 loads, 21600 truth intersections. The prototype replaced fixed best-heap
push/pop with single-sift root replacement. It passed Release6/6 and retained
exact paired snapshots/results, but GIST FP16 median P50 regressed7.88%
and several P99 medians regressed. Rejected; not present in production source.
No sanitizer/coverage/tidy acceptance is claimed for the rejected candidate.
Complete rejected header preserved in raw.tar.gz; identity.git_diff stores
tracked candidate diffs. Do not silently discard these negative results.
