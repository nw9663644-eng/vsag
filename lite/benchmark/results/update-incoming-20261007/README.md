# Update repairs former outgoing targets, 2026-10-07

Source parent a62fc0c plus the recorded implementation/test change.
GraphBackend::Update cleared incoming links to the updated slot, replaced its outgoing
list, and repaired former incoming sources. Former outgoing targets were omitted when
their only incoming edge disappeared. Remove already accounts for both directions.
Bookkeeping was consistent: this is missed best-effort connectivity repair, not
invalid-slot, corrupted-snapshot or memory-safety evidence.

## Reproduction and minimal fix

Valid four-node graph, degree2/budget128, vectors0/100/1/2. Slot0 originally points
to1 and2; node1 has only that incoming edge. Updating0 selects closer2/3 and drops
0->1. Old FP32 test fails IncomingLinkCountAt(1)>0 with0. Corrected test covers
same-value0/changed0.25 in FP32/FP16, incoming-table consistency, degree bound,
full-budget search and filtering:108 assertions pass. The initial test compile
used a float instead of a pointer; fixed before reproducing the library failure.
The first no-tests-matched log is not product failure evidence; the real failure
is regression-before-final.log.

Independent internal-backend phase trace restores the existing Cohere10k initial
snapshot and executes10000 distinct-ID Update/Remove/Add cycles. Cycle97 Update
ID4527 first creates zero-in-degree ID3626, a former outgoing target. Zero-in
nodes change0 to1. Trace checks each stage across compaction, stops at first new
orphan. After fixing, the same trace finishes all10000 cycles without a new orphan.
This is one recorded input, not a global no-orphan guarantee for arbitrary graphs.

Fix: call existing ensure_incoming for former outgoing targets after normal repair.
It does not refill/rebuild unaffected outgoing lists, add an algorithm, change
budgets, storage or snapshot format. Safe-edge selection can return without repair
if no safe local replacement exists. Exceptions retain existing tl::expected
translation. Full/third-party code is untouched.

## Public API verification and cost

Same diagnostic runner bound explicitly to saved pre-fix/rebuilt post-fix libraries,
with hashes/ldd. CPU0, normalized Cohere10k/768dim,100 observed queries, L2Top10,
degree16/construction/query128. Three processes per variant/flow,12 runs. Build-only
versus build plus10000 same-vector Update/Remove/Add cycles touching all IDs.
No concurrent build/test/tidy/profiler. CPU is whole-process user+system, not isolated
mutation time, with0.01s rounding.

| Flow | Library | Recall@10 | Whole-process median CPU s |
|---|---|---:|---:|
| build | before | 0.960 | 2.03 |
| build | after | 0.960 | 1.79 |
| build plus CRUD | before | 0.933 | 6.39 |
| build plus CRUD | after | 0.934 | 6.25 |

Build snapshots/results remain byte-identical across variants. Mutation snapshots
intentionally change. All query/count/API and exact SaveLoad checks pass.
Endpoint gains ONE hit out of1000, still below prior Cohere0.95 floor; no general
or statistical quality-gain claim. This fixes the orphaning omission, not the
complete recall problem. CPU medians are descriptive, not a speedup promise;
even untouched construction shows variation/code-generation effects across builds
and normal run conditions.

## Slot-order control and remaining problem

After-fix CRUD snapshot is reordered to original external-ID slot order. All vector
bytes and ordered stored edges by ID remain identical, independently checked.
Only physical slot mapping changes. This jointly changes ring/entry/tie-order,
not only ring. Scalar/native budget128 recall remains0.934;100 per-query hits
unchanged (wins0/losses0/ties100). This control does not explain/recover this
recorded loss; it does not prove slot order never matters elsewhere.

Original graph has160000 stored edges; post CRUD160000, but only90392 original
ID-based edges remain (56.495%). All original vector bytes remain unchanged.
This demonstrates topology drift with restored content, not proof every replaced
edge hurts recall. Next investigate unnecessary same-vector Update rewiring and
neighbor replacement during Remove/Add using fixed budgets and new held-out
queries. Do not assume orphan count/slot permutation alone solves the problem,
or retune these observed queries to hide the loss.

## Verification and evidence

After final FP32/FP16 regression: default Release4/4, diversity Release3/3,
ASan+UBSan6/6 pass. Fresh unit-only emitted Lite source/internal-header coverage
959/1062=90.30%, raw gcov JSON retained; not Full/extern/benchmark/branch coverage.
Graph/test/standalone trace pass format/tidy15; non-user header warnings suppressed,
not whole-repository lint. Existing randomized CRUD/filter/persistence/FP16 pass.
The trace reuses repository FP32 snapshot reading and existing internal Backend
introspection, not a new public API. Source/build command is recorded separately.

First-replicate snapshots/libraries remain on host. Later generated snapshots are
hashed/checked then removed to limit disk use. Big files/binaries are not committed.
verify.py recomputes CPU and emitted coverage, checks query outputs, phase/control
records and publication hashes; it cannot re-read absent snapshots. Raw logs have
separate hashes from normalized publication text. Scripts encode host paths;
reproduce using NEW output roots/recorded binaries, never overwrite old evidence.
Only personal branch is pushed; PR #2904/#2926 remain frozen.

Publication checks caught host-probe default formatting and one compiler-log
trailing blank. Repository formatting, final probe rebuild/tidy and identical
before/after trace replay passed; original source/log hashes remain recorded.
