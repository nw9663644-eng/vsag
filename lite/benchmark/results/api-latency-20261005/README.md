# Loaded Lite API query latency, GIST 100k

Measured on 2026-10-05; verified on 2026-10-06. Base source commit:
63329c022952fd86316a91331e99a9cd336db729 plus the API measurement changes.
Source/binary hashes are in final-metadata.json. CPU information is in environment.txt.

This experiment loads a transformed FP32 graph through Index::Load and queries
through the actual Lite Index::Search SIMD path. It is a warm query experiment.
Serialization, scalar diagnostics and offline neighbor transformation are outside
query timing. Load timing starts from an already populated in-memory stream and
is not a fresh filesystem cold start. It is not online graph-building or CRUD timing.

CPU 0, one full query warmup, 10 timed passes over 100 independent Top-10 queries,
five fresh processes per configuration, rotating configuration order. Each process
emits 1,000 latency samples; P50/P99 use nearest rank. The table is the median of
five process-level summaries. query_loop_cpu_ms covers the full 1,000-query loop
and includes checks and timing bookkeeping, not only kernel execution.

| Mode | ef | Recall@10 | P50 us | P99 us | Loop CPU ms | Load ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| preserve | 1536 | 0.902 | 4035.594 | 4786.391 | 4009.495 | 152.263 |
| diverse | 160 | 0.913 | 703.388 | 876.524 | 691.444 | 140.107 |
| diverse_reverse | 128 | 0.903 | 618.959 | 769.057 | 613.070 | 142.798 |

At the selected Recall>=0.90 gate, preserve and diverse_reverse score 0.902 and
0.903. Their P50 ratio is about 6.52x and P99 ratio about 6.22x. The pure diversity
configuration scores 0.913; it is not an exactly equal-recall comparison.
These are selected points from a coarse budget sweep, not globally optimal
settings. Budgets were selected on the same 100 queries; there is no holdout.
Repeated timing does not increase the number of independent quality queries.
Cohere, other scales/distributions, cold queries, online construction, mutation
maintenance and memory are not established by these measurements.

## Reproduction

Build the standalone Lite benchmark target as in ../../README.md, then run:

```text
taskset -c 0 BUILD/lite_graph_route_probe SNAPSHOT DATASET NEW_OUTPUT 1536 uniform preserve 10
taskset -c 0 BUILD/lite_graph_route_probe SNAPSHOT DATASET NEW_OUTPUT 160 uniform diverse 10
taskset -c 0 BUILD/lite_graph_route_probe SNAPSHOT DATASET NEW_OUTPUT 128 uniform diverse_reverse 10
```

Use distinct outputs for five process repetitions and rotate the three commands.
The original exact commands and input paths are in final-commands.json. Snapshot:
/home/ubuntu/project/vsag-lite-independent-crud-quality-20261005/gist-100k-after.snapshot.
Dataset: /home/ubuntu/project/vsag-lite-datasets/gist/prepared-10k-100k/scale-100000.
Both inputs were generated in prior reproducible CRUD/dataset experiments.
They are not duplicated here due to size. `after` means the incoming-repair
implementation; this snapshot already underwent long CRUD.

For each command, `.csv` is the scalar diagnostic per-query output,
`.csv.api.csv` is actual API quality/timing summary, and
`.csv.api.csv.latencies.csv` contains every measured query latency. `-summary.csv`
is the scalar diagnostic summary. Scalar and API quality are reported separately.
Empty `.stderr` files confirm successful runs; command exit codes were checked.
SHA256SUMS covers the committed evidence. No dataset, binary or private handoff
rules are included. Next validate the simpler candidate with independent queries
and online construction/CRUD timings before proposing production adoption.
