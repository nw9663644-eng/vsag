# Normalized Cohere preparation and online CRUD pilot (2026-10-06)

## Scope and provenance

Measured library source: e547eb1cc595828a19ffc82b6bdbf8fd5a43069a.
Cohere small 100k is 768-dimensional cosine data. This experiment normalizes rows
using FP64 norms/division and stores FP32 coordinates, then uses the existing
squared-L2 API. It does not introduce a public cosine metric or change index code.
See preparation manifests for original and prepared file hashes and source-ID maps.
Index IDs are row ordinals, not original source IDs.

For each scale, exhaustive FP64 squared-L2 ground truth on stored coordinates is
recomputed. All 100 pilot queries have identical ordered Top10 to exhaustive
original-coordinate cosine ranking at both scales. Maximum absolute difference
between stored squared-L2 and twice raw cosine distance is 1.66345e-8 (10k) and
1.71835e-8 (100k). This audit covers selected queries only.

## Predeclared pilot protocol

See protocol.json, commands.json and pilot.py. CPU affinity is 0; FP32 degree 16,
construction/maintenance/query ef 128. Each mode uses its own actual online library
and preserves initial adjacency; no offline topology replacement is used. One
process per configuration, default then diverse, with 100 initial queries and
1000 cycles of changed Update, restored Update, Remove and Add. A query follows
every ten complete cycles (100 reads, read:mutation-call ratio 1:40).

Changing coordinate zero by +0.125 temporarily violates unit normalization; queries
run only after restoring original data. This checks structural maintenance and
restored-data retrieval, not persistent normalized cosine updates or arbitrary
large updates. The deterministic affected IDs cover 10% of 10k and 1% of 100k.

## Results

Recall is Recall@10. CPU times describe this single process, not repeat medians.

| Scale / mode | Initial recall | Post-CRUD recall | Build ms | Mutation CPU ms | Mixed total CPU ms | Mixed P50 us | Mixed P99 us |
|---|---:|---:|---:|---:|---:|---:|---:|
| 10k default | .960 | .957 | 2453.825 | 850.491 | 883.339 | 325.432 | 412.580 |
| 10k diverse | .982 | .979 | 2932.077 | 1002.400 | 1041.061 | 381.250 | 467.029 |
| 100k default | .891 | .892 | 42351.194 | 1161.846 | 1213.765 | 515.168 | 719.522 |
| 100k diverse | .948 | .947 | 49789.285 | 1259.442 | 1318.546 | 580.376 | 790.961 |

The predeclared .90 pilot quality floor fails for default 100k both before and
after CRUD. Diverse clears it, with higher construction and maintenance costs.
These are equal-budget points with different recall, not matched-quality speedups.
The experimental policy remains OFF by default. All four Save/Load checks retain
query IDs and distances according to the existing probe checks.

## Verification and remaining gates

Fixture tests cover normalization, source IDs, offsets, deterministic exact ties,
invalid sizes/dimensions/values/IDs and overwrite refusal; see fixture.log.
audit-summary.json checks 400 initial and 400 mixed raw latency samples against
nearest-rank P50/P99 and checks 4000 CRUD cycles. CSV files include all raw samples.
Artifacts hashes identify binaries and snapshots; datasets, snapshots and binaries
are not committed. Load timings read populated streams and are not cold-start tests.

Queries [0,100) are observed pilot/tuning data. Reserve [100,400) for validation
and [400,1000) for final evaluation; retrieval on these has not yet been measured.
Next: predeclare query-budget grids and common quality floor, select budgets using
validation only, freeze them, then run final repeated/interleaved measurements.
A known-source Full build with matching data/CPU/memory/CRUD protocol is still
required for a final Full/Lite claim. This pilot is neither independent acceptance
nor a complete Full comparison. No new C++ coverage/sanitizer result is claimed.

Dependencies used: numpy 2.2.6, pyarrow 21.0.0 and h5py 3.16.0 (shared SIFT helpers).
