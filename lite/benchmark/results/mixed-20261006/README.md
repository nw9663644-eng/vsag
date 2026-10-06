# Serial mixed query/mutation pilot, GIST100k

2026-10-06, base commit b50ea57c08ac8353a4f8b5d4dea55ad8ffda5a7c.
Library code is unchanged. The benchmark adds optional QUERY_EVERY after
CRUD_CYCLES. Omitting it keeps the existing grouped mutation flow. An explicit
value must be 1..CRUD_CYCLES. New .mixed.csv records every interleaved query's
latency and query-row index. CRUD summary appends query cadence/count, mixed
aggregate recall, query P50/P99, query CPU and total mixed-loop CPU.

## Workload fixed before running

CPU0, serial operations on the previous default/online-diversity graphs already
constructed at budget 128 and subjected to 1,000 same-vector churn cycles.
Default runs the default library; candidate runs the opt-in diversity library,
so Add/Update continue their respective online policies. Both maintenance
budgets stay 128. Query budgets are frozen 8192/512 from the previous final study.
All 600 queries are previously observed final-study rows, not a new blind set.

Each process executes 20,000 cycles. A cycle selects original slot i*8191 modulo
100,000 and its original external ID, updates first coordinate by +0.125, restores
the original vector, removes it, and reinserts it. That is 80,000 mutation calls.
Every 10 completed cycles issues one query, for 2,000 queries and a 1:40
query-to-mutation-call ratio. The 20,000 selected IDs are distinct within this
run (20% of the base), and each query occurs only after the whole restored cycle,
so the original truth is valid. Queries repeat in dataset order; mixed aggregate
recall weights this repeated/event sequence and is not 600 independent samples.

At the end, all 600 queries are evaluated once, and Save/Load must preserve each
result ID and distance exactly. Cycles restore content, but not necessarily graph
structure. This does not exercise concurrent readers or arbitrary update shapes.

| Mode | End Recall@10 | Mutation CPU s | Query CPU s | Mixed CPU s | Mixed query P50 us | Mixed query P99 us |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| default | 0.941167 | 25.991 | 35.070 | 61.084 | 17770.442000 | 19192.779000 |
| diverse | 0.940667 | 28.339 | 4.333 | 32.690 | 2207.488000 | 2651.458000 |

Both end-point quality gates pass 0.90 with nearly equal recall (0.941167 versus
0.940667). Initial recall was 0.954/0.950. Candidate mixed-loop CPU is 32.69 s
versus 61.08 s, a 1.87x selected-workload ratio. Its mutation CPU is about 9.04%
higher, while query CPU is substantially lower. This is a more relevant tradeoff
than extending the earlier 8.41x query-only ratio to all workloads.

Each mode has ONE fresh process: these are descriptive pilot results, not a
repeated-run speedup estimate. Workload order is candidate then default; order,
CPU frequency and mutation schedule can affect timings. Other read/write ratios,
SIFT/Cohere, all-record churn, sustained millions of calls, concurrency and
large vector displacements remain unvalidated. No default adoption is implied.

## Timing definitions and raw data

With interleaving enabled, crud_loop_cpu_ms sums mutation-phase CPU including
vector preparation, success checks and timing bookkeeping. mixed_query_cpu_ms
covers the query calls and clock bookkeeping, excluding result scoring and
sample output. mixed_loop_cpu_ms covers the complete interleaved loop, including
scoring and other overhead; it excludes initial diagnostics/load/warmup, final
quality queries, Save/Load and file writing. Phase sums need not equal total.
P50/P99 are wall latency; operation P50 includes success-check overhead.

All 40,000 mutation-cycle rows (four latencies each) and 4,000 query-event rows
are published. Every reported operation/query percentile was recomputed from raw
samples. Mixed/event recall is an aggregate counter; per-event hits and per-query
post-cycle results are not dumped. Summary end recall and exact reload checks
were checked by the running program. This is not an independent full truth audit.

Release and ASan updated fixtures cover successful interleaving, query count,
quality on a small exact fixture, P99>=P50 and cadence-range rejection. Tidy/format
version 15 and diff checks passed. No library tests were broadened because only
the benchmark/its fixtures changed; previous API library regressions are retained.

## Reproduction

```text
taskset -c 0 DEFAULT_BUILD/lite_graph_route_probe DEFAULT_SNAPSHOT DATASET NEW_OUTPUT 8192 uniform preserve 1 20000 10
taskset -c 0 DIVERSE_BUILD/lite_graph_route_probe DIVERSE_SNAPSHOT DATASET NEW_OUTPUT 512 uniform preserve 1 20000 10
```

DIVERSE_BUILD requires ENABLE_DIVERSE_NEIGHBOR_EXPERIMENT=ON; default is OFF.
The snapshots and precise commands are listed in commands.json. Source and both
library/probe hashes accompany the results. Large inputs remain on the host.
Protocol was written before measurement; raw evidence is under
/home/ubuntu/project/vsag-lite-mixed-20261006. Next repeat the relevant workload
with controlled order and additional ratios/distributions before broader claims.
