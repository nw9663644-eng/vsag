# Native Full / Lite: full-small-aligned-20261009

Native Full library source provenance: d18c82a1f1f23ff84362516e86af5f3cb2e34475, known installed incremental shared rebuild; not a fresh all-object build or latest upstream. SHA256 9aeaa550703f116bef2959769d4f2f03da254b07c906ba941d8186224cc70c72. Installed matching headers are used. The reference is native HGraph, never old Lite. Raw profiles and runtime ISA logs are archived.

Full small profile uses official memory_io, explicit construction threads1 and no redundant floating raw vectors. Both support AVX2/AVX512 on the same pinned EPYC host; selected kernels and numerical ordering are not guaranteed identical. Full RaBitQ randomized rotations vary recall between trials; consult every raw row.

Three alternating paired trials, ef128 for both, three independent warm/uncontrolled loads each. This is a same-budget diagnostic, not same-recall comparison. The measured Lite is the earlier scalar-block I/O candidate; query code is unchanged by 3e7e100 but FP16 save timing is superseded by the row-I/O report. BLAS/OMP inheritance was not explicitly controlled in this earlier driver revision.

| Dataset | Storage | Recall Full/Lite | P50 Full/Lite us | Loaded RSS Full/Lite KiB | Load Full/Lite ms |
|---|---|---|---|---|---|
| cohere10k | fp16 | 0.987/0.960 | 157.997/172.306 | 42972/22608 | 13.192/8.767 |
| cohere10k | fp32 | 0.987/0.960 | 180.776/188.876 | 58368/37596 | 23.850/13.569 |
| cohere10k | rabitq8 | 0.986/0.961 | 197.957/201.796 | 36104/13816 | 8.039/7.305 |
| gist10k | fp16 | 0.966/0.915 | 164.206/180.856 | 46796/26300 | 15.333/10.646 |
| gist10k | fp32 | 0.966/0.916 | 167.317/182.485 | 66028/45060 | 27.767/16.112 |
| gist10k | rabitq8 | 0.965/0.914 | 194.796/196.526 | 38028/15640 | 9.293/8.171 |
| sift10k | fp16 | 0.958/0.985 | 88.050/79.008 | 30172/10052 | 3.725/3.008 |
| sift10k | fp32 | 0.958/0.985 | 87.699/79.898 | 32832/12560 | 5.271/3.718 |
| sift10k | rabitq8 | 0.968/0.978 | 121.988/107.758 | 29704/7424 | 2.803/5.133 |

Lite loaded total RSS is smaller in these cells, but includes a smaller library/dependency baseline. Also inspect before-create/before-load RSS and incremental data memory; do not attribute all savings to vector layout. SIFT RaBitQ load is still slower than Full. Query latency is not universally better and high-budget Lite is substantially slower at a similar quality floor.

rows.json retains per-trial aggregates and fresh loader samples; summary.json uses medians, never only the best run. identity.json records arguments, source diff and binary/input provenance. raw.tar.gz preserves commands, stdout/stderr, peak RSS and available query/neighbor/config files. All snapshots pass ordered post-load search checks.

This is zero-round CRUD, not changed-vector throughput or long-term correctness acceptance. P99 comes from only100 historical queries per cell and is not a robust production tail estimate. Cold cache, all-data100k repeated trials, larger query cohorts, long changed-vector CRUD, complete deployment package closure and fresh Full rebuild remain outstanding. See ../../ALIGNED_COMPARISON.md for reproduction and limitations.
