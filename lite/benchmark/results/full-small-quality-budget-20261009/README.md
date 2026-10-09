# Native Full / Lite: full-small-quality-budget-20261009

Native Full library source provenance: d18c82a1f1f23ff84362516e86af5f3cb2e34475, known installed incremental shared rebuild; not a fresh all-object build or latest upstream. SHA256 9aeaa550703f116bef2959769d4f2f03da254b07c906ba941d8186224cc70c72. Installed matching headers are used. The reference is native HGraph, never old Lite. Raw profiles and runtime ISA logs are archived.

Full small profile uses official memory_io, explicit construction threads1 and no redundant floating raw vectors. Both support AVX2/AVX512 on the same pinned EPYC host; selected kernels and numerical ordering are not guaranteed identical. Full RaBitQ randomized rotations vary recall between trials; consult every raw row.

Lite query ef512 versus Full ef128; construction128 unchanged. BLAS/OMP/MKL threads1. This tests a similar quality floor, NOT equal budgets or exactly equal recall. Cohere Lite still falls slightly below Full.

| Dataset | Storage | Recall Full/Lite | P50 Full/Lite us | Loaded RSS Full/Lite KiB | Load Full/Lite ms |
|---|---|---|---|---|---|
| cohere10k | fp16 | 0.987/0.985 | 171.426/587.537 | 43008/22576 | 13.952/9.559 |
| cohere10k | fp32 | 0.987/0.985 | 185.436/697.526 | 58324/37604 | 25.395/14.691 |
| cohere10k | rabitq8 | 0.986/0.984 | 201.966/601.907 | 36124/13748 | 8.381/7.760 |
| gist10k | fp16 | 0.966/0.971 | 167.897/569.367 | 46788/26340 | 16.433/11.467 |
| gist10k | fp32 | 0.966/0.971 | 171.807/622.165 | 66064/45056 | 30.569/17.936 |
| gist10k | rabitq8 | 0.964/0.970 | 205.625/590.228 | 38056/15616 | 9.923/8.148 |

Lite loaded total RSS is smaller in these cells, but includes a smaller library/dependency baseline. Also inspect before-create/before-load RSS and incremental data memory; do not attribute all savings to vector layout. SIFT RaBitQ load is still slower than Full. Query latency is not universally better and high-budget Lite is substantially slower at a similar quality floor.

rows.json retains per-trial aggregates and fresh loader samples; summary.json uses medians, never only the best run. identity.json records arguments, source diff and binary/input provenance. raw.tar.gz preserves commands, stdout/stderr, peak RSS and available query/neighbor/config files. All snapshots pass ordered post-load search checks.

This is zero-round CRUD, not changed-vector throughput or long-term correctness acceptance. P99 comes from only100 historical queries per cell and is not a robust production tail estimate. Cold cache, all-data100k repeated trials, larger query cohorts, long changed-vector CRUD, complete deployment package closure and fresh Full rebuild remain outstanding. See ../../ALIGNED_COMPARISON.md for reproduction and limitations.
