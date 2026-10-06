# Corrected Full physical-delete baseline: reverse edges enabled

The previous Full mixed profile enabled physical deletion without enabling
incoming-edge tracking. That configuration was accepted by the known library,
but Move had no incoming neighbors to rewrite. Enabling the existing official
`use_reverse_edges=true` parameter removes the reproduced non-last-delete crash
and the two sampled short-result events. No Full or Lite library code changed.
This corrects our experimental configuration; it is not a library fix and does
not establish a latest-upstream defect or fix.

## Source evidence and controlled correction

GraphDataCell::GetIncomingNeighbors returns an empty vector when reverse_edges_
is absent. GraphDataCell::Move and SparseGraphDataCell::Move use those incoming
lists to rewrite references from the moved last slot to the removed slot.
HGraph force_remove_one compacts vector storage afterward. HGraphParameter
propagates use_reverse_edges from flat bottom-graph parameters to the upper
sparse graphs. The default is false and support_force_remove does not enable it.

The official HGraph documentation describes reverse edges as incoming-neighbor
tracking with approximately doubled edge storage, unsupported with compressed
storage. It does not explicitly document the physical-delete dependency; our
source inspection and controlled runs establish it for the recorded library.
The library accepts the reverse-edges-OFF profile without a rejection. A future
upstream validation or fallback repair could make that combination safer, but
no such library change or external issue is included here.

An 8x16 one-hot public API reproducer was compiled against the same shared
library, with the reverse-edge flag as the only behavioral configuration change.
All twelve controls now exit 0: remove non-last, update/restore then remove,
remove last, and remove/readd, each repeated three times. Earlier reverse-OFF
controls had six SIGSEGV outcomes; their logs and GDB stale-slot observation
remain in full-short-diagnostic-20261006. They must not be generalized to the
reverse-ON profile.

A permanent full_delete_regression target now checks every remaining ID by
self-query after deletion, including the moved last ID, and checks finite zero
self-distance. Four CTest cases cover the four operation sequences. Its existing
vector inputs remain alive throughout all borrowed Dataset calls. The target is
confined to the optional Full benchmark CMake project.

## Fixed-budget Cohere remeasurement

| Queries per mutations | Initial Recall@10 | End Recall@10 | Mixed Recall@10 | Mutation CPU ms | Query CPU ms | Whole mixed CPU ms | Query P50/P99 us | Quality passes |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 per 4 | 0.952 | 0.951 | 0.9534 | 585.877 | 303.657 | 895.896 | 305.084 / 373.311 | 3/3 |
| 1 per 40 | 0.952 | 0.951 | 0.9530 | 575.259 | 35.100 | 613.449 | 349.222 / 422.961 | 3/3 |

Times are medians of three process runs. CPU0, Cohere100k normalized FP32/768dim,
600 previously observed queries [400,1000), degree16, construction128,
query128, one warmup, 1000 cycles, cadence1/10. Order alternates cadence across
repeats. Profile is FP32 flat, support_force_remove=true, use_reverse_edges=true,
store_raw_vector=true. No query budget tuning occurred on these final queries;
they are an observed regression set, not a fresh blind holdout.

Each cycle uses ID (i*8191)%100000 and performs changed UpdateVector(force=true),
restored UpdateVector(force=true), FORCE_REMOVE, then Add(original). Temporary
coordinate change +0.125 is not normalized; queries run only after the data is
fully restored. All 24000 mutations succeeded, live counts were checked, and
all six Save/Load checks compared the full 600-query returned ID sequences and
distances (1e-5 relative scale). The 3300 sampled mixed queries all returned ten
results. End-scan result counts are not independently exported; end recall is
computed by the runner, rather than reconstructed from mixed samples.

Previously the reverse-OFF profile ended at 0.9405 (0/6 quality passes) and had
six sampled short-result events. The corrected profile ends at 0.951 (6/6
passes), with no short mixed events. Reverse adjacency costs extra memory and
maintenance: cadence1 mutation CPU rose from 393.006 to 585.877 ms and cadence10
from 389.877 to 575.259 ms. That is a configuration cost, not a regression from
a valid equivalent baseline. The old profile was unsafe for physical deletion.

## Comparison scope

Frozen historical Lite default / online-diverse end recall was
0.957833 / 0.960333. Their historical whole mixed CPU medians were
3870.573 / 2379.522 ms (cadence1) and 1439.872 / 1385.265 ms (cadence10).
The corrected Full profile is faster in these batches and passes the same
quality floor; recall is still lower and runs were not interleaved Full/Lite.
Full forced update writes codes whereas Lite rewires locally. These are matched
logical operations, not identical algorithmic maintenance work or exactly equal
quality. No claim of a global optimum or general Lite CPU advantage is supported.

The earlier compressed Full pure-query and load-memory references remain valid
for their recorded profiles. They lack reverse adjacency and cannot be silently
reused as memory measurements of this corrected physical-delete profile.
Snapshot/final RSS from this benchmark also has a different lifecycle from the
separate load-only probe. A new matched load-only measurement would be needed
before claiming a memory ratio against reverse-ON Full.

## Verification and evidence

- Full delete regression CTest 4/4, including all live-ID self queries.
- Existing mixed fixture: both cadences, mutation/count/sample accounting,
  Save/Load, old CLI behavior, diagnose mode, eight invalid CLI combinations.
- clang-format-15 and final clang-tidy-15 pass for both changed C++ targets.
  Initial tidy identified an integer-width multiplication in the new test;
  it was corrected and final checks rerun. This is not Full ASan or coverage.
- audit.py verifies profile flags, 12 controls, 6000 four-operation cycles,
  3300 mixed samples, raw hits and nearest-rank P50/P99, fixed query budget,
  and six successful post-CRUD roundtrips.
- SHA-256 binds actual source, runners, shared library and datasets. Shared
  library is the same d18c82a cached incremental build, not a clean or latest
  upstream build. Snapshots and binaries stay on the server.
- Original logs are retained with original hashes; published logs trim trailing
  whitespace and have separately verified publication hashes.

Next, consolidate the SIFT/GIST/Cohere acceptance report with actual quality,
CRUD CPU and memory boundaries; do not continue tuning already observed final
queries or promise that Lite beats Full on every metric. If comparing load-only
memory for the new physical-delete profile, measure it separately.

Only the personal experiment/lite-rabitq-next-20260926 branch is pushed.
PR #2904 and #2926 remain unchanged.
