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
The [2026-10-07 load-only follow-up](results/load-reverse-20261007/README.md) now
measures the corrected Full profile: median loaded RSS 568320 KiB versus default
Lite 341196 KiB (-39.96%), warm load 145.931 versus 137.407 ms (-5.84%). These are
initial pre-CRUD snapshots, common quality floor with different recall, not cold
start or exactly equal-quality performance. The earlier table remains historical.

## Adoption and next gates

1. Keep default online policy unchanged. Diversity remains experimental opt-in:
   SIFT 1:40 regresses, and GIST mixed timing has only one process per mode.
2. Corrected reverse-ON Full load-only comparison is now recorded in the linked
   2026-10-07 follow-up. Keep lifecycle/profile boundaries explicit; prioritize
   build and maintenance profiling rather than more load-only repetitions.
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

## CPU profiling and full-ID churn follow-up, 2026-10-07

[CPU0 diagnostic](results/cpu-profile-20261007/README.md) attributes about half
of build/Update/reinsert user-mode samples to distance calculation, with heap
comparison also a hotspot. Counters confirm approximately one CPU utilized for
this workload. Sampling is diagnostic; it is not isolated phase latency or a
new production speedup.

Cohere10k/768dim, query128, all10000 original IDs each receive same-vector
Update/Remove/Add once. Existing100 observed queries retain recall0.933 for
default (initial0.960), diversity0.960 (initial0.982), identically in both
sampling repeats and separate counter runs. Default falls below the0.95 floor
used in earlier Cohere studies; this exploratory protocol did not predeclare
a new acceptance gate. Preserve the negative result and investigate quality
at full-ID churn; earlier low-fraction churn passes do not generalize.
No library change or diversity default adoption follows from this diagnostic.

## Typed comparator follow-up, 2026-10-07

[Comparator optimization](results/comparator-20261007/README.md) preserves
ordering/budgets and all recorded old/new snapshots and ordered neighbors across
48 runs. After verification builds finished,24 final runs give whole-process
CPU medians for default build2.18 to1.90 s (-12.84%), build plus full-ID CRUD
7.15 to6.59 s (-7.83%); diversity build2.47 to2.15 (-12.96%), build plus CRUD
8.21 to7.19 (-12.42%). This is Cohere10k only, three processes per configuration,
not an isolated mutation/query ratio or statistical/global optimum claim.
Release default4/4, diversity3/3, ASan+UBSan6/6; fresh Lite emitted-source/internal
header coverage957/1060=90.28%, format/tidy15 pass. Core dispatch change is
semantics-preserving on these checks, while default full-ID churn recall remains
0.933. Quality diagnosis and100k/other-distribution verification remain open.

## Breadth and routing follow-up, 2026-10-07

[Cross-scale follow-up](results/comparator-breadth-20261007/README.md) adds
SIFT100k/128dim and GIST10k/960dim default-policy old/new comparisons, 24 runs
at fixed degree16/budget128, three processes per case/flow/variant. Whole-process
CPU medians: SIFT build22.96 to19.50 s (-15.07%), build plus1000 CRUD cycles
24.06 to19.73 (-18.00%); GIST build2.40 to2.25 (-6.25%), build plus CRUD
2.96 to2.55 (-13.85%). All12 old/new snapshot pairs streamed byte-equal before
cleaning only generated temporary snapshots; ordered ID/hex-distance outputs
and recall remain identical. SIFT recall0.956, GIST0.916 before/0.907 after
these small-fraction cycles; this is not full-ID churn, exact equal-quality Full
comparison or an isolated mutation/query speedup. No new implementation change.

On existing Cohere10k full-ID snapshots, scalar per-query hits match all400
native historical rows and current native aggregate recall. All missed truth
IDs are unvisited (visited-not-returned0). Default misses40 to67, stored-edge
reach9672 to9068 and zero-in nodes0 to6, while weak component remains one and
reverse reach10000. Stored-edge reach excludes the actual search implicit ring.
This supports investigating traversal, saturated pruning and slot compaction;
it does not identify a unique cause or fix the0.933 default quality limit.

