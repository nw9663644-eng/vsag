# SIFT online diversity: fixed-budget cross-dataset validation

Source: `167db90310c56eda7cd7e7f13839c6b390f2376a`. Linux x86_64, CPU 0.
The existing SIFT 100k base prefix and first 100 test queries are reused. These queries were previously observed: this is not an independent blind evaluation.

Two new FP32 graphs were built through the real Lite API, degree 16 and maintenance ef 128. Default and experimental graphs use their corresponding compiled libraries for both construction and mutations. No offline neighbor transformation is applied. Per-query ef is also 128. The experimental build remains opt-in and OFF by default.

Each fresh process loads the same initial snapshot and executes 2000 cycles, each containing changed-vector Update (coordinate 0 +0.125), restoration Update, Remove and Add. The deterministic sequence touches 2000 distinct external IDs (2% of the base). Queries run after the full restored cycle, so original ground truth remains applicable. Query cadence is every 1 or 10 cycles, equivalent to read:mutation-call ratios 1:4 and 1:40. Three fresh processes per mode/cadence; mode order alternates across replicates. One construction per mode, not repeated build timing. See protocol and exact commands.

| Metric (median across 3 processes) | Default | Online diversity |
| --- | ---: | ---: |
| Initial Recall@10 | 0.956 | 0.984 |
| Final Recall@10, either cadence | 0.954 | 0.986 |
| Mixed CPU ms, reads:mutations 1:4 | 1738.773 | 2095.098 |
| Mixed query P50/P99 us, 1:4 | 253.554 / 369.260 | 304.612 / 405.030 |
| Mixed CPU ms, reads:mutations 1:40 | 1275.388 | 1548.234 |
| Mixed query P50/P99 us, 1:40 | 259.354 / 363.970 | 309.124 / 411.861 |

Initial construction took 17.385 s / 20.154 s, a descriptive single-build comparison. All 12 final recalls meet the predeclared 0.95 floor. All executions passed API operation/count checks and exact Save/Load result ID/distance comparisons. Higher recall comes with approximately 20.5% / 21.4% more mixed CPU and 21% more maintenance CPU. This is a same-budget, different-quality comparison, not evidence of matched-quality speedup. The GIST selected-budget benefit cannot be generalized to this SIFT configuration. Keep diversity disabled by default until a matched-quality SIFT comparison and the missing Cohere/Full comparisons establish adoption boundaries.

Timing fields retain the definitions in `../mixed-20261006/README.md`. CPU is process CPU, not utilization percentage; serialized operation, not concurrent CRUD validation. Each timing sample repeats one of 100 queries; 2000/200 events do not mean that many independent queries. Data are fully restored before each measured search; sustained arbitrary-vector updates, larger churn fractions, filters, FP16 and RaBitQ are not covered here.

`summary.json` includes replicate min/max. Raw query latency events, four mutation timings per cycle, scalar query diagnostics, API summaries, logs and commands are retained. `environment.txt` records executable/library hashes. `input-sha256.json` records dataset and uncommitted large snapshot hashes. Snapshots stay on the remote server under `/home/ubuntu/project/vsag-lite-sift-online-20261006`; vectors, snapshots and executables are not committed. `run.py`, `mixed.py`, `analyze.py` record the exact scripts used at that server path; preparation deliberately refuses snapshot overwrite. Run `python3 lite/benchmark/results/sift-online-20261006/verify.py` to audit retained samples and percentiles. No library source change in this increment; earlier library tests/coverage are historical evidence, not newly rerun results.
