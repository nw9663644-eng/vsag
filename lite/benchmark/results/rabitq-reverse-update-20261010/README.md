# Reverse RaBitQ Update local transaction journal (2026-10-10)

This optimizes an existing **internal reverse-adjacency path**, not the public default.
Control is production parent77b8543 with whole-state copy transactions; candidate journals only
the replaced encoding and affected outgoing/incoming rows. Both measured overlays enable
incoming adjacency by the identical one-token constructor-default transform (false to true),
recorded and independently checked. Both use NONE protection. Public constructor default stays
false, Add/Remove retain their reverse full-copy fallback, and the first cold CACHED Update
retains copy isolation for the count-array rebuild.

Source evidence: MutableGraphState::UpdateTransactional copied all model/codes/IDs/maps/edges
on reverse updates; UpdatePrepared already localized sources using incoming_[slot]. Existing
remember_row and snapshot/Validate fixtures supply the outgoing rollback approach. Native
RaBitQ Batch4/filter/supplement dispatch and all scoring/formulas/order/model/budgets/API/snapshot
format are unchanged. Reverse rows are saved before count deltas or edge mutations; failure
restores rows by swaps and valid counts from restored incoming cardinalities, without allocating.
The known memory totals now include reverse vector payload/capacity, previously reported only
separately; these totals are not allocator-inclusive RSS or transient journal memory.

## Fixed-budget paired measurements

10k GIST960/Cohere768,600 preserved queries,k10,degree16,maintenance ef128,query ef512,CPU0,
one thread,three full-ID passes of true changed whole-vector Update only (30000 updates/builder).
Three alternating-order pairs per dataset,12 fresh builders. No Remove/Add operations were
timed here; no claim of public-default,query,Full or generic speedup.

| Dataset | Full-copy Update block (ms) | Local journal (ms) | Change |
|---|---:|---:|---:|
| gist10k600 | 66776.309 | 11404.673 | -82.92% |
| cohere10k600 | 62684.514 | 9309.281 | -85.15% |

All six pairs show lower Update-block duration in this sample, not a statistical/universal
claim. Each block includes operation timing/loop overhead. summary.json independently derives
per-operation P50/P99 and throughput; rows.json preserves build/load/save/query and external
process-peak RSS. RSS includes input matrices/build/query/load and is not a mutation-only peak.
Both variants retain ordered IDs/hex distances/hits, initial/final query CSV and snapshot SHA
exactly; native Save/Load exact check runs inside each builder. Final Recall@10 remains GIST
0.858667 and Cohere0.935500 for this Update-only workload, below research floors0.90/0.95.
Do not compare these with mixed CRUD .811167/.908167 as an optimization-induced quality gain.

## Validation and replay

Release6/6,ASan/UBSan5/5,fresh scoped coverage5/5,RaBitQ-disabled4/4,format15/tidy15 passed.
New internal failure injection covers500 positions each for NONE,RECOUNT,CACHED cold and warm:
347 observed allocation failures,zero state/rebuild/retry mismatches,plus successful mutations.
Existing public fixture covers another6000 positions. An initial test-only exception-escape lint
failure was fixed by catching fixture setup/validation failures at main; original log retained,
all final validation rerun. No production change after timing. Scoped Lite coverage2887/3032=95.22%;not whole Full coverage.

python3 lite/benchmark/results/rabitq-reverse-update-20261010/verify.py
audits360000 Update rows,14400 truth intersections,quantiles,throughput,paired exact results,
dependency/header bindings,validation exits,fresh coverage union and all hashes without rerunning
experiments. raw.tar.gz preserves actual measured runner,original/compiled headers,patch,adapter
compile/link commands,LD bindings,source receipts,query/truth/latencies and validation logs.
run-host.py is syntax-checked only after pinning archived candidate; replays require retained
dataset/source/build dependencies,output helper copy and compatible native AVX configuration.
Large replacements are reproducibly generated from retained base and recipe; only new RAM
snapshots were removed after exact load and SHA receipts. No old source/data/raw/binaries deleted.

100k,true interleaved CRUD,reverse Add/Remove local journals,public-path memory/time decision,
fresh native Full aligned configuration/SIMD/quality,cold-I/O and complete deployment package
acceptance remain open. PR2904/2926 are not updated.

## Boundary summary

This is an internal-path structural optimization; public defaults and project acceptance remain
unchanged. See the Chinese design note for rollback,cache and memory boundaries.
