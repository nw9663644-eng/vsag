# Integrated storage: three-distribution 10k pilot

2026-10-09. Measured library revision d279ddf96f268c92ec12176fac1aa4e04c12f1da; opt-in benchmark edits are identified by source hashes. This measures the integrated public Index API, not historical standalone RaBitQ probes.

## Frozen protocol

SIFT128, GIST960, normalized Cohere768; 10,000 vectors and 100 previously observed queries each. Squared-L2 Top10 ground truth comes from existing prepared subsets and its file hashes are recorded. All modes use degree 16/ef 128, CPU 0, Release; three fresh initial processes per mode with rotated order. This is equal budget, not exactly equal Recall. One additional RaBitQ process per dataset performs 100 cycles of same-value Update, Remove, re-add of the original vector (1% of IDs); ground truth remains applicable. It is not sustained changed-vector or concurrent validation.

## Initial medians

| Dataset | Storage | Recall@10 | Build ms | P50 us | P99 us | Save ms | Warm Load ms | Snapshot bytes | Whole-process peak KiB |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| sift | fp32 | 0.985 | 742.790 | 80.258 | 104.127 | 25.815 | 3.626 | 6560064 | 28280 |
| sift | fp16 | 0.985 | 726.873 | 79.639 | 102.848 | 22.775 | 3.316 | 4000064 | 23228 |
| sift | rabitq8 | 0.978 | 785.777 | 157.246 | 227.585 | 7.628 | 7.684 | 2960672 | 34688 |
| gist | fp32 | 0.916 | 1635.639 | 195.565 | 341.832 | 153.088 | 9.766 | 39840064 | 178784 |
| gist | fp16 | 0.915 | 1717.460 | 182.046 | 278.784 | 97.955 | 7.337 | 20640064 | 129400 |
| gist | rabitq8 | 0.914 | 1940.691 | 461.820 | 613.597 | 9.616 | 9.289 | 11284416 | 226176 |
| cohere | fp32 | 0.960 | 1625.611 | 188.836 | 239.674 | 122.525 | 8.437 | 32160064 | 143944 |
| cohere | fp16 | 0.960 | 1656.993 | 177.077 | 212.006 | 80.155 | 6.107 | 16800064 | 104280 |
| cohere | rabitq8 | 0.961 | 1787.558 | 413.841 | 537.509 | 8.754 | 8.743 | 9363552 | 181840 |

## Short RaBitQ churn: single observation per dataset

| Dataset | Initial Recall | After100cycles | Loop wall ms |
|---|---:|---:|---:|
| sift | 0.978 | 0.977 | 52.758 |
| gist | 0.914 | 0.906 | 187.909 |
| cohere | 0.961 | 0.961 | 153.866 |

## Interpretation and limits

The study floors are SIFT/Cohere>=.95 and GIST>=.90, not universal official acceptance thresholds. These observed-query pilot configurations meet them before and after the short workload. Repeated processes are not new independent queries. Cohere uses prepared normalized vectors and L2, not a new cosine/IP backend.

RaBitQ reduces snapshot bytes vs FP32 by about 55–72%, but queries are slower and whole-process peak memory is higher in these runs. Build includes initial flat insertion, quantizer training and temporary FP32 topology. Peak includes input arrays, temporary representations, original index and reloaded index; it is not isolated owned-state RSS. Save/Load use RAM filesystem in the same process with uncontrolled cache; they are not cold start, durable-write latency or fresh-process load. Each run checked all query IDs/distances after Load. Large RAM snapshots are ephemeral and not archived; recorded snapshot hashes alone cannot independently revalidate missing snapshots.

The initial 30-run attempt completed but its RAM evidence disappeared across SSH session closure. Those outputs are not used as the final archived evidence. The runner was updated to archive small evidence in the same session and the complete 30-run protocol was rerun. raw.tar.gz includes stdout, time-v output, commands, per-query hits, ordered neighbor hex distances and input query/truth bytes; large base vectors and snapshots remain host-only/ephemeral. Verify recomputes truth intersections and medians, not all original-vector distances or exhaustive ground truth.

## Reproduction

```bash
VSAG_GRAPH_STORAGE=rabitq8 VSAG_GRAPH_DEGREE=16 VSAG_GRAPH_EF=128 taskset -c 0 BUILD/lite_graph_crud_quality DATASET /dev/shm/NEW.snapshot 0 100 NEW.queries.csv
python3 lite/benchmark/run_integrated_pilot.py BUILD NEW_RAM_DIR --archive NEW_DURABLE_EVIDENCE_DIR --sift SIFT10K --gist GIST10K --cohere COHERE10K
python3 lite/benchmark/results/integrated-storage-pilot-20261009/verify.py
```

The original positional CLI remains unchanged; optional storage/degree/ef environments and appended CSV columns make measured options explicit. The storage fixture covers all modes, CRUD reload equality and malformed values in Release and ASan+UBSan. No library source changed in this task, and no new library-wide coverage result is claimed. Format/tidy15 passed.

Next: isolated loaded-state RSS and fresh-process load, then 100k and long mixed CRUD on all distributions before promotion. Do not claim overall superiority, optimality or completed project acceptance. PR source branches remain frozen.

中文：本轮30组正式接口10k试验完整归档，RabitQ初始Recall SIFT.978/GIST.914/Cohere.961，100短cycles后.977/.906/.961；快照比FP32小约55–72%，但查询较慢且整个进程峰值内存更高。全局验收仍缺100k、独立加载内存、长期真实更新；历史查询不是盲测，RAM同进程Load不是冷启动。
