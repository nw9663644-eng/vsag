# Journaled public RaBitQ Update

2026-10-09, control 120835dbd04954108bc7f907bf8c633c88c3c44a.
Server 118.195.162.200 was verified as VM-0-10-ubuntu with internal 10.206.0.10;
source and library identities are recorded separately. This is a bounded
functional/performance study, not final dataset acceptance.

## Change and source evidence

UpdatePrepared changes one encoded slot and adjacency rows, not model, IDs,
slot mapping or container lengths. UpdateTransactional backs up that code and
records each affected row before its first write. Journaling covers inbound
erasure, outgoing replacement, reverse-edge pruning and repair. On exception,
metadata/planes are copied back, rows swapped back without allocation, fallback
counts/timing restored and the journal pointer cleared before rethrowing.
The public expected-error adapter remains responsible for translating failures.
Add/Remove still clone all state. Experimental incoming-index Update uses the
full-copy fallback; no public concurrent use is introduced. The directed inbound
scan still costs O(total edges), and high indegree can journal many rows. Formats,
fixed-model semantics, selection and query defaults are unchanged.

| Synthetic workload | Control CPU median ms | Journal CPU median ms | Change |
|---|---:|---:|---:|
| 100 alternating coordinate updates,2000x128,degree8/ef64 |14.894|4.794|-67.81%|

Seven fresh processes per mode, alternating library order, CPU 0, fixed seed 47,
same external consumer and same generated inputs. Build/serialization/checks
are excluded from process CPU timing. Allocation replacement is identical for
both modes with faults disabled during timing. All 14 final encoded snapshots
are retained compressed and are exactly equal. This is one synthetic workload,
not SIFT/GIST/Cohere, not whole-vector changes, not Recall, RSS or startup.

## Validation

Release CTest 5/5 and ASan+UBSan 7/7 pass. 200 continuous changed transactions
compare exact snapshots against copied transactions with incoming mode on/off.
10 API cases contain 2961 assertions. Existing current fault consumer covers 81
Add/Update/Remove failure points. A complex 32-node 17dim degree4 graph additionally
enumerates 180 failing allocations across Update IDs 0/5/20, every failure keeping
the complete snapshot unchanged; both Release and sanitizer consumers pass.
Lite source/header unit line coverage 2224/2378=93.52%, tests/vendor excluded.
Format/tidy15 pass; dependency warnings are not reported as a zero-warning Full
repository result. Source and artifact hashes, raw timing rows and final snapshot
bytes are verifiable without rerunning performance measurements.

```bash
python3 lite/benchmark/test_rabitq_candidate.py BUILD --stress-faults
python3 lite/benchmark/test_rabitq_candidate.py SANITIZED_BUILD --stress-faults --sanitize
python3 lite/benchmark/test_rabitq_candidate.py BUILD --measure-changed --baseline-build CONTROL_DIR --output NEW_JSON
python3 lite/benchmark/results/rabitq-update-journal-20261009/verify.py
```

Control library copy is outside Git at
/home/ubuntu/project/vsag-lite-rabitq-delta-control-20261009. If unavailable,
rebuild the recorded revision with matching settings and record the new hash.
Remaining priorities: Add/Remove transaction copies, inbound scanning costs,
then standard three-distribution quality/CPU/memory/long-CRUD acceptance. Do not
claim that all CRUD copies or performance gaps are solved. No PR branch is pushed.

中文：公开Update已从全状态复制改成旧编码与受影响邻接行的回滚日志，新增/删除和实验incoming模式仍全复制。200次逐状态对照全等，180复杂图失败点保持完整快照，覆盖率93.52%；单核合成CPU14.894→4.794ms仅对该负载成立，14最终快照全字节相同。下一步新增/删除事务与标准数据集验收，不能称项目完成。
