# RaBitQ owned build adjacency (2026-10-11)

Source evidence: build_graph_topology owns GraphBackend::TakeBuildLinks rows.
Previously make_rabitq_graph_backend copied rows to GraphTopology CSR, freed rows,
then MutableGraphState expanded CSR into new rows. Add an internal tagged owned-row
constructor and delegate the CSR constructor. Shrink rows before transfer, one at a time,
rather than retain build-only spare slots or allocate another whole topology.
shrink_to_fit is a non-binding standard request; tested GCC shrinks these rows.
Reverse-adjacency construction rejects bad targets before indexing counts.

No API, graph edges, quantization/model, degree/ef, default incoming policy, mutation
algorithm or format changed. Source BruteForce survives until successful publication.
This reuses the existing Lite builder, not an upstream Full graph rewrite.

## Frozen matched-host diagnostic

Parent0444bf9 versus candidate, BOTH public default NONE/reverse=false.
CPU0, OMP/BLAS/MKL1; deterministic sin((id*7+d)*.17) float inputs,dim17;
degree16/construction128/query512.10k/100k each three alternating process pairs.
12 complete BuildGraph executions, no concurrent compilation/testing during timing.
Probe reuses rabitq_build_allocation_probe: ordinary-new traffic recorded only during
BuildGraph; wall time and getrusage HWM checkpoint before Save/query; native snapshot
hash and ordered ID/hex-distance records for eight deterministic queries.

|Count|Build median old/new ms|Change|HWM median old/new KiB|Change|
|---|---:|---:|---:|---:|
|10000|433.491/435.550|+0.47%|18856/18856|+0.00%|
|100000|23432.080/23807.694|+1.60%|87628/65460|-25.30%|

Cumulative new requested bytes decrease4760184/38653816 at10k/100k.
This is allocation traffic, NOT peak/live/retained memory. HWM includes source and
all construction stages; launch HWM can obscure10k. No10k peak improvement claimed.
Retain as memory tradeoff; build times do not consistently improve.
100k synthetic dim17 is NOT GIST960/Cohere768/SIFT128 or changed-vector long CRUD.
All six snapshot/query pairs match. Eight observed queries check equality, not recall.
No Full, package, cold I/O, load/query/CRUD speed gain or complete acceptance claimed.

## Validation and reproduction

Tests cover empty owned state; extreme IDs; exact owned/CSR initial and Update/Remove/Add
snapshots; query equality; reverse off/on; invalid row count, range, self/duplicate edge,
degree overflow and duplicate IDs. Public build fault injection checks atomicity/retry.
Release6,ASan/UBSan5,fresh coverage5,RaBitQ-OFF4 plus format/tidy15 evidence accompany results.
Coverage is scoped Lite/shared SIMD, not whole Full.19 fresh raw counters are archived.

Confirm candidate source hashes in identity.json, rebuild matching Release and use recorded
compile/link commands on the matching host. Control source is archived and parent pinned.
run.py requires a fresh evidence folder without rows.json. Copy it to another folder at the
same four-level location under this repo for rerun; matching host dependencies are required.
validate.py waits until12 measurements/summary completed. verify.py recomputes raw outputs,
paired summaries/equality, successful validation, scoped gcov union and artifact hashes.
Exact RAM snapshot targets are hashed then unlinked; no datasets/source/old results/libraries
are removed. No policy changes in either adapter. Save/query happen after timing checkpoints.
