# RaBitQ routing-only work and large-query regression check, 2026-10-11

## Delivered change

Remote1.13.5.198/VM-0-10-ubuntu/HostKeyAlias119.45.24.226,
`/home/ubuntu/project/vsag-lite-baseline-v01`, personal experiment/lite-rabitq-next-20260926,
parent9c44640fcd7fcf58665d2dbf72c808522eabbe88. Only this personal fork branch is updated;
PR2904/2926 are not changed. Actual measured dirty source and library SHA are pinned in identity,
not represented as a clean parent build.

Source evidence: graph_search_impl consumes FilterEstimate.distance and centered_ip, not
lower_bound. The standalone filtered_search full scan does consume lower_bound to prune.
Disassembly of the no-filter-only prototype shows the single filter_estimate helper still
computes the error term, another divss and lower-bound arithmetic, and a live call from routing.
This is assembly evidence of unused work, not a complete hardware/profile attribution.
Native BasicSearcher::Search/search_impl uses entry dispatch plus a mode template; this is
the architectural pattern followed here, not a claim that native already has our filter flag.
Existing native shared RaBitQ SIMD kernels remain unchanged and are not counted as a new gain.

Production now selects filter_estimate<false>/filter_estimate_batch4<false> only in graph
routing. The coarse distance and centered-IP arithmetic are unchanged; lower_bound is a zero
placeholder there. Default callers retain their original full lower-bound calculation. At
>=65536 slots, graph_search_adjacency dispatches empty user filters to evaluate_filter=false;
nonempty callbacks retain the original specialization and semantics. Small-graph routing
keeps its previous user-filter handling. No graph, model, scoring formula, traversal order,
filter accept/reject behavior, ef, k, public options, snapshot or FP32/FP16 production change.

## Public API results: original100-query windows, all costs retained

Seven rotating triples, CPU0/one thread including BLAS, degree16/build128/query512/k10,
same initial snapshot and input per cell, one warmup and100 historical queries/process.
Control is current parent9c44640; reference is pre-small-heap changec55466b. No build/test/lint
overlaps timed queries. Medians below are medians of seven per-process nearest-rank quantiles,
not pooled quantiles or final P99 acceptance.

| Input | Parent P50 us | New P50 us | Change | P50 wins | Parent P99 us | New P99 us | Recall both |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| GIST100k | 1117.571 | 1115.220 | -0.21% | 5/7 | 1292.076 | 1269.487 | .859 |
| SIFT10k | 203.144 | 203.964 | +0.40% | 4/7 | 244.794 | 243.523 | .987 |
| GIST10k | 504.686 | 494.987 | -1.92% | 6/7 | 656.793 | 646.263 | .970 |
| Cohere10k | 488.188 | 474.818 | -2.74% | 3/7 | 555.916 | 530.576 | .984 |

The short-window GIST100k improvement is tiny; Cohere's favorable median has only3/7 paired
wins, and SIFT's P50 median regresses. These are not a universal speedup claim. Rejected
prototypes and the no-filter-only public stage are preserved, not selected as final performance.
The verifier checks84 timed runs/8400 queries/98 commands and8 separate allocation runs/800
queries. All ordered IDs and hex distances are identical across all three libraries and the
native builder; original truth intersections and recorded quantiles are recomputed.
Ordinary-new requests/bytes are unchanged from parent:10k30 requests/60448,63776,63008 bytes
(SIFT/GIST/Cohere),100k31 requests/82664 bytes. No new memory gain is claimed.

## GIST100k: longer timing windows, same100 distinct queries

The independent repeat stage uses public API/CPU0/same parameters, seven rotating triples,
one warmup pass and then100 historical queries repeated ten times/process. It executes21000
queries across21 processes, **not1000 independent queries**. These repeated samples do not
close larger-query, quality or tail-latency acceptance. Comparison IDs refer to the same three
libraries as above, not native Full.

| Metric us | Parent9c44640 | New | Referencec55466b | New vs parent | New vs reference |
| --- | ---: | ---: | ---: | ---: | ---: |
| Mean query latency | 1092.761717 | 1072.303254 | 1102.406495 | -1.87%,7/7 wins | -2.73%,7/7 wins |
| P50 | 1100.791 | 1082.083 | 1108.500 | -1.70%,6/7 wins | -2.38%,7/7 wins |
| P99 | 1281.466 | 1271.118 | 1305.916 | -0.81%,7/7 wins | -2.66%,6/7 wins |

