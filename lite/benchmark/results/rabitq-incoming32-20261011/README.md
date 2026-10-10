# Narrow internal RaBitQ incoming slots (2026-10-11)

Source evidence:native src/basic_types.h uses uint32_t InnerIdType. Lite incoming source slots
previously used uint64_t. Only incoming rows and transaction backups become uint32_t;
external IDs,outgoing slots,degree counts,models,scoring,budgets,API,snapshot remain unchanged.
Explicit checked conversion rejects slots above UINT32_MAX before insertion. Boundary regression
tests max and max+1;it does not allocate billions of nodes. Disabled reverse has no new slot limit.
Accounting reports4-byte incoming payload and unchanged vector headers. No pool/CSR claim.
Both measured overlays enable reverse via identical one-token false-to-true default transform.
Control is5d633c9 with64-bit incoming;candidate is current32-bit incoming. Both NONE protection.
Public reverse remains false. Journals and failure guarantees remain;logical state,not capacities.

## Paired measurements

10k GIST960/Cohere768,600 queries,k10,degree16/maintenance128/query512,CPU0/thread1,three full-ID
passes of true whole-vector Update/Remove/Add,three alternating pairs per dataset,12 builders.
1080000 timed operations. Queries before/after,not interleaved. All paired ordered IDs,hex
distances,hits and snapshot SHA are identical;native Save/Load exact for every builder.

| Dataset |64/32-bit mixed CRUD ms|Change|Final recall|
|---|---:|---:|---:|
|gist10k600|20327.354 / 20116.230|-1.04%|0.811167|
|cohere10k600|17470.224 / 17346.610|-0.71%|0.908167|

|Dataset/operation|64-bit P50/P99 us|32-bit P50/P99 us|
|---|---:|---:|
|gist10k600/update|313.013 / 1347.830|310.154 / 1328.230|
|gist10k600/remove|18.160 / 88.377|17.400 / 86.418|
|gist10k600/add|271.075 / 310.653|268.524 / 307.933|
|cohere10k600/update|264.424 / 1137.634|262.985 / 1121.915|
|cohere10k600/remove|26.529 / 87.878|25.169 / 85.418|
|cohere10k600/add|240.665 / 271.975|240.055 / 271.215|

## Same-snapshot fresh-process warm loads

Both loaders consume each identical snapshot three times,72 loads. 160000 incoming edges:
payload1280000 to640000B (-50%);vector headers240000B unchanged,total1520000 to880000B (-42.11%).
Known capacity excludes map nodes/allocator/transient allocations. Resident increment uses
/proc/self/statm after load minus fresh-process baseline. ru_maxrss can inherit launcher HWM,
and builder peak includes matrices and two live indexes;neither proves mutation-only peak.
RAM/page-cache warm measurements are not cold I/O. Snapshot bytes remain unchanged.

|Dataset|Known capacity64/32 B|Resident increment64/32 KiB|Warm internal load64/32 ms|
|---|---:|---:|---:|
|gist10k600|12964320 / 12324320|16808 / 15532|8.949 / 8.434|
|cohere10k600|11043456 / 10403456|14880 / 13662|8.341 / 7.805|

Quality unchanged,still below research floors. Do not equate this internal-memory gain
with public-default or Full advantage. No SIMD/scoring/query improvement is claimed.

## Verification

Release6,ASan/UBSan5,fresh coverage5,RaBitQ-disabled4,format/tidy15 pass. Existing reverse
Update/Add/Remove allocation faults,NONE/RECOUNT/CACHED cold/warm,middle/last/single-node
delete,retry/continued mutation and mixed/growth golden tests remain passing.
Scoped Lite coverage2936/3077=95.42%;not whole Full coverage.
python3 lite/benchmark/results/rabitq-incoming32-20261011/verify.py independently derives
1.08M schedules/quantiles,14400 truth states,72 load byte deltas,exact paired results,
fresh coverage union,header/dependency/source receipts and hashes. Raw actual runner,headers,
adapter commands,query/truth/latencies,probe data,patch,native slot source and logs preserved.
Final replay pins captured candidate header;syntax-checked only,not rerun.
Only19 verified generated counters and new RAM snapshots(after native load/SHA) unlinked;
no old source,data,raw results or shared binaries deleted.PR2904/2926 untouched.

Next:incoming allocation/layout overhead and fixed-budget quality. Public reverse stays off;
100k/interleaved real CRUD,fresh aligned Full,cold I/O/complete package acceptance remain open.
