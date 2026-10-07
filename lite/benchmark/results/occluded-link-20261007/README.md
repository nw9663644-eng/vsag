# Occluded reverse-link retention: local recovery, global rejection

Measured parent: `247b7e130708752b247b6daa214856fd50ccb425`.
No new library policy is adopted. The prototype and conditional unit test were
archived here, restored to the parent byte-for-byte, rebuilt and tested (4/4).

## Source evidence and minimal rule

Full `src/impl/pruning_strategy.cpp::select_edges_by_heuristic` sorts candidates
by source distance and rejects a candidate when alpha times its distance to an
already selected neighbor is below its source distance. HGraph applies this to
saturated reverse rows in `hgraph_build.cpp`. Lite's existing experimental
`nearest()` diversity rule applies to outgoing neighbor selection; `link()`
otherwise removes the farthest candidate subject to incoming safeguards.

This isolated FP32 candidate only rejects a new reverse link when its source
row is full, its target already has an incoming link, and an existing neighbor
is strictly closer to the source and closer to the new target than the new
source-target distance. It preserves the old row exactly in that case.
This uses the alpha=1 geometric predicate, but is a conservative variant, not
a full equivalent of Full's heuristic: existing neighbors are not jointly
pruned or guaranteed mutually diverse. It does not prove route redundancy.
First incoming links, undersized rows and FP16 retain the original path.
Degree limits, fallback, `ensure_incoming`, Remove layout, entry points, SIMD,
query budgets, public API and CMake options remain unchanged. The private macro
is `VSAG_LITE_EXPERIMENT_OCCLUDED_LINK`; candidate build flags are recorded.

## Primary comparisons

Cohere normalized 10k x 768, FP32 L2, top 10, 100 existing observed queries,
degree 16, construction/maintenance/search 128, diversity OFF. Same public
runner and explicit library binding; CPU 0, three fresh-process repeats per
variant/flow, middle repeat reverses flow and variant order. All builds and lint
finished before timings; no profiler or concurrent build ran during timings.

| Flow | Baseline recall | Candidate recall | Baseline CPU median | Candidate CPU median |
| --- | ---: | ---: | ---: | ---: |
| Build only | 0.960 | 0.960 | 2.18 s | 2.24 s |
| Build + 10,000 same-value Update/Remove/Add cycles | 0.940 | 0.928 | 5.45 s | 5.54 s |

Recall and snapshots within each variant/flow repeat are deterministic. CPU is
whole-process user plus system time, with 0.01-second resolution, including
input/staging, queries, persistence and output. It is not isolated CRUD latency.
Median increases are descriptive, not statistical slowdown claims. Both final
recalls fail the historical .95 Cohere floor. The candidate is worse on these
queries and has no demonstrated CPU benefit; this does not generalize to every
dataset or independently held-out queries.

## Same-initial control and original event

Both libraries also restore the exact same baseline-build-r0 snapshot and run
the existing internal mutation trace. Initial hits are 960/1000; final hits are
940 baseline and 931 candidate. Queries and full edge scans make this a quality
diagnostic, not a timing comparison. It does not rescue the candidate.

A separate event-only replay restores the original cycle-3000 Remove state and
adds the original ID/vector once. Baseline reproduces the previous Add snapshot
byte-for-byte. Both results have identical IDs, slots and vector bytes.
The candidate preserves row 6727 including edge 6727->1707; baseline drops that
edge. Query 0 recovers 6 to 7 truth hits, with 1001 distance evaluations and 129
expanded nodes in both. The public native API confirms recall .6/.7 at budget
128; scalar route results agree. Multiple rows can differ in this policy replay,
so it is not a new single-edge causal control. The previous single-edge control
is linked in [event-routing evidence](../event-routing-20261007/README.md).
Hardcoded event IDs appear only in the diagnostic wrapper, never library logic.

The local recovery confirms the hypothesis can act on that case, while the
same-initial and full workload show it is not a suitable general policy.
Do not promote this rule or raise budgets to hide the remaining quality loss.
Next investigate broader routing coverage and slot-sensitive maintenance;
use independent validation queries before promoting any refined policy.

## Validation and reproduction

Both final fixtures pass 24 assertions for retention behavior, reverse-table
consistency, bounded degree, nonzero incoming counts in the fixture and search.
Default CTest passes 4/4, candidate 3/3 (quantization probe disabled). Format15
and tidy15 pass prototype files and the event wrapper. Catch2 network download
initially timed out; the failed configure log is retained. Final configuration
uses the existing previously built Catch2 source cache, with no extern edits.
No new ASan or unit-coverage claim is made for this rejected prototype.

`candidate.patch` applies to the measured parent for isolated reconstruction.
`compile-flags.json`, configure/build logs, source copies, `run.py`, commands,
input/library hashes and restoration receipt identify the experiment.
`secondary-checks.json` records the event and same-initial commands.
`event_add.cpp.txt` reuses the existing snapshot reader and diagnostic writer;
it is a host-only little-endian FP32 v2 tool, not the public portable loader.
Large snapshots and binaries remain in the host experiment directory; they
are not committed. `artifacts.json` separates original and normalized hashes.
Run `python3 verify.py` to recompute recall, raw truth intersections, CPU,
secondary outcomes and hashes. Missing host artifacts are explicitly unavailable.
