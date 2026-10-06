# VSAG Lite acceptance and adoption report, 2026-10-06

## Scope and delivery state

This consolidates recorded experiments, not a new performance run.
Evidence parent: a 66b 7b 4e 5903224dbb 197e 6238cd 5c 8818ec 1773.
Linked experiments retain their own measured source, binaries, protocols and hashes;
historical runs are not relabeled as measurements of current source.
Advanced development is on personal branch experiment/lite-rabitq-next-20260926.
PR #2904 and #2926 have not received subsequent changes. Updating their source
branches requires separate user approval.

Lite has standalone build/install, BruteForce, FP32/FP16 graph storage, runtime SIMD,
external-ID filtering, serial Add/Update/Remove/Search and validated Save/Load.
Query overrides are separate from construction and maintenance budgets.
Calls still require external serialization. Online diversity remains opt-in and OFF
by default. FP16 is not 8bit RaBitQ: codec/layout/search probes do not deliver a
public quantized Lite backend.

## Requirements and boundaries

| Requirement | Evidence | Acceptance boundary |
|---|---|---|
| Standalone build/configuration/example | [Historical report](FINAL_REPORT.md), [installed API consumer](results/query-options-20261006/README.md) | Implemented; final packaging must identify its delivery commit |
| CRUD/filter/persistence | [API regressions](results/query-options-20261006/README.md), [CRUD samples](results/api-crud-20261006/README.md), mixed studies below | Serial and restored-data workloads; concurrent CRUD and arbitrary persistent displacements unproven |
| Architecture and API scope | [English design](../../docs/docs/en/src/development/lite_first.md), [Chinese](../../docs/docs/zh/src/development/lite_first.md) | Dedicated Lite API and retained subset; not complete Full API equivalence |
| Two small-data configurations | Historical 10k/100k; three 100k distributions below | 1M is optional scale-boundary work, not a stated prerequisite |
| Binary/snapshot/load/memory/CRUD/P50/P99/recall | Historical report and linked raw studies | Separate lifetime/load-only peaks; shared-object size is not deployment dependency closure |
| Improvement over Full in footprint/load/memory | [Load-only probe](results/load-memory-20261006/README.md) | Default RSS -23.38%, warm load -25.26% for recorded compressed Full profile; not reverse-ON memory or cold start |
| Mentor: single-core build/search and Full | CPU0 protocols, corrected Full below | CPU pinning is not utilization/cycles/cache-miss/flame-graph attribution |
| Mentor: SIFT/GIST/Cohere, 768dim+ | SIFT128, GIST960, normalized Cohere 768 | Distributions covered; GIST gate 0.90, not 0.95 |
| Mentor: 8bit RaBitQ | [Feasibility](RABITQ_LITE_FEASIBILITY.md), probes in benchmark README | Experimental; public CRUD/filter/snapshot-compatible quantized backend remains open |

Historical Release/ASan/UBSan, installed-consumer, format 15/tidy 15 and coverage
checks retain their source revisions. This documentation change claims no new
implementation test run or new coverage percentage.

## Three distributions

Selected fixed configurations are not a global optimum. Each cycle is changed
Update (+0.125 in coordinate zero), restore Update, Remove, Add original.
Queries occur after restoration; original truth remains valid. Each cycle has
four mutations: 1:4 and 1:40 mean queries per mutation calls. Final-split budgets
were frozen before observation; those queries are now observed and cannot be
reused to select a new supposedly blind optimum.

| Dataset/study | Default/diversity query budget | End Recall@10 default/diversity | Gate | Workload |
|---|---|---|---|---|
| [SIFT100k/128dim](results/sift-matched-20261006/README.md) | 256/96 | 0.966333/0.976333 | 0.95 | 300 queries; 2000 cycles; 3 processes per mode/cadence |
| [GIST100k/960dim](results/mixed-20261006/README.md) | 8192/512 | 0.941167/0.940667 | 0.90 | 600 observed queries; 20000 cycles; ONE process per mode, 1:40 pilot |
| [Cohere 100k/768dim](results/cohere-matched-20261006/README.md) | 768/256 | 0.957833/0.960333 | 0.95 | 600 queries; 1000 cycles; 3 processes per mode/cadence |

Construction/maintenance remain 128. Cohere caller normalization was verified
against raw cosine truth using exact stored-L2 Top-10; no public cosine metric
was introduced. Queries do not observe temporary unnormalized updates.
All these studies check post-CRUD snapshot roundtrips.

