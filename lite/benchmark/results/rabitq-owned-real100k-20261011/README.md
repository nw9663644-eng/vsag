# RaBitQ ownership: real100k acceptance slice (2026-10-11)

Frozen production candidate4f73870 versus parent0444bf9. Both are Lite, NOT Full VSAG.
Both public NONE/reverse=false; no CACHED/safe-link adapter enabled.
This extends the synthetic ownership diagnostic to real high-dimensional inputs.
No production edits or degree/budget/model/seed tuning during this study.

GIST960 and normalized Cohere768,100k base/100 observed query vectors,k10,
degree16/build128/query512,CPU0 and BLAS/OMP/MKL1. Three alternating paired trials per
dataset;12 complete builders and36 fresh-process loaders. No concurrent build/test timing.
Base/query/GT identities and original preparation manifests preserved. Truth is existing
subset-specific squared-L2 GT; Cohere stores FP32 normalized rows with original cosine
rounding audit. This collection verifies raw GT intersections, not recomputation of GT.

## Resource/cost and quality

|Dataset|Whole-process peak old/new KiB|Change|Build old/new ms|Change|Recall old/new|
|---|---:|---:|---:|---:|---:|
|gist100k|928420/903892|-2.64%|39122.822/39091.702|-0.08%|0.859000/0.859000|
|cohere100k|759556/734956|-3.24%|35838.626/35809.990|-0.08%|0.937000/0.937000|
\n|Dataset|Save old/new ms|Change|\n|---|---:|---:|\n|gist100k|47.454/65.928|+38.93%|\n|cohere100k|38.101/60.065|+57.65%|\n\nBoth query P50 medians increase; Save median regresses substantially. Do not claim overall speed acceptance. Reasons are not established by this study. Source still compacts full adjacency in save_mutable_snapshot via GetGraph; ownership handoff can also change row allocation locality. These are follow-up hypotheses requiring phase/cache profiling, not proven causes.\n
|Dataset|P50 old/new us|P99 old/new us|Fresh warm load old/new ms|Snapshot bytes|Loaded total RSS old/new KiB|
|---|---:|---:|---:|---:|---:|
|gist100k|1088.753/1115.092|1368.705/1332.067|62.696/60.714|112804416|121628/121628|
|cohere100k|1068.973/1134.902|1311.848/1312.488|53.161/53.228|93603552|102864/102848|

Peak is /usr/bin/time whole builder high-water RSS INCLUDING input rows, source index,
graph construction, querying and native Save/Load validation with two index states.
It is NOT an isolated build-stage peak. Synthetic dim17's25.30% peak saving does not
transfer as-is to high-dimensional data: fixed source/input and encoded-state memory
dominate. Cumulative allocation traffic was not instrumented in this real study.
Medians mix trials; raw paired rows are preserved. Host is not exclusive and timing
differences are not statistical/general guarantees. No query/load speed win is attributed
to this ownership-only change. Loading still uses CSR, with unchanged persisted layout.
All six native snapshots and ordered query files match exactly;12 builders additionally
check native Save/Load ordered result equality. Query return quality is unchanged.
Recall at fixed512 may still miss study quality goals; no threshold/budget adjustment.
100 previously observed queries give exploratory P99, not a robust tail or blind cohort.

## Requirements and limits

This supplies fresh P6/P7/P8 evidence for two real100k datasets and validates a structure
change's resource/correctness effect. It is not P9's native Full comparison or P10's
long-changed-data quality gate. Rounds=0: no CRUD throughput or enduring Update/Remove/Add
claim. No FP32/FP16 fresh comparison, complete package closure or cold-cache claim.
Fresh Release6 and driver fixture passed. ASan/UBSan5,OFF4 and scoped Lite95.41195%
coverage are inherited from unchanged4f73870 code, NOT rerun or new whole Full evidence.
Remaining: interleaved/long true changed-value CRUD and quality, larger query cohorts,
fresh native Full config/SIMD/quality-aligned comparison, final deployment package metrics.

## Reproduction

Production checkout4f73870 is required by run_owned_real_acceptance.py; the helper is
committed later as evidence. Copy the recorded helper into the matching checkout without
changing production, confirm source/library hashes and existing host dataset paths, then
use a fresh results directory. Current helper fixed-output guard rejects overwriting this
study. Preserve original helper before adapting only its fresh destination for another run.
Control header/backend and exact compiler/link/dependency commands are archived; same
shared Release objects are bound by SHA. Libraries reside on RAM for comparison.
run_aligned_comparison.py executes native Save/Load correctness checks and paired SHA/
ordered-neighbor checks before its temporary snapshot directories are removed.
Only newly generated RAM snapshots are removed; original source/data/results retained.
A later collection-only fixture replay failed before benchmarking because the RAM control
library was no longer present; failure logs are retained. The original successful fixture
log is restored from the already-hashed archive, NOT a successful later replay.
Raw stdout/stderr/commands/latencies/neighbors/GT/manifests are in raw.tar.gz; members and
canonical SHA manifests bind them. verify_owned_real_acceptance.py rederives evidence
without rerunning performance. Paths and query history are recorded, not portable downloads.
