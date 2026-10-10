# RaBitQ cached incoming-safe link pruning (2026-10-11)

Source evidence: floating src/lite/graph_backend.cpp::link scans distance-ranked edges
from farthest to nearest,avoiding removal of an existing target's sole incoming edge.
Adapt exactly that incoming-count gate to encoded MutableGraphState::link. New edges can
be dropped if their target already has another incoming edge;old edges require indegree>1.
If no safe edge exists,retain the original farthest-edge fallback. This is NOT diversity
pruning or proof that every orphan/connectivity loss is eliminated.

Internal ConfigureIncomingProtection gains a final protect_link=false argument,valid only
with CACHED. Count preparation occurs before inserting the new link. The existing incremental
count synchronization and rollback paths remain. No new reverse index or pairwise distances.
Public adapter remains NONE,reverse=false. API,degree/ef,model/rotation/scoring and VSAGLQ01v1
remain unchanged. This is internal opt-in experimental code,not enabled public behavior.

## Frozen paired quality/cost study

Parent22fa22c control versus candidate;BOTH adapters CACHED with all post-Add/Remove flags
false. Only candidate enables link protection. Thus this is NOT public NONE versus CACHED,
and not the older incoming-count-cache speed study. Both retain existing Update protection.
10k GIST960/Cohere768,600 previously observed queries,k10,degree16/maintenance128/query512,
CPU0,BLAS/OMP/MKL1. Three full-ID true whole-vector Update/Remove/Add passes,90000 calls
per builder;three alternating pairs per dataset,12 builders and1080000 mutation calls.
No builds/tests ran during timing. Original data/recipe/SHA and raw neighbor/hit/latency
records are retained. No budget/threshold/seed tuning after seeing results.

|Dataset|Final recall old/new|Gain percentage points|CRUD median old/new ms|CRUD change|
|---|---:|---:|---:|---:|
|gist10k600|0.811667 / 0.899167|+8.750|26470.177 / 26788.848|+1.20%|
|cohere10k600|0.908000 / 0.947000|+3.900|23462.340 / 23999.809|+2.29%|

|Dataset|Post-CRUD query old P50/P99 us|New P50/P99 us|
|---|---:|---:|
|gist10k600|407.651 / 465.951|439.810 / 520.779|
|cohere10k600|403.991 / 491.239|428.569 / 475.830|

|Dataset/operation|Old P50/P99 us|New P50/P99 us|
|---|---:|---:|
|gist10k600/update|462.520 / 1374.609|419.890 / 1453.638|
|gist10k600/remove|107.758 / 177.315|113.628 / 178.335|
|gist10k600/add|268.234 / 306.354|276.404 / 314.983|
|cohere10k600/update|385.251 / 1189.853|367.161 / 1295.750|
|cohere10k600/remove|117.818 / 179.406|117.897 / 177.295|
|cohere10k600/add|239.254 / 270.644|246.204 / 276.165|

All initial ordered ID/hex-distance/hit records are byte-identical. Final graphs
and results intentionally differ. Each of12 builders natively verifies exact Save/Load
ordered ID/distance equality. Snapshot bytes remain11284416/9363552;degree limits unchanged.
Final queries are before/after maintenance,NOT interleaved into the mutation loop.

Both candidate recalls still miss the pre-existing study floors GIST.90/Cohere.95.
These are study targets,not OSPP official numerical thresholds. Query timings compare
different final qualities;higher recall can cost more traversal. No equal-recall query
speed win,public-default improvement,Full comparison or complete acceptance is claimed.
Repeated deterministic graph outcomes on the same observed queries are not independent
quality samples or blind generalization. Raw paired per-query wins/losses are in summary.
Known permanent count storage is the same8N between both CACHED variants;no memory saving
is claimed. External peak includes input matrices/staging/two indexes,not mutation-only peak.

## Validation

Release6,ASan/UBSan5,fresh coverage5,RaBitQ-OFF4,format/tidy15 pass. Rule tests cover newly
added versus existing targets,no-safe-edge fallback,invalid input and policy rejection.
A concrete saturated-row Add fixture verifies the old policy leaves a target with zero
incoming edges while protected policy retains one,with reverse off/on. Continued mixed
changes and exact mutable persistence pass. Existing public/default golden behavior passes.
Allocation regression explores24000 internal positions (8000 safe-policy cold/warm positions)
plus6000 public positions. Reverse on/off,Update/Add/Remove,hole/last/singleton,failure/retry
and continued changes pass without state mismatch. Non-reverse rollback invalidates cache;
diagnostic attempted-rebuild counters may advance. The initial expanded fixture incorrectly
required these counters to roll back like reverse-copy mode;failed log retained,assertion
corrected to the existing contract. Persistent snapshots and retry goldens remain strict.
Final graph fixture was added after timing;production header remained byte-identical.
Measured test source and final validated source are separately retained.
Scoped Lite coverage2950/3091=95.44%,not whole Full coverage.

## Evidence and reproduction

Run python3 lite/benchmark/results/rabitq-safe-link-20261011/verify.py to audit hashes,
1080000 schedules,14400 truth intersections,operation/query quantiles,initial byte equality,
paired hit deltas,10 final command exits and the fresh19-counter coverage union.
It does not regenerate exhaustive changed-data truth or reread deleted large snapshots.
New RAM snapshots were deleted only after native exact Load/Save checks/hash/archive;
old datasets/source/raw/binaries were preserved. No Full/OS cache privileges changed.

For host replay,use a NEW result directory,matching parent source/build objects/SIMD/data
and actual archived measured-run-host.py,candidate-state.h and recorded adapter build commands.
Final run-host.py pins the measured candidate header from this raw archive;syntax-checked
only,not rerun. Original absolute host dependencies/input SHA remain authoritative.

Decision: retain this promising internal opt-in candidate,NOT enable public default yet.
Next isolate remaining route misses and test a bounded candidate/diversity rule separately,
then100k/interleaved real CRUD and fresh native Full configuration/SIMD/quality alignment.
Cold I/O,complete package sizing and final adoption decision remain pending.
