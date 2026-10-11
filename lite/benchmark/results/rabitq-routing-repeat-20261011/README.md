# GIST100k longer query windows, 2026-10-11

Public API, same initial snapshot, degree16/build128/query512/k10, CPU0/thread1, seven rotating
triples: parent9c44640, new dirty routing-only/no-filter library, referencec55466b.
One warmup pass then100 historical queries repeated ten times/process:21 processes/21000
executed queries, **only100 distinct queries**, not a new1000-query quality/tail cohort.

| Metric us | Parent | New | Reference | New vs parent | New vs reference |
| --- | ---: | ---: | ---: | ---: | ---: |
| Mean query latency | 1092.761717 | 1072.303254 | 1102.406495 | -1.87%,7/7 wins | -2.73%,7/7 wins |
| P50 | 1100.791 | 1082.083 | 1108.500 | -1.70%,6/7 wins | -2.38%,7/7 wins |
| P99 | 1281.466 | 1271.118 | 1305.916 | -0.81%,7/7 wins | -2.66%,6/7 wins |

Independent verifier recomputes every quantile/mean, truth hit and all210000 ordered IDs/hex
distances against native builder.8590/10000 hits/process, recall.859 unchanged.23 commands
pass. No timed build/test/lint overlap. Quantiles are medians of per-process nearest-rank
quantiles, not pooled quantiles. Repeated queries are correlated; do not treat21000 executions
as21000 independent samples or claim a general guarantee/statistical test.

Supports removing the earlier small regression on this workload, not a verified causal
explanation, complete100k acceptance, a recall fix or a native Full speed advantage. The
original100-query window has only.21% median P50 improvement. Both datasets/protocols are
preserved, including negative candidates and library file-size cost (+4.26%).

See ../rabitq-routing-only-public-20261011/README.md for production code, all-stage results,
validation, final-probe post-measurement stream bool style fixes and unresolved acceptance.
Use run_rabitq_routing_repeat.py with a new output path and explicitly pinned sources/libraries;
verify_rabitq_routing_repeat.py reads an extracted archive. identity.json pins actual measured
dirty sources. raw.tar.gz and archive-manifest.json preserve raw rows/inputs/native exports,
sources/commands and per-member SHA256/size. Large RAM snapshot bytes have size/SHA receipts,
not committed binary copies. Original raw and saved libraries are retained on server.
