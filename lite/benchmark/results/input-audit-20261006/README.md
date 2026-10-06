# Investigation of the failed independent-query gate

2026-10-06, source commit 704e544f1ed570a2a0e4551f4da5f66d3c7b3f7d.
We checked data and scoring before further parameter experiments.

* All 100,000 snapshot IDs are unique and exactly cover 0..99999.
* For every external ID, the FP32 vector bytes in the long-CRUD snapshot equal
  that ID's prepared base vector. Slot permutation from deletion is accounted for.
* An independent standalone double-precision squared-L2 exhaustive scan recomputed
  Top-10 sets for eight uniformly spread holdout rows: 0,42,85,128,170,213,256,299.
  All eight sets match the existing preparer's exact truth. This is a sample check,
  not a full audit of all 300 truth rows. Order inside tied results is not checked.
* Aggregate recall from scalar diagnostics equals actual Lite API recall for all
  three frozen configurations on all 300 holdout queries. This does not assert
  per-query result equality or timing equivalence between the two paths.

No data misalignment or sampled truth discrepancy was found. The quality gate
remains failed. Evidence points toward insufficient robustness of the selected
parameters/graph policy across query subsets, not a corrected scoring bug.
This investigation does not prove that every implementation issue is excluded.

Next work is bounded: use observed rows 0..399 for selection/validation, compare
a coarse recall-cost frontier for preserve and the simpler diversity candidates,
and reserve rows 400..999 for final evaluation. Freeze configurations before
opening that final set. A failure to meet the quality gate ends adoption of that
configuration; do not add more topology-only patch layers to rescue a timing ratio.
Long churn and online construction cost should follow only promising quality-gated
configurations. Cohere still needs separate data and validation.

## Reproduction

```bash
g++ -O3 -std=c++17 audit_truth.cpp -o audit_truth
./audit_truth /home/ubuntu/project/vsag-lite-gist-holdout-20261006/scale-100000
```

This small helper is for the known fixed audit inputs (at least 300 queries,
matching dimensions and Top-10 truth), not an untrusted-file validator. Its
implementation shares no distance kernel with the existing preparer. It passed
format/tidy version 15. Actual audit exit code was zero. JSON/CSV evidence and
source hashes are retained. Production and benchmark query code are unchanged.
