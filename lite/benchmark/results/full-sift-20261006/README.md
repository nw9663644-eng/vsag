# Full HGraph SIFT reference with query warmup

The existing Full benchmark gains optional query ef/warmup, raw latency samples and query-loop process CPU. Default CLI still uses ef128/no warmup; CSV fields append. No library source/ABI/policy/format change. `test_full_query_options.py` covers legacy CLI, nondefault ef256/warmup1, exact recall, raw count/order/percentiles and invalid numeric input.

## Measurement

CPU0, Linux x86_64, thread environments set to one. Full HGraph FP32: degree16, construction/query ef128, compressed graph, stored raw vectors. Three fresh processes build new graphs, warm once and time one pass over SIFT100k's already-observed rows[400,700). The preceding Lite runs use identical input/truth and warmup1/timed1. Different algorithms/graphs are compared. Full runs were not interleaved with Lite.

The benchmark was rebuilt from this branch. The installed Full library is reused, with exact path/hash in `artifacts.json` and loaded path in `environment.txt`; its source revision was NOT re-established here. This is not latest-upstream acceptance. Rebuild from known source/config before a final acceptance report.

| Warm Full metric, median of 3 | Value |
| --- | ---: |
| Recall@10 | 0.990333 |
| Build | 15.110 s |
| Query P50/P99 | 176.556 / 210.955 us |
| Query-loop CPU, 300 queries | 51.971 ms |
| Save/load | 53.031 / 67.458 ms |
| Snapshot | 57156886 bytes |
| Build/load steady RSS | 193564 / 192820 KiB |
| Whole-process peak RSS | 280836 KiB |

Query CPU includes copying, search, scoring and result bookkeeping; excludes warmup/file writes/save/load. Latency covers search wrapper and neighbor conversion. CPU is process time, not utilization. Load is warm. RSS retains query/truth/results but frees base input; matching Lite RSS is not measured, so no memory ratio is claimed.

All six pilot/warm runs passed Save/Load ID equality and relative distance tolerance 1e-5. Pilot no-warmup Recall0.991667 differs from warm rebuilt graphs0.990333; do not pool their graphs/timings. `pilot-no-warmup/` and `warm/` remain separate.

## Comparison boundary

`lite-initial-reference.json` summarizes three preceding Lite initial query runs: default ef256 Recall0.968667/P50 471.469us/P99 673.094us/query CPU136.056ms; diversity ef96 Recall0.977667/P50 232.604us/P99 314.454us/CPU67.525ms. All pass a common .95 gate, but quality differs and budgets are not globally optimal. Full has higher quality and lower latency at these points. Ratios are descriptive references, not controlled statistical speedup claims. Full mixed CRUD/maintenance has NOT been measured; prior Lite mixed savings are not Full-relative end-to-end gains.

Raw shared-object sizes have unequal debug/symbol content. Identical `strip --strip-unneeded -o OUTPUT INPUT` on copies yields Full40463344 bytes/Lite138064 bytes; hashes in `stripped-artifacts.json`. This compares one shared-object file, not complete distributions/dependency closures/deployment packages. Derived binaries are not committed or loaded. Raw sizes remain in `artifacts.json`. Full snapshot is smaller than the initial diversity Lite snapshot64213448 bytes: smaller library does not imply smaller index.

Lite's reduced library footprint is evident for these artifacts, but query/build performance remains behind this Full reference. Keep diversity OFF by default. Next: Cohere metric preparation, known-source Full build and aligned memory/CRUD protocol, then target optimizations based on those gaps.

## Evidence

Warm data retain900 timed rows, logs, protocols/commands, source/executable/library hashes, snapshot hashes, min/max and environment. No large snapshots, binaries or datasets committed. Server originals: `/home/ubuntu/project/vsag-lite-full-sift-20261006`. `run.py`, `warm.py`, `summarize.py` are the executed scripts. `python3 lite/benchmark/results/full-sift-20261006/verify.py` audits retained quality/options/counts/percentiles.

Actual checks: benchmark Release build, old/new CLI exact fixture and invalid inputs, clang-format15/clang-tidy15 (non-user warnings suppressed), raw count/P50/P99 audits, SHA256 and git diff checks passed. Only benchmark code changes; no new library coverage/sanitizer result claimed. Private fork only, PR sources unchanged.
