# Reverse RaBitQ Add local transaction journal (2026-10-10)

This optimizes an existing **internal reverse-adjacency Add path**, not public defaults.
Control is parent35d1b3d (local Update journal but full-copy Add/Remove); candidate changes only
reverse Add to journal existing outgoing/incoming rows and roll back the appended slot.
Both measured overlays enable incoming adjacency by the identical one-token default false-to-true
transform, recorded and independently checked. Both use NONE protection. Public default remains
false; reverse Remove and cold CACHED Add retain copy isolation. No quality/graph policy change.

Source evidence: AddTransactional copied the entire state for reverse Add; the non-reverse path
already had row_limit-limited outgoing journaling and append/truncate rollback. This change adds
incoming outer capacity preparation/append and existing incoming-row backups before edge/count
changes, excludes the new slot via the same row limit, and restores old reverse rows/counts before
truncating the appended slot. No new SIMD/scoring/index algorithm; native RaBitQ Batch4/filter/
supplement dispatch, formula, candidate ordering, model,degree/ef,API and snapshot are unchanged.
Rollback preserves logical state,not exact vector capacities. Reverse memory payload/capacity
accounting from35d1b3d remains; this is not an allocator-inclusive or transient-journal RSS claim.

## Fixed-budget paired measurements

10k GIST960/Cohere768,600 preserved queries,k10,degree16,maintenance ef128,query ef512,CPU0,
one thread,three full-ID passes of Remove followed by true changed whole-vector Add:
30000 removals and30000 adds/builder. Three alternating-order pairs per dataset,12 fresh builders.
Update is not timed in this workload. Remove implementation is identical in both variants.

| Dataset | Full-copy Remove/Add block (ms) | Local Add journal (ms) | Change |
|---|---:|---:|---:|
| gist10k600 | 156625.917 | 65534.431 | -58.16% |
| cohere10k600 | 204033.785 | 62390.095 | -69.42% |

| Dataset / operation | Control P50/P99 (us) | Candidate P50/P99 (us) |
|---|---:|---:|
| gist10k600 / Remove | 1812.220 / 7043.596 | 1553.705 / 2655.653 |
| gist10k600 / Add | 2667.221 / 8432.666 | 560.127 / 624.598 |
| cohere10k600 / Remove | 2572.085 / 6606.516 | 1481.067 / 2495.064 |
| cohere10k600 / Add | 3437.696 / 7597.734 | 541.119 / 602.117 |

The table reports the whole Remove/Add block,not Add alone. summary.json independently derives
separate Add/Remove P50/P99 and total throughput from all720000 operation samples; rows.json keeps
all build/load/save/query/snapshot metrics and external process-peak RSS. Process peak includes
input/build/query/load,not a mutation-only peak. Observed changes in Remove/query are not evidence
that their unchanged algorithms were optimized. No public-default,Full or universal/statistical
gain is claimed. Exact paired initial/final ordered IDs/hex distances/hits,query CSV and snapshot
SHA are preserved; each builder runs native Save/Load exact checks. Final Recall@10 remains gist10k600 0.849500, cohere10k600 0.923333;no quality repair,not comparable to Update-only recall as an optimization-induced gain.

## Validation and replay

Release6/6,ASan/UBSan5/5,fresh scoped coverage5/5,RaBitQ-disabled4/4,format15/tidy15 passed.
Internal fault injection tests500 positions per operation and policy across NONE,RECOUNT,CACHED
cold/warm: Add306 observed allocation failures and Update363,zero state/rebuild/retry mismatches.
The updated fixture injects preparation allocations as well and turns on protection stage flags;
these counts are not a performance comparison with the prior fixture. Another6000 public
allocation positions and existing empty-to100 growth/mixed CRUD golden tests remain passing.
No failed product build/test or lint repair in this round. Scoped Lite coverage2906/3047=95.37%;not whole Full coverage.

python3 lite/benchmark/results/rabitq-reverse-add-20261010/verify.py
audits720000 Remove/Add rows,14400 truth intersections,quantiles/throughput,exact paired results,
dependency/header bindings,validation exits,fresh coverage union and hashes without rerunning
benchmarks. raw.tar.gz preserves actual measured runner,original/compiled headers,patch,adapter
compile/link commands,LD binding,source receipts,query/truth/latencies and validation logs.
run-host.py is syntax-checked only after pinning archived candidate; replay needs retained
dataset/source/build dependencies and matching native SIMD configuration. Large replacements are
regenerated from retained base and recipe. Only19 verified generated coverage counters and new
RAM snapshots (after exact load and SHA receipts) were removed; no old source/data/raw/binaries.

Remaining work: reverse Remove local journal,public-path memory/time decision,quality at fixed
budget,100k/interleaved true-value CRUD,fresh native Full aligned configuration/SIMD/quality,
cold-I/O and complete deployment package. PR2904/2926 are not updated; project acceptance is open.
