# Large RaBitQ visited-state memory optimization, 2026-10-11

## Delivered code: smaller query workspace, not a query speedup

Mutable RaBitQ adjacency search now selects a byte or packed visited state **once per call**.
Below65536 slots it retains byte semantics; at/above65536 it uses64-bit words. The templated
TestAndSet has no per-node representation-policy branch. FP32/FP16 production paths are unchanged.
The word/mask logic follows native `src/utils/visited_list.h`, without pulling its persistent
pool, allocator or epoch-tag dependencies into Lite. Both representations remain query-owned,
so no shared cache, stale mutation state or new concurrent-call guarantee is introduced.

For GIST100k/RaBitQ8 at the same budget, the visited payload decreases100000 to12504 bytes
(-87.496%). Measured cumulative ordinary-new requests per public query decrease170160 to82664
bytes (-51.42%), with31 requests unchanged. All100 measured queries have the exact87496-byte
reduction. This is requested transient allocation, **not peak live memory, loaded RSS or whole-process
peak**; it does not by itself close the project's peak-memory or Full-comparison acceptance.

| Dataset | Old P50 us | Final P50 us | Change | Final P50 pair wins | Old P99 us | Final P99 us | Recall both |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| SIFT10k | 207.805 | 210.174 | +1.14% | 0/7 | 247.013 | 246.314 | .987 |
| GIST10k | 506.357 | 509.057 | +0.53% | 3/7 | 665.293 | 653.203 | .970 |
| Cohere10k | 484.537 | 476.277 | -1.70% | 4/7 | 544.837 | 543.667 | .984 |
| GIST100k | 1108.420 | 1121.442 | +1.17% | 1/7 | 1278.856 | 1299.616 | .859 |

The final implementation is retained as a **memory/latency tradeoff**, not a stable CPU gain.
SIFT's7/7 slower paired P50 and GIST100k's6/7 slower pairs are explicitly retained; do not call
these regressions disproved by noise. The small-scale path avoids per-node policy branching but
does not guarantee identical compiled instruction layout or latency. GIST100k P99 is also1.62%
slower here. Quantiles are medians of seven per-process nearest-rank quantiles over100 historical
queries each (P50 index49/P99 index98), not final tail-latency acceptance or statistical guarantees.
Larger/unobserved query sets and more distributions remain needed. GIST100k recall.859 is unchanged
and its graph-quality problem remains unresolved.

## Rejected prototypes are preserved, not selected as final performance

`query-visited-bitmap-20261011` contains the first all-storage bitmap prototype (12 cells/168
timed runs). Several FP32/FP16 cells slowed, and Cohere10k RaBitQ P50 slowed6.05%; this broad
implementation was not adopted. `query-visited-adaptive-20261011` contains the later per-node
dynamic-policy prototype (4 cells/56 runs); GIST10k P50 slowed7.96% despite a favorable100k
median. It was replaced by compile-time specialization. Do not present that prototype's100k
-3.91% median as the final code's performance. Sources, library hashes, CSVs and commands for all
three stages are archived. The pre-change shared library remains at
`/home/ubuntu/project/vsag-visited-bitmap-control-636519e/libvsag-lite.so` with SHA256
e8f7808b5638973974ed0704b0bd0e375e18cc1e2a0cf475d346c748f5291135.
Incremental experimental libraries were rebuilt between stages; their exact measured sources and
hashes are preserved, not all intermediate binary bytes.

## Protocol, correctness and code verification

Actual remote1.13.5.198/VM-0-10-ubuntu/HostKeyAlias119.45.24.226; repository
`/home/ubuntu/project/vsag-lite-baseline-v01`; personal experiment/lite-rabitq-next-20260926,
parent636519e. Measured dirty source hashes are pinned in identity.json, not represented as a
clean parent build. Public SearchWithOptions, CPU0/thread1 including BLAS, degree16/build128/
query512/k10, same initial snapshot/variant, seven alternating fresh-process pairs and one warmup
pass/process. No build, test or lint workload overlapped timed queries. Allocation-interception
runs are separate and no intercepted latency is reported. Not Full, post-CRUD performance,
cold I/O, durable Save or complete deployment-package measurement.

- Independent raw verifier:56 timed runs/5600 queries,8 allocation runs/800 queries,70 successful
  recorded commands. Every ordered ID/hex-distance file matches current native builder and old
  library byte-for-byte; truth intersections and quantiles recomputed. Every allocation pair has
  unchanged request count and exactly the representation-payload byte difference (zero for10k).
- Final Release6/6, ASan+UBSan5/5, RaBitQ-disabled4/4 and fresh coverage6/6 pass. Counters were reset
  only inside the verified coverage build, with reset-path/hash receipts preserved; no source or
  original experimental result was deleted. Fresh non-test src/lite+include/vsag/lite line union
 3053/3212=95.0498%; new helper16/16. This is not whole native Full coverage or branch coverage.
- Existing96-node public fixture in FP32/FP16/RaBitQ (1/17/128 dimensions, repeated changed-value
  CRUD, filters, ties, external IDs, Save/Load) yields identical output and snapshot-ledger SHA
  against the old library. This small fixture exercises the byte representation.
- New synthetic dimension1 boundary fixture crosses65537→65536→65535→65536→65537 via Remove,
  changed-value Add and Update. Unfiltered/accept-all/even-ID/reject-all searches plus Save/Load
  yield160 output rows and identical snapshot ledger per old/final/sanitized library. All three
  outputs/ledgers exact, sanitizer replay clean. It validates representation switching, not real
  high-dimensional long-term CRUD acceptance.
- Format15 passes. Source/helper/test/probe-only tidy15 passes with non-user dependency warnings
  suppressed, not a fresh complete header lint. Initial helper implicit-bool conversion and
  fixture cast/auto style warnings were fixed before their final measurement/replay; failed logs
  remain. Production public API, formula/model, query budget, graph/journal semantics and snapshot
  format unchanged. The65536 threshold is a measured engineering policy, not a portable optimum.

## Replay and open acceptance

Committed runners/verifiers preserve each stage. Final replay uses
`python3 lite/benchmark/run_query_visited_specialized.py` and
`python3 lite/benchmark/verify_query_visited_adaptive.py OUTPUT` (same four-cell raw schema).
Runners refuse an existing output path; select a new output directory and pin all library/source/
input/compiler identities. All raw files and validation logs/receipts are in raw.tar.gz with
SHA256/size manifest; extract into a fresh directory before running the verifier. Original plain
raw, datasets and control library are preserved on server; owned new RAM snapshots and fixtures
expire automatically. Large snapshot/ledger/executable bytes have hashes/size receipts, not
committed binary copies.

Only the personal branch is pushed; PR2904/2926 unchanged. CPU routing/scoring optimization still
needed, as are fresh aligned native Full, repeated100k/real high-dimensional interleaved changed-value
CRUD, larger query-tail cohorts, graph-quality remediation and complete package closure. Project
is not complete; this change is not evidence that Lite query performance now exceeds native Full.
