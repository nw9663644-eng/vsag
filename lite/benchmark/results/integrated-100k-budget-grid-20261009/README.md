# 100k observed-query budget grid

2026-10-09. Reuse the exact nine snapshots from integrated-100k-pilot; no construction/model/default change. Before the sweep, freeze ef grid 128/512/2048/8192 and SIFT/Cohere .95, GIST .90 study floors. These are not universal official thresholds. 36 fresh loaded processes, one per grid cell, CPU 0,100 historical queries each. This is selection evidence, not blind held-out or repeated performance acceptance.

## All cells

| Dataset | Storage | Query ef | Recall@10 | P50 us | P99 us | Loop CPU ms |
|---|---|---:|---:|---:|---:|---:|
| sift | fp32 | 128 | 0.956 | 272.584 | 372.151 | 26.709 |
| sift | fp32 | 512 | 0.988 | 829.741 | 1205.574 | 81.528 |
| sift | fp32 | 2048 | 0.996 | 2784.418 | 3737.868 | 282.275 |
| sift | fp32 | 8192 | 0.997 | 9991.639 | 11768.661 | 1005.729 |
| sift | fp16 | 128 | 0.956 | 242.515 | 341.192 | 23.945 |
| sift | fp16 | 512 | 0.988 | 723.505 | 1058.397 | 72.107 |
| sift | fp16 | 2048 | 0.996 | 2480.746 | 3380.566 | 248.444 |
| sift | fp16 | 8192 | 0.997 | 9505.671 | 11167.163 | 926.050 |
| sift | rabitq8 | 128 | 0.946 | 308.594 | 423.720 | 30.969 |
| sift | rabitq8 | 512 | 0.975 | 917.629 | 1300.602 | 91.727 |
| sift | rabitq8 | 2048 | 0.979 | 3266.316 | 4268.776 | 333.657 |
| sift | rabitq8 | 8192 | 0.982 | 12018.175 | 14353.303 | 1204.693 |
| gist | fp32 | 128 | 0.742 | 471.590 | 644.276 | 46.891 |
| gist | fp32 | 512 | 0.860 | 1553.356 | 1941.997 | 153.846 |
| gist | fp32 | 2048 | 0.929 | 4680.476 | 5504.369 | 463.707 |
| gist | fp32 | 8192 | 0.964 | 14740.605 | 16032.155 | 1460.384 |
| gist | fp16 | 128 | 0.741 | 461.259 | 630.807 | 46.390 |
| gist | fp16 | 512 | 0.865 | 1410.399 | 1740.851 | 140.745 |
| gist | fp16 | 2048 | 0.931 | 4857.394 | 5685.544 | 480.635 |
| gist | fp16 | 8192 | 0.965 | 15054.948 | 16503.287 | 1485.978 |
| gist | rabitq8 | 128 | 0.748 | 699.845 | 889.210 | 70.623 |
| gist | rabitq8 | 512 | 0.859 | 2468.935 | 2898.427 | 248.247 |
| gist | rabitq8 | 2048 | 0.924 | 9189.297 | 10253.493 | 914.418 |
| gist | rabitq8 | 8192 | 0.964 | 34040.379 | 36208.762 | 3404.594 |
| cohere | fp32 | 128 | 0.891 | 451.480 | 630.426 | 44.638 |
| cohere | fp32 | 512 | 0.941 | 1523.476 | 1906.128 | 149.651 |
| cohere | fp32 | 2048 | 0.971 | 5228.584 | 6114.715 | 517.980 |
| cohere | fp32 | 8192 | 0.989 | 16726.631 | 18036.873 | 1660.961 |
| cohere | fp16 | 128 | 0.890 | 428.439 | 582.548 | 42.849 |
| cohere | fp16 | 512 | 0.941 | 1473.897 | 1822.400 | 143.538 |
| cohere | fp16 | 2048 | 0.971 | 5159.046 | 6110.326 | 515.209 |
| cohere | fp16 | 8192 | 0.989 | 16860.688 | 18287.698 | 1676.699 |
| cohere | rabitq8 | 128 | 0.889 | 658.466 | 796.493 | 65.805 |
| cohere | rabitq8 | 512 | 0.937 | 2243.621 | 2663.501 | 221.513 |
| cohere | rabitq8 | 2048 | 0.967 | 8969.383 | 9722.756 | 887.906 |
| cohere | rabitq8 | 8192 | 0.983 | 32696.639 | 35067.728 | 3265.253 |

## Lowest tested budget meeting each floor

| Dataset | Storage | Selected ef | Recall | P50 us |
|---|---|---:|---:|---:|
| sift | fp32 | 128 | 0.956 | 272.584 |
| sift | fp16 | 128 | 0.956 | 242.515 |
| sift | rabitq8 | 512 | 0.975 | 917.629 |
| gist | fp32 | 2048 | 0.929 | 4680.476 |
| gist | fp16 | 2048 | 0.931 | 4857.394 |
| gist | rabitq8 | 2048 | 0.924 | 9189.297 |
| cohere | fp32 | 2048 | 0.971 | 5228.584 |
| cohere | fp16 | 2048 | 0.971 | 5159.046 |
| cohere | rabitq8 | 2048 | 0.967 | 8969.383 |

## Interpretation and boundaries

SIFT RaBitQ needs at least 512 in this tested grid (.975) while floating modes pass at 128 (.956). GIST all modes first pass at 2048 (FP32 .929,FP16 .931,RaBitQ .924). Cohere all first pass at 2048 (FP32/FP16 .971,RaBitQ .967). Floors are met on the observed cohort, but recalls are not identical and finer budgets were not searched. Do not call this exactly equal-quality performance or an optimal configuration. RaBitQ queries remain slower at these selected cells despite its smaller snapshot/RSS.

Quality is measured after loaded-only RSS/VmHWM checkpoints. Existing first-query mode warms one query at the stored default before the quality loop; that loop reads all query/truth records and uses SearchWithOptions with the selected per-call ef. P50/P99 time only SearchWithOptions; loop CPU additionally includes input reads, validation and truth intersections. Source/binary/input/snapshot hashes distinguish the loader quality extension from the original 100k load batch. Stored graph defaults and files are not changed by per-call budgets.

Raw CSV is retained for each cell, but this initial grid does not archive every quality-loop neighbor/hit row. Report verification recomputes selection and checks CSV/options/hashes, not independent per-query truth intersections. The consumer directly scored against recorded GT and passed exact-clique fixtures in Release and ASan+UBSan. Main 100k builder traces separately archive full query neighbors; those cannot be substituted for higher-ef traces. A future repeated/final run must retain per-query quality-loop evidence if stronger audit is required.

```bash
VSAG_LOAD_QUERY=DATASET/queries.fvecs VSAG_LOAD_QUALITY_TRUTH=DATASET/groundtruth.ivecs VSAG_LOAD_QUALITY_EF=2048 taskset -c 0 BUILD/lite_load_memory SNAPSHOT DIM 100000
python3 lite/benchmark/run_quality_budget_sweep.py BUILD RAM_SNAPSHOTS --identity MAIN100K/identity.json --archive NEW_GRID_DIR
```

Next use these bounded settings for long mixed/real changed-vector validation and repeated latency at matched floors, plus Full comparison. No public default, library algorithm, format or PR branch is changed by this task.

中文：36格预声明查询预算网格只用历史100查询，RaBitQ可在SIFT512/GIST2048/Cohere2048达到本轮门槛，但查询仍慢，且不是精确等召回/最优/盲验收。只保留逐格汇总CSV，未保存高预算逐query明细，verifier不冒充独立truth重算。模型/构建/默认预算均未改。
