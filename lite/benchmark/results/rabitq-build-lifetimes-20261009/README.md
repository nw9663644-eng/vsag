# RaBitQ construction scratch lifetimes

Control b0434c8a9cf3b190fb6a0a3de18dda927a7575e6; candidate production cbaea1fff090dc78113ac9a208e3f46c1aa0f4f2 plus entry error fix adae3a8d2512faa308bb4ce8bd8d4b996354d679. Both share exact graph-build reservation from e7dc151. This is old/new Lite regression evidence.

The FP32 training matrix is freed immediately after encoding and before constructing the floating graph. After copying topology, the floating graph is destroyed before mutable encoded state initialization. Source BruteForce remains alive until successful publication. Graph connectivity, trained model, seed47, codes, queries and snapshot format are preserved. The two releases target overlapping ownership; allocator RSS reclamation can differ across platforms.

GIST/SIFT/Cohere10k, three alternating pairs per dataset, degree16, construction/query ef128, CPU0,k10,100queries,no warmup. BLAS/OMP/MKL threads1. Three fresh loader processes per built snapshot. All nine pairs have byte-equal snapshot SHA and ordered ID/distance exports.

| Dataset | Peak RSS control/candidate KiB | Reduction | Build ms control/candidate | Recall |
| --- | ---: | ---: | ---: | ---: |
| SIFT10k |34184/29108|14.85%|617.026/611.391|.978|
| GIST10k |172584/135000|21.78%|1690.542/1672.628|.914|
| Cohere10k |140592/110412|21.47%|1570.414/1574.127|.961|

Build time is essentially flat. Per-process P50 medians SIFT81.438/85.328us(+4.78%),GIST184.437/166.807(-9.56%),Cohere161.817/166.607(+2.96%). Timings have mixed changes; no query-speed improvement is attributed to this lifecycle edit. Query implementation is unchanged, but allocation layout/cache effects may influence observed timing. Warm load and loaded RSS remain in rows/summary without an improvement claim.

The new build-failure test probes500 allocation positions for each representation:128 FP32,143 FP16,197 RaBitQ injected failures all returned errors, preserved source snapshots and allowed retry. It exposed a prior exception from allocation of the public BuildGraph error placeholder; the entry fix translates bad_alloc/length_error. Existing Add/Update/Remove probes remain.
Validation: Release6/6,ASan/UBSan8/8,coverage6/6,default-RaBitQ-off4/4; production Lite2617/2758=94.8876%. clang-format15/clang-tidy15/diffcheck pass, with dependency warnings suppressed. No full-VSAG suite coverage claim.

identity.json preserves exact uncommitted source diff captured at b0434c8, input/library/runner hashes, CPU and arguments. Candidate library0d3482f1d8795d41308f1c8e55a9f89f02b084382951f3e943c7666fdf1eb4a5; controlb695e6711cd5b1de7eda4aefb869324d08b1c9ab9434a273c66f365394ed649e. Source was committed after capture without rebuilding/changing the measured library. raw.tar.gz preserves raw logs/commands/quantiles/neighbors, and validation.txt contains the fault summaries.

Run python3 verify.py after obtaining the adjacent GIST100k archive. Reproduce via run_aligned_comparison.py arguments in identity.json with frozen matching libraries/configuration.
Page cache is warm/uncontrolled, host is not isolated,100queries is a small P99 cohort. Zero CRUD rounds here do not measure lasting changed-value throughput. Further elimination of the full source copy needs a recoverable ownership design; all-dataset100k quality, long real-data CRUD, cold loading, fresh Full and complete package closure remain pending.
