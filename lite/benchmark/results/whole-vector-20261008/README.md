# Whole-vector replacement rejects unconditional old-row retention

Measured parent: `fcca19d0bccf012f5d56186e6b13c61b638bc074`. The previous [small-coordinate validation](../restoration-validation-20261008/README.md) did not establish a general benefit. This frozen pilot tests larger changes without altering the library: 100k initial vectors, degree16, ef128, 1,000 distinct updated IDs and masks0/1 only. Mask0 uses maintained topology; mask1 restores original outgoing rows on updated sources while retaining maintained rows elsewhere.

## Source and minimal implementation

`GraphBackend::Update` already accepts a complete finite vector and maintains incoming/outgoing edges. The existing persistent probe and `Index::Save/Load` checks are reused. The new opt-in mode reads `replacement.fvecs` in update-cycle order, checks dimension/count/finite values and requires a changed vector, then calls native `Index::Update`. The trace validates every stored coordinate against the supplied replacement. The first coordinate may remain unchanged; its CSV columns are only a ledger, not complete replacement evidence.

```bash
lite_graph_route_probe --replacement-update SNAPSHOT DATASET NEW_OUTPUT_CSV CYCLES trace
python3 lite/benchmark/edge_restoration_probe.py \
  SNAPSHOT MAINTAINED_ADJACENCY_U32 CHANGED_DATASET NEW_OUTPUT_CSV \
  CYCLES MASK SLOT_PROBE_BINARY --replacement-vectors REPLACEMENT_FVECS
```

`DATASET` supplies queries, original truth, changed truth and replacements; the restoration driver consumes changed truth under its existing `groundtruth.ivecs` name. The driver writes full replacement bytes to anonymous memory snapshots and records their SHA. Omitting the new options preserves the old first-coordinate `+0.125` modes. Existing output protection remains in force. Library `src/`, `include/`, API, defaults, CMake and maintenance policies are unchanged.

## Frozen synthetic update geometry

For cycle c, target ID is c*8191 modulo100,000 and donor ID is (c+1000)*8191 modulo100,000. Target and donor sets are distinct, disjoint and donors remain unmodified. Each replacement is the FP32 midpoint of original target and donor vectors. Cohere alone is normalized with an FP64 norm and rounded back to FP32, following the caller's original normalization policy. All replacement vectors differ from their originals.

The three datasets retain their previous query cohorts: SIFT128/Cohere768 each 100 observed queries, GIST960 source rows100:400 with 300 historically observed queries. None is blind. Exact changed-data Top-10 truth is recomputed against all 100k actual stored vectors with FP64 direct squared-L2 differences and ascending-ID ties. Original truth is retained separately. Replacement maps, full vectors, displacement measurements, queries and truths are archived.

This is a synthetic whole-vector interpolation stress protocol, not arbitrary production embeddings. Update coverage is 1%, while the preceding coordinate-only study updated 10%; absolute recalls between those protocols cannot isolate displacement magnitude alone. Within each new mask pair, vectors, queries, truth, degree and budget are identical.

## Retrieval results

Six fresh native Update processes run the existing baseline/candidate libraries with 1,000 calls each; all final Save/Load results preserve ordered IDs and distances. Twelve restoration processes use one common baseline Load/Search library, CPU0 pinning and anonymous snapshots. Baseline/candidate labels describe topology origin.

| Dataset/origin | Maintained | Restore updated-source rows | Net truth hits | Query wins/losses/ties |
|---|---:|---:|---:|---|
| SIFT baseline | 0.947 | 0.949 | +2/1000 | 1/2/97 |
| SIFT candidate | 0.948 | 0.951 | +3/1000 | 1/1/98 |
| Cohere baseline | 0.885 | 0.884 | -1/1000 | 4/5/91 |
| Cohere candidate | 0.885 | 0.884 | -1/1000 | 4/5/91 |
| GIST baseline | 0.754667 | 0.706667 | -144/3000 | 29/94/177 |
| GIST candidate | 0.755333 | 0.707000 | -145/3000 | 29/94/177 |

GIST baseline restoration gains 65 true hits but loses 209; candidate gains 65 and loses 210. With 10,000 paired bootstrap resamples, seed20261008, recall-delta95% intervals are [-0.062, -0.035] and [-0.062333, -0.035333]. Both two-sided sign p-values are about 3.39e-9. These descriptive statistics on observed queries support a clear counterexample within the frozen protocol, not a universal claim about all update workloads.

SIFT/Cohere deltas remain small and their intervals include zero. Full per-case edge counts, visits, hit changes and exploratory statistics are in `verified.json`. This experiment measures retrieval quality; single-run mutation CPU includes diagnostic preparation/checks and is not a stable maintenance-performance result. No query speedup or memory improvement is claimed.

**Decision:** do not adopt unconditional original-row retention for changed vectors. The large GIST loss survives input, native-result and complete-snapshot audits. Small-update point gains cannot justify keeping old outgoing rows for every displacement. Any future bounded retention candidate must re-evaluate neighbors in the new geometry and be tested online, since post-hoc restoration does not reproduce subsequent online selection/repair.

## Independent audit and tests

```bash
python3 lite/benchmark/results/whole-vector-20261008/verify.py
```

The standard-library audit checks all artifacts/members, frozen plan, source/binary identities and previous-query/library evidence. It independently verifies the 3,000 replacement vectors and donor schedule, midpoint geometry, Cohere normalization (relative2e-7/absolute1e-8 tolerance) and reported displacement. Actual replacement bytes remain exact inputs for full control-snapshot SHA reconstruction and distance checks.

All three original snapshots and all twelve complete control hashes pass. The audit validates native initial/changed IDs/ranks/hits and 20,000 native distances, plus 20,000 scalar control distances using FP64 squared-L2. Each mask0 control exactly reproduces maintained scalar neighbors and matches native returned ID sets. There are 2,000 factor/query states and native calibrations across 500 query rows; 16,000 reused slot-mask states must agree and are not independent samples. Native/scalar ID agreement does not prove identical internal visit sequences. Offline host checks report availability, and archive paths are never extracted. Exhaustive truth preparation is recorded, not repeated offline.

The topology bundle preserves original/baseline/candidate adjacency in source order as three successive uint32 degree+target rows per source. Individual maintained streams and CSV hashes are reconstructed exactly. This is evidence encoding, not a new Lite snapshot format. Large vector snapshots and binaries are excluded; replacement vectors and complete ordered topologies are retained.

Release and ASan+UBSan route/slot builds and the new fixture pass. The three-node exact oracle changes coordinates beyond coordinate zero, checks nearest IDs/distances, Save/Load, all-coordinate snapshot bytes and restoration. Unchanged vectors (including signed-zero-only changes), NaN/Inf, count/dimension mismatch, truncation and missing replacement input are rejected. Old persistent, storage-only, row-restoration and slot fixtures pass; clang-format15, clang-tidy15 and Python syntax compilation pass. No new library coverage percentage or library CTest result is claimed because library code did not change.

Host directory: `/home/ubuntu/project/vsag-lite-whole-vector-20261008`. Raw evidence contains successful commands/exits, library bindings, actual replacement files, all query results, native roundtrip receipts, test logs and input identities. Historical host scripts depend on existing data/libraries. The personal experiment branch alone receives this work; PR branches remain frozen.
