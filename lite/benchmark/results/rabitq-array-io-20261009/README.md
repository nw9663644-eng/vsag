# RaBitQ integer-array I/O

Three alternating pairs per dataset,10k vectors/100 historical queries, CPU0,degree16 and construction/query ef128. Control and candidate snapshots and ordered neighbor CSVs are byte-identical in all nine pairs.

Control e8781f1; candidate a95183c. Native StreamReader vector block-I/O principle with explicit little-endian fallback and unchanged invalid-input validation.

| Dataset | P50 old/new us | P99 old/new us | Save old/new ms | Fresh load old/new ms | Recall |
|---|---|---|---|---|---|
| sift10k | 108.277/108.958 | 171.306/172.326 | 3.878/2.374 | 5.377/3.583 | 0.978 |
| gist10k | 201.045/212.536 | 333.042/335.782 | 5.891/4.671 | 8.351/6.825 | 0.914 |
| cohere10k | 213.264/199.407 | 309.034/305.204 | 5.313/3.769 | 7.676/5.924 | 0.961 |

All trials are retained, medians not best runs. Query differences in the I/O-only comparison are noise, not a claimed speedup. Cache warm/uncontrolled; zero-round CRUD;100 historical queries are too few for stable production P99. Old Lite is a code regression control, NOT native Full. See ../rabitq-stages-20261009/README.md for100k pairs, tests, source evidence and remaining acceptance. Use run_aligned_comparison.py --control-library with the matching code versions to reproduce.