This supports removal of the previously observed small100k regression **for this workload**,
not a general100k speed guarantee, a verified explanation of the earlier regression, or a
resolution of all project performance requirements. All210000 ordered neighbors and8590
truth hits/process are independently verified; recall remains.859, not improved.
The current measured library is412512 bytes versus395648 for both saved old libraries
(+16864 bytes/+4.26% file size). This is a cost of additional compiled code, not complete
deployment-package measurement. No loaded RSS, peak, cold-load, durable I/O, Full or CRUD
throughput improvement is claimed.

## Prior candidates, all preserved

- `rabitq-floyd-replace-20261011`: single down/up heap adjustment/all scales. Internal probe
  P50 GIST100k+2.04%, SIFT+1.69%, GIST10k-1.93%, Cohere+2.06%; Cohere P99+10.00%.
  Rejected.56 runs/68 commands, source overlay and exact visit/rerank/result checks pass.
- `rabitq-evict-first-20261011`: packed path pop-before-push. Internal probe GIST100k
  P501091.602→1097.730(+.56%), Cohere475.487→500.776(+5.32%). Rejected.56 runs/67
  commands, exact source/result/visit/rerank verifier passes. Not a production result.
- `rabitq-no-filter-20261011`: all-scale empty-filter specialization, internal probe GIST100k
  -3.39%, SIFT-4.43%, GIST10k-4.93%, Cohere+1.38%.56 runs/67 commands pass. This apparent
  gain is not selected as the public-library result.
- `rabitq-no-filter-public-20261011`: first production experiment, large no-filter only,
  before routing-only estimate.84 public runs show GIST100k-.92%/3 wins, SIFT+1.96%,
  GIST10k+3.22%, Cohere-2.02%. No stable general improvement; not the final source. A
  control library and disassembly are preserved under vsag-nofilter-only-diagnostic-20261011.

## Verification and reproduction

Fresh Release6/6, ASan+UBSan5/5, RaBitQ-disabled4/4, fresh coverage6/6 pass. New tests compare
route-only vs full estimates for scalar/batch4 at dimensions1/17/128/768/960, exact coarse
distance/centered IP and zero placeholder. Forced packed/no-filter route matches unpruned
reference across ties, nonmonotonic IDs, budgets, k and changed-value CRUD epochs. Existing
tests still cover real callbacks, including reject-all routing and snapshot/error behavior.
Public96-node fixture in FP32/FP16/RaBitQ and threshold-crossing65537→65536→65535→65536→65537
fixture have identical outputs and snapshot-ledger SHA against parent; boundary sanitized
replay160 rows is exact and clean. These synthetic fixtures do not replace high-dimensional
long-term changed-value CRUD acceptance.

Fresh non-test Lite line union3072/3233=95.0201%, not whole native Full or branch coverage.
Coverage counters were reset only inside the verified build; reset-path/hash receipts remain.
Format15/diff checks pass. Initial hand-formatted new test/template calls required format
correction before timing. Initial scoped tidy incorrectly applied the compilation database
to an unregistered standalone probe (missing include), then exposed inherited implicit-stream
bool diagnostics. Final probe uses explicit bool casts and its own include flags; actual
measured probe source is retained in the repeat archive. These post-measurement stream-check
edits do not change the timed query loop; final probe compile is checked separately, not
misrepresented as a rerun of21000 queries. Failed tidy log is retained. Final lint is scoped
to changed production/test lines and standalone probe and passes (67267 dependency/line-filter
warnings suppressed in production/test and27102 in probe), not a clean full-header lint.

Run/verify_rabitq_routing_only_public.py and run/verify_rabitq_routing_repeat.py reproduce the
two final protocols; separate runners/verifiers cover each earlier stage. Runners refuse
existing output paths: select new paths and explicitly pin sources/libraries/inputs. Raw
archives include commands, queries/truth, CSVs, measured source and validation receipts;
each archive is extracted into fresh RAM scratch and its independent verifier re-run, with
every member's SHA256/size checked. Large snapshot/ledger bytes have hash/size receipts,
not committed binary copies. Original plain raw, source, datasets and saved libraries are
preserved. No disk cleanup is performed; only owned temporary RAM fixtures expire.

Still open: GIST100k graph-quality/recall.859, broader/independent query distributions,
fresh quality/configuration/SIMD-aligned native Full comparison, repeated other100k datasets,
high-dimensional long-term interleaved changed-value CRUD and complete package/peak metrics.
This is modest query work reduction, not evidence Lite now outperforms native Full or that
the project has finished acceptance.
