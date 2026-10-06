# Fixed-parameter GIST holdout: quality gate failed

2026-10-06. Base commit c9f65430c5c681a172b083bd9f47531252e750d9.
No search or graph-policy code changed. The new preparation wrapper selects
source query rows [100,400), disjoint from tuning rows [0,100), and reuses
lite_prepare_gist's exact distance/ID tie-breaking implementation. Every selected
vector was checked against the raw fbin row and checked for no exact-vector
overlap with the previous tuning set. Input/output hashes and row provenance
are in holdout-manifest.json. This is a new split of the same GIST source,
not a new distribution or a Cohere validation.

We froze the previous selected configurations before seeing these 300 queries.
No parameter retuning was done on this split. CPU 0, one warmup pass followed
by five timed passes. One fresh process per configuration; timings are descriptive
single-run measurements, not the five-process repeat claim of the earlier study.
Each process then executes 1,000 serial modified-update/restore/remove/re-add
cycles and requires exact Save/Load query-result equality.

| Mode | Fixed ef | Recall before CRUD | Recall after CRUD | Query P50 us | Query P99 us |
| --- | ---: | ---: | ---: | ---: | ---: |
| preserve | 1536 | 0.867667 | 0.866667 | 4409.919000 | 5053.194000 |
| diverse | 160 | 0.837000 | 0.846000 | 811.172000 | 949.039000 |
| diverse_reverse | 128 | 0.836667 | 0.843333 | 714.784000 | 872.970000 |

None meets Recall>=0.90. Preserve scores 0.867667 while diverse_reverse scores
0.836667, a 0.031 absolute difference. Their earlier tuning-split scores were
0.902 and 0.903. Therefore the earlier 6.52x P50 ratio is specific to selected
points on the original 100 queries and cannot be promoted to a general
matched-quality speedup. Candidate latency remains lower here, but quality is
also lower, so there is no validated equal-quality speedup on this split.
After CRUD, quality remains below the gate for every fixed configuration.

This is a failed acceptance gate, not proof that diversity is universally worse.
The method may require a broader quality/cost frontier. Any future parameter
selection must use a designated training/validation split and reserve still
unused query rows for final assessment; these 300 rows are now observed and
must not be described as blind holdout after further tuning. Preserve previous
results as historical evidence and retain this limitation alongside them.

Preparation fixtures validate known exact-neighbor IDs, query offsets, overlap
prevention via minimum offset, out-of-range rejection and existing-output refusal.
The actual split additionally checks exact-vector disjointness. Existing C++
regressions already passed at the unchanged source commit; this increment only
adds the Python preparation wrapper, its fixtures and reports.

## Reproduction

Build lite_prepare_gist in a Lite build with ENABLE_RABITQ_LITE_PROBE enabled, then:

```text
python3 lite/benchmark/prepare_gist_holdout.py BUILD/lite_prepare_gist BASE_FBIN QUERIES_FBIN NEW_DATA --offset 100 --count 300
python3 lite/benchmark/test_prepare_gist_holdout.py BUILD/lite_prepare_gist
taskset -c 0 BUILD/lite_graph_route_probe SNAPSHOT NEW_DATA/scale-100000 NEW_OUTPUT 1536 uniform preserve 5 1000
taskset -c 0 BUILD/lite_graph_route_probe SNAPSHOT NEW_DATA/scale-100000 NEW_OUTPUT 160 uniform diverse 5 1000
taskset -c 0 BUILD/lite_graph_route_probe SNAPSHOT NEW_DATA/scale-100000 NEW_OUTPUT 128 uniform diverse_reverse 5 1000
```

Exact measurement commands and paths are in commands.json. Prepared inputs are
retained at /home/ubuntu/project/vsag-lite-gist-holdout-20261006. Sources are
/home/ubuntu/project/vsag-lite-datasets/gist/hf-100k/{base-100k,queries}.fbin.
Existing long-CRUD repaired-implementation snapshot is reused. Raw per-query
scalar diagnostics, actual API summaries, timed query samples and mutation
samples are included. Checksums cover this directory; no binary or base vectors
are committed. Production graph policy and PR branches remain unchanged.
