# Exact graph build reservation: GIST/Cohere10k

Production change e7dc1517c7a9709ef7a278f5fa187a487ecba59a. Control source3242489 with frozen library SHA in identity.json. This is old/new Lite, NOT native Full.

Source evidence: Index::BuildGraph keeps its BruteForce backend alive until a complete replacement is returned, preserving failure atomicity. The private GraphBackend formerly grew vector/ID/adjacency/incoming containers incrementally. On a growth boundary, source data, old graph buffer and new graph buffer were simultaneously resident. The candidate calls ReserveBuild(source.Size()) before Add, with overflow checks, and reserves final vector, ID, outgoing-row, incoming-row and ID-to-slot capacities. It does not release/move the source, change graph routing, API, snapshot format or RaBitQ encoding.

Three alternating paired trials per dataset/storage, CPU0, degree16, construction/query ef128, k10,100queries, no warmup and three fresh loads. One BLAS/OMP/MKL thread. Every pair has identical snapshot SHA and ordered neighbor export; Recall is unchanged.

| Dataset/storage | Peak RSS control/candidate KiB | Reduction | Build ms control/candidate |
| --- | ---: | ---: | ---: |
| GIST FP32 |178824/125636|29.74%|1303.565/1376.102|
| GIST FP16 |129428/103764|19.83%|1394.825/1371.877|
| Cohere FP32 |143888/102868|28.51%|1310.580/1332.258|
| Cohere FP16 |104308/84276|19.20%|1270.424/1271.630|

Build time has mixed noise and is not claimed as improved. Snapshot size, loaded RSS, load latency and query latency are unchanged within noise. External peak includes input/source, graph construction and process baseline; it is the relevant current build peak but not allocator-internal attribution.

Validation: Release6/6; ASan/UBSan8/8 including exhaustive allocation-failure rollback; coverage6/6; default-RaBitQ-off4/4; production Lite2606/2752=94.6948%; format15/tidy15/diffcheck pass. This source change does not touch RaBitQ construction, whose separate peak remains a future target.

raw.tar.gz preserves commands, stdout/stderr, parameters, per-query latency/neighbor rows and peak RSS. identity.json records exact source diff, input hashes, CPU, binaries and invocation. Run python3 verify.py.
