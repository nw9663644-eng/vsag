# RaBitQ Add displaced-target incoming protection (2026-10-10)

Internal structural candidate on personal experiment/lite-rabitq-next-20260926,
parent f5aa4e3d43bd7fecd476aa7877f3441e5c8d770d. PR2904/2926 are unchanged.
This is a quality/cost study, not a native Full comparison or completed acceptance.

## Source evidence and minimal change

src/lite/rabitq_graph_state.h::link ranks saturated reverse rows by distance,
then drops their farthest edge. The previous Add guard only checked the new slot.
A four-record regression (vectors 0,100,1,2; degree2; add .5) demonstrates that an
old target can lose its only incoming edge. The candidate records old targets
removed by Add's link calls and passes them, after the new slot, to the existing
local incoming protector. AddTransactional keeps all this work inside its journal;
failure invalidates counts and restores rows/ID/code lengths without allocation.
AddTransactional with reverse adjacency retains its existing copy fallback. Direct
Add is internal and does not promise strong rollback; public callers use AddTransactional.

ConfigureIncomingProtection has one further internal false-by-default flag,
protect_add_displaced. Public adapters remain NONE; flags are not persisted.
No API, format, degree, ef, model, SIMD, graph construction or Full defaults change.
Reuse is the existing Lite floating GraphBackend incoming-repair idea, not Full HGraph.
Protection is best-effort when no safe local replacement exists. It is not a
global connectivity or recall guarantee.

## Frozen protocol

10k GIST/Cohere,600 previously observed queries each,k10,degree16,
construction/maintenance128,query512,CPU0,one thread. Three full-ID changed-vector
Update/Remove/Add passes,90000 mutations per builder. Four fresh builders,one
pair per dataset: GIST control then candidate; Cohere reversed. No concurrent
validation builds or benchmark reruns. New-slot/Remove guards are ON in both.
Only displaced-target Add protection differs. Do not use previous timing batches
as this pair's performance control; no blind-query or significance claim.

Both measured adapters compile the current source. Control's new displaced flag
is false; it is not a parent binary. The colocated state headers in the host script
are unused reference copies: quoted lite/rabitq_snapshot.h resolves repository
-I src and includes the repository lite/rabitq_graph_state.h. identity.json and
post-run identical-adapter -MM dependency receipts document this explicitly.
The archived control-state.h is the parent source reference only.
Control final hits and all ordered ID/hex-distance rows are byte-identical to
previous structural-guard both results, independently audited.

| dataset | variant | Recall@10 | CRUD ms | ops/s | final query P50/P99 us | peak KiB |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| GIST | control | .847500 | 27960.031756 | 3218.88 | 424.651/504.640 | 219516 |
| GIST | displaced | .855167 | 28760.826137 | 3129.26 | 415.541/469.060 | 219528 |
| Cohere | control | .922000 | 24120.140056 | 3731.32 | 404.863/451.870 | 176728 |
| Cohere | displaced | .924500 | 24486.984462 | 3675.42 | 402.091/442.111 | 176724 |

GIST gains46 truth hits (61 winning/24 losing/515 tied queries); Cohere gains15
(28/13/559). CRUD block cost rises2.86%/1.52%. Query point estimates improve,
but one pair does not establish repeatable latency improvement. Snapshot bytes
11284416/9363552 are unchanged per dataset; no clear memory advantage.
Initial query hits and ordered ID/hex-distance CSVs are byte-identical across variants;
final graphs differ intentionally. Each builder's native Save/Load validates its
own ordered query results exactly.

Both final recalls still fail study floors.90/.95 (not official OSPP numeric requirements).
Do not default-enable or claim acceptance. Next diagnose remaining missed truth
visitation and edge coverage; orphan repair alone is insufficient. Avoid unconditionally
retaining old neighbors, previously rejected, or increasing ef to conceal losses.
100k persistent changed-vector/interleaved reads,fresh Full SIMD/config/quality alignment
and strict cold I/O remain outstanding.

## Validation and evidence

- Release6/6; displaced-guard ASan/UBSan5/5; restored-default ASan/UBSan5/5.
- Fresh coverage CTest5/5; RaBitQ-disabled4/4; clang-format/tidy15 passed.
- 48 golden configurations: dim1/17/128,reverse adjacency on/off,eight stage combinations;
  actual counts/recount,snapshot and ordered searches agree after every mutation.
  New regression covers direct/transactional Add with/without reverse adjacency.
- 6000 allocation positions across three storages and four operation kinds.
  Actual RaBitQ failures Add50/Update71/Remove39/Build192; zero changed-after-failure,
  invalid snapshots or escaped exceptions. Existing warmed retry/changed-update/load checks pass.
- Fresh Lite2850/2995=95.1586%,shared instantiated SIMD233/249=93.5743%,
  combined3083/3244=95.0370%. This is scoped compiled Lite code,not whole Full coverage.
  Node documentation checker and Full entire suite were not run.

verify.py independently checks360000 operation rows,4800 truth intersections,
raw query/operation quantiles,throughput,initial byte equality,paired query deltas,
previous-control equality,10 validation exits,fresh gcov and hashes. raw.tar.gz
contains90 members,5940416 bytes,including full sources,compact queries/truth,
input recipe/SHA,adapter compile/link/ldd/argv and successful validation logs.
Large replacement matrices are reproducible from preserved base plus recipe/SHA,
not archived. RAM snapshots were SHA-recorded and natively loaded before deleting
only those new snapshots; offline audit cannot directly inspect them afterward.
Measured RAM adapter paths disappeared after the SSH session,so the initial
post-run -MM receipt attempt failed before packaging; identical archived adapter
text was recreated at a new RAM path for dependency-only replay. No benchmark or
product test rerun resulted from this provenance repair. No production edits after timing.

## Replay

Copy run-host.py into a NEW empty result directory and run from this matching repo,
with the preserved host datasets and compile/link objects in identity.json.
It refuses completed rows.json. Input preparation,builds,runs and compact archives
must remain in the same SSH script because RAM files may not persist between sessions.
Do not overwrite the original results. Raw library hashes identify measured bindings,
but RAM libraries are not claimed to persist. SHA256SUMS authenticates canonical artifacts.
