# Persistent changed-vector Update replay

Measured parent: `b0c2b61cdde3f1f36b97aac7e58097649afcf708`. This extends [the bounded persistent-update fixture and CRUD raw audit](../crud-raw-20261007/README.md) to representative 100k datasets. It does not change the Lite library or adopt the direction-aware repair candidate.

## Source evidence and minimal change

`src/lite/graph_backend.cpp::Update` validates and stores the changed vector, replaces outgoing links, repairs affected nodes and protects incoming links of old targets. The previous large replay restored vectors before querying; its recall therefore did not test retrieval with persistent changed data.

The existing route probe now has an independent opt-in command:

```bash
lite_graph_route_probe --persistent-update SNAPSHOT DATASET_DIR NEW_OUTPUT_CSV CYCLES
```

It directly loads the original FP32 graph with public `Index::Load`, updates distinct original slots `(cycle * 8191) % N`, changes only the first coordinate by FP32 `+0.125`, and leaves every changed value stored. It calls only `Update`: no restore, Remove, Add or rebuild. The schedule requires gcd(N,8191)=1 and 1<=CYCLES<=N. A non-finite or unchanged first coordinate is rejected. Search uses the snapshot's stored ef, then checks exact ordered ID/float-distance equality after Save/Load. Old commands are unchanged.

Dataset inputs are `queries.fvecs`, `groundtruth.ivecs`, and `changed-groundtruth.ivecs`. Both truth files have identical query/k shapes and unique live IDs. Outputs are the summary CSV, `.neighbors.csv` (`phase,query,rank,id,distance`), and `.updates.csv` (`cycle,id,original_first,changed_first,latency_us`). Hexadecimal floats preserve original and changed values. Existing output paths are refused. The diagnostic is externally serialized and does not add concurrent-call support.

No public API, graph policy, SIMD, snapshot version, default parameters, CMake options or library source changed. Shared-library hashes match the prior archived [direction-aware repair candidate](../diverse-repair-20261007/README.md).

## Protocol and independent truth

SIFT128, GIST960 and normalized Cohere768 each use the same previously stored 100,000-vector initial graph, degree16/ef128, L2 Top10, and 100 already observed queries. Baseline/candidate pairs start from the identical snapshot. CPU affinity is 0 with explicit LD_LIBRARY_PATH and recorded ldd. One fresh process per dataset/variant gives six processes, 60,000 Update calls and 1,200 initial/changed query states. Each process updates 10,000 distinct IDs (10%); this is not full100k churn, concurrent mutation, arbitrary update distributions, or a repeated statistical timing study.

`prepare-host.py` memory maps the snapshot's original FP32 vectors and IDs. It evaluates exhaustive squared L2 with FP64 subtraction/summation, applies exactly rounded FP32 changed first coordinates, and orders by distance/external ID. The recomputed initial truth sets match all 100 original queries on every dataset. Changed Top10 sets differ on 0 SIFT queries, 14 GIST queries, and 52 Cohere queries. Both ground truths and the original query bytes are archived; no new large base/snapshot copy is generated. Changed Cohere vectors are not renormalized; the metric remains squared L2, not cosine. Preparation uses cached NumPy dependencies and OPENBLAS_NUM_THREADS=1, outside native experiment timing.

## Results

| Dataset | Initial recall (both) | Changed baseline | Changed candidate | Update CPU baseline ms | Candidate ms |
|---|---:|---:|---:|---:|---:|
| SIFT | 0.956 | 0.954 | 0.954 | 2905.586 | 2980.400 |
| GIST | 0.742 | 0.736 | 0.736 | 5788.828 | 5985.841 |
| Cohere | 0.891 | 0.894 | 0.899 | 5202.492 | 5370.140 |

Candidate versus baseline: no final recall gain on SIFT/GIST, +5/1000 hits on Cohere. Mutation-block CPU is +2.6%, +3.4%, +3.2% respectively in these single runs. It includes scratch allocation, native Update and local checks/timing, excludes exported CSV I/O and queries, and is not pure kernel time. It cannot establish stable speed/CPU differences from one run.

Initial and changed recall use different data/ground truth; their difference alone cannot isolate topology effects. The direct native-load initial results should not be substituted with results from a reconstructed diagnostic graph. This small coordinate perturbation is a bounded representative-data check, not a replacement for whole-vector or workload-specific update validation. There is no new holdout, universal acceptance gate, optimality claim or default candidate adoption.

## Verification

- Release route and slot targets built; persistent-update, existing route, and slot fixtures passed.
- The persistent fixture changes the actual nearest neighbor and independently checks its ID/distance, update receipt and roundtrip. Invalid counts/suffixes, truth shapes/IDs, missing changed truth, and each existing output path are rejected.
- ASan+UBSan build and persistent fixtures passed; candidate library persistent fixtures also passed.
- clang-format15 dry run and clang-tidy15 route/slot checks passed; third-party warnings were suppressed.
- No library coverage or new library CTest result is claimed because no src/include code changed.

Run the standard-library audit:

```bash
python3 lite/benchmark/results/persistent-update-20261007/verify.py
```

It checks published/member SHA256, all 60,000 mutation schedules and exactly rounded first-coordinate receipts, 12,000 native returned neighbors, ordering/uniqueness, truth intersections, summary identities, and six successful exits with roundtrip receipts. With original host snapshots present, it additionally checks each original changed coordinate and recomputes all 12,000 returned squared-L2 distances, accepting FP32 kernel rounding within rel_tol=3e-6/abs_tol=1e-6. All checks passed with snapshots/source inputs available. Off-host it explicitly reports unavailable host checks; it does not regenerate the exhaustive 100k truth during the audit.

`raw.tar.gz` contains summaries, neighbors, updates, truth/query files, prepared metadata, identity and test/lint logs. `manifest.json` and `members.json` bind the evidence; archive members are read without extracting paths. `prepare-host.py`, `run-host.py`, `package-host.py` preserve absolute-path historical commands, not a portable download/build pipeline. Large snapshots, binaries and private project instructions are not committed. Host: `/home/ubuntu/project/vsag-lite-persistent-20261007`.

Next, a storage-only control that changes vector bytes while preserving the original edges can separate changed data from topology maintenance effects. The candidate remains optional pending that diagnosis and a justified quality/cost decision. Only the personal experiment branch is updated; PR branches remain frozen.
