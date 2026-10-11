# GIST100k RaBitQ route/selection diagnostic, 2026-10-11

Production remains a126a53 (measured repository HEAD7173cc0; this supplement
does not change business C++). Initial GIST960100k,100 existing queries,k10,
degree16/build128/query512,CPU0,one OMP/BLAS/MKL thread. Not a CRUD-after graph.

## Source evidence and diagnostic method

Existing graph_search_impl visits nodes before filter acceptance and routes
using the same coarse heap regardless of the filter. An accept-all callback
records visited IDs and ranks all visited nodes by the full8-bit distance,
whereas the public unfiltered path reranks only its coarse512 shortlist.
The probe uses the existing MutableGraphState and full_distance/top_k functions,
not a separate ANN implementation or modified production routing algorithm.

For all100 queries, the internal formal result matches the public API's ordered
IDs and float distance bits. Traced visited count equals the formal count and
the callback's distinct visited count. Native snapshot preparation exercises
its Save/Load roundtrip. Exhaustive encoded scan scores all100000 records using
the same frozen model/full distance; it is a quality diagnostic, not a proposed
production implementation or query timing benchmark.

| Diagnostic | Hits out of1000 | Recall@10 |
| --- | ---: | ---: |
| Formal query ef512 | 859 | .859 |
| True neighbors among visited nodes | 860 | coverage .860 |
| Full8-bit rerank of all visited nodes | 859 | .859 |
| Full8-bit scan of all encoded records | 997 | .997 |

Of141 formally missing truth IDs,140 were never visited,1 was visited but not
returned. Mean visited nodes3696.15. Under this initial workload, expanding the
rerank shortlist alone does not fix the main loss. The encoded ranking ceiling
is much higher, supporting routing coverage as the next optimization target.
This does not prove a universal quantization guarantee, a CRUD root cause, or
that a particular routing change will improve recall or performance.

## Verification, raw evidence and limitations

trace.queries.csv records all100 query summaries; trace.truth.csv records1000
individual truth-ID flags. Archived GT/query hashes, measured headers/probe,
production library/static archive/probe hashes and commands are in identity.json.
verify_gist_route_quality.py verifies source/input hashes,1000 GT IDs, formal hit
counts against the native prepare trace and mutually consistent missed-ID counts;
audit.json reports PASS. Input snapshot hash/bytes are pinned, its large body
was temporary. No original source/data/old result/library was removed.

The measured probe first failed tidy15 on float memcmp, multiple declarations
and implicit bool-to-count conversions. Final source compares memcpy'd uint32
bits, splits declarations and uses explicit casts; format15 and final source-only
tidy15 pass. Measured source is archived unchanged; final executable differs in
hash and was compiled/linted, not rerun on this100k experiment. No fresh library
Release/SAN/coverage claim is made because production sources did not change.
These diagnostic passes are not a fresh full test suite or a speed improvement.

Replay: compile the archived measured probe with c++ -O3 -DNDEBUG -std=c++17
-DVSAG_LITE_RABITQ_X86_SIMD -Isrc -Iinclude plus the pinned current static library.
Run run_gist_route_quality.py in a fresh result destination after adapting only
host/output/probe paths. It refuses an existing identity.json and prepares/runs
within one session so RAM snapshots survive. The final public helper is intended
to perform the same bit-level check; use archived measured source for exact replay.

## 中文结论与下一步

初始GIST100k正式召回85.9%，全编码扫描99.7%；141个漏召回中140个没被访问。
全部已访问节点精排仍85.9%，本组主要缺口是路由覆盖，不是简单扩大精排名单。
下一步先隔离验证更准确的候选评分/扩展策略，维持degree/build/query预算和模型，
记录候选质量与耗时，不能直接开启全扫描或提高ef冒充优化。尚需CRUD后诊断及
跨数据集复核；未修改正式查询，未推PR2904/2926，不宣称验收完成。
