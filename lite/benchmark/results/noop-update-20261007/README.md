# Identical graph updates preserve topology, 2026-10-07

Source parent b487ff8 plus this implementation/test/documentation change.
Graph Update previously searched/replaced neighbors even when input stored values
were identical, changing adjacency and snapshots. After normal validation/ID lookup,
FP32 compares complete float bytes, FP16 compares valid encoded bits; identical
stored representation returns success before nearest/link/repair work. This preserves
existing topology, not a tolerance threshold or a repair/rebuild request.

FP32 signed zeros are different byte representations and still written. FP16 inputs
that round to identical stored bits are no-ops, but encoding/range checks still run;
FP16 may still allocate its temporary encoded vector. Null/NaN/Inf/wrong dimension,
missing IDs and FP16 overflow remain errors. Real stored-value changes retain the
existing incoming-target repair. BruteForce behavior, budgets, storage format, Full,
third-party code and concurrency support are unchanged.

## Tests and public contract

Public API regression on FP32/FP16 graph snapshots fails on pre-change library and
passes after:56 assertions, including exact snapshot invariance, malformed inputs,
missing IDs, FP32 signed zero, FP16 equivalent representation/overflow, actual0.25
change and exact self-query. Prior outgoing-target regression still covers changed
FP32/FP16 updates. Same-value Update is not a graph repair request.
BuildGraph only converts BruteForce to Graph; already-graph indices reject it.
The header and English/Chinese website contracts explicitly record these boundaries.

Default Release4/4, diversity Release3/3, ASan+UBSan6/6 pass. Fresh unit-only emitted
Lite cpp/internal-header line coverage964/1067=90.35%, raw gcov JSON retained;
not Full/extern/benchmark/branch coverage. Graph/test/header format15 and graph/test
tidy15 pass; non-user diagnostics suppressed, not whole-repository lint.

## Fixed same-value workload

Cohere10k/768dim normalized FP32,100 observed queries, L2Top10, degree16 and
construction/maintenance/query128. Default OFF only. Same diagnostic runner bound
via LD_LIBRARY_PATH to saved pre-change/post-change libraries. Three processes per
variant/flow,12 total; variant/flow order reverses on odd repeat, CPU0. No simultaneous
build/test/profile. Whole-process user+system CPU includes staging/build, optional
CRUD, quality/SaveLoad/output, with0.01s resolution; not isolated update CPU.
CRUD runs10000 distinct-ID same-vector Update/Remove/Add cycles, all IDs touched.

| Flow | Library | Recall@10 | Median whole-process CPU s |
|---|---|---:|---:|
| build | before | 0.960 | 1.81 |
| build | after | 0.960 | 1.81 |
| build plus same-value CRUD | before | 0.934 | 6.27 |
| build plus same-value CRUD | after | 0.940 | 4.41 |

Selected whole-process reduction29.67%, not a generic Update speedup. Six extra
hits out of1000, still below prior Cohere0.95 floor; observed deterministic regression
set, not new blind acceptance/statistical significance. Initial snapshots remain
byte-identical; mutated topology intentionally differs. All API/count/SaveLoad query
checks pass. First-replicate snapshots remain on host; later generated snapshots
are hashed then removed safely to limit disk use. No big snapshots/binaries committed.
Inherited internal phase trace finishes all10000 cycles without newly orphaned IDs;
this is a recorded input, not a global no-orphan guarantee.

## Actual-changed control

Same initial snapshot and existing native route-probe consumer,1000 distinct-ID cycles
(10% of base), changed Update first coordinate by+0.125, restored Update, Remove, Add.
All1000 changed FP32 coordinate bytes differ from original, checked before execution,
so neither update can take the identity shortcut. Query only after restoration,
query every10 cycles (1:40 query-to-mutation calls), budget128. Three before/after
processes each, order alternates, CPU0;6 total successful runs. Initial/post quality,
counts and internal exact SaveLoad checks pass in each version.

Both libraries end Recall@10=0.957. Mutation-phase CPU medians624.749 before versus
624.339 ms after are essentially unchanged; no meaningful speedup claim. This scope
uses changed/restore values and10% ID fraction, not the same-value100% workload.
The old/new exact neighbor sequences are not exported across control variants; only
native aggregates/sample accounting and each library's own roundtrip are audited.
Changing graph behavior is not bypassed to manufacture the same-value result.

## Remaining work and reproduction

Overall full-ID quality remains open. Next isolate Remove/Add neighbor drift,
retaining long-range routing links while respecting degree/CRUD/persistence costs;
validate with new held-out queries before adopting another topology policy. Do not
raise already-observed budgets or infer all-update benefits from the no-op workload.
No public RaBitQ backend, concurrency feature or in-place rebuild is added here.

Scripts/protocol, source/binary/library/input hashes, ldd, query-neighbor dumps,
CPU CSV, controls, tests and raw gcov are retained. verify.py re-derives fields,
medians, shape/hashes and emitted coverage; it does not reload removed big snapshots.
Use new output roots and recorded binaries to reproduce, do not overwrite original
records. Original Catch2 failure printed raw non-UTF8 snapshot bytes; a lossless raw
gzip and its hash are included, alongside escaped human-readable publication log.
Other logs normalize trailing whitespace and retain original hashes. Initial string
assertion was changed to a boolean comparison only to avoid dumping binary contents;
semantic fail/pass replay uses the same final test binary and explicit libraries.
Only personal experiment/lite-rabitq-next-20260926 is pushed; PRs remain frozen.
