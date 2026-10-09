# Floating graph bounded heap admission

Candidate: 624252f5549c1c3cac12f663293effa0b0eabce3 (production sources).
Control: 4fc5191c2f03bc639cbe399f06c8ebd495f7e9d5.
This is an old/new Lite regression comparison, NOT native Full VSAG.

The official BasicSearcher admits candidates only while the best heap is undersized or the distance improves its boundary. Lite now applies its existing distance/slot ordering before heap writes. Visited marking, allowed filtered results, distance computation, topology, API, snapshot format and budgets are unchanged. Allowed filtered results must be collected before routing rejection.

Three alternating paired trials per dataset/storage, CPU0, degree16, construction ef128, query ef128, k10, 100 historical queries, no warmup, single BLAS/OMP/MKL thread. Cached SIFT/GIST/normalized Cohere 10k. Each pair has identical snapshot SHA and ordered neighbor exports (IDs and distances). See identity.json for commands, input provenance, library and runner hashes, CPU and the exact source patch. Source was uncommitted at capture; the candidate commit contains that patch.

Median per-process latency (microseconds):

| Dataset | Storage | P50 control / candidate | P99 control / candidate | Recall@10 |
| --- | --- | --- | --- | --- |
| SIFT | FP32 | 80.198 / 54.739 | 105.078 / 69.337 | .985 |
| SIFT | FP16 | 78.428 / 52.669 | 100.928 / 66.969 | .985 |
| GIST | FP32 | 186.635 / 153.146 | 312.214 / 229.375 | .916 |
| GIST | FP16 | 182.636 / 144.837 | 283.125 / 233.154 | .915 |
| Cohere | FP32 | 207.845 / 147.916 | 270.984 / 182.506 | .960 |
| Cohere | FP16 | 175.447 / 123.837 | 213.444 / 148.567 | .960 |

P50 reductions are 31.75%,32.84%,17.94%,20.70%,28.83%,29.42%, respectively. Median build time also decreases (see summary.json); this is bulk graph construction, not online Add throughput. Snapshot size is identical. Load/RSS fluctuations are not claimed as improvements. This change targets routing and does not reduce the package size.

Release6/6, ASan/UBSan8/8, coverage6/6. Production Lite merged coverage2592/2737=94.7022%, not whole Full coverage. clang-format-15, clang-tidy-15 (no user-source diagnostics; dependency warnings suppressed), diff check passed. The new test specifically retains an allowed entry rejected by coarse routing in FP32 and FP16.
The adjacent synthetic differential regression covers genuinely changed vectors, removal/re-addition, filtering, ties, negative/nonmonotonic IDs and reload equivalence, but is not lasting real-dataset CRUD acceptance.

raw.tar.gz retains per-query latency/neighbor/recall CSVs, stdout/stderr, peak RSS, commands and configs. rows.json includes three fresh-loader samples for each process; page cache is warm/uncontrolled. Driver uses zero CRUD rounds; its placeholder crud_ops and crud_ms are NOT meaningful throughput. P99 from only100 queries is exploratory. Full comparison, high-dimensional100k repeats, longer changed-value CRUD, cold cache and a larger query cohort remain outstanding.
Run python3 verify.py to independently check both floating performance result directories and the synthetic regression archive without extraction.

Reproduce using run_aligned_comparison.py with the arguments in identity.json and the frozen control/candidate library hashes. To rebuild control, use a separate remote checkout at4fc5191 with the same Lite CMake/SIMD configuration; do not overwrite the active checkout or reinterpret that library as Full.
