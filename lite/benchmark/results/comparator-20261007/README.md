# Typed comparator optimization, 2026-10-07

Source parent 549a44d plus this recorded change. Following official StandardHeap's
concrete CompareMax/CompareMin pattern, Lite priority queues and sorts now use
Closer/Farther objects. Operators call the original distance/slot comparison;
queue direction, tie order, distances, budgets, graph policy and snapshot format
remain unchanged. No Full, third-party, public API or concurrency change.
Prior CPU profiles identified distance, visit and heap/comparator hotspots.

The existing optional query-hit output now also emits .neighbors.csv containing
ordered ID and hexfloat distance for exact differential checks. Original hit CSV
schema remains unchanged, no sidecar without query-output argument, existing
sidecars are rejected before the workload. Small fixture verifies output and
non-overwrite behavior.

## Fixed comparison

CPU0, normalized Cohere 10k/768dim, existing 100 observed queries, L2 Top 10,
degree 16/construction/query 128. Two library modes: default OFF/diversity ON.
Build-only vs 10000 distinct-ID same-vector Update/Remove/Add cycles, with staging,
build, quality queries and snapshot roundtrip in both. Three processes per
mode/flow/variant =24 final runs, reversed variant/mode/flow order on odd repeats.
Each variant uses the SAME new diagnostic runner, explicitly bound by
LD_LIBRARY_PATH to saved old or rebuilt new libvsag-lite.so. ldd/hash evidence
confirms binding; do not describe this as two unrelated build/compiler settings.

A separate 24 exploratory runs overlapped verification builds. Preserve them for
correctness but exclude their timings from the final performance conclusion.
Final runs began after build/test/tidy jobs completed; unrelated system services
still run. No profiler instrumentation in final runs. /usr/bin/time user+system
CPU includes the whole process, not isolated maintenance;0.01s rounding and
normal frequency/cache variability apply. It is not a statistical confidence bound.

| Library mode | Flow | Old median CPU s | New median CPU s | Change | Recall@10 |
|---|---|---:|---:|---:|---:|
| default | build | 2.18 | 1.90 | -12.84% | 0.960000 |
| default | crud | 7.15 | 6.59 | -7.83% | 0.933000 |
| diverse | build | 2.47 | 2.15 | -12.96% | 0.982000 |
| diverse | crud | 8.21 | 7.19 | -12.42% | 0.960000 |

All 48 runs: old/new snapshots byte-identical,100-query hit CSVs byte-identical,
1000 ordered ID/hexfloat-distance rows byte-identical for each mode/flow across
all repeats. API/count/roundtrip checks pass. Published neighbor files and hashes
are independently auditable; large snapshots/binaries remain on the server.
Fixed query workloads do not measure general query latency gains; do not extend
these whole-process CPU ratios to other datasets/scales, cold start or concurrency.

Default after full-ID churn remains 0.933 (initial 0.960); diversity remains 0.960
(initial 0.982). The default quality limitation is NOT fixed by dispatch optimization.
Candidate stays OFF by default. Timing gains do not establish quality acceptance
or whole-project completion. Next diagnose full-ID quality degradation separately,
and confirm performance/semantic equivalence at 100k and another distribution.

## Verification

Default Release 4/4; diversity Release 3/3; default ASan+UBSan 6/6 pass.
Fresh unit-only gcov run after resetting generated counters:957/1060 emitted
Lite source/internal-header lines =90.28%. File counts are in coverage.json and
raw gcov JSON is retained; this is not Full/extern/benchmark or branch coverage.
Source graph/backend and diagnostic probe pass clang-format 15/clang-tidy 15.
Non-user header warnings are suppressed, not a whole-repository lint claim.
New sidecar fixture checks 8x 16 one-hot outputs, unchanged hit schema and overwrite
rejection. Existing unit tests cover filter traversal, FP16, ties, invalid inputs,
randomized CRUD and persistence. No new algorithm correctness promise.

verify.py checks manifest/raw neighbor hashes, protocol/binding, CPU derivation,
48-run equivalence, medians/changes and coverage >=90%. Test logs retain scope.
Reproduction scripts encode original host paths; use NEW output roots/prefixes
and recorded library binaries, do not overwrite old evidence. Snapshots and old
libraries in /home/ubuntu/project/vsag-lite-comparator-20261007 and final inputs
in sibling vsag-lite-comparator-final-20261007 remain available on the host.
Only personal experiment/lite-rabitq-next-20260926 is pushed; PRs remain frozen.

The first publication verifier used a wrong fixed CLI token offset; corrected to
locate taskset explicitly. Recorded commands and measurements were unchanged.
