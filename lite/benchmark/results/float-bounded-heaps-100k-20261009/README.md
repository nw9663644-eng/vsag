# SIFT100k floating routing confirmation

Control4fc5191, candidate production624252f. Old/new Lite, NOT Full. Same SIMD build, degree16/construction128, queryef512, CPU0, k10,100queries, no warmup, zero CRUD rounds, three alternating pairs per FP32/FP16 and three fresh loads each. All six snapshot hashes and ordered neighbor CSVs agree; Recall@10 is .988 in every process.

Median microseconds:
| Storage | P50 control/candidate | P99 control/candidate |
| --- | --- | --- |
| FP32 | 832.982 / 523.389 | 1161.985 / 637.078 |
| FP16 | 749.053 / 485.279 | 1037.127 / 620.026 |

P50 decreases37.17%/35.21%; P99 decreases45.17%/40.22% in this small query cohort. Bulk construction median17416.009’11213.520ms(FP32),15165.908’9946.918ms(FP16). Snapshot65,600,064/40,000,064bytes unchanged. Load and RSS essentially unchanged; no improvement claimed.
At the start of this run separate sanitizer/coverage/tidy checks were still completing, so trial0 may have incidental host contention. Later trials retain the direction; timings are not a controlled isolated-host result. Trial1/2 P50 FP32 control832.982/810.243 vs candidate513.859/528.349; FP16 control749.053/780.863 vs candidate477.079/505.438. Keep all trials, not a cherry-picked best run.

identity.json preserves hashes, exact commands, CPU and source diff at capture4fc5191; source was committed624252f during the experiment with no change to its measured library. rows/summary/raw/SHA retain evidence. Warm/uncontrolled cache is not cold loading,100queries is not robust productionP99, .988 is not identical quality to the prior Full1.000 run. Cannot infer superiority over Full from these old/new Lite pairs.
Independent check: python3 ../float-bounded-heaps-20261009/verify.py.
