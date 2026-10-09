# RaBitQ Batch4 graph filtering (2026-10-09)

Baseline is pushed commit `a1d81048bfef5f1cc744f36baa7f94a2dcbe2de9`.
The candidate reuses the native three-bit centered-IP Batch4 kernel already used
by Full VSAG. Lite collects up to four previously unvisited graph neighbors,
computes their coarse estimates together, then inserts them into the heaps in
the original lane order. Entry points, ring neighbors, termination, tie rules,
filter callback order, reranking, graph topology, degree/ef, encoding, API and
snapshot format are unchanged.

Release GCC 11.4, CPU0, RABITQ8, degree16, ef128, 10k bases, 100 historical
queries, k10, three alternating fresh processes per dataset:

| Dataset | P50 baseline -> candidate (us) | P50 change | Recall |
| --- | ---: | ---: | ---: |
| SIFT | 109.477 -> 105.898 | -3.3% | 0.978 |
| GIST | 209.526 -> 201.306 | -3.9% | 0.914 |
| Cohere | 204.224 -> 190.656 | -6.6% | 0.961 |

All nine paired query and neighbor files are byte-identical. This is modified
Lite versus old Lite, not a Full VSAG parity result, and page cache is
uncontrolled. No FP32/FP16, 100k, cold-load or CRUD-performance claim is made.

Release passed 6/6; ASan+UBSan with leak detection passed 8/8. A Batch4 versus
single-estimate bit test covers dimensions 1/7/17/128/768/960. Coverage passed
6/6 and the modified production scope reached 1257/1315 lines (95.6%).
clang-format-15, clang-tidy-15 and git diff checks passed.

`identity.json`, `rows.json`, `audit.json`, `summary.json`, `raw.tar.gz` and
`SHA256SUMS` preserve the exact comparison. Next work is an aligned Lite versus
native Full configuration/ISA comparison, then 100k repetition and real
changed-vector long CRUD; this microbenchmark must not replace those gates.
