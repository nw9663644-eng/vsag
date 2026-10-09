# RaBitQ bounded routing heap admission

Three alternating pairs per dataset,10k vectors/100 historical queries, CPU0,degree16 and construction/query ef128. Control and candidate snapshots and ordered neighbor CSVs are byte-identical in all nine pairs.

Control a95183c; candidate0ecee16. Native BasicSearcher heap-bound principle, preserving visited marks, filtered ranking, slot ties and all result semantics in these paired fixtures.

| Dataset | P50 old/new us | P99 old/new us | Save old/new ms | Fresh load old/new ms | Recall |
|---|---|---|---|---|---|
| sift10k | 109.877/83.029 | 168.735/137.468 | 2.281/2.263 | 3.553/3.421 | 0.978 |
| gist10k | 199.786/174.737 | 326.193/294.954 | 4.533/4.474 | 6.615/6.614 | 0.914 |
| cohere10k | 197.035/168.985 | 301.693/278.094 | 4.131/3.835 | 5.963/5.994 | 0.961 |

All trials are retained, medians not best runs. Query differences in the I/O-only comparison are noise, not a claimed speedup. Cache warm/uncontrolled; zero-round CRUD;100 historical queries are too few for stable production P99. Old Lite is a code regression control, NOT native Full. See ../rabitq-stages-20261009/README.md for100k pairs, tests, source evidence and remaining acceptance. Use run_aligned_comparison.py --control-library with the matching code versions to reproduce.
