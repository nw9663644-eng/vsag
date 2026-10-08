# Geometry-scored old-neighbor reuse is not adopted

Measured parent: `4deb61f3b09f5135f7fcdd45e1ecc59936b03497`. The preceding whole-vector experiment rejected unconditional restoration of an updated node's old outgoing row. This experiment evaluates a narrower online candidate: after the existing `GraphBackend::Update` ANN search, rescore the old outgoing neighbors under the new vector, add only old neighbors strictly closer than the farthest ANN-selected candidate, sort the combined candidates and retain the existing degree. Search budget, degree, public API, snapshot format and query behavior remain fixed.

## Source evidence and isolated change

`GraphBackend::Update` already searches for neighbors using the new vector, removes old incoming references, installs the new vector, links the chosen neighbors and repairs affected nodes. The isolated `VSAG_LITE_EXPERIMENT_SCORED_OLD_UPDATE` block is inserted immediately after `nearest()` and before existing link preparation. It is FP32-only and uses a fixed 128-entry buffer: at most 64 ANN neighbors plus at most 64 old outgoing neighbors, consistent with the validated maximum degree. FP16 behavior is unchanged.

The candidate is compiled outside the repository from the exact parent source plus `candidate.patch` and linked with the parent's remaining object files. Checked-in `src/`, `include/`, API, defaults and CMake files are unchanged. The fixture proves that a competitive old neighbor is retained, a distant old neighbor is rejected, degree and reverse-edge consistency survive Update/Remove/Add, and invalid updates retain existing behavior for FP32 and FP16.

## Frozen evaluation

All runs use 100k-vector snapshots, degree 16, `ef_search=128`, CPU0 and historically observed queries. There is no blind-test claim and no parameter retuning. Each case runs in three fresh processes with alternating baseline/candidate order.

- Coordinate protocol: 10,000 distinct IDs, first coordinate increased by the exact FP32 result of `+0.125`.
- Whole-vector protocol: 1,000 distinct IDs and the frozen midpoint replacements from `whole-vector-20261008`.
- Queries: SIFT128 and Cohere768 use 100 rows each; GIST960 uses 300 rows.
- Quality: Recall@10 against protocol-specific changed-vector exhaustive truth.
- Maintenance cost: process CPU time around native Update. Three repeats support a descriptive median only.

## Results

| Protocol | Dataset | Baseline | Candidate | Net truth hits | Query W/L/T | Paired bootstrap 95% | CPU median change |
|---|---|---:|---:|---:|---:|---:|---:|
| Coordinate | SIFT | 0.954 | 0.954 | 0/1000 | 0/0/100 | [0, 0] | -0.86% |
| Coordinate | Cohere | 0.894 | 0.896 | +2/1000 | 1/0/99 | [0, 0.006] | +0.27% |
| Coordinate | GIST | 0.683 | 0.680 | -9/3000 | 18/24/258 | [-0.008667, 0.002333] | -0.25% |
| Whole vector | SIFT | 0.947 | 0.949 | +2/1000 | 1/0/99 | [0, 0.006] | -0.36% |
| Whole vector | Cohere | 0.885 | 0.886 | +1/1000 | 1/0/99 | [0, 0.003] | -0.50% |
| Whole vector | GIST | 0.754667 | 0.755000 | +1/3000 | 4/4/292 | [-0.001667, 0.002667] | +1.04% |

All six paired intervals include zero. Candidate output is identical to baseline for coordinate SIFT, changes only one query in each Cohere/whole-SIFT cohort, and changes 63 of 300 coordinate-GIST query outputs. The coordinate-GIST loss shows that scoring old neighbors in the new geometry avoids the large whole-vector failure of unconditional restoration, but still does not establish a generally beneficial Update policy. CPU differences change sign and stay near measurement noise.

**Decision:** do not adopt this candidate in the default Lite graph backend. It has no stable quality or maintenance-CPU advantage under the frozen cross-distribution protocols. Future work should measure why competitive old candidates alter downstream repair and test a diversity or connectivity criterion rather than distance-only retention.

## Audit and validation

```bash
python3 lite/benchmark/results/scored-old-candidates-20261008/verify.py
```

The standard-library verifier checks the flat archive without extracting it, every member hash, the frozen plan, parent/candidate source identities, compile flags, Release and ASan+UBSan fixture receipts, 36 successful process records and dynamic-library bindings. It checks 120,000 ordered neighbor rows, 198,000 update rows, exact schedules, FP32 coordinate updates, deterministic repeats, initial equality, changed-truth intersections, reported recalls, paired statistics and CPU medians.

Release and ASan+UBSan candidate fixtures pass. The unchanged baseline fixture passes against the default library, and the existing graph suite passes in both builds with 545,120 assertions in 14 test cases. Clang-format 15 dry-run and clang-tidy 15 passed on the isolated candidate before measurement. No new library coverage percentage is claimed because production library code was not changed.

`raw.tar.gz` contains sources, the minimal patch, build receipts and logs, inputs needed to recompute Recall, all summaries/neighbors/update ledgers, process logs and library bindings. It excludes snapshots, binaries and object files. Host scripts require the existing datasets and build trees. This result is committed only to the personal experiment branch; PR source branches remain unchanged.
