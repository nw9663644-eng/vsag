# Isolated build-row capacity candidate (2026-10-11)

Source evidence: make_rabitq_graph_backend shrinks every build adjacency row before
moving ownership. Existing GraphBackend::TakeBuildLinks already transfers owned rows.
Hypothesis: retaining build capacity avoids many reallocations and could change query
locality, at a permanent capacity cost. This was NOT an established regression cause.

Control bf50173 and candidate share every production header/object and streamed Save.
Only isolated candidate adapter removes the six-line build-row shrink loop.
No production source changes or public option. API/model/degree/ef/edges/order/format/
public NONE/reverse=false unchanged. Candidate backend SHA and exact source diff verified.
Old Lite/control is NOT Full. Current headers retain recently implemented streamed Save.

GIST960/normalized Cohere768 each100k/100 observed queries,k10,degree16/build128/query512,
CPU0/OMP-BLAS-MKL1;three alternating pairs/dataset,12 complete builders/36 fresh loaders.
No concurrent compile/test while timed. Rounds0,NOT changed-value durable CRUD acceptance.
No parameter/seed/budget tuning after results. Inputs hashes and manifests archived.
All six pairs have native snapshot SHA and ordered neighbor equality; each builder also
natively verifies Save/Load100 ordered results. Loaded state drops build slack when CSR
is expanded, so loaded RSS is not built-state retained capacity.

|Dataset|Build old/new ms|Change|Query P50 old/new us|Change|Whole-process peak old/new KiB|Change|
|---|---:|---:|---:|---:|---:|---:|
|gist100k|38781.468/39015.944|+0.60%|1081.373/1084.913|+0.33%|903840/903888|+0.01%|
|cohere100k|35971.954/35977.733|+0.02%|1100.393/1146.963|+4.23%|735052/735052|+0.00%|

|Dataset|P99 old/new us|Save old/new ms|Warm load old/new ms|Recall both|Snapshot bytes|
|---|---:|---:|---:|---:|---:|
|gist100k|1341.637/1387.996|66.121/65.373|63.929/62.751|0.859000|112804416|
|cohere100k|1340.187/1352.817|61.064/59.719|57.136/56.131|0.937000|93603552|

## Decision and boundaries

No production adoption in this commit. One observed small-query cohort and three paired
trials cannot establish allocation/cache causality or general timing gains. The capacity
cost is not fully instrumented in this study. No hardware performance counters collected.
Retain current shrinking default pending a separately justified built-state capacity and
multi-cohort cost/quality study. Do not infer no-shrink is faster from fewer allocations.
The driver records whole-process builder peak including inputs/native reload,not isolated
adjacency memory. Fresh loader RAM cache is uncontrolled;not cold I/O.100 observed queries
give exploratory P99 only;fixed512 Recall still insufficient,unchanged by candidate.
No Full/package/CRUD advantage. This study tests row-capacity hypothesis,not ANN semantics.

Fresh unchanged production Release6 passed before timing. Prior bf50173 ASan/UBSan5,
OFF4 and scopedLite95.456% coverage are inherited,not rerun or candidate SAN evidence.
Candidate adapter compiled and completed native lifecycle/paired checks;no claim of
candidate allocation-fault/sanitizer acceptance. Private experiment does not enable a
public runtime switch or affect PR2904/2926.

## Replay and verification

Helper requires bf50173 business checkout and new output directory;archive its actual
helper before adapting only output destination. Same host cached datasets required.
Exact control/candidate adapters,compiler/link/dependency logs and shared-object hashes
retained. Native snapshots live only in newly generated RAM dirs and driver checks paired
SHA before deleting exact temp targets. No original source/data/results/library cleanup.
Raw queries,GT,manifests,neighbor/latency records,stdout,commands and source identities
archived. Existing subset GT was not recomputed;verifier recomputes raw result intersections
and quantiles only. verify_row_capacity_candidate.py does not rerun performance.
Pending project acceptance:query layout/route optimization,interleaved true changed CRUD,
latest native Full config/SIMD/quality alignment,broader query tails and package closure.
