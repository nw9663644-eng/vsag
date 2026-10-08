# GIST persistent Update topology and routing trace

Measured parent: `98fa611dbea0f0b7aa7ba9650e1a6b098a904a53`. This diagnostic follows the [storage-only control](../storage-control-20261007/README.md). It uses GIST100k/960dim, degree16, stored ef128, the same 10,000 distinct first-coordinate `+0.125` updates and the same 100 already observed queries. Baseline and the existing direction-aware refill candidate are each run once on CPU0 with explicit library binding. It does not adopt a library policy.

## Source and minimal tool change

`src/lite/graph_backend.cpp::Update` removes old incoming edges, replaces outgoing neighbors, links reciprocal candidates and repairs affected nodes. `SearchImpl` uses uniform entry points, slot-ring neighbors, bounded candidate heaps and early stopping. The existing scalar `graph_route_probe::search` mirrors that unfiltered routing. The public `Index::Save/Load` boundary is reused; the original snapshot parser now also accepts a stream.

Append `trace` to either opt-in persistent command:

```bash
lite_graph_route_probe --persistent-update SNAPSHOT DATASET NEW_OUTPUT_CSV CYCLES trace
lite_graph_route_probe --storage-only-update SNAPSHOT DATASET NEW_OUTPUT_CSV CYCLES trace
```

After native queries and Save/Load checks, the tool parses the in-memory final snapshot. It checks unchanged IDs/options and every vector coordinate against the specified update schedule. It outputs directed edge additions/removals, full final adjacency order, per-query routing counts, per-truth visited/returned flags and scalar returned neighbors. It then keeps the changed vectors but substitutes the original adjacency lists and repeats the scalar trace at the same budget. All five new output paths refuse overwrite before mutations begin. Existing commands and library behavior remain unchanged.

Maintained scalar returned ID sets must equal actual API results in the same process. The audit additionally verifies original-topology scalar ID sets against the previous native storage-only control and the new native output against previous Update neighbors, including hexadecimal distances. Scalar distances are separately checked against FP64 squared-L2 on the stored changed representation. These are scalar diagnostic visits, not direct instrumentation of the SIMD native search internals; agreement of returned IDs does not prove every internal visit is identical.

## Results

| Variant | Original topology hits | Maintained hits | Lost truth hits | Gained truth hits | Changed neighbor sets | Removed / added edges |
|---|---:|---:|---:|---:|---:|---:|
| Baseline | 741/1000 | 736/1000 | 27 | 22 | 81,427/100,000 | 212,240 / 212,170 |
| Candidate | 741/1000 | 736/1000 | 28 | 23 | 81,322/100,000 | 211,820 / 211,751 |

Original-topology diagnostic visits cover 741 true neighbors; maintained visits cover 736 for both variants. Every missing true neighbor is unvisited in these traces; `visited_not_returned=0` in all four phases. Mean visited-node counts are 1287.09 original, 1288.60 baseline maintained and 1286.55 candidate maintained. Thus nearly equal total visit counts conceal different search coverage.

All lost true neighbors retain at least one explicit incoming edge. Incoming degree decreases for only 9/27 baseline and 10/28 candidate lost query/ID pairs. Initial explicit edge count is 1,600,000; final counts are 1,599,930 and 1,599,931. The loss is not explained by isolated targets or a large net drop in edge count.

Updates touch 10% of vector IDs but change neighbor sets on about 81% of nodes. Baseline removes 132,569 edges from sources outside the updated-ID set and adds 132,499; candidate removes/adds 132,097/132,028. Ordered adjacency rows change on 83,734 and 83,657 nodes, including rows whose membership is unchanged. `edges.csv` records whether each endpoint belongs to the update schedule; `verified.json` retains the full endpoint-category counts.

These observations narrow the issue to changed routing under broad maintenance. They do not identify a causally harmful individual edge, prove a general regression from 100 observed queries, or establish an optimal maintenance policy. Ring routing and entry points are unchanged; it is incorrect to describe these targets as globally unreachable. The one-coordinate protocol is not whole-vector application churn. Candidate and baseline still tie on aggregate GIST recall.

## Evidence and verification

```bash
python3 lite/benchmark/results/update-trace-20261008/verify.py
```

The standard-library verifier checks all artifact/member SHA256 values, previous-report linkage, directed edge-set differences, rank order, bounds, uniqueness and degree limits; reconstructs the full original/final topology; verifies 400 query states and 4,000 truth flags; and checks 4,000 scalar distances when the host snapshot is available. Native and original-control ID sets must match their archived references. Host input/source/binary checks explicitly report availability. Archive paths are never extracted.

The raw archive preserves commands, successful exits, library binding, source/binary identities, query/truth bytes, native/diagnostic neighbors, edge deltas and tests. Full adjacency CSVs are losslessly stored as little-endian uint32 streams: for each of 100,000 sources in ID order, one degree followed by that many ordered target IDs. `edge-conversion.json` binds packed and original CSV hashes; the verifier recreates each CSV exactly and checks its hash. This is an evidence encoding, not a new Lite snapshot format. Large vector snapshots and binaries are omitted. Host directory: `/home/ubuntu/project/vsag-lite-update-trace-20261008`.

Release and ASan+UBSan trace fixtures pass for native and storage-only modes. Sparse eight-node tests reconstruct final edge sets from recorded deltas, check updated-endpoint flags and exercise real edge addition/removal; three-node exact-neighbor and protected-output cases pass. Existing route fixtures, clang-format15 and clang-tidy15 pass. Library `src/`, `include/`, public API, defaults and CMake are unchanged, so no new library coverage percentage or CTest result is claimed. Diagnostic serialization/tracing costs and single-run mutation CPU are not used to claim a speedup.

Next use a controlled edge-retention/restoration ablation to determine which class of changes preserves GIST routes, then validate quality and single-core maintenance cost across distributions before changing library policy. The personal experiment branch alone receives this work; PR branches remain frozen.
