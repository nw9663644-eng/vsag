# Full HGraph restored-data CRUD comparison (2026-10-06)

Full FP32 HGraph completed six single-core physical-delete runs on normalized
Cohere 100k / 768 dimensions / 600 previously observed queries (original rows
400..999). Every run started at Recall@10 0.952 and ended at 0.9405, below the
predeclared 0.95 floor. All API mutations and post-CRUD Save/Load consistency
checks completed. Completion does not mean the quality gate passed.

| Query cadence | End Recall@10 | Mixed Recall@10 | Mutation CPU ms | Query CPU ms | Whole mixed CPU ms | Query P50/P99 us | Quality passes |
|---|---:|---:|---:|---:|---:|---:|---:|
| One query per four mutations | 0.9405 | 0.9453 | 393.006 | 293.125 | 691.541 | 294.673 / 363.532 | 0/3 |
| One query per forty mutations | 0.9405 | 0.9480 | 389.877 | 34.429 | 427.079 | 344.732 / 416.800 | 0/3 |

CPU/latency numbers are medians of three process runs. Six short Top-10 query
events occurred across the first cadence (two in each run); none occurred in the
second cadence's sampled queries. The benchmark retains these short results,
counts missing neighbors as recall misses, and records returned_count in raw
mixed CSV. It does not invent missing neighbors or treat API errors as misses.
The legacy non-CRUD path still requires exactly k results.

## Source evidence and profile

- Official include/vsag/index.h defines force_update and FORCE_REMOVE. Full
  HGraph hgraph.cpp UpdateVector(..., true) writes codes without Lite's local
  update rewiring; this is a matched logical API workload, not identical
  maintenance algorithms.
- hgraph_modify.cpp moves the last slot on physical deletion. GraphDataCell::Move
  and SparseGraphDataCell::Move implement this operation; compressed graph uses
  the throwing default GraphInterface::Move in the current known library.
- Initial compressed + support_force_remove fixture failed with "Move not
  implemented in GraphInterface". Its log is retained. Only the opt-in FP32
  mixed profile uses flat + support_force_remove=true. Existing compressed
  pure-query/load-only baselines are unchanged and must not be silently merged
  with this physical-delete profile.
- Full shared library comes from the previously recorded d18c82a cached
  incremental build, not a fresh full rebuild or latest upstream. Actual source,
  executable, shared-library and dataset SHA-256 are in provenance-sha256.json.
  Benchmark source parent is 72f4960; changed runner source is hashed separately.

## Workload and timer boundaries

Full runner syntax:

```sh
full_rabitq_dataset_benchmark DATASET SNAPSHOT fp32 128 1 1000 1
# Last arguments: ef_query, warmup_rounds, cycles, query_every.
```

CPU affinity is core 0. Degree 16, ef_construction 128, query ef 128, one warmup
round. Cadences 1 and 10 each have three independent builds, alternating cadence
order. Each cycle selects external ID (cycle * 8191) % 100000, performs changed
UpdateVector(force=true), restores original UpdateVector(force=true), physically
removes the ID, then adds its original vector. Live counts are checked after
remove/add. Queries run only after complete restoration, so frozen ground truth
remains applicable. Temporary coordinate +0.125 is not renormalized; this is not
a persistent cosine-update, concurrent, or large-churn acceptance test.

Mutation CPU includes input-copy/setup, API calls, timing and sample bookkeeping.
Query CPU includes API/output conversion and latency sample bookkeeping; hits are
counted afterward. Whole-loop CPU includes hit counting and inter-operation
bookkeeping. Original base-file reread, build, initial queries, final quality
scan and Save/Load are outside mixed-loop CPU. API timers use steady_clock;
CPU timers use process clock. Build/initial-query fields in stdout remain
pre-CRUD; post-CRUD recall is specifically in .crud.csv. Post-CRUD roundtrip
compares all 600 returned ID sequences and distances (1e-5 relative scale).

## Comparison with frozen Lite evidence

The earlier cohere-matched-20261006 evidence used the same normalized base,
queries, 1,000 cycles, ID order and cadences. Lite default query ef 768 and online
diverse query ef 256 both passed the final floor, ending at 0.957833 / 0.960333.
Their whole-loop CPU medians were 3870.573 / 2379.522 ms for cadence 1 and
1439.872 / 1385.265 ms for cadence 10. Lite maintenance ef remains 128.

These are historical measurements, not interleaved Full/Lite reruns. Full's
lower query/maintenance times here are not an equal-quality speedup because
Full fails the common quality floor and its update implementation does different
work. Full alone should first be calibrated on the existing validation split
under this physical-delete profile; freeze the selected budget before another
final evaluation. The final 600 queries are already observed, not a new blind
holdout. Do not claim global optimality or a final performance victory.

## Verification and retained failures

- test_full_mixed.py: two small cadences, all four successful API mutations,
  live counts, raw hit/percentile accounting, Save/Load, legacy path, seven
  invalid CLI combinations. Tiny graph post-CRUD quality is reported separately;
  it is not asserted to be perfect connectivity.
- clang-format-15 --dry-run --Werror and clang-tidy-15 with warnings-as-errors
  passed for the runner. Third-party header warnings were suppressed by tidy;
  this is not whole-repository tidy or Full sanitizer coverage.
- audit.py checked 6,000 cycles (24,000 API mutations), 3,300 raw mixed query
  rows, hit accounting and nearest-rank P50/P99, fixed budgets and six successful
  roundtrips. End recall is computed by the runner's full 600-query scan, not
  independently reconstructed from the cadence samples.
- first-strict-topk-failure retains the first large run that stopped when a query
  returned fewer than k results. Reporting was then extended to retain valid
  short results; parameters and the quality floor were unchanged.
- Snapshots stay on the server; only scripts, raw CSV, logs and metadata are
  committed. Original logs retain whitespace; published copies trim trailing
  whitespace and preserve original SHA-256 in original-evidence-sha256.json.

No Lite library code or default graph policy changed. Push target is the personal
experiment/lite-rabitq-next-20260926 branch only. PR #2904 and #2926 source refs
remain frozen.
