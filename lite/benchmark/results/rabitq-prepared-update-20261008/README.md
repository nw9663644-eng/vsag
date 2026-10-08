# Reuse prepared RaBitQ updates

2026-10-08. Control library is 1b49e07600af3923ef67289648faf7662881c162;
candidate source identity is recorded in sources.json. This is a bounded
synthetic update study, not final three-distribution quality/performance acceptance.

## Source evidence and minimal change

The fixed-model adapter already prepared a code for identical-encoding checks,
but discarded it before ordinary Update normalized/encoded again. The codec now
retains normalized query and complete code in PreparedEncoding; the adapter moves
that same bundle into UpdatePrepared on its transactional clone. Input is
transformed/normalized/encoded once. Legacy ordinary Update delegates through the
same preparation; private fixed-model and trusted-caller constraints are explicit.
Shape, finite query and all metadata checks run before modifying adjacency.
Public signatures, model training and encoded persistence are unchanged.

| Workload | Control median CPU ms [range] | Candidate median CPU ms [range] | Median change |
|---|---:|---:|---:|
| 100 alternating first-coordinate changes;2000 synthetic 128dim,degree8/ef64 |15.405 [15.028,15.766]|14.954 [14.605,15.152]|-2.93%|

Seven fresh processes per mode, alternating library order, pinned CPU 0, same
Release external consumer, fixed training seed 47. Every update targets ID 0,
coordinate 0 alternates +0.125/-0.125; all other coordinates remain unchanged.
Timing uses process std::clock and excludes build, serialization and verification.
This is neither whole-vector replacement nor standard datasets. Both libraries
use the same consumer allocator replacement with fault injection off during
measurement. CPU ranges overlap; this small pilot does not establish a general
speedup. Full-state cloning remains the main target for further optimization.
All 14 final snapshots are retained in compressed JSON and are exactly equal,
including model, code planes, metadata, IDs, options and ordered topology. Only
final states are archived; unit/oracle fixtures cover intermediate mutation
behavior separately. This is not a new Recall or quality-gate measurement.

## Validation

Release CTest 5/5 and ASan+UBSan 7/7 pass. 9 RaBitQ API cases contain 2361 assertions.
Ordinary/prepared mutation snapshots match across 1/17/128/768/960 dimensions;
malformed query size, plane size, nonfinite query/norm and zero code norm are
rejected before state changes. Codec 28-record 7-dimension byte parity and legacy
360 paired graph mutations pass. Current shared/static/sanitized consumers pass
86 allocation-failure points with exact old snapshots retained; the count fell
because redundant allocations were removed. Lite executable source/header
coverage is 2197/2337=94.01%, excluding test bodies/vendor code. Format/tidy15 pass;
a Catch2 move-expression diagnostic and an isolated-declaration diagnostic were
repaired and rerun. No performance target or whole-project completion is declared.

## Reproduction and next step

```bash
python3 lite/benchmark/test_rabitq_candidate.py CANDIDATE_BUILD --measure-changed --baseline-build CONTROL_LIBRARY_DIRECTORY --output NEW_JSON_PATH
python3 lite/benchmark/test_rabitq_candidate.py CANDIDATE_BUILD
python3 lite/benchmark/test_rabitq_candidate.py CANDIDATE_BUILD --static
```

The saved control copy is outside Git at
/home/ubuntu/project/vsag-lite-rabitq-prepared-control-20261008. Rebuild its
recorded revision and configuration if unavailable; record any new binary hash.
The measurement helper saves the actual generated source and compressed final
snapshots alongside its JSON. Verify artifact hashes, recomputed medians and
exact final states with verify.py; this does not rerun the benchmark.
PreparedEncoding must come from the state's unchanged fixed model; there is no
new public prepared-data API or cross-model conversion guarantee. Actual changed
mutations still copy complete state for failure atomicity. Next work should stage
only mutation deltas, retain exhaustive failure-injection checks, then run the
standard SIFT/GIST/Cohere acceptance matrix. Existing PR source branches are frozen.

中文：本轮移除真实更新的重复归一化/编码，实际改值仍全状态事务复制。七次/模式单核合成试验中位15.405→14.954ms，范围重叠，不宣称普遍稳定加速；14个最终快照完整字节全等。通过86个分配失败点、9cases2361asserts及94.01% Lite范围覆盖率。下一重点仍是局部事务及标准数据集验收，不是继续叠加同类小优化。
