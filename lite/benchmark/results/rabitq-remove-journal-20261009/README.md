# Journaled physical RaBitQ Remove

2026-10-09, control 1833328108d0cde5f684501c32d4864f0fefa411.
This is bounded deletion evidence, not final standard-dataset acceptance.

## Source-based change

Physical Remove moves the last code/ID into the hole and repairs directed
neighbors. The transaction saves both codes, IDs and rows, journals inbound
erasure and last-slot rewrites, and retains the erased map node via C++17 extract.
If repair/allocation fails it restores original container lengths within retained
capacity, codes, IDs, rows and original mapping. Reinsertion uses the same node
and cannot exceed old map load; no other map insertion/rehash occurs during
Remove. Failure counters/timing and transient journal pointers are restored.
No allocator call is needed for rollback. The public bool contract is unchanged:
false still cannot distinguish an absent ID from a failed transaction.
Experimental incoming adjacency retains full-copy fallback. Default public
Add/Update/Remove now avoid unconditional complete-state clones; growth, inbound
scans, high-indegree changes and transient journals still have costs. Formats,
query behavior, fixed model and caller-serialization requirements are unchanged.

| Synthetic workload | Control CPU median ms | Journal CPU median ms | Change |
|---|---:|---:|---:|
| Delete IDs 0..99 from 2000x128; final 1900; degree8/ef64 |11.075|2.542|-77.05%|

Seven fresh processes per mode in alternating library order, CPU 0, seed 47,
same Release consumer and generated initial vectors. Timing excludes initial
build and final serialization/checks. The consumer allocator replacement is the
same for both modes; injection is off during timing. All 14 complete final
encoded snapshots are archived compressed and exactly equal. This is neither
SIFT/GIST/Cohere, whole-vector update, Recall, P50/P99, RSS nor cold-load evidence.

## Verification

Release CTest 5/5 and ASan+UBSan 7/7 pass. 200 copied/journaled deletes compare
intermediate snapshot bytes with alternating hole/last-slot deletion down to
singleton/empty; both incoming modes are covered. 12 API cases contain 4365
assertions. Ordinary consumer checks 70 current allocation failure points across
all CRUD. A 32-node 17dim degree4 fixture exhausts 141 Remove failure prefixes for
IDs 0/5/20/31, including last-slot deletion, exact snapshot restoration and zero
observed allocator calls after the injected failure until Remove returns.
Release and sanitizer stress consumers pass. Lite source/header unit coverage
2324/2499=93.00%, excluding test/vendor bodies. Format/tidy15 pass. The first
coverage build failed for /tmp disk space and was rerun successfully with
TMPDIR=/dev/shm and one build worker; failure is not counted as a passing check.
No historical data was deleted. The helper's allocation monitor observes C++ new
calls in these fixtures; it is not a proof of every OS/allocator configuration.

```bash
TMPDIR=/dev/shm python3 lite/benchmark/test_rabitq_candidate.py BUILD --stress-remove
TMPDIR=/dev/shm python3 lite/benchmark/test_rabitq_candidate.py SANITIZED_BUILD --stress-remove --sanitize
TMPDIR=/dev/shm python3 lite/benchmark/test_rabitq_candidate.py BUILD --measure-remove --baseline-build CONTROL_DIR --output NEW_JSON
python3 lite/benchmark/results/rabitq-remove-journal-20261009/verify.py
```

Saved control is outside Git at /home/ubuntu/project/vsag-lite-rabitq-remove-control-20261009.
If unavailable, rebuild its measured revision with matched settings and record
new binary hashes. Exact final equality is distinct from the separate 200
intermediate-state fixtures. Next priority is standard three-distribution
quality/CPU/memory and long mixed-CRUD acceptance; no PR source branch changed.

中文：默认删除已实现局部回滚，保留被删映射节点并恢复补洞编码/ID/邻接，141复杂失败点观察回滚分配为0、原快照不变；200逐状态删除对照、12cases4365asserts、93.00% Lite覆盖率通过。合成删除CPU11.075→2.542ms仅限此负载。默认CRUD均不再每次全状态复制，扩容/扫描等成本仍存在；标准三分布及长期混合验收仍待完成。
