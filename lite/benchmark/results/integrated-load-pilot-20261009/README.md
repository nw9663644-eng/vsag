# Initial loader diagnostic: superseded peak accounting

2026-10-09. This63-run pass found lower loaded current RSS but shared getrusage
high-water floors on small configurations. Its raw rows and hashes are retained
for provenance, not used as the final loader peak table. See
[corrected current-image VmHWM study](../integrated-load-final-20261009/README.md).
Both studies use the same10k cached datasets, RAM snapshots and observed first
queries; neither is strict cold I/O or allocator-owned memory.

中文：保留初轮加载诊断及原始数据，getrusage平台值不当作纯加载峰值；最终报告使用另一次63运行的当前进程VmHWM。没有删除或重新标记初轮数据。
