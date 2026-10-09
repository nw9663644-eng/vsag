# Native Full / Lite: full-small-sift100k-20261009

Native Full library source provenance: d18c82a1f1f23ff84362516e86af5f3cb2e34475, known installed incremental shared rebuild; not a fresh all-object build or latest upstream. SHA256 9aeaa550703f116bef2959769d4f2f03da254b07c906ba941d8186224cc70c72. Installed matching headers are used. The reference is native HGraph, never old Lite. Raw profiles and runtime ISA logs are archived.

Full small profile uses official memory_io, explicit construction threads1 and no redundant floating raw vectors. Both support AVX2/AVX512 on the same pinned EPYC host; selected kernels and numerical ordering are not guaranteed identical. Full RaBitQ randomized rotations vary recall between trials; consult every raw row.

One paired trial only, ef512 for both; three independent warm/uncontrolled loads each. Preliminary 100k evidence, not repeated final acceptance. BLAS/OMP inheritance was not explicitly controlled in this earlier driver revision.

| Dataset | Storage | Recall Full/Lite | P50 Full/Lite us | Loaded RSS Full/Lite KiB | Load Full/Lite ms |
|---|---|---|---|---|---|
| sift100k | fp16 | 1.000/0.988 | 567.668/685.395 | 70892/66036 | 32.819/38.888 |
| sift100k | fp32 | 1.000/0.988 | 616.976/877.770 | 96064/91060 | 48.363/45.856 |
| sift100k | rabitq8 | 0.991/0.975 | 646.326/623.866 | 62464/40452 | 25.481/55.502 |

Lite loaded total RSS is smaller in these cells, but includes a smaller library/dependency baseline. Also inspect before-create/before-load RSS and incremental data memory; do not attribute all savings to vector layout. SIFT RaBitQ load is still slower than Full. Query latency is not universally better and high-budget Lite is substantially slower at a similar quality floor.

rows.json retains per-trial aggregates and fresh loader samples; summary.json uses medians, never only the best run. identity.json records arguments, source diff and binary/input provenance. raw.tar.gz preserves commands, stdout/stderr, peak RSS and available query/neighbor/config files. All snapshots pass ordered post-load search checks.

This is zero-round CRUD, not changed-vector throughput or long-term correctness acceptance. P99 comes from only100 historical queries per cell and is not a robust production tail estimate. Cold cache, all-data100k repeated trials, larger query cohorts, long changed-vector CRUD, complete deployment package closure and fresh Full rebuild remain outstanding. See ../../ALIGNED_COMPARISON.md for reproduction and limitations.
