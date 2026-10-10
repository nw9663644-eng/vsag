# RaBitQ maintenance Batch4 reuse (2026-10-10)

## Source evidence and minimal change

The pinned native `src/simd/kernels/rabitq_compute.h` supplies
`RaBitQFloatThreeBitCenteredIPBatch4Impl`; existing Lite AVX2/AVX512
wrappers and generic dispatch already use it in query routing.
This change reuses that dispatch for `MutableGraphState::link/repair`
neighbor scores. Candidates are gathered in the original order,
four centered inner products are computed together, and the original
supplementary distance formula/sum is applied independently.
Scalar tails and a scalar golden template preserve bitwise scores.
No new SIMD kernel, persistent buffer/cache, allocations beyond the existing
ranking vector, API, snapshot format, degree, search budget, topology policy,
rotation/model, or rollback change is intended.

## Fixed paired workload

Control: parent e7e73b4e839d12c8d708986fcc62300ff91e07a2 header.
Candidate: measured header and patch in raw.tar.gz.
Both public adapters use NONE, not the experimental protected policy.
GIST/Cohere: 10k records, each 600 historical queries, k=10,
degree=16, construction/maintenance ef=128, query ef=512, CPU0/thread1.
Three alternating pairs per dataset; every builder performs three full-ID
true changed-value Update/Remove/Add rounds (90,000 operations).
Twelve builders total, 1,080,000 operations, 14,400 initial/final truth intersections.
No builds/tests were run concurrently with measurement.
Replacement matrices regenerate from preserved base/recipe and SHA receipts;
actual query/truth files and operation latencies are archived.

| Dataset | Control CRUD median ms | Candidate median ms | Change |
| --- | ---: | ---: | ---: |
| gist10k600 | 25523.234303 | 25225.618091 | -1.166% |
| cohere10k600 | 22582.874539 | 22141.659656 | -1.954% |

All six paired samples improved; this is a small workload-specific observation,
not statistical significance or a universal speedup. Per-operation P50/P99,
throughput, search latency, snapshot bytes and peak RSS are in summary.json.
Every pair's initial/final ordered IDs, hex distances, hits and complete snapshot
SHA are identical; every builder passes native exact Save/Load.
Final recall remains GIST .811167 / Cohere .908167: this change does not fix the
known maintained-graph quality gap. No new query/package/loading/Full advantage
is claimed.

## Validation and reproduction

Release6, ASan/UBSan5 (including allocation rollback), fresh scoped coverage5,
RaBitQ-disabled4, clang-format15 and clang-tidy15 passed.
The added scalar-vs-Batch4 golden test covers candidate counts0..65,
reversed candidate order, repeated codes and 13 dimensions including tails.
Initial tidy rejected direct float memcmp in the new test; explicit byte-pointer
comparison fixed it, all validation was rerun, failure/repair logs retained.
The measured production header stayed byte-identical; timings were not rerun.
Coverage raw JSON and independently recomputed aggregates are included;
scope is Lite compiled production/public headers and instantiated shared SIMD,
not whole Full VSAG. Node checker/whole Full suites were not run.

On the verified original host, run `python3 PATH/verify.py` for offline audit.
For host replay, check out identity.json base_head, apply archived candidate.patch,
build the measured Release tool (matching its SHA), copy run-host.py to a NEW
empty result directory and run it from repository root with TMPDIR=/dev/shm.
The helper pins the archived candidate; original output cannot be overwritten.
Historical compiler/link paths, datasets/dependency wheels and ABI must exist.
Final replay helper was syntax-checked only, not rerun; raw/measured-run-host.py
is the actual executed script. SHA256SUMS covers canonical files.

Only two verified inactive old static archives (29,187,792 bytes) were removed
after timings, with paths/hashes/rebuild targets in raw/cleanup.json.
Current libraries, source, data and old raw evidence were preserved.
Fresh generated gcda counters were reset before coverage.
Only this run's new RAM snapshots were removed after exact Load and SHA.
100k, interleaved changed-value CRUD, fresh config/SIMD/quality-aligned Full,
cold I/O and complete package acceptance remain outstanding.

## Per-operation latency detail

Medians across three builders per variant, microseconds; not every operation improves.

| Dataset / operation | Control P50/P99 | Candidate P50/P99 |
| --- | ---: | ---: |
| gist10k600 / update | 387.831 / 1441.488 | 389.821 / 1402.279 |
| gist10k600 / remove | 111.327 / 184.906 | 113.777 / 184.737 |
| gist10k600 / add | 272.855 / 310.524 | 269.664 / 309.562 |
| cohere10k600 / update | 341.002 / 1223.432 | 335.233 / 1179.804 |
| cohere10k600 / remove | 119.559 / 183.626 | 116.628 / 178.186 |
| cohere10k600 / add | 241.206 / 271.954 | 238.126 / 269.644 |

GIST Update and Remove P50 rise slightly despite lower overall CRUD time.
No query-latency optimization is claimed by this maintenance-only change.
