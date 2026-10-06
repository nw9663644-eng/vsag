# Frozen online graph query budgets: final GIST split passed

2026-10-06. Source commit 236049e8fe64ff031e6cb2dfd51e4fe96ba02aad.
Online default/diversity graphs were built from scratch with degree16, ef128,
then underwent 1,000 same-vector Update/Remove/Add cycles. Their stored adjacency
is reused unchanged for this query study. `NEIGHBOR_MODE=preserve` is used for
both, so the online diversity graph is not transformed offline again.

## Protocol fixed before final-query evaluation

The previously observed source rows [100,400) are the validation split. A coarse
predeclared budget grid selects the lowest tested ef reaching validation
Recall@10>=0.92. Default selects ef8192 (0.940667), online diversity selects ef512
(0.938333). `validation/protocol.json` precedes selection; `frozen-configs.json`
was written and hashed BEFORE preparing/evaluating rows [400,1000).
Frozen SHA256: 68fadaf2903dccc46dc128d51dba71a427a78f19399bddee3b940887eaae9c09.

The final 600 queries have no exact-vector overlap with any previously observed
row. Existing precise groundtruth preparation is reused. Final acceptance is
Recall@10>=0.90 with fixed budgets; no final-set retuning or replacement occurred.
All original 1,000 source queries are now observed. They must not be reused as
an unseen final set after further tuning.

CPU0, one full warmup pass, three timed passes over 600 queries, three fresh
processes per configuration with rotated execution order. Raw samples contain
1,800 latencies per process (10,800 total). Reported P50/P99 are medians of the
three process-level nearest-rank summaries. Every reported percentile was
recomputed from raw samples; scalar/API aggregate recall matches each run.

| Online graph | Loaded query ef | Final Recall@10 | P50 us | P99 us | Query-loop CPU ms |
| --- | ---: | ---: | ---: | ---: | ---: |
| default | 8192 | 0.954 | 17303.044 | 18678.941 | 30704.685 |
| diverse | 512 | 0.95 | 2056.702 | 2445.813 | 3627.451 |

Both pass the final gate. The selected-point P50 ratio is 8.41x and P99 ratio
7.64x at close, not identical, recall (0.954 versus 0.950). This independently
supports a quality/cost benefit for these configurations on GIST100k. It does
not establish a global optimum, a universal speedup, or exact equal-quality
performance. The grid is coarse and can overshoot; default ef4096 missed the
validation margin by only 0.000667. A finer baseline grid could reduce the ratio.

Query budgets here override the ef stored in the loaded measurement snapshot.
Original construction was at ef128; construction at ef8192/512 was not measured.
The current public Lite API has no independent per-query ef parameter. This
study uses the existing experimental loader/measurement path. Do not combine
these query measurements with earlier construction/mutation timings into a
net throughput claim, or assume mutations at the overridden ef retain their
previous cost. A practical query-budget interface decoupled from construction
and mutation is a subsequent implementation task.

Memory, cold-start timing, SIFT/Cohere generalization, longer or concurrent CRUD,
large-displacement updates, and Full VSAG matching are not established here.
The candidate remains behind the OFF-by-default experimental build option.
The previous offline selected-point study's failed holdout remains valid;
this result uses newly implemented online selection and newly frozen budgets.

Independent double-precision exhaustive audit matched eight Top-10 sets evenly
spread over the final 600 queries (rows0,85,171,256,342,428,513,599). This samples
8/600 truths, not a full independent proof. The helper/source and outputs are in
final/. No library code changed in this increment; preceding ON/OFF tests and
coverage results are recorded in ../online-diverse-20261006.

## Reproduction and evidence

`validation/commands.json` reproduces the grid, `final/commands.json` the frozen
measurement runs. Exact input snapshot hashes and measurement library/binary
hashes are in metadata.json. Final dataset row provenance and input/output
hashes are in final-dataset-manifest.json. Data is retained on the experiment
host at /home/ubuntu/project/vsag-lite-gist-final-20261006. Original online
snapshots are at /home/ubuntu/project/vsag-lite-online-diverse-20261006.

```text
python3 lite/benchmark/prepare_gist_holdout.py BUILD/lite_prepare_gist BASE_FBIN QUERY_FBIN NEW_DATA --offset 400 --count 600
taskset -c 0 BUILD/lite_graph_route_probe DEFAULT_POST_CRUD_SNAPSHOT NEW_DATA/scale-100000 NEW_OUTPUT 8192 uniform preserve 3
taskset -c 0 BUILD/lite_graph_route_probe DIVERSE_POST_CRUD_SNAPSHOT NEW_DATA/scale-100000 NEW_OUTPUT 512 uniform preserve 3
```

Repeat each configuration in three fresh processes with distinct outputs.
Changing budgets after inspecting this final split constitutes further tuning,
not a reproduction of the blind acceptance test. SHA256SUMS covers the published
raw evidence. Large datasets, binaries and private project records are excluded.
