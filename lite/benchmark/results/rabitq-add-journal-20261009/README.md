# Journaled public RaBitQ Add

2026-10-09, control f44010c6392acf28eb54201a5bc42bba2df5dd1f.
This is bounded functional/performance evidence, not final standard-dataset acceptance.

## Change and safety boundary

Add prepares code and neighbor selection before writes, geometrically reserves
metadata/plane/ID/adjacency buffers, then inserts the new ID and appends its owned
record. Existing rows are captured before reverse-edge changes or pruning.
Failure swaps old rows back, truncates all appended lengths and erases the new
ID without allocation; fallback counters are restored. Capacity/bucket increases
can remain. No unconditional whole-index clone remains for default public Add,
but normal expansion can still move buffers. Model/API/encoded format are
unchanged. Experimental incoming adjacency uses the copy fallback; Remove still
copies full state. The method reuses existing codec, nearest/link and rollback
components, not a new graph implementation.

| Synthetic workload | Control CPU median ms | Journal CPU median ms | Change |
|---|---:|---:|---:|
| 100 new vectors, initial 2000x128, final 2100, degree8/ef64 |23.772|5.340|-77.54%|

Seven fresh processes per mode, alternating library order, CPU 0, fixed seed 47.
The shared external consumer appends IDs 2000..2099 with first-coordinate values
count*0.125 and unchanged other generated coordinates. The fixed model is not
retrained. Process CPU timing excludes build, serialization and checks. Fault
injection is off during timing; allocator replacement is identical for both.
All 14 final encoded snapshots are retained compressed and exactly equal. No
Recall, P50/P99, RSS, cold load or standard dataset result is claimed here.

## Validation

Release CTest 5/5 and ASan+UBSan 7/7 pass. 200 growing copied/journaled comparisons
cover empty state, geometric expansion, nonsequential/negative IDs and incoming
mode on/off, with exact snapshots after every Add. 11 API cases contain 3563
assertions. Current ordinary consumer checks 73 Add/Update/Remove allocation
failure points; the complex 32-node 17dim graph checks 159 Add failure points,
retaining exact snapshots in Release and sanitizer runs. Lite unit source/header
line coverage 2283/2437=93.68%, excluding tests/vendor. Format/tidy15 pass.
One sanitized external compile initially failed for disk space; it was rerun
with TMPDIR=/dev/shm after verifying the RAM filesystem permits execution.
No historical data or build evidence was deleted to work around that failure.

```bash
python3 lite/benchmark/test_rabitq_candidate.py BUILD --stress-add
TMPDIR=/dev/shm python3 lite/benchmark/test_rabitq_candidate.py SANITIZED_BUILD --stress-add --sanitize
python3 lite/benchmark/test_rabitq_candidate.py BUILD --measure-add --baseline-build CONTROL_DIR --output NEW_JSON
python3 lite/benchmark/results/rabitq-add-journal-20261009/verify.py
```

Saved control is outside Git at /home/ubuntu/project/vsag-lite-rabitq-add-control-20261009.
Rebuild its measured revision with matched flags if unavailable and record a new
binary hash. Final-state equality does not imply proof of every intermediate
mutation; the repeated-growth fixtures supply separate intermediate checks.
Next priorities are transactional Remove and standard three-distribution
quality/CPU/memory/long-CRUD acceptance. No PR source branch was updated.

中文：公开Add已移除每次整索引事务克隆，扩容仍会搬移缓冲区，失败后容量可保留但逻辑内容和快照恢复。200次增长逐状态全等、159复杂新增失败点和73普通失败点通过；11cases3563asserts，覆盖率93.68%。合成新增CPU23.772→5.340ms仅限该负载。删除仍全复制，标准数据集验收未完成。