## Confirmed Update repair omission, 2026-10-07

[Update repair](results/update-incoming-20261007/README.md) now checks former
outgoing targets after replacing neighbors, using existing safe incoming repair
without rebuilding their outgoing lists. A four-node regression fails on old code
and passes108 assertions on FP32/FP16 with same/changed updates. The actual
Cohere10k trace first orphaned ID3626 at cycle97 Update ID4527; after fixing,
all10000 cycles complete without newly orphaned nodes. No global guarantee follows.

Default/diverse Release4/4 and3/3, ASan+UBSan6/6, fresh emitted Lite source/internal
header coverage959/1062=90.30%, format/tidy15 pass. Twelve public API processes
retain identical initial builds, successful mutations/counts and exact roundtrips.
Full-ID endpoint recall changes only0.933 to0.934 (one additional hit), still below
the prior0.95 floor. The confirmed omission is fixed; overall quality is not.

Slot-order restoration preserves all vectors/ID-based edges but changes none of
100 hit counts. Only56.495% of original stored edges remain after restored-content
churn. This supports investigating unnecessary Update rewiring and Remove/Add
neighbor drift, not raising observed-query budgets or blaming slot order alone.

## Identical stored-value Update, 2026-10-07

[No-op graph Update](results/noop-update-20261007/README.md) validates inputs/IDs
and FP16 range before comparing stored representation. Identical FP32 bytes or
encoded FP16 bits preserve adjacency and snapshots; actual changes retain repair.
Public FP32/FP16 regression56 assertions, default/diverse Release4/4 and3/3,
ASan+UBSan6/6, emitted-source/internal-header coverage964/1067=90.35%, format/tidy15
pass. Header and English/Chinese contracts are synchronized. BuildGraph remains
a BruteForce-to-Graph conversion, not an in-place rebuild.

Fixed Cohere10k same-value full-ID CRUD,12 fresh processes: whole-process CPU
median6.27 to4.41 s (-29.67%), endpoint recall0.934 to0.940, still below0.95.
Initial builds remain identical. A separate6-process changed/restore control
(1000cycles,10%IDs,budget128) cannot take the identity shortcut and ends0.957
in both versions; mutation CPU624.749 versus624.339 ms is essentially unchanged.
Do not call this an all-Update speedup, final quality acceptance or new holdout.
Remove/Add topology drift and public RaBitQ delivery remain open.

## Remove/Add attribution, 2026-10-07

[Phase diagnostics](results/remove-add-trace-20261007/README.md) reproduce
10,000 rolling-query events twice at the original Cohere10k budget128. Thirteen
cycles change sampled hits: Remove has seven losses/one gain, Add two losses/seven
gains. These are different sampled queries, so their signed sums do not explain
the full0.960-to0.940 recall drop. Ten full-query checkpoints change survivor
edges but no immediate hits. ID-based edges exclude the removed ID and avoid
compaction artifacts; per-cycle queries exclude deleted truth. Both phases now
have reproducible events for further routing controls, not a proven faulty
statement or new retention policy. Release4/4, Release/ASan fixtures and
format/tidy15 pass; no library source or budget changes and no new coverage claim.

## Event routing controls, 2026-10-07

[Three-event controls](results/event-routing-20261007/README.md) distinguish
slot-order sensitivity from stored-edge replacement. Restoring surviving/pre-cycle
order recovers the sampled losses at1099 and7112; restoring old topology at the
current order does not. At3000 the opposite holds. Replacing only6727→3000 with
6727→1707, preserving all other ordered edges/slots/vector bytes, recovers query0
hits6→7. Target1707 retains one incoming edge, so zero-orphan checks alone do not
ensure finite-budget route quality. All22 states load/query through public APIs
and match scalar returned ID sets; raw compressed node exports and available
host snapshots are audited. No library policy, budget or quality gate changes,
no new timing/ASan/coverage claims. Next evaluate a general opt-in incoming
retention control, with full CRUD cost/quality and independent-query validation.

