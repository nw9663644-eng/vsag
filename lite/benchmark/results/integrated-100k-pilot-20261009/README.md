# Integrated 100k fixed-budget and loaded-state pilot

2026-10-09. Library at 7d7c175565b924d6ed327c4a18fb864d3bb6a6e6, with original loader source hash in identity.json. Existing cached datasets are reused; runner count extension is recorded separately. This is a pilot, not full acceptance.

## Initial fixed degree 16/ef 128: one builder per mode

| Dataset | Storage | Recall@10 | Build ms | P50 us | Snapshot bytes |
|---|---|---:|---:|---:|---:|
| sift | fp32 | 0.956 | 19724.573 | 269.504 | 65600064 |
| sift | fp16 | 0.956 | 16278.714 | 240.285 | 40000064 |
| sift | rabitq8 | 0.946 | 21032.332 | 317.464 | 29600672 |
| gist | fp32 | 0.742 | 40728.457 | 476.119 | 398400064 |
| gist | fp16 | 0.741 | 38307.376 | 452.220 | 206400064 |
| gist | rabitq8 | 0.748 | 43532.080 | 680.415 | 112804416 |
| cohere | fp32 | 0.891 | 39070.267 | 442.960 | 321600064 |
| cohere | fp16 | 0.890 | 35264.694 | 416.051 | 168000064 |
| cohere | rabitq8 | 0.889 | 41222.521 | 635.725 | 93603552 |

## Loaded-only medians: seven new processes per configuration

| Dataset | Storage | Load ms | Loaded RSS KiB | Current-image VmHWM KiB | First query us |
|---|---|---:|---:|---:|---:|
| sift | fp32 | 46.018 | 91016 | 91676 | 406.802 |
| sift | fp16 | 38.559 | 65936 | 66516 | 373.933 |
| sift | rabitq8 | 86.154 | 40320 | 58000 | 475.411 |
| gist | fp32 | 169.882 | 416500 | 417216 | 578.438 |
| gist | fp16 | 112.718 | 228940 | 229712 | 572.048 |
| gist | rabitq8 | 115.716 | 121636 | 139320 | 918.890 |
| cohere | fp32 | 141.064 | 341348 | 341996 | 619.276 |
| cohere | fp16 | 95.797 | 191272 | 191972 | 646.297 |
| cohere | rabitq8 | 111.767 | 102948 | 120632 | 898.231 |

## Boundaries and findings

100k vectors, 100 historically observed queries, L2 Top10, degree 16/ef 128, CPU 0. Initial construction/query numbers are one observation each, not stable performance medians. Load/first-query rows are seven fresh processes with rotated order. RSS/VmHWM are measured after load/trim before reading one query, with no base matrix resident. RAM page cache is uncontrolled, not cold I/O. Model/binary/source/input/snapshot identities are recorded. Each loader first result matches the generating builder exactly.

SIFT floating modes reach the study floor .95, but RaBitQ .946 does not. GIST and Cohere all fail .90/.95 at the fixed 128 budget. Do not replace these failures with 10k passing outcomes. A separate [per-call budget grid](../integrated-100k-budget-grid-20261009/README.md) evaluates quality at higher ef without retraining or changing stored construction settings; it is observed-query selection, not blind final acceptance.

RaBitQ loaded RSS is lower than FP32 by about 56% on SIFT, 71% on GIST and 70% on Cohere. Snapshot bytes are lower, but SIFT load and first queries are slower; GIST/Cohere load improves over FP32 but does not beat FP16. Standard long mixed CRUD, quality-matched repeated timing and Full comparison remain pending. No new library coverage claim is made; no library source changed.

All large snapshots were on RAM filesystem and are not committed. Small raw evidence was archived in the same SSH session before logout. raw.tar.gz retains nine builder query traces and 63 loader traces; inputs.tar.gz contains query/truth bytes. Base datasets remain cached host files with recorded hashes. Missing snapshots cannot be independently revalidated from their hashes alone. The loader quality extension was compiled later for the separate grid; its source/binary identity differs and is not relabeled as this initial loader batch.

Reproduce with run_loaded_storage_pilot.py --count 100000 using an input identity describing scale-100000. Defaults remain 10k, and unsupported counts are rejected before creating output. Warm-cache memory data is not allocator-owned bytes or a promise of all deployer RSS behavior. Existing PR source branches are frozen.

中文：100k固定16/128显示SIFT RaBitQ.946、GIST三mode约.74、Cohere三mode约.89，未全部达到研究门槛；不混用10k成绩。63个新加载进程确认RaBitQ常驻内存优势约56–71%，但SIFT加载及首次查询代价仍在。下一步独立预算匹配、长期真实混合维护与Full对照。
