# RaBitQ streamed adjacency Save (2026-10-11)

Source: save_mutable_snapshot called GetGraph/compact_graph, materializing all offsets
and edges before writing. Existing native src/storage/stream_writer.h::WriteVector and
Lite write_integer_array use contiguous block I/O. Stream the same CSR wire order from
read-only row adjacency in an at-most8192uint64/64KiB buffer, reused for offsets and edges.
Check sum/count overflow and retain scalar little-endian fallback and stream errors.
No public API/model/encoding/topology/degree/budget/default/format change.
GetAdjacency is internal read-only; original GetGraph remains for callers/tests/load.
Validate remains before writing. Save can still allocate validation scratch in cached/
reverse modes;64KiB refers only to this adjacency staging buffer, not all Save memory.

## Frozen fresh loaded-state Save comparison

Parentb09631c versus candidate, both public NONE/reverse=false. Real GIST960 and
normalized Cohere768,100k. Prepare one unchanged snapshot/dataset using degree16/
build128/query512; its SHA matches all six previous real100k snapshots/dataset.
CPU0 and OMP/BLAS/MKL1;seven alternating paired fresh processes/dataset,28 saves.
No tests/builds overlapped timed runs. Probe loads input before checkpoint, then times
ofstream open + Index::Save + close. Native roundtrip output SHA must equal input.
RAM/pagecache uncontrolled, not cold I/O or fdatasync durability.
VmRSS/VmHWM checkpoints bracket Save; loader allocation/launcher can hide Save-only
peaks. This is NOT the preceding build-then-Save timing, whose allocation layout differs.

|Dataset|Save old/new median ms|Change|Before HWM old/new KiB|After HWM old/new KiB|
|---|---:|---:|---:|---:|
|gist100k|52.819/45.774|-13.34%|134964/134964|151216/134964|
|cohere100k|44.151/37.441|-15.20%|116212/116216|132460/116216|

28 output snapshot hashes equal input. File sizes and semantics remain unchanged.
This measures loaded-state Save only, NOT query/CRUD/build/Full advantage or resolution
of prior query P50 regressions. Two prepare builders natively verify100 ordered queries
after Save/Load, but not a new query benchmark/quality claim. No retuning after results.
The full graph transient is removed by construction; checkpoint differences are not
a universal peak-saving guarantee. See raw rows for per-pair variation and RSS.
Previous build-then-Save regression is not automatically proven resolved by this protocol.

## Verification and limits

Release6,ASan/UBSan5,freshCov5,RaBitQ-OFF4,format15/tidy15 and probe-tidy passed.
Initial uppercase local constant failed identifier-naming lint, corrected before timing;
original failure log retained. No product test failure.
CSR bytes match for0/1/8191/8192/8193/9000 rows,variable degree including empty rows,
bulk/scalar endian and limited-output short writes. Existing lifecycle/allocation faults
and snapshot roundtrips retained. Coverage is scoped Lite/shared SIMD, not whole Full.
Original19fresh counters are archived; verification recomputes their union.

run_stream_save.py uses recorded host paths, matching Release objects and new output.
Replay at parent business checkout plus archived candidate source/patch, rebuilding
Release first; restore measured candidate headers and verify their SHA before running.
Current fixed output guard prevents overwriting evidence; adapt only fresh destination.
Exact old headers/backend, compiler/link/dependency commands and object hashes retained.
New RAM snapshots are SHA-verified then exact-path unlinked; no old source/data/results
or libraries removed. Base data stays cached; snapshot bodies not archived but SHA/size
and input identities retained. Small stdout/raw scripts/source/query/GT are archived.
Long changed-value/interleaved CRUD,latest aligned native Full,larger query cohorts and
deployment package final acceptance remain open. No complete-project claim.
