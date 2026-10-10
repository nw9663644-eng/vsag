# Exclusive-stage RaBitQ mutation diagnosis (2026-10-10)

Diagnostic source HEAD bc3e9bd948fcab6265be7d0ba81e214fe280597b, personal experiment/lite-rabitq-next-20260926.
No production source/library changed. PR2904/2926 unchanged. This is NOT an optimization win, a native Full comparison, or completed acceptance.

## Evidence and isolated change

MutableGraphState::nearest, decode_query, link, repair, UpdatePrepared and Remove supply explicit stage boundaries.
The earlier built-in scan timer reports individual operations, not accumulated exclusive stages.
An isolated RAM overlay adds a single-thread RAII process-CPU/wall profiler; nested scopes subtract child inclusive time.
Adapter Add/Update/Remove establish operation boundaries; prepare_encoding has its own scope.
Scoring covers the candidate loop AND sort in link/repair. nearest includes routing/coarse/full scoring, not just graph traversal.
scan covers the existing Update/Remove row-scan boundaries, including remembered transaction rows.
Other adapter/link/repair buckets include bookkeeping, transaction overhead and unattributed work; these are not specific allocator measures.
decode_query reconstructs transformed normalized encoded coordinates, NOT inverse rotation or original float decoding.
No per-distance clocks. No public policy, model, degree/ef, API, snapshots or returned ordering changed.

## Frozen diagnostic workload

One diagnostic builder each for GIST/Cohere10k,600 observed historical queries,k10,degree16,
maintenance128/query512,CPU0,BLAS/OMP/MKL1; three full-ID true changed-vector Update/Remove/Add passes,
90000 mutations per dataset. NOT a new uninstrumented performance pair or a repeat of the rejected stack-scratch optimization.
The instrumented overlay is bound by first -I and pre-timing -MM receipts for state,codec and profiler.
Raw contains exact formatted compiled sources,adapter,compile/link/ldd/commands,measured Python scripts and compact inputs/truth.
Large replacements are reconstructed from preserved base+recipe/checksum; not archived here.

| Exclusive CPU bucket | GIST % | Cohere % |
| --- | ---: | ---: |
| nearest including route/scoring | 29.20 | 30.91 |
| incoming row scan | 19.08 | 22.21 |
| neighbor score + sort | 20.15 | 17.90 |
| transformed-code reconstruction | 13.77 | 11.93 |
| prepare encoding including transform | 6.28 | 5.97 |
| remaining link/repair/adapter | 11.52 | 11.07 |

Decode is material but NOT the largest stage. nearest and full-row scans remain first-class structural targets.
Do not add inclusive link/repair times to these exclusive buckets; that double-counts decoding and scoring.
Process CPU can include all threads; this run pins the recorded single-thread workload.
High-frequency clock calls perturb these distributions and have nonzero overhead; clock-read/empty-scope
Release fixtures are archived for calibration, not subtracted as a universal constant.
One run/distribution does not establish a stable production percentage or end-to-end benefit.

## Correctness / limitations

Both initial/final hits and ordered ID/hex-distance files match previous uninstrumented NONE control records byte-exact.
Final snapshot SHA matches historical records; each new builder natively Save/Loads its own results exactly before guarded RAM snapshot deletion.
This is deterministic regression equivalence, not contemporary apples-to-apples latency evidence.
Final Recall .811167/.908167 remains failing historical study floors .90/.95 (not official OSPP numerical rules).
No repair-policy or quality improvement is claimed.

Independent verify audits180000 mutation schedule rows,2400 truth states,manifest/source/dependency binding,
profile exclusive/inclusive accounting and historical result/snapshot receipt equality.
Offline audit cannot reread deleted snapshots or regenerate exhaustive GT; source and original data/raw remain preserved.
Profiler nested scopes,exception unwinding and operation restoration have Release and ASan/UBSan fixtures.
Production Release/Coverage/disabled-backend results are inherited from unchanged bc3e9bd, NOT new suite/coverage runs.
No new whole-Full test or documentation checker result.

Reproduce by copying run-host.py and profile_support.py into a NEW empty result directory on the matching host/repo
with original datasets and build objects preserved. Do not overwrite completed evidence.
Run python3 verify.py for offline audit. Current replay helper is the measured one; no extra timing rerun.
Next: optimize measured route/scan costs at fixed quality/budget,then validate end-to-end in uninstrumented alternating pairs.
100k persistent/interleaved CRUD,fresh Full configuration/SIMD/quality alignment,cold I/O and full deployable package acceptance remain open.
