# RaBitQ small-graph best-heap optimization, 2026-10-11

## Delivered production change and limits

Parent c55466b4a2352fd3f5fdecc3996cf153ac00f8e4, personal experiment/lite-rabitq-next-20260926,
remote1.13.5.198/VM-0-10-ubuntu/HostKeyAlias119.45.24.226,
repository `/home/ubuntu/project/vsag-lite-baseline-v01`. Only the personal fork branch is updated;
PR2904/2926 remain unchanged. The project is not complete.

Source evidence: Lite graph_search_impl admits a candidate better than the full best heap's root,
then pushes and pops; existing QueryHeap exposes retained candidates for final rerank. Native
`src/impl/heap/standard_heap.cpp` also bounds admission then pushes/pops; it does **not** provide
the new root-replacement algorithm. This is a targeted extension of Lite's existing heap,
not a claim that native StandardHeap was copied or that native Full was benchmarked here.

QueryHeap::ReplaceTop walks one downward heap path, selecting the worse child with the existing
comparator. Production calls it only for an admitted candidate and a nonempty, full best heap,
in the prune_rejected/select_without_pop/byte-visited specialization. Candidate queue insertion,
rank/slot ties, graph, query budget, quantizer/scoring, filters, public API, snapshot format and
FP32/FP16 production paths are unchanged. Packed visited uses the original push/pop path.
The old unpruned and pop-based template references also retain their original operations.

## Actual shared-library public API comparison

| Input | Old P50 us | New P50 us | Change | P50 pair wins | Old P99 us | New P99 us | Recall both |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| SIFT10k | 205.525 | 199.055 | -3.15% | 6/7 | 237.734 | 230.945 | .987 |
| GIST10k | 514.946 | 505.679 | -1.80% | 4/7 | 664.653 | 655.694 | .970 |
| Cohere10k | 487.209 | 475.539 | -2.40% | 5/7 | 543.778 | 540.976 | .984 |
| GIST100k | 1087.315 | 1111.183 | +2.20% | 2/7 | 1278.368 | 1285.399 | .859 |

Small-input latency medians improve, but pairwise changes are not uniformly favorable and GIST's
4/7 wins do not establish a robust statistical speedup. GIST100k regresses in five of seven P50
pairs despite retaining the previous packed-path operations. Its cause is **not verified**;
do not claim a proven code-layout cause, statistical equivalence, noise dismissal or a100k win.
The retained optimization targets small graphs, with this observed large-graph cost explicitly
reported. Further independent larger-query validation is needed before any upstream promotion.

Allocation runs are separate from latency runs. On all100 measured queries per10k input, one
16384-byte ordinary-new request is avoided (best no longer grows512 to1024 just to hold513
candidates). Requests31→30; cumulative ordinary-new bytes SIFT76832→60448,
GIST80160→63776, Cohere79392→63008. GIST100k remains31 requests/82664 bytes.
This is cumulative requested allocation, not loaded RSS, peak live allocation or process peak.
The earlier100k visited-bitmap memory gain is not counted as a new gain in this report.

Protocol: public SearchWithOptions, CPU0/one thread including BLAS, degree16/build128/query512/
k10, same initial snapshot and inputs, seven alternating fresh-process pairs, one warmup pass
per process and100 historical queries. Reported quantiles are medians of per-process nearest-
rank P50(index49)/P99(index98), not pooled quantiles or final tail-latency acceptance. No build,
test or lint overlapped the timed public runs. Old shared library SHA256
f0dc8ce31c4bf7bc936fb59929fb22348195bd352c1a3e6c46451e19fe47e60d is preserved at
`/home/ubuntu/project/vsag-root-control-c55466b/libvsag-lite.so`. Measured dirty sources and
current library hashes are pinned in identity.json; parent HEAD alone is not their source ID.
Independent verifier passes56 timed runs/5600 queries plus8 allocation runs/800 queries,
70 commands, truth intersections, quantiles and every ordered ID/hex distance against the
native builder and old library. All expected per-query allocation reductions are exact.

## Isolated candidates retained separately

`rabitq-ring-wrap-20261011`: replaced the two runtime modulo expressions for ring neighbors
with boundary conditionals. Same neighbors/visit order and exact native outputs, but GIST10k
P50+10.97% and P99+12.86%; SIFT P50-1.19%, Cohere+.83%, GIST100k-2.63%.
Seven pairs/four cells/56 runs,67 commands, independent verifier PASS. **Not adopted**.

`rabitq-root-replace-20261011`: isolated all-scale root replacement, prior to the production
byte-only gate. P50 SIFT/GIST/Cohere10k -4.43%/-6.55%/-2.43%, each6/7 paired wins;
GIST100k+1.37%,2/7 wins.56 runs/68 commands, exact IDs/hex distances and visited/reranked
counts, independent verifier PASS. This internal-state probe is **not** the production public
API result. Its favorable medians must not replace the public table above. Both actual measured
headers, source hashes, compiler commands, CSVs and failed preparation logs remain preserved.

## Verification

- Fresh Release6/6, ASan+UBSan5/5, RaBitQ-disabled4/4 and fresh coverage6/6 pass.
- Differential heap test: capacities1/2/3/16/512,4096 seeded tie-heavy records each, identical
  priority_queue root/size after every admitted insertion, heap property at each step and exact
  final pop sequence. Existing graph reference/filtered/mutation tests also pass.
- Existing public96-node fixture in FP32/FP16/RaBitQ, dimensions1/17/128, repeated changed-value
  CRUD, ties/external IDs/filter/SaveLoad: old/current output and snapshot ledger SHA exact.
- Boundary65537→65536→65535→65536→65537 via Remove/changed Add/Update, four filters, queries and
  native Save/Load: old/current/sanitized library outputs160 rows each and ledger SHA exact,
  clean sanitizer replay. This is synthetic threshold functionality, not high-dimensional
  long-term CRUD acceptance.
- Fresh non-test src/lite+include/vsag/lite line union3069/3228=95.0743%, QueryHeap17/17.
  Counter resets were restricted to verified coverage-build paths with hashes/path receipts.
  This is not whole-native Full coverage or branch coverage. Format15 and diff checks pass.
- Broader header-filter tidy15 initially fails on the pre-existing explicit float cast/type at
  rabitq_graph_state.h:79 (modernize-use-auto), outside this change. Its log is preserved; this
  is not reported as a clean full-header lint. The focused source/test/new-query-heap check
  passes (71211 dependency/header warnings suppressed). It excludes unrelated header diagnostics;
  no unrelated business code
  is modified to hide that earlier failure.

## Reproduction and remaining acceptance

Use run_rabitq_root_public.py and verify_rabitq_root_public.py; the two isolated runners and
verifiers reproduce their own protocols. Runners refuse existing output paths; choose a new
directory and explicitly pin source, libraries and dataset identities. raw.tar.gz preserves
plain CSVs/commands/inputs/source/validation logs; archive-manifest.json checks every member's
SHA256/size. Extraction into a fresh directory and independent verifier replay pass. Large RAM
snapshots and ledgers have hash/size receipts, not committed binary copies. Original plain raw,
source, datasets and old control library remain on server. No disk cleanup was performed.

No new Full comparison, binary-package closure, loaded RSS/peak, cold/durable I/O or real long-
term high-dimensional CRUD measurement is claimed. GIST100k recall.859 and CPU regression remain
open, as do native Full quality/configuration/SIMD alignment, repeated100k, larger query cohorts,
interleaved changed-value CRUD and complete deployment-package metrics. Do not claim Lite is
faster than native Full or that all project deliverables have been accepted.
