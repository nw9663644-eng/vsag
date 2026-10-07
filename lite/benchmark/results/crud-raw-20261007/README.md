# Native CRUD neighbor evidence and persistent-update correctness

Measured source parent: `6839595cebc8d33c5cc27b86fc764b7c7b1d367d`. This report completes the raw-evidence gap identified in [the preceding 100k experiment](../diverse-repair-scale-20261007/README.md). It does not adopt the experimental repair policy or change the Lite library.

## Source evidence and minimal change

`graph_route_probe.cpp::measure_crud` already calls public `Index::Update`, `Remove`, `Add`, `SearchWithOptions`, `Save`, and `Load`. Previously it exported aggregate post/mixed recall and operation timing, but no native returned IDs for independent recall recomputation. It now retains mixed results after query timing and writes `.post.neighbors.csv` and `.mixed.neighbors.csv` after the mutation loop. Columns are `event,cycle,query,rank,id,distance`; distance is hexadecimal floating point. New sidecars refuse existing paths. Original CLI and CSV schemas remain available. Retention allocations/bookkeeping alter whole-loop CPU and memory: these runs are correctness diagnostics, not a new performance comparison.

`--self-test` additionally checks persistent changed-vector storage against an independent exhaustive squared-L2 oracle: 24 nodes, 768 dimensions, non-contiguous external IDs, k=4, degree=8, ef=24, both FP32 and FP16. Sparse integer coordinates make distances exactly representable. Eight vectors are changed and remain changed during all queries and Save/Load. Initial, changed, and reloaded states each check 24 queries, totaling 144 query-state checks and 576 ordered ID/distance comparisons per library. The full-node budget deliberately checks data semantics rather than approximate routing quality. It does not validate arbitrary FP16 rounding or concurrent calls.

Library algorithms, default policy, query budget, snapshot formats, SIMD, API and CMake options are unchanged. The direction-aware repair candidate remains the archived prototype from [its report](../diverse-repair-20261007/README.md), using the same verified shared-library hashes.

## Fixed diagnostic replay

CPU 0, FP32, stored degree 16 and ef 128; SIFT128, GIST960 and normalized Cohere768 each have 100,000 live vectors and 100 previously observed queries, L2 Top-10. Each variant loads the same original stored snapshot, performs 10,000 cycles of changed Update (first coordinate +0.125), restore Update, Remove, and Add original vector. Every tenth completed cycle queries one of the 100 queries cyclically. This is 10% distinct IDs, not a full 100k churn. Six fresh processes completed successfully: 60,000 cycles / 240,000 mutation calls, 6,000 mixed-query events and 600 final-query events. No new held-out queries are used. Mixed searches happen after restore/re-add; persistent changed-vector searches are validated only by the bounded fixture above.

| Dataset | Post baseline | Post candidate | Mixed baseline | Mixed candidate |
|---|---:|---:|---:|---:|
| SIFT | 0.948 | 0.950 | 0.9521 | 0.9529 |
| GIST | 0.723 | 0.726 | 0.7293 | 0.7312 |
| Cohere | 0.897 | 0.900 | 0.8924 | 0.8937 |

`verify.py` independently intersects all 66,000 returned IDs with archived `groundtruth.ivecs`, checks event/cycle/query/rank, uniqueness, ID bounds, finite nonnegative distances and distance/ID ordering, and matches both runner CSV and recorded run aggregates. All 6,600 events pass. These values exactly reproduce the previous aggregate results. They substantiate the recorded quality tradeoff, not statistical significance or optimality. Candidate default adoption remains deferred.

## Verification and reproducibility

- Release route/slot targets built successfully; route and slot Python fixtures passed.
- ASan+UBSan route target built and route fixtures (including persistent-update checks) passed.
- Baseline and candidate explicit-library `--self-test` passed; shared-library selection is recorded by `ldd`.
- clang-format 15 was applied; clang-tidy 15 exited zero with only suppressed third-party warnings.
- Each native run validates every final query's ordered IDs and float distances through Save/Load.
- No new library unit-coverage claim is made: no `src/` or `include/` change.

Run the portable raw audit with Python standard library only:

```bash
python3 lite/benchmark/results/crud-raw-20261007/verify.py
```

`raw.tar.gz` includes native sidecars, summaries, raw operation samples, truth files, six commands/exits, source/input/library hashes and test logs. `members.json` binds every archive member; `manifest.json` binds published artifacts. The audit reads members without extracting paths. When original host inputs remain available it additionally rehashes them; off-host it explicitly reports their unavailability. It recomputes recall, but does not independently recompute every returned distance from the 100k base.

`run-host.py` and `package-host.py` preserve historical commands and absolute host dependencies; they are not portable dataset download/build entry points. Large snapshots, binaries and private project instructions are not committed. Host evidence directory: `/home/ubuntu/project/vsag-lite-crud-raw-20261007`.

Further work should decide repair adoption from quality versus CPU cost, and evaluate persistent changed-vector ANN recall on representative workloads before integration. No PR is updated by this experiment.
