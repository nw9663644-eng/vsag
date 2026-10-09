# Integrated storage: fresh loaded-only 10k processes

2026-10-09. Integrated library at 3ad0fb9228ba0b1595b6c943a2ed9f97fe002c8d; loader edits are identified by source hashes. This extends the existing load_memory consumer; no library algorithm or snapshot format changed.

## Frozen scope

Three existing 10k datasets and FP32/FP16/RaBitQ, degree 16/ef 128. One new RAM snapshot per configuration, then seven fresh loader processes with rotated storage order on CPU 0. Loader never reads original base vectors. Loaded RSS is measured after closing the input stream and malloc_trim, before reading the single query. Baseline process image and library remain included. VmHWM is read at the same pre-query checkpoint. First query reads only the first fvec record and returns 10 IDs/distances, checked against the builder query exactly. Historical query is not blind validation. Cache is uncontrolled and snapshots are on RAM filesystem, so this is not strict cold I/O.

| Dataset | Storage | Load ms | Loaded RSS KiB | Load VmHWM KiB | First query us | Snapshot bytes |
|---|---|---:|---:|---:|---:|---:|
| sift | fp32 | 3.972 | 12540 | 12544 | 110.687 | 6560064 |
| sift | fp16 | 3.207 | 10064 | 10068 | 105.678 | 4000064 |
| sift | rabitq8 | 8.473 | 7420 | 9048 | 201.005 | 2960672 |
| gist | fp32 | 16.877 | 45092 | 45096 | 312.603 | 39840064 |
| gist | fp16 | 10.589 | 26288 | 26292 | 270.343 | 20640064 |
| gist | rabitq8 | 11.333 | 15544 | 17228 | 545.029 | 11284416 |
| cohere | fp32 | 13.743 | 37520 | 37536 | 356.942 | 32160064 |
| cohere | fp16 | 8.731 | 22556 | 22560 | 258.586 | 16800064 |
| cohere | rabitq8 | 10.457 | 13672 | 15116 | 497.080 | 9363552 |

## Interpretation

RaBitQ loaded current RSS is lower than FP32 by approximately 41% on SIFT, 66% on GIST and 64% on Cohere, and lower than FP16 as well. This supports a deployment-memory advantage at these 10k configurations, unlike the higher build/whole-process peaks in the prior integrated pilot. It does not establish memory behavior at 100k or after long churn. SIFT RaBitQ load is over twice FP32; GIST/Cohere load is faster than FP32 but slower than FP16. First queries are slower than both floating-storage modes. Keep these costs with the size/memory gains.

The older getrusage process_peak_rss_kib is preserved in raw data. Small modes show a shared launch-related high-water floor (~19–20MiB) despite lower current-image VmHWM; it must not be reported as clean standalone loader allocation peak. The final table uses current-image VmHWM at the pre-query checkpoint. Neither metric is allocator-owned component bytes or a guarantee of every platform/launcher behavior.

## Verification and availability

63 fresh loader runs and 9 generating builder runs completed. Raw stdout/stderr/commands,63 first-query ordered result files and builder result rows are archived in raw.tar.gz. Model/storage snapshot hashes and sizes are recorded, but large RAM snapshots are ephemeral and not committed. The runner validates all cached dataset hashes before generating snapshots and archives small evidence in the same session before logout. Public schema/CLI is unchanged without optional query environment; Release and ASan+UBSan fixtures cover all storage modes, dimension/short query checks and overwrite rejection. Format/tidy15 pass after an explicit streamsize cast/capacity check. No new library coverage number is claimed.

```bash
VSAG_LOAD_QUERY=DATASET/queries.fvecs VSAG_LOAD_QUERY_RESULTS=NEW.first.csv taskset -c 0 BUILD/lite_load_memory SNAPSHOT DIM COUNT
python3 lite/benchmark/run_loaded_storage_pilot.py BUILD NEW_RAM_DIRECTORY --archive NEW_SMALL_EVIDENCE --inputs PRIOR_PILOT/identity.json
python3 lite/benchmark/results/integrated-load-final-20261009/verify.py
```

The first 63-run loader pass is preserved as diagnostic evidence in integrated-load-pilot-20261009. It exposed the getrusage floor and was superseded by the current-image VmHWM pass, not relabeled as final metrics. Large snapshots/input matrices are not in Git; raw identities are verifiable, but missing snapshot hashes cannot be independently revalidated off-host. Next gate remains 100k, long mixed/changed CRUD and quality-matched Full comparisons; PR source branches remain frozen.

中文：本轮63个新进程只加载索引，未载入原始矩阵，在首次查询前测RSS/VmHWM；三种数据集RaBitQ加载常驻内存比FP32低约41–66%，但首次查询更慢、SIFT加载更慢。旧getrusage峰值有启动器平台值，未当独立加载峰值使用；最终表使用当前进程VmHWM。仅10k、RAM暖缓存、历史单条查询，不是100k/长期/冷启动最终验收。
