# Snapshot row I/O: byte-preserving paired regression

Control: c96aec8; final library change: 3e7e100. SIFT/GIST10k, 100 queries each, three alternating pairs per representation, CPU0, degree16/ef128. Eighteen pairs have identical snapshot SHA and ordered neighbor CSVs.

| Dataset | Storage | Save old/new ms | Fresh load old/new ms |
|---|---|---|---|
| sift10k | fp32 | 26.514/4.082 | 4.018/3.960 |
| sift10k | fp16 | 22.719/12.138 | 3.148/3.182 |
| sift10k | rabitq8 | 7.596/3.912 | 8.644/5.362 |
| gist10k | fp32 | 151.265/16.351 | 17.256/16.759 |
| gist10k | fp16 | 97.005/40.935 | 10.752/10.810 |
| gist10k | rabitq8 | 9.721/5.997 | 11.429/7.844 |

Scalar-only FP16 block writes regressed GIST save (98.192 to121.206ms) in the earlier lite-block-io-valid-20261009 pilot. That implementation was replaced with reusable whole-row encoding; earlier raw evidence remains on the remote. No query speedup is attributed to this I/O change. Loader samples are warm/uncontrolled, not cold.

rows.json retains per-trial aggregates and fresh loader samples; summary.json uses medians, never only the best run. identity.json records arguments, source diff and binary/input provenance. raw.tar.gz preserves commands, stdout/stderr, peak RSS and available query/neighbor/config files. All snapshots pass ordered post-load search checks.

This is zero-round CRUD, not changed-vector throughput or long-term correctness acceptance. P99 comes from only100 historical queries per cell and is not a robust production tail estimate. Cold cache, all-data100k repeated trials, larger query cohorts, long changed-vector CRUD, complete deployment package closure and fresh Full rebuild remain outstanding. See ../../ALIGNED_COMPARISON.md for reproduction and limitations.
