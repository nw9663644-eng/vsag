# RaBitQ invalid-ID and complete-encoding fast paths

2026-10-08. Control library is the integrated public candidate at
`aa79efe2545448aa1f5a1385e0571b6a3bedeee9`; candidate source changes are
identified in `sources.json`. This is not general CRUD or final quality acceptance.

## Source evidence and change

Existing `GraphBackend::Update` returns for validated identical stored data;
BruteForce checks duplicate/missing IDs before mutation. The new public RaBitQ
adapter applies these boundaries before cloning its transaction: duplicate Add,
absent Update/Remove, and identical encoded Update. Encoding identity includes
both planes and all six metadata fields, using exact stored bytes. Metadata-only
changes do not count as no-ops. Legacy experimental mutable Update is unchanged.

## Bounded measurement

| Workload | Control median CPU ms | Candidate median CPU ms | Change |
|---|---:|---:|---:|
| 100 identical Update calls, 2000 live synthetic 128dim vectors | 15.367 | 0.376 | -97.55% |

Seven fresh processes per library, alternating library order, CPU 0, same Release
consumer and generated vectors. Degree8/ef64, deterministic training seed47.
Process CPU time uses std::clock. Build, initial/final serialization and checks
are outside the timed loop. Raw per-process measurements and exact generated
consumer source are included; both library hashes are recorded. The consumer's
allocation replacement is the same for both libraries, with fault injection off
during measurement. This is a synthetic same-value Update test, not SIFT, GIST
or Cohere, not query latency, not cold start and not evidence for changed-vector
performance. The candidate snapshot remains exactly unchanged. The control may
rewrite topology during same-value Update; these are deliberately different
maintenance semantics, not an identical mutation trace speedup.

## Correctness and safety

Release CTest 5/5, ASan+UBSan 7/7 pass. Eight RaBitQ unit cases contain 2291 assertions
including five dimensions' same-value snapshot identity and plane/metadata
discriminators. Shared/static/sanitized external consumers pass 91 allocation
failure points with unchanged snapshots. Invalid-ID prechecks do not trigger the
first injected allocation on the tested toolchain. Lite source/header unit line
coverage is 2171/2310=93.98%, with test bodies/vendor code excluded.

## Reproduction

```bash
python3 lite/benchmark/test_rabitq_candidate.py CANDIDATE_BUILD
python3 lite/benchmark/test_rabitq_candidate.py CANDIDATE_BUILD --static
python3 lite/benchmark/test_rabitq_candidate.py SANITIZED_BUILD --sanitize
python3 lite/benchmark/test_rabitq_candidate.py CANDIDATE_BUILD --measure-noop --baseline-build CONTROL_LIBRARY_DIRECTORY --output NEW_JSON_PATH
```

The measured control copy is outside Git at
`/home/ubuntu/project/vsag-lite-rabitq-noop-control-20261008`; rebuild aa79efe with
matching Release/ISA settings if unavailable, and record the new binary hash.
Measurement writes its actual generated source alongside the JSON. Output must
be new. Source hashes and raw rows can be verified without rerunning benchmarks.

## Remaining cost

A truly changed Add/Update/Remove still copies the entire state. The no-op
precheck also introduces an additional encoding pass for changed Update;
prepared-code reuse and transactional delta staging remain future work. OOM
error construction can allocate. No claim is made that all CRUD copying, all
allocator overhead or graph-quality issues are solved; same-value Update is not
a repair request. Existing independent encoded format and fixed model remain.

中文：本轮仅消除重复/缺失ID及完整编码同值请求的事务复制；合成单核同值Update收益不能推广到真实改值或三个标准数据集。实际改变状态仍复制全状态，且当前更新预检查多一次编码，需要下一步复用编码并优化真实事务。保持91个分配失败点原快照不变、8cases2291asserts及93.98% Lite范围覆盖率；PR来源未改。
