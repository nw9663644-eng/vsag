# RaBitQ snapshot load: remove duplicated ID validation (2026-10-11)

Source evidence: load_mutable_snapshot created an unordered_set to reject duplicate IDs;
MutableGraphState already rejects them through slots_.emplace(...).second while building
the required ID-to-slot map. Remove only the first set and its header include. No map reserve,
graph layout,model,query,CRUD,public policy,SIMD,API or VSAGLQ01v1 format changes.

## Matched warm loading

Default reverse=false / NONE for both variants. Parent e017145 control and candidate have
identical frozen Lite headers except removal of this set. CPU0,single process;GIST960 and
Cohere768 each10k,degree16/build128/query512. Two zero-round builders generate valid current
snapshots,not a repeated CRUD benchmark. Fifteen alternating fresh-process pairs per dataset.
All60 native Load/Save round trips have the exact input SHA;known graph/code/map byte counts
are identical. Source/dependency/compile receipts and raw CSV/stdout are retained.

|Dataset|Old/new load median ms|Change|Old/new baseline-subtracted RSS KiB|Faster pairs|
|---|---:|---:|---:|---:|
|gist|6.483486 / 6.243492|-3.70%|13836 / 13364|15/15|
|cohere|5.721933 / 5.503448|-3.82%|11908 / 11492|15/15|

This is a small warm-load/allocator-retention improvement,not a permanent index layout
reduction or a statistical guarantee. Current RSS is sampled after load before re-saving.
The removed temporary set can leave allocator-resident pages after destruction;known
resident index capacity is unchanged. getrusage ru_maxrss retains a launcher-related floor
and is explicitly NOT claimed as clean-loader peak improvement. RAM/page-cache warm is not
cold filesystem I/O. Initial query evidence is setup validation,not query/CRUD/Full advantage.

## Correctness and limitations

Malformed duplicate-ID snapshots remain INVALID_BINARY;new tests cover negative,zero and
INT64_MIN/MAX duplicates near the start/end. Public Save/Load bytes remain identical.
Duplicate rejection now occurs in the constructor after graph parsing/adjacency expansion:
malformed duplicate input may do more work before rejection;error message/validation order
is not preserved. Existing count/dimension/graph bounds remain. Do not claim earlier rejection
or constant-memory parsing. Allocation-failure tests still pass;exception handling unchanged.

Release6,ASan/UBSan5,fresh coverage5,RaBitQ-disabled4,format/tidy15 production and probe pass.
Fresh scoped Lite coverage2933/3074=95.41%;not whole Full coverage.

## Reproduction

From repository root,on the recorded host,use a new results directory and run run-host.py.
It freezes all Lite headers from e017145 and derives the exact candidate minimal patch;
existing cached10k vectors/truth paths are required and hashed. It refuses completed-row
overwrite. Builders/probe compile commands,environment,input hashes,snapshot hashes,source
and validation logs are retained. Large fresh RAM snapshots/round-trip files were removed
only after exact re-save hashes and durable receipts;old datasets/results were not removed.
Snapshot hashes cannot independently prove missing snapshot bytes;native round-trip receipts
are evidence from the measured host. verify.py audits retained artifacts without replay:

~~~bash
python3 lite/benchmark/results/rabitq-load-id-map-20261011/verify.py
~~~

Fresh original performance reproduction is not performed by the verifier. collect.py is
an evidence-generation recipe tied to fresh validation logs/counters,not a portable benchmark.

Still pending: mixed real-value CRUD quality floors,100k/interleaved endurance,fresh native
Full configuration/SIMD/quality-aligned comparison,cold I/O and complete installed package.
Public default policies and PR2904/2926 remain untouched;project is not fully accepted.
