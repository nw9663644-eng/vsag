# Cohere 100k frozen-budget final evaluation (2026-10-06)

## Protocol and source evidence

Library/API and benchmark source: 1faa26cfd5122f1d1d0a0cc7a7c9f9d42c9dcbf6.
Uses existing SearchWithOptions and graph_route_probe: query budgets do not change
construction/CRUD ef 128. Initial snapshots are actual online degree16 FP32 graphs
from cohere-normalized-20261006, not offline topology transforms. Each mode loads
its own library (experimental diverse policy remains OFF by default).

protocol.json was written before validation. Pilot queries [0,100) were already
observed; validation uses [100,400). Smallest tested budget reaching Recall@10
>=.955 was frozen before final preparation. Final uses [400,1000), with floor .95
and no retuning. before-final.json records freeze SHA and absent final directory.
Validation/final manifests include exact FP64 truth, normalization and hashes.
All 300 validation and 600 final ordered Top10 match original-coordinate cosine;
this audits the selected source queries, not unseen populations. Prepared base
hashes match pilot and neither held-out range shares vector bytes with the other
ranges (input-audit.json).

## Validation selection

| Mode | Query ef | Recall@10 |
|---|---:|---:|
| default | 128 | 0.900667 |
| default | 192 | 0.924333 |
| default | 256 | 0.933333 |
| default | 384 | 0.946000 |
| default | 512 | 0.953000 |
| default | 768 | 0.960667 |
| default | 1024 | 0.965000 |
| diverse | 96 | 0.934333 |
| diverse | 128 | 0.943000 |
| diverse | 192 | 0.954333 |
| diverse | 256 | 0.963333 |
| diverse | 384 | 0.969333 |
| diverse | 512 | 0.975000 |
| diverse | 768 | 0.983000 |

Frozen budgets: default 768, diverse 256. These are grid-selected points, not a proof of globally optimal baseline.

## Final repeated mixed workload

Three fresh processes per mode/cadence, CPU0, alternating mode order by repeat.
One full warmup pass and one timed pass of 600 initial queries. Each run then
executes 1000 cycles (changed Update, restore Update, Remove, Add). Query follows
every 1 or 10 cycles: read:mutation-call ratios 1:4 and 1:40. End quality covers
all 600 queries; Save/Load verifies identical IDs and distances. Mixed reads cycle
through queries, so 1000 events are not 1000 independent queries.

Times below are process medians across three runs. Raw per-query/per-cycle CSVs
and audit.json provide nearest-rank P50/P99 checks and min/max run variation.

| Read:mutation | Mode | Initial recall | End recall | Mutation CPU ms | Query CPU ms | Mixed total CPU ms | Mixed P50 us | Mixed P99 us |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 1:4 | default | 0.958000 | 0.957833 | 1276.801 | 2589.928 | 3870.573 | 2632.990 | 3175.337 |
| 1:4 | diverse | 0.961333 | 0.960333 | 1282.127 | 1091.220 | 2379.522 | 1108.404 | 1385.477 |
| 1:40 | default | 0.958000 | 0.957833 | 1173.052 | 265.549 | 1439.872 | 2726.266 | 3336.362 |
| 1:40 | diverse | 0.961333 | 0.960333 | 1273.670 | 110.805 | 1385.265 | 1130.933 | 1348.189 |

For 1:4, candidate mixed CPU change is -38.52%; mutation CPU change is +0.42%.

For 1:40, candidate mixed CPU change is -3.79%; mutation CPU change is +8.58%.

Quality passes: 12/12. Raw records verified: {'initial': 7200, 'mixed': 6600, 'cycles': 12000}.

## Interpretation and limits

Both selected points pass a common quality floor, with different recall; this is
not exact equal-quality performance. Candidate query savings must be weighed
against maintenance and initial graph-construction overhead (pilot ~17.6% at 100k).
Three runs quantify this machine/workload, not general production throughput.
Mixed total CPU includes scoring and bookkeeping, so it need not equal phase sums.

A temporary coordinate +.125 is not renormalized. Queries occur only after full
restoration of original normalized data, preserving truth validity. This is not
persistent normalized-vector update validation, concurrency or large-update proof.
The 1000 deterministic IDs cover 1% of base; histories are repeated deterministically.
Warm in-memory stream Load is not cold start. No library changes, new coverage or
sanitizer claims. Keep the policy opt-in until Full comparison and adoption review.

All 1000 Cohere source queries are now observed; future tests on these must not be
called new blind tests. Next required work: known-source Full comparison with the
same data and single-core protocol, matching RSS/CRUD measurements, and a unified
SIFT/GIST/Cohere adoption table. Do not keep retuning these final queries.

## Reproduction

Use prepare_cohere.py with isolated numpy/pyarrow/h5py dependencies. Run frontier.py
then final.py from the remote repository, with fresh output directories and the
recorded pilot snapshots/build binaries. Scripts embed this experiment's host paths;
adjust paths explicitly on another host. Commands JSON files preserve actual CLI.
Large datasets/snapshots/binaries are excluded from Git. Their hashes and initial
pilot provenance remain in the referenced pilot directory and manifests.