| Dataset | Queries:mutations | Whole-loop CPU ms default/diversity | Diversity change | Interpretation |
|---|---|---:|---:|---|
| SIFT | 1:4 | 2160.586/1944.176 | -10.02% | Query savings offset higher maintenance |
| SIFT | 1:40 | 1315.469/1498.993 | +13.95% | Write-heavy regression; do not default-enable |
| GIST | 1:40 | 61083.855/32689.577 | -46.48% | Single-process descriptive pilot; repeat before speedup claims |
| Cohere | 1:4 | 3870.573/2379.522 | -38.52% | Useful selected query-heavy workload |
| Cohere | 1:40 | 1439.872/1385.265 | -3.79% | Small gain, higher maintenance; not universal |

Maintenance increases about 19% on SIFT, about 9% on GIST pilot, about 8.6% on
Cohere 1:40. Initial construction pilot overhead is about 16% for SIFT and 17.6%
for Cohere, excluded from mixed CPU. Query latency gains do not establish a
build-plus-maintenance lifetime gain. Phase CPU sums can differ from whole-loop
CPU because scoring/bookkeeping scope differs.

[Earlier offline GIST holdout](results/gist-holdout-20261006/README.md) failed
0.90 for all three frozen configurations (end 0.866667/0.846/0.843333).
Preserve that negative evidence: later actual-online policy and budgets are
separate configurations, not retroactive passes. The [online query-only GIST
study](results/online-final-20261006/README.md) had 0.954/0.950 recall and 8.41x
selected P50 ratio. Its coarse selection and high default budget do not prove
an optimal baseline or 8.41x mixed-CRUD gain.

## Correct Full comparison

[Corrected Full physical-delete study](results/full-reverse-20261006/README.md):
FP32 flat, support_force_remove=true, use_reverse_edges=true, raw vectors,
degree 16, construction/query 128. Recorded known-source d 18c 82a shared library
was built incrementally with cached dependencies, not clean latest upstream.
All six runs pass end Recall@10 >=0.95 (0.951); all 3300 sampled mixed queries
return ten results; all 24000 mutations succeed; six snapshot roundtrips pass.
Four permanent tiny delete regression tests and twelve controls also pass.

| Queries:mutations | Full end recall | Full mixed CPU ms | Lite default/diversity CPU ms |
|---|---:|---:|---:|
| 1:4 | 0.951 | 895.896 | 3870.573/2379.522 |
| 1:40 | 0.951 | 613.449 | 1439.872/1385.265 |

Full is faster in these batches at the common floor. Lite recall is higher;
runs were not interleaved Full/Lite; forced Full update and Lite local rewiring
perform different maintenance. This is not exact equal-quality performance or
universal Lite CPU superiority. Reverse-OFF failures remain evidence of that
unsafe profile, superseded as the valid comparison. No Full library fix was made.
Older Full SIFT installed-library source was not established; it remains a
historical reference, not the known-source Cohere baseline.

## Footprint and loading

[Common load-only probe](results/load-memory-20261006/README.md): seven rotated
fresh CPU0 processes per mode, warm uncontrolled cache, whole-process memory.

| Profile | Load ms | Loaded RSS KiB | Load-stage peak KiB | Snapshot bytes |
|---|---:|---:|---:|---:|
| Full compressed pure-query snapshot | 185.732 | 445324 | 576284 | 313616358 |
| Lite default | 138.812 | 341220 | 341876 | 321600064 |
| Lite diversity | 130.028 | 331896 | 332628 | 317024600 |

Default loaded RSS is 23.38% lower and warm load 25.26% faster for these profiles.
Lite snapshots here are larger than Full. Loader retains no base/query/build
arrays. Full empty creation is outside timing; Lite static Load includes creation;
peaks cover startup/load. These are not reverse-ON Full memory measurements.
Reverse adjacency needs its own load-only experiment before claiming that ratio.

## Adoption and next gates

1. Keep default online policy unchanged. Diversity remains experimental opt-in:
   SIFT 1:40 regresses, and GIST mixed timing has only one process per mode.
2. Measure corrected reverse-ON Full load-only memory with the existing common
   loader and rotated fresh processes; do not reuse compressed-profile memory.
3. Confirm the mentor's RaBitQ public deliverable, then design the minimal backend
   from existing codec/source evidence. Gate training ownership, filters, serial
   CRUD, slot compaction, snapshot validation/versioning, SIMD fallback and accuracy
   before adding a public storage choice.
4. Profile CPU0 build/Add/Update/search separately before another performance change.
   Target measured maintenance/build cost. Use new held-out queries for new selection
   decisions; repeat relevant GIST mixed workloads before broad timing claims.
5. Prepare the delivery candidate, example, regression/sanitizer checks and report
   at an explicit commit. Push personal branch only until PR update approval.
   Concurrent CRUD is a separately scoped feature.

Core serial functionality is implemented and tested. Public quantized delivery,
final accepted scope and remaining comparison gaps are still open. The whole
project cannot yet be described as complete or globally optimal.
