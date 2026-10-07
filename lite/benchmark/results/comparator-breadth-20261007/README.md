# Comparator breadth verification, 2026-10-07

Source parent d806f14825eb35942655d1732c0f6cf5969302b2. No new C++ or algorithm change.
Default policy OFF only. Extend previous Cohere10k comparison to SIFT100k/128dim
and GIST10k/960dim, each with existing100 observed prefix queries, L2 Top10,
degree16/construction/query128. Fixed settings, no recall retuning or new holdout.
Build-only vs build plus1000 distinct-ID same-vector Update/Remove/Add cycles:
1% of SIFT100k and10% of GIST10k. Not full-ID churn or the four-call changed/restore
mixed protocol. All operation/live-count/query/roundtrip checks run in the probe.

## Protocol and results

CPU0, three fresh processes per case/flow/variant,24 runs. Variant/case/flow order
reverses on odd repeat. Same current diagnostic runner, old/new libraries explicitly
selected through LD_LIBRARY_PATH, ldd and hashes. Libraries/runner match the previous
comparator study exactly; no intervening build/test/profiler workload.
/usr/bin/time user+system covers WHOLE process (IO/staging/build/optional CRUD/query/
SaveLoad/output),0.01s resolution; this is not isolated mutation/search timing.
Three repeats give descriptive medians, not statistical significance/global optimum.

| Case | Flow | Old median CPU s | New median CPU s | Change | Recall@10 |
|---|---|---:|---:|---:|---:|
| sift100k | build | 22.96 | 19.50 | -15.07% | 0.956000 |
| sift100k | crud | 24.06 | 19.73 | -18.00% | 0.956000 |
| gist10k | build | 2.40 | 2.25 | -6.25% | 0.916000 |
| gist10k | crud | 2.96 | 2.55 | -13.85% | 0.907000 |

All12 pairs passed actual streaming byte comparison of old/new snapshots, SHA256
comparison, identical query-hit CSV and identical1000 ordered ID/hexfloat-distance
rows. Snapshot/hash/recall invariants also hold across all three repeats per case/flow.
The current runner internally compares every query's ID/distance after SaveLoad.
This strengthens evidence for the semantics-preserving dispatch change on an additional
scale/distributions; it is not exhaustive equivalence for all inputs/platforms.

## Boundaries and evidence

Recall here is at fixed128, not the selected matched-quality budgets in earlier final
studies. Approximate recall is not expected to be1. Equivalence does not itself prove
quality acceptance. Small-fraction churn here cannot erase the earlier Cohere10k
full-ID default degradation0.960 to0.933. Diversity, FP16 and other scales are not
newly timed here; their prior unit/regression evidence remains at its measured commit.
No new library tests/sanitizer/coverage claims, since no implementation changed.

Original disk free space was3.5GiB. Each NEW temporary pair retains at most two
snapshots until byte comparison succeeds, records hashes, then deletes only that
pair's generated files with resolved path checks. Existing inputs/history/old libraries
are untouched. Big snapshots are not retained/published; audit checks recorded hashes
and comparison receipts, not independent re-comparison of absent bytes.
Raw logs remain on host, normalized publication logs have separate hashes. Protocol,
commands, input/library/runner SHA, ldd, CPU CSV, exact outputs and comparison receipts
are included. run.py encodes original host paths; use a NEW output root/prefix and
recorded binaries to reproduce, never overwrite original records.

Only personal experiment/lite-rabitq-next-20260926 is pushed; PRs remain frozen.
The routing traces below narrow the full-ID quality problem; next isolate the harmful mutation;
no blind budget tuning or additional default feature adoption follows from this report.

## Full-ID Cohere routing diagnosis (after timing completed)

Four existing before/after snapshots from the earlier Cohere10k final study,
100 observed queries, budget128; default/diversity before build and after100%
distinct-ID same-vector churn. Existing route probe preserve mode, no topology
transformation. Scalar per-query hits exactly match all100 historical native
hit rows in each configuration; native SearchWithOptions also matches aggregate
recall with stored/query budget128. This diagnoses those observed snapshots,
not a new held-out quality study or speed comparison.

| Snapshot | Recall | Missed truth not visited | Visited truth not returned | Zero in-degree | Stored-edge reach from0 | Mean visited nodes |
|---|---:|---:|---:|---:|---:|---:|
| default-build | 0.960000 | 40 | 0 | 0 | 9672 | 1015.880000 |
| default-crud | 0.933000 | 67 | 0 | 6 | 9068 | 953.820000 |
| diverse-build | 0.982000 | 18 | 0 | 0 | 9928 | 1193.880000 |
| diverse-crud | 0.960000 | 40 | 0 | 4 | 9605 | 1082.010000 |

All four stored graphs have one weak component of10000 nodes and reverse-edge
reach10000 from0. Directed reach excludes SearchImpl's implicit slot-ring steps;
it is not proof of disconnection under the actual full-budget search. For default,
missed truths increase40 to67 while visited-but-not-returned stays0. This supports
investigating traversal/topology/candidate coverage rather than blaming result
sorting or claiming the typed comparator caused degradation. It does not prove
six zero-in nodes cause every miss, or identify a unique erroneous mutation.
Diversity also loses recall and has4 zero-in nodes; it is not a complete repair.

Next inspect bounded link pruning/incoming-edge preservation and compaction's
physical-slot ring/entry changes at the first harmful operation. Use a minimal
reproducer and fixed/new independent quality queries before a topology change;
keep budget and snapshot invariants. Do not indiscriminately rebuild graphs or
retune these observed queries to hide the issue. No library modification here.
