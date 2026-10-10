# RaBitQ structural incoming-guard factorial (2026-10-10)

The actual internal graph state adds two optional stage flags to
ConfigureIncomingProtection(mode, protect_add, protect_remove), both false by
default. Public RaBitQBackend remains NONE. This is an experimental quality
candidate, not a new public API/configuration or default adoption.

Source evidence is the existing Lite FP32/FP16 GraphBackend::Add/ensure_incoming
and Remove/repair path, NOT native Full HGraph. It ensures incoming connectivity
for a new slot and repairs affected orphan targets. RaBitQ previously adapted
that guard only after Update. This study separates the missing Add and Remove
stages under unchanged degree/model/search budget.

After Add/link, the optional guard checks the new slot. After Remove compaction
and existing repair, the optional guard checks sorted unique affected targets,
skipping targets outside the current slot range. The same local rule selects a
farthest replaceable edge only when its displaced target has another incoming
edge; no degree increase, full reverse index or unconditional old-neighbor
retention is added. Cached count deltas and mutation journals are reused.
Stage flags/counts are runtime-only, not persisted. Every default stage is off.

## Frozen factorial replay

GIST/Cohere10k;600 previously observed queries each, k10, degree16,
construction/maintenance ef128, query ef512, CPU0, threads1. Three full-ID passes
of changed Update/Remove/re-add of the changed row,90,000 calls per process.
Same preserved bases, replacement recipe and direct-difference FP64 truth.
The fresh control uses the9b915c5 CACHED Update-only library. Three new isolated
libraries add Add-only, Remove-only, or both stage guards. One process per case,
eight builders total. GIST order control/add/remove/both; Cohere reverse order.
No concurrent validation builds. This is not a native Full comparison or blind
holdout. All timing comparisons below use these fresh controls, not old runs.

| Guard stages beyond Update | GIST final Recall | Cohere final Recall | GIST mutation ms | Cohere mutation ms |
| --- | ---: | ---: | ---: | ---: |
| Neither (control) | .811667 | .908000 | 27111.656739 | 23933.491018 |
| Add only | .845167 | .919667 | 28479.628376 | 25158.894495 |
| Remove only | .814667 | .910333 | 27393.547664 | 24611.784929 |
| Both | .847500 | .922000 | 28845.142099 | 24722.774810 |

Both yields215/84 additional truth hits (+3.583/+1.400 percentage points).
Per-query wins/losses/ties are175/33/392 (GIST),74/5/521 (Cohere).
Add-only contributes201/70 hits; Remove-only18/14 hits. These are descriptive
factorial results, not a sole-cause proof or corrected statistical significance.
Repeated observed queries and multiple candidates limit generalization.

Both increases mutation block6.39%/3.30%; throughput3319.61→3120.11 and
3760.42→3640.37 calls/s. The block includes wrappers/checks/timers, not a kernel.
Query costs also increase: GIST P50/P99 406.302/456.930→418.652/515.469us;
Cohere410.490/460.840→423.290/522.078us. Do not present shorter/lower-quality
control queries or this quality improvement as a query-speed win.
Operation quantiles, build/save/load/snapshot/peak details are in rows.json and
independently recomputed summary.json. Snapshot sizes remain11284416/9363552
bytes; whole-process peaks control/both219484/219528 and176716/176552KiB,
not a cold-load/deployment-memory claim.

Initial hit and ordered ID/hex-distance CSVs are byte-identical across all stages.
Final graph snapshots/results deliberately differ. Each builder's native
Save/Load checks reproduce its own exact ordered IDs/distances.
Both final recalls still fail .90/.95 study targets (not official OSPP numbers).
No default adoption,100k acceptance, interleaved reads, cold I/O or native Full
advantage is established. Update-only prior studies use a different protocol.

## Safety and audit

Final Release CTest6/6; both-guard ASan/UBSan5/5 including warmed allocation
failures; restored-default ASan/UBSan5/5; fresh coverage CTest5/5;
RaBitQ-disabled CTest4/4; clang-format15 dry-run and clang-tidy15 including
Lite headers/allocation test passed. Golden tests cover24 configurations:
dim1/17/128 × reverse adjacency on/off × four stage selections. Every step
compares CACHED/RECOUNT actual degrees, snapshots and queries through120 Updates,
Remove/Add interruptions, failure/retry, middle/last deletion to empty,
65 Add/Update regrowth and disabling. All successful structural paths retain
valid cache accounting; public default is tested separately.

The warmed both-guard allocation suite explores6000 positions across3 storages
and4 operations. RaBitQ actual failures Add50/Update71/Remove39/Build192 all
have zero changed-after-failure, invalid snapshot or escaped exceptions;
retry continues with a changed Update and validated Save/Load.
Fresh coverage Lite2832/2977=95.13%, compiled shared SIMD233/249=93.57%,
combined3065/3226=95.01%, NOT whole Full VSAG coverage. Node document checker and
native Full suite not run. Post-timing edits only clarify one production comment
and flatten the golden configuration loop with identical24 cases/order;
measured and final source hashes/full text are recorded separately.
Default library SHA remains identical before/after those nonfunctional edits.

python3 verify.py audits all artifacts/member SHA,720,000 operation schedules,
9600 initial/final truth intersections, paired hit deltas, initial byte equality,
operation/query quantiles and throughput,10 validation exits and fresh raw gcov.
It does not rerun exhaustive truth or directly inspect deleted RAM snapshots.
Original queries/truth/receipts, old/new headers, adapter build/ldd/argv/environment
and validation logs are archived. Large replacements are reproducible from
preserved bases/recipe/SHA, not falsely claimed archived. Isolated candidate
libraries were built in RAM; complete source/commands/hashes persist in raw.

Host replay from the matching repository: copy run-host.py to a NEW empty result
directory, invoke it from the repository. It requires the preserved9b915c5
control library, matching Release objects/runner, bases, frozen query archive and
cached NumPy paths. It rebuilds all three isolated stage libraries, persists
compact evidence after each builder and keeps preparation/runs within one SSH
session. It refuses completed rows.json. This is host-specific, not portable Full
acceptance. Only19 generated gcda and new successfully checked/hashed RAM
snapshots were removed; source/data/original results preserved.

Next: investigate targets orphaned by Add::link edge eviction, since the new-slot
guard does not protect every displaced old target. Check routing/quality with
fixed budgets and transaction rollback before considering further adoption.
Then100k, new/native Full alignment and cold-I/O acceptance remain required.
