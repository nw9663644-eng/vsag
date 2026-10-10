# RaBitQ incremental counts across successful structural CRUD (2026-10-10)

The real MutableGraphState now preserves a valid runtime incoming-count cache
across successful Add and Remove. Public RaBitQBackend still uses NONE; both
benchmarked libraries use the same experimental CACHED incoming-protection policy.
Control is the e3d4d89 library, whose Add/Remove invalidate that cache. Candidate
maintains it. This does not change protection targets/selection, graph degree,
model, public API, traversal budget or persistence format.

Source evidence: Add changes edges through replace_neighbors/link/sync_incoming;
Remove subtracts the removed row's outgoing edges, discards incoming edges to its
slot, remaps the last slot into that position, then uses the existing repair path.
Candidate appends a zero count before Add edge deltas. Remove decrements removed
outgoing targets, clears the deleted count, moves the already-adjusted last count
during compaction and pops its tail before repair deltas. No second graph-wide
recount or full reverse-edge index is added. Failed journal transactions invalidate
before rollback; copy-transaction failure leaves the original cache intact.
A subsequent Update rebuilds if invalid. Allocation growth is reserved before
transactional publication. Counts remain runtime-only, with unchanged8N logical
storage (capacity growth is accounted); NONE initially allocates none.

## Fixed mixed replay

GIST/Cohere10k, each600 previously observed queries, k10, degree16,
construction/maintenance ef128, query ef512, CPU0, threads1. Three full-ID passes
of changed Update, Remove and re-add of the same changed row:30,000 cycles,
90,000 mutation calls per process. Same bases/recipe/exact changed-data truth.
One pair per distribution, control first on GIST/candidate first on Cohere.
Validation builds/tests ran after all measurements, not concurrently.

| Metric | GIST control → candidate | Cohere control → candidate |
| --- | ---: | ---: |
| Mutation block ms | 29915.096948 →26909.484528 (-10.05%) | 27813.465568 →24584.332523 (-11.61%) |
| Update P50 us | 567.667 →468.371 | 515.969 →409.691 |
| Update P99 us | 1538.767 →1435.129 | 1382.559 →1265.793 |
| Mutation block ops/s | 3008.51 →3344.55 | 3235.84 →3660.87 |
| Final Recall@10 | .811667 →.811667 | .908000 →.908000 |

The main saving is the next Update no longer recounting after successful
Remove/Add. Remove/Add timings are not uniformly improved: Cohere Remove P50
121.917→123.838us, P99 186.716→189.035us; GIST Add P50 271.884→272.644us.
All operation/query quantiles and peak RSS are in independently recomputed
summary.json. This block includes wrappers/checks/timers, not just a kernel.
Single pairs cannot establish statistical significance or universal speed gains.

Initial/final hit CSVs and ordered ID/hex-distance CSVs are byte-identical;
paired final snapshot SHA is identical. Each builder performed native exact-result
Save/Load checks. Snapshot bytes remain11284416 (GIST)/9363552 (Cohere).
Whole-process peak KiB is219400→219540/176740→176728, not a deployment-load-memory
benefit. This is a comparison with old Lite, NOT native Full.

Both mixed-maintenance recalls still fail .90/.95 study targets. These are not
official OSPP numeric floors. The prior Update-only .897667/.9515 study used a
different operation protocol; do not mix those results with this combined replay.
Default protection remains disabled. This change fixes experimental bookkeeping
cost, not connectivity quality or acceptance. No100k, cold-I/O, interleaved reads,
new native Full or public-default performance benefit is established.

## Tests and audit

Final Release CTest6/6; warmed cached-adapter ASan/UBSan5/5;
restored-default ASan/UBSan5/5; fresh coverage CTest5/5;
RaBitQ-disabled CTest4/4; clang-format15 and clang-tidy15 with Lite header filter.
Golden tests cover dim1/17/128, reverse adjacency on/off,120 Updates with two
Remove/Add interruptions, every-step actual cached-degree validation and
snapshot/query equality, failure/retry, then middle/last removals to empty and
65 Add/Update regrowth operations (capacity growth). Successful structural CRUD
does not add a rebuild: the continuous120 Update sequence now rebuilds once,
versus three times previously. Journal failure adds a rebuild; copy failure
preserves its original valid cache.

Allocation tests now prewarm RaBitQ with a changed Update, inject Add/Update/Remove
failures, retry and continue with another changed Update and validated snapshot
load. Cached-adapter test explores6000 positions across3 storages/4 operations;
RaBitQ actual failures Add45/Update71/Remove38/Build192, all with zero
changed-after-failure, invalid snapshot or escaped exceptions.
Fresh coverage: Lite2817/2963=95.07%, compiled shared SIMD233/249=93.57%,
combined3050/3212=94.96%. This is scoped Lite/public headers/instantiated kernels,
NOT whole Full VSAG coverage. Node document checker and native Full suite not run.
A premature gcov collection gate expected12 completed commands while validation
was still running; no extraction occurred. After all10 commands finished, the
gate was corrected and fresh raw gcov collected. No product/test failure occurred.

python3 verify.py checks artifact/member SHA,360,000 scheduled mutation rows,
4800 raw truth intersections, nearest-rank operation/query quantiles, throughput,
paired snapshots/results, all10 validation command exits and fresh gcov counts.
It does not rerun exhaustive ground truth or directly read deleted RAM snapshots.
Large replacement matrices are reproducible from preserved bases/recipe/SHA,
not claimed archived. Exact original argv/environment/ldd, old/new source header
and isolated-adapter build provenance, original query/truth receipts and all logs
are archived. Sources/data/original results preserved; only19 generated gcda were
cleared and new RAM snapshots deleted after successful checks/hash.

Host replay from the matching measured repository (recorded libraries/objects,
source bases and cached NumPy paths required): create a NEW_OUTPUT directory,
copy run-host.py and identity.json there, then invoke python3 NEW_OUTPUT/run-host.py
from the repository. It refuses completed rows.json and keeps dataset preparation
and all builders in one SSH session. This is host-specific, not a portable Full
benchmark; exact per-run commands in raw archive remain authoritative.

Next focus: fixed-budget routing/maintenance quality, with separate Update-only
and Remove/Add diagnoses; no parameter increase to mask recall loss. Then100k,
latest native Full configuration/SIMD/quality alignment and cold-load acceptance.
