# Reverse RaBitQ Remove local transaction journal (2026-10-10)

This optimizes the existing **internal reverse-adjacency Remove path**, not public defaults.
Control is parent2364d52 (local Update/Add journals but full-copy reverse Remove); candidate
changes only reverse Remove to affected outgoing/incoming row backups and shrink/restore rollback.
Both overlays enable incoming adjacency by the identical single-token false-to-true transform,
recorded and independently checked. Both use NONE protection. Public default stays false;
cold CACHED Remove retains copy isolation. No quality or graph-policy change.

Source evidence: RemoveTransactional copied the entire reverse state. The existing non-reverse
path already backed up deleted/moved codes, outgoing rows, and an extracted map node.
Official HGraph graph_force_remove_one uses incoming/outgoing neighborhoods to locate impacted
nodes, but its label/tombstone/code-slot semantics differ; its removal routine is not transplanted.
This change snapshots incoming deleted/last/removed-target rows before count deltas and snapshots
rows before erase/renumber. Rollback restores outer sizes before swapping saved reverse rows,
restores valid counts from original incoming cardinalities, and reuses the existing node handle.
The original capacity remains after shrinking, so restoring sizes needs no allocation.
Logical state, not exact vector capacities, is preserved. No scoring/SIMD/formula/model/order/
degree/ef/API/snapshot changes. Reverse memory accounting is unchanged, not transient-journal RSS.

## Fixed-budget paired measurements

10k GIST960/Cohere768,600 preserved queries,k10,degree16,maintenance ef128,query ef512,CPU0,
one thread,three full-ID passes of Remove followed by true changed whole-vector Add:
30000 removals and30000 adds/builder. Three alternating-order pairs per dataset,12 fresh builders.
Update is not timed in this workload. Add implementation is identical in both variants.

| Dataset | Full-copy Remove/Add block (ms) | Local Remove journal (ms) | Change |
|---|---:|---:|---:|
| gist10k600 | 65928.356 | 12563.964 | -80.94% |
| cohere10k600 | 62249.974 | 10340.707 | -83.39% |

| Dataset / operation | Control P50/P99 (us) | Candidate P50/P99 (us) |
|---|---:|---:|
| gist10k600 / Remove | 1571.716 / 2730.809 | 38.520 / 1169.654 |
| gist10k600 / Add | 553.449 / 619.496 | 292.074 / 368.323 |
| cohere10k600 / Remove | 1489.659 / 2506.485 | 30.089 / 1042.167 |
| cohere10k600 / Add | 527.149 / 589.078 | 250.245 / 289.165 |

The table reports the whole Remove/Add block,not Remove alone. summary.json independently
derives separate Remove/Add P50/P99 and total throughput from all720000 operation samples;
rows.json retains build/load/save/query/snapshot metrics and external process-peak RSS.
Process peak includes input/build/query/load,not mutation-only memory. Any Add/query timing
change is not evidence of optimizing their unchanged algorithms. No public-default,Full,
universal or statistical gain is claimed. Exact paired initial/final ordered IDs/hex distances/
hits,query CSV and snapshot SHA are preserved; every builder runs native Save/Load exact checks.
Final Recall@10 remains gist10k600 0.849500, cohere10k600 0.923333;no quality repair,not comparable to Update-only recall as an optimization-induced gain.

## Validation and replay

Release6/6,ASan/UBSan5/5,fresh scoped coverage5/5,RaBitQ-disabled4/4,format15/tidy15 passed.
Remove fault injection covers middle,last,single-node deletion across NONE,RECOUNT,CACHED
cold/warm:6000 allocation positions,692 observed allocation failures,zero snapshot/cache-rebuild/
retry/continued-mutation mismatches. Mutual deleted/moved edges and a common source are covered.
After each attempt and retry,Add and true Update are checked against copied direct-mutation
golden states,including regrowth after deleting the sole node. Existing reverse Add/Update
and6000 public allocation positions plus mixed/growth/removal golden tests remain passing.
Initial test-only narrowing-conversion warnings were fixed before timing; the failed lint log is retained. Final checks pass. Scoped Lite coverage2924/3065=95.40%;not whole Full coverage.

python3 lite/benchmark/results/rabitq-reverse-remove-20261010/verify.py
audits720000 Remove/Add rows,14400 truth intersections,quantiles/throughput,exact paired results,
dependency/header bindings,validation exits,fresh coverage union and hashes without rerunning
benchmarks. raw.tar.gz preserves actual measured runner,original/compiled headers,patch,adapter
compile/link commands,LD binding,source receipts,query/truth/latencies and validation logs.
run-host.py is syntax-checked only after pinning archived candidate; replay needs retained
dataset/source/build dependencies and matching native SIMD configuration. Large replacements
are regenerated from retained base and recipe. Only19 verified generated coverage counters and
new RAM snapshots (after exact load and SHA receipts) were removed; no old source/data/raw/binaries.

Remaining work: public-path memory/time decision,quality at fixed budget,100k/interleaved
true-value CRUD,fresh native Full aligned configuration/SIMD/quality,cold-I/O and complete
deployment package. PR2904/2926 are not updated; project acceptance remains open.
