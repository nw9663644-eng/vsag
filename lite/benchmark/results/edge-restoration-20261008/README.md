# GIST Update row-restoration ablation

Measured parent: `b9a46996540c36cdab9bb03bf7f87cb3616c0dc3`. This follows the [Update routing trace](../update-trace-20261008/README.md) and changes only which complete adjacency rows are used for retrieval on the already changed vectors. GIST100k/960dim, 10,000 distinct first-coordinate `+0.125` updates, degree16, ef128, the same 100 observed queries and changed-data squared-L2 truth are fixed. The baseline and direction-aware candidate labels identify the previous maintained topologies. Every new process uses the same baseline library for Load/Search; no new native Update is performed.

## Minimal experiment

The existing `graph_slot_probe` reuses the snapshot parser and scalar routing from `graph_route_probe` and compares scalar mask0 returned IDs with actual `Index::SearchWithOptions` results. The new Linux-only Python driver creates a v2 FP32 snapshot in an anonymous `memfd`, preserving original ID order and all vector coordinates except the specified first-coordinate updates. It selects full rows from original or maintained adjacency without increasing the degree limit:

| Restoration mask | Updated-source rows | Other-source rows |
|---|---|---|
| 0 | Maintained | Maintained |
| 1 | Original | Maintained |
| 2 | Maintained | Original |
| 3 | Original | Original |

Rows retain their exact target order. Count, dimension, representation, degree, ef and IDs are preserved; payload length reflects the selected edge count. The driver checks input layout, degree, unique/in-range/non-self targets, distinct schedule and changed finite FP32 values. Three result paths refuse overwrite. The memory descriptor is passed only to the existing probe, then closed; no large hybrid snapshot is written to disk. Receipts record input, adjacency, binary and complete control-snapshot SHA256.

```bash
python3 lite/benchmark/edge_restoration_probe.py \
  INITIAL_SNAPSHOT MAINTAINED_ADJACENCY_U32 CHANGED_DATASET_DIR \
  NEW_OUTPUT_CSV CYCLES RESTORATION_MASK SLOT_PROBE_BINARY
```

The maintained adjacency encoding is the prior report's ordered uint32 stream, with one degree followed by target IDs per source. The experiment requires external IDs equal physical slots. The dataset directory must contain `queries.fvecs` and changed-data truth named `groundtruth.ivecs`. This is a bounded experimental driver, not a new Lite snapshot format or public maintenance API.

## Fixed-budget results

| Topology source | Mask0 maintained | Mask1 restore updated | Mask2 restore other | Mask3 original |
|---|---:|---:|---:|---:|
| Baseline | 0.736 | 0.740 | 0.733 | 0.741 |
| Candidate | 0.736 | 0.750 | 0.733 | 0.741 |

Relative to mask0, baseline mask1 gains 15 truth hits and loses 11, net +4; queries have 12 wins, 8 losses and 80 ties. Candidate mask1 gains 20 and loses 6, net +14; 16 wins, 5 losses and 79 ties. Mask2 loses 3 net hits in both variants despite restoring 90% of rows. Mask3 reproduces the prior original-topology control exactly. Results for all masks are in `verified.json`.

Candidate mask1 visits a mean 1292.31 nodes versus mask0 1286.55, about +0.45%; baseline mask1 visits 1283.35 versus 1288.60. Explicit edge counts remain 1,599,930 for baseline masks0/1 and 1,599,931 for candidate masks0/1; masks2/3 have 1,600,000. Every missing truth remains unvisited in these scalar traces, with zero visited-but-not-returned truth. Visit counts are diagnostic work indicators, not measured latency or CPU savings.

For this fixed geometry, restoring old rows on updated sources helps, especially when other rows retain candidate maintenance. Restoring every other row does not help. The two row groups interact: changes cannot be treated as independent additive improvements. These controls identify a row-category intervention with an observed retrieval effect, not a harmful individual edge or an online update implementation.

Mask1 candidate is selected after observing these same queries, so 0.750 is exploratory rather than blind validation. This remains below the separate GIST acceptance gate of 0.90; the historical passing configurations used different query budgets. The one-coordinate perturbation does not establish safety for arbitrary whole-vector replacement. No maintenance CPU, fresh build, concurrent CRUD, general improvement across distributions or default adoption is claimed.

## Evidence and checks

Eight fresh processes are pinned to CPU0 with one explicit library binding. They cover 800 distinct factor/query states and 800 native ID-set calibrations. The reused slot probe also executes its eight entry/ring/tie masks. Snapshot and reference are identical, so these masks must return identical ordered neighbors and trace counts; all 6,400 slot/query states pass. They do not represent 6,400 independent queries. Native ID-set agreement does not prove identical native SIMD and scalar visit sequences.

```bash
python3 lite/benchmark/results/edge-restoration-20261008/verify.py
```

The standard-library verifier checks archive/member hashes and prior-report linkage, raw neighbor ranks/IDs/hexadecimal distances, truth intersections, all repeated-mask identities and native calibration receipts. On the original host it independently reconstructs each full snapshot SHA from original vector chunks plus the chosen ordered rows and FP32 patches, and checks 8,000 scalar returned distances with FP64 squared-L2. Masks0/3 reproduce the prior maintained/original scalar neighbors exactly; both mask3 snapshots have the same SHA. Host source/input checks explicitly report availability. Archive paths are never extracted.

Release and ASan+UBSan slot builds and new fixtures pass. Fixtures check exact snapshot bytes and all four row-selection factors, native exact neighbors, output preservation, invalid masks/schedules and malformed adjacency (truncation, trailing bytes, self links, bounds, duplicates, excess degree). Existing slot fixtures and Python syntax compilation pass. C++ sources, library implementation, API, defaults and CMake are unchanged; no new library CTest or coverage result is claimed.

`raw.tar.gz` preserves successful commands/exits, library binding, identities, all output rows, receipts, queries/truth and test logs. It references the prior report's complete adjacency evidence instead of duplicating it. Large snapshots and binaries are excluded. Host scripts retain absolute historical paths and are not a portable dataset-download pipeline. Host directory: `/home/ubuntu/project/vsag-lite-edge-restoration-20261008`.

Next validate this intervention across SIFT and Cohere and on new GIST queries before designing an opt-in online retention policy. Any online candidate must still adapt to larger vector changes and be tested for maintenance cost and persistence. Only the personal experiment branch receives this work; PR branches remain frozen.
