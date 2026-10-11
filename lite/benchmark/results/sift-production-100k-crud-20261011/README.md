# Current Lite SIFT100k real changed-value CRUD matrix, 2026-10-11

## Frozen protocol

Production C++a126a531da52a45c037b6d51e7fafc693505ed00, library SHA
0f729af8fd98323988f398d65ac75a9d67431889f2e4f87d05ed227aeba9374a.
Measured before committing the Python/tool/result supplement; identity.json pins
the measured tool sources, builder and library. Public FP32/FP16/RaBitQ8 builders.
Same SIFT128100k original base,100 existing queries,k10,degree16,build128,query512,
CPU0,one BLAS/OMP/MKL thread. One fresh process per storage, fixed order FP32,
FP16,RaBitQ. No concurrent build/test. Not a statistical performance conclusion.

Three rounds of10000 distinct IDs each: ID=(round*65537+operation*8191)%100000.
Replace with FP32(.875*current+.125*original donor), donor offset7919*(round+1).
Every replacement differs from the current full vector. Execute Update,Remove,Add
per ID:30000 replacements/90000 API mutation calls per storage,270000 total.
Queries only before/after the mutation block, not interleaved with writes.
FP64 direct-difference groundtruth is recomputed initially/finally; initial GT
matches the original subset GT byte-for-byte. All modes use the exact same final
groundtruth. Receipts contain original base, query, GT and replacement hashes.

## Current same-parameter results

| Metric | FP32 | FP16 | RaBitQ8 |
| --- | ---: | ---: | ---: |
| Initial Recall@10 | .988 | .988 | .975 |
| Changed-data Recall@10 | .989 | .989 | .983 |
| Build ms | 12968.672 | 11300.322 | 14053.185 |
| CRUD block ms | 10801.636 | 9340.009 | 12542.166 |
| API mutations/s | 8332 | 9636 | 7176 |
| Final query P50 us | 539.707 | 508.177 | 559.947 |
| Final query P99 us | 685.103 | 645.244 | 693.763 |
| Post-CRUD Save ms | 53.870 | 123.550 | 94.032 |
| Same-process warm Load ms | 55.963 | 48.467 | 68.997 |
| Snapshot bytes | 65600064 | 40000064 | 29600672 |
| Whole-process peak KiB | 252600 | 202436 | 206688 |

| API latency us P50/P99 | FP32 | FP16 | RaBitQ8 |
| --- | ---: | ---: | ---: |
| Update | 210.245 / 283.903 | 196.325 / 265.923 | 252.323 / 368.641 |
| Remove | 15.729 / 29.079 | 14.438 / 27.229 | 27.060 / 42.338 |
| Add | 129.597 / 200.734 | 93.498 / 155.536 | 133.046 / 181.446 |

All three native Save/Load roundtrips passed ordered-query result checks in the
driver. Final snapshot hashes are recorded in rows.json; formats differ by
storage, so cross-storage snapshot/neighbor equality is not expected.

RaBitQ has the smallest snapshot (29.60MB vs40.00/65.60MB). In these observations
it is slower than FP16 for final query and CRUD and has0.6percentage-point lower
recall. Equal parameters do not imply equal graph/quality/SIMD instructions.
This does not establish a same-recall win. Its whole-process peak is slightly
higher than FP16: compression is not a blanket peak-memory guarantee. Peak
includes base/query/replacements, graph construction and a second loaded index,
not isolated index memory. Warm Load and Save allocation history differ from
the separate fresh-load/loaded-state-save supplement. P99 uses only100 existing,
previously observed queries and is exploratory. Final recall increases relative
to initial while data changes; this is not proof of a better maintenance algorithm.

## Audit and replay

`run_sift_persistent_crud.py` prepares/executes within one SSH session to avoid
RAM inputs disappearing, refuses existing result output, and preserves small
query/truth/receipt/operation/neighbor/latency/command files. Replacement matrices
and snapshots are temporary and reconstructible from the archived generator and
retained original base plus receipts. No original source/data/results removed.
`verify_sift_persistent_crud.py RESULT_DIRECTORY` checks270000 API schedules,
600 initial/final truth-query states, ordered row schema, finite distances, query
P50/P99 from raw timings, input/source hashes and per-operation latency quantiles.
audit.json contains its derived summary. No new C++ tests were run because the
business source and library are unchanged from a126a53; previous validation and
its full-header tidy warning remain distinct. New preparation Python tests3/3.

## 中文结论及下一步

SIFT100k三存储真实改值已补测：FP32/FP16最终召回98.9%，RaBitQ98.3%。RaBitQ
索引最小，但本轮查询和增删改均慢于FP16；只一轮各模式、固定顺序，不称稳定
优势或性能达标。GIST召回问题仍未解决；下一补当前原生Full同配置/SIMD及同
召回率对照、更多查询/重复轮次和读写交错验收。只个人分支，PR2904/2926不改。
