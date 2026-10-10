# Current RaBitQ reverse adjacency tradeoff (2026-10-10)

No production C++ change in this experiment. Both adapters are byte-identical to current
public RaBitQBackend and use the same06ab591 state header. Control keeps reverse=false;
candidate changes only that constructor default to true. Protection stays NONE.
Previous Update/Add/Remove journals exist in both variants. Public default remains false.
This is NOT the preceding old-copy versus local-Remove comparison.

## Fixed-budget mixed CRUD

10k GIST960/Cohere768,600 preserved queries,k10,degree16,maintenance128,query512,CPU0,one thread.
Three full-ID passes of true whole-vector Update/Remove/Add per builder,90000 operations.
Three alternating pairs per dataset,12 fresh builders;1080000 measured operations.
Initial/final queries are outside mutation loops; this is not interleaved-query acceptance.
Native public Save/Load verifies exact IDs/distances for every builder.

| Dataset | Reverse off/on CRUD ms | Change | Final recall off/on | Builder peak KiB off/on |
|---|---:|---:|---:|---:|
| gist10k600 | 25007.966 / 20511.163 | -17.98% | 0.811167 / 0.811167 | 219536 / 219528 |
| cohere10k600 | 22422.324 / 17637.928 | -21.34% | 0.908167 / 0.908167 | 176756 / 176704 |

| Dataset/operation | Off P50/P99 us | On P50/P99 us |
|---|---:|---:|
| gist10k600/update | 381.352 / 1382.599 | 310.504 / 1359.671 |
| gist10k600/remove | 110.518 / 181.326 | 18.310 / 88.917 |
| gist10k600/add | 267.354 / 306.143 | 270.933 / 308.804 |
| cohere10k600/update | 338.482 / 1174.773 | 266.214 / 1135.045 |
| cohere10k600/remove | 121.407 / 183.146 | 26.589 / 88.378 |
| cohere10k600/add | 238.555 / 272.634 | 240.845 / 273.133 |

## Same-snapshot load and resident memory

Each builder snapshot is loaded by BOTH flags,three fresh processes per flag (72 loads).
This isolates flag cost from graph topology. Snapshot inputs are RAM/page-cache warm.
For each snapshot the two loaders have identical model/codes/IDs/outgoing edges/map entries;
known-byte difference equals incoming logical/capacity bytes exactly.
Known bytes include vector headers/payload/capacity,not hash-map node/allocator/transient bytes.
Resident increment is post-load /proc/self/statm minus that fresh process baseline.
ru_maxrss is retained raw but can include launcher inherited HWM; it is not loader-only peak.
Whole builder peak also includes base/replacements/build/query and two live indexes on load.
Consequently its small deltas cannot establish mutation-only memory superiority.

| Dataset | Known capacity off/on B | Incoming B | Resident increment off/on KiB | Warm internal load off/on ms |
|---|---:|---:|---:|---:|
| gist10k600 | 11444320 / 12964320 | 1520000 | 13766 / 16776 | 6.122 / 8.637 |
| cohere10k600 | 9523456 / 11043456 | 1520000 | 11970 / 14900 | 5.355 / 7.978 |

All measured incoming edges equal outgoing edges; exact initial/final result comparisons
and per-query recall deltas are in summary.json. No assumed equality or quality improvement.
Fixed-budget recall still fails research floors; no public-default adoption is justified solely
by this speedup. Binary/snapshot format is unchanged; overlay ELF sizes are not package sizing.
Remaining100k,long interleaved CRUD,fresh aligned Full,cold I/O and complete package remain open.

## Evidence and replay

python3 lite/benchmark/results/rabitq-reverse-tradeoff-20261010/verify.py
independently checks1.08M operation schedule/quantiles,14400 truth intersections,72 load probes,
same-snapshot logical/capacity deltas,paired recall/results,header/dependency binding and hashes.
Release6 repeated this round;new probe format15/tidy15 and Python syntax checks pass.
Production source unchanged: sanitizer/coverage/OFF results are inherited from06ab591,not rerun.
Setup mode spelling corrected before timing;interrupted setup log retained.
After timing,RAM probe executables were rebuilt from captured headers for malformed-input
checks only;initial executable-presence assertion stopped before those checks,no timing rerun.
Only newly generated RAM snapshots were unlinked after exact native load and SHA receipts.
No old source,data,raw results or shared artifacts were deleted;PR2904/2926 untouched.

run-host.py pins measured header from raw.tar.gz for replay;retained data/object dependencies
and matching SIMD are required. Final replay is syntax-checked,not rerun.

Decision: retain public reverse=false;next investigate incoming layout/allocator footprint
without losing local mutation/exception guarantees,then fixed-budget graph quality.