## 2026-10-07: two-incoming retention rejected

The [retention experiment](results/two-incoming-20261007/README.md) raised the
old-candidate pruning preference under an isolated compile macro. Cohere10k
initial recall improved .960 to .972; after 10,000 same-value CRUD cycles it was
.940 baseline and .939 candidate (three repeats). Whole-process CPU medians
were 4.92 and 5.01 seconds, with no demonstrated cost benefit. Starting from
the same baseline graph yielded .940 and .942 in diagnostic traces, still
below the .95 historical floor. These are existing observed queries, not new
holdout acceptance. The library and test prototype were removed and the
restored default passed 4/4 CTest. No default policy, new ASan result or public
RaBitQ delivery is implied.

## 2026-10-07: occluded reverse-link rejection

The [occluded-link experiment](results/occluded-link-20261007/README.md)
preserved a previously identified routing edge and recovered one query from
6 to 7 hits at the same budget. However, three full 10,000-cycle CRUD repeats
ended at recall .928 versus baseline .940; the same-initial-graph diagnostic
ended .931 versus .940. Whole-process CPU medians were 5.54 versus 5.45 seconds,
with no demonstrated benefit. The candidate was withdrawn and the default
restored/retested (4/4). This is negative evidence on observed queries, not a
new accepted policy or independent quality gate.

## 2026-10-07: slot factors separated

The [slot-factor diagnostic](results/slot-factors-20261007/README.md) isolates
entries, implicit ring and tie order at stored ef128. Restoring entries alone
recovers one hit at each of two previously observed events. All eight masks
remain .940 after full churn; no per-query hit improvement at that endpoint.
All-restored factors match physically reordered controls; default diagnostic
ID sets match native APIs. Library policy and quality floor remain unchanged.
Next prioritize stored-topology maintenance and validate any candidate with
full CRUD cost, cross-distribution data and independent queries.

## 2026-10-07: direction-aware refill remains a candidate

The [repair experiment](results/diverse-repair-20261007/README.md) preserves valid
links and prioritizes non-occluded refill candidates, with distance fallback to
retain degree. Cohere10k full churn improves .940 to .950 in three repeats;
300 reserved queries improve .940 to .948, still below the historical .95 target.
SIFT/GIST10k single observations improve .979/.874 to .984/.884; their paired
intervals include zero. Cohere whole-CPU medians4.46/4.54s and SIFT single-run
cost2.31/2.60s show no established cost benefit. The prototype was archived and
withdrawn from active source pending100k/mixed/changed-update validation. Default
CTest4/4 passes; no new sanitizer, coverage or universal quality gate is claimed.

## 2026-10-07: 100k repair cost/quality tradeoff

The [100k scale validation](results/diverse-repair-scale-20261007/README.md) runs
changed-update/restore/remove/re-add with interleaved queries from shared historical
initial snapshots. After10,000 cycles (10% IDs), SIFT/GIST/Cohere post recall improves
.948/.723/.897 to .950/.726/.900 in three repeats, while mutation-block CPU medians
increase1.51%/3.99%/3.13%. The1,000-cycle pilot has no final recall gain. This is not
full100k churn, fresh build timing, persistent-update retrieval or new holdout. All
42 processes pass exact final-query Save-Load checks; raw samples reconstruct timing
medians, but post/mixed truth hits remain runner aggregates. No library/PR/default
policy change, universal performance benefit or new sanitizer/coverage claim follows.

## Native CRUD raw audit (2026-10-07)

[Report](results/crud-raw-20261007/README.md): 6,600 native post/mixed query events independently recomputed from returned IDs and archived truth reproduce the preceding 100k results. FP32/FP16 persistent changed-vector query and Save/Load pass a bounded exhaustive oracle fixture. No library policy adoption, new performance gain, held-out query or concurrent-call claim; the quality/cost decision remains open.
