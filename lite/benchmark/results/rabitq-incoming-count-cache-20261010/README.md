# RaBitQ runtime incoming-count cache (2026-10-10)

This is a real internal graph-state change, not a new public option. The public
adapter still uses IncomingProtection::NONE. RECOUNT/CACHED are internal
experimental policies used by golden tests and isolated benchmark libraries.
They adapt floating GraphBackend::ensure_incoming: protect the changed slot and
old outgoing orphan targets, replacing a local farthest edge only when its
displaced target retains another incoming edge. The fixed degree, construction
budget, query budget, model, public API and snapshot format are unchanged.

CACHED lazily builds one uint64_t count per slot, then applies edge-set differences
in sync_incoming and handles direct incoming-edge removals during Update.
Consecutive Updates avoid the prototype's O(N+E) recount on every operation.
Add/Remove invalidate before size/slot changes. Failed journal transactions
invalidate before adjacency rollback; reverse-adjacency copy transactions leave
the original cache intact on failure. The next successful Update rebuilds as
needed. Counts are runtime-only, never persisted. GetMemoryUsage includes their
logical/capacity bytes. NONE allocates no count vector initially, but the new
members/branches still exist: no zero-overhead claim.

The cache requires 8N logical bytes after its first Update: 80,000 bytes at10k
and 800,000 at100k (capacity may grow). Disabling retains allocated capacity.
Mixed Add/Remove/Update churn can require repeated full recounts and has NOT
been measured here. A full reverse-edge index is not added.

## Frozen experiment

GIST/Cohere10k, 600 previously observed queries each, k10, degree16,
construction/maintenance ef128, query ef512, CPU0, one process per case.
Three full-ID whole-row changed-value passes produce30,000 Updates per process;
Cohere replacements are re-normalized. Identical preserved base, model and
changed-data truth are used for RECOUNT and CACHED. Query/truth receipts are in
raw.tar.gz; large replacements are regenerated from preserved base + exact recipe
and SHA, not falsely claimed archived.

| Dataset | Recount mutation block ms | Cached ms | Change | Final Recall@10 |
| --- | ---: | ---: | ---: | ---: |
| GIST10k | 18326.886468 | 15432.329161 | -15.79% | .897667 |
| Cohere10k | 15657.821598 | 12760.902898 | -18.50% | .951500 |

Both initial/final hit CSVs and ordered ID/hex-distance CSVs are byte-identical
between policies; final snapshot SHA is identical per pair. Save/Load exact-result
checks ran in all four builders. summary.json recomputes Update P50/P99,
mutation-block throughput, query quantiles/recall, snapshot bytes and whole-process
peak RSS from raw evidence. The block includes wrapper/check/timing costs, not
only a kernel. GIST ran recount first; Cohere cached first. Single pairs do not
establish statistical significance or universal speed improvement.

Quality is unchanged from the protected prototype, not from unprotected default:
GIST remains below the .90 study floor; Cohere reaches the .95 study floor.
Those floors are study targets, not official OSPP numbers. Default adoption and
overall acceptance remain unsupported. This is not a Full VSAG comparison,
100k result, cold-load study, query-speed claim, or mixed-workload benefit.

## Validation and failures

Final Release CTest6/6; cached-adapter ASan/UBSan5/5 including allocation rollback;
restored-default ASan/UBSan5/5; fresh coverage CTest5/5; RaBitQ-disabled CTest4/4.
clang-format15 dry-run and clang-tidy15 with Lite header filter passed.
The new golden test covers dimensions1/17/128, reverse-adjacency on/off,
120 Updates with two Remove/Add interruptions, snapshot/query identity after
each change, actual cached-degree validation, failure/retry, policy validation,
memory accounting and disable. Continuous120 Updates rebuild three times;
a failed journal transaction triggers another rebuild, while copy rollback
correctly preserves its original valid cache.

Fresh gcov JSON coverage: Lite2799/2943 (95.11%), compiled shared SIMD233/249
(93.57%), combined3032/3192 (94.99%). The expanded test instantiates more shared
SIMD lines than earlier reports. This is scoped Lite/public-header/shared-kernel
coverage, NOT whole Full VSAG coverage. Raw gcov is in coverage-raw.tar.gz.

The first new test used the wrong prepared-encoding API and failed compilation.
A later test incorrectly expected the copy-transaction cache to be invalidated
and failed one assertion; the expectation was corrected (product semantics
unchanged). Failed logs and final successful logs are preserved. Timed production
header is unchanged; the final unit-test hash is recorded separately in
validation.json. The restored default library SHA matches identity.json.
Node document checker and whole native Full test suite were not run.

## Reproduction/audit

From this directory: python3 verify.py. It verifies all artifacts/member SHA,
120,000 operation schedules,4800 raw truth intersections, nearest-rank quantiles,
paired byte equality, snapshot receipts and fresh gcov counts without extraction
or benchmark rerun. It does not independently redo exhaustive dataset truth or
read deleted RAM snapshots; those boundaries are explicit.

Host replay: from the measured repository, with its matching Release objects and
builder, run python3 lite/benchmark/results/rabitq-incoming-count-cache-20261010/replay-host.py NEW_OUTPUT.
The preserved source bases, frozen query archive and cached NumPy paths must exist.
Preparation/build/run must stay in the same SSH session. It builds isolated
adapters from build-variants.json, never edits the default adapter, refuses an
existing output directory and writes compact input receipts; snapshots/large
replacement matrices stay in RAM. It is a new replay helper, syntax-checked but
not rerun for this completed measurement; exact originally executed per-run
argv/environment/ldd and build commands are already archived.

Only141 verified idle, rebuildable .o files (146,073,464 bytes) were removed
from build-lite-baseline-asan to unblock builds; source, executables, libraries,
data and original results were preserved. The NUL path manifest is archived.
Next: fixed-budget quality repair and cheaper mixed-CRUD accounting, then100k,
latest native Full quality/configuration alignment and cold-I/O acceptance.
