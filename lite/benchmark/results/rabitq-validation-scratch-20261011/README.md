# RaBitQ contiguous reverse-adjacency validation, 2026-10-11

## Scope and source evidence

Parent `109d554f70c1ea46cecf05a232a18515fa766ce5` enabled public reverse
adjacency. `MutableGraphState::Validate` then rebuilt a full row-allocated
reverse graph, copied every actual incoming row and sorted both row copies.
Both construction/native Load and `save_mutable_snapshot` invoke Validate.
This candidate replaces only that comparison with three contiguous local
buffers: offsets, cursors and sorted actual incoming sources. Traverse outgoing
edges in ascending source order and consume the matching sorted reverse edge.
Every target cursor must end exactly at its row boundary. The original outgoing
bounds/self-edge/duplicate/degree, ID map and cached-count checks remain.

No validation is disabled. No public API, snapshot version, graph edges, search,
quantizer, SIMD kernel, incoming construction or FP32/FP16 backend changes.
The CSR/contiguous-buffer organization follows existing internal GraphTopology
and snapshot block-I/O structures, not a new Full VSAG algorithm transplant.

## Five paired fresh processes per dataset and operation

GIST960 and normalized Cohere768, 100k vectors. CPU0, one OMP/BLAS/MKL thread;
degree16/build128/query512. Two zero-CRUD builders only prepare the snapshots
and exercise native Save/Load ordered-query verification. Each fixed snapshot
is used by both libraries; five alternating control/candidate pairs for Load
and five for loaded-state Save per dataset (20 loads,20 saves).
No builds/tests/lint overlap timed measurements. Inputs and snapshots use RAM;
fresh processes do not imply cold disk I/O. Save times open+Save+close after Load,
not construction or long CRUD. This is Lite-before versus Lite-after, not Full.

| Dataset | Load old/new median ms | Change | Save old/new median ms | Change |
| --- | ---: | ---: | ---: | ---: |
| GIST100k | 104.207 / 93.943 | -9.85% | 71.492 / 62.060 | -13.19% |
| Cohere100k | 95.253 / 87.440 | -8.20% | 62.051 / 53.993 | -12.99% |

| Dataset | Loaded RSS old/new KiB | Loader process peak old/new KiB | Snapshot bytes |
| --- | ---: | ---: | ---: |
| GIST100k | 132992 / 132272 | 156952 / 153216 | 112804416 |
| Cohere100k | 113944 / 113300 | 137540 / 134244 | 93603552 |

All20 Save outputs were SHA-256 checked by the runner against the input snapshot
before their exact temporary paths were removed. Initial GIST and Cohere snapshot
hashes are respectively `f5fc771b74dedebcb72931e6a9e7113e47332e30319eb67d6da4406e70ffe265`
and `35ee729f8ebe6bd9ee54811b47fe48c618b9cdba3c822be69bc498c63690434b`.
Control/candidate library hashes and measured sources are pinned in identity.json.
Large RAM snapshots are not archived; original base inputs and old evidence remain.
RSS differences include allocator-retained validation pages, not permanent layout
compression. This protocol is not the prior post-CRUD build-then-Save pair, so it
does not prove that earlier regression is fully resolved. No new recall, query
latency, CRUD throughput or native Full improvement is claimed.

## Verification and reproducibility

Release6/6, ASan/UBSan5/5, coverage-build5/5 and RaBitQ-disabled4/4 tests pass.
Existing allocation-failure rollback tests pass. New exact-multiset tests cover
empty/singleton, unordered rows, missing/extra/duplicate/wrong/invalid sources,
invalid outgoing target and one target with256 incoming sources.
Gcov for graph_state.h from the current API-test translation unit reports92.08%
of1161 lines; this is not whole-library coverage or a fresh union of all TUs.
Format15 and git diff --check pass. Full header-filter tidy15 fails on the
unchanged line78 `const uint32_t tail_bits = static_cast<uint32_t>(...)` with
modernize-use-auto. Changed-line tidy15 passes; both logs are retained. Do not
report a clean full lint run.

Run `python3 lite/benchmark/verify_rabitq_validation.py RESULT_DIRECTORY` to
audit40 rows,43 command exits, pairing, raw CSV/median agreement and archived
source hashes. `benchmark_rabitq_validation.py` records exact commands and refuses
an existing result directory. To replay, rebuild the parent into a separate
control directory, rebuild the candidate, and adapt only host/output paths to
a fresh destination. Small raw results, source, patch and validation logs are
archived here. Baseline library was hashed and copied before rebuilding.

## 中文结论与剩余验收

保留全部正反向一致性校验，用连续缓冲减少整图临时重建和逐行分配；两组100k
五对实验的热加载中位数下降约8%～10%，已加载状态保存下降约13%。这些不是
Full对照、冷启动、查询或CRUD收益。GIST100k召回缺口、最新Full配置/SIMD与
质量对齐、读写交错长期CRUD、完整部署包仍待验收。只推个人实验分支，不更新
PR2904/2926，也不宣称项目完成。
