# Lite 8-bit RaBitQ design and delivery boundary

Status (2026-10-09): implementation-aligned design for the opt-in personal development branch, audited at `bcaf9c31e89abe811de84ffad3e1f63dadaa6882`. The public candidate is implemented; performance acceptance and upstream promotion are not complete. This supersedes the earlier RABITQ enum / VSAGLT01 v4 proposal. It does not assert maintainer or mentor approval of the candidate format.

## Decisions

| Area | First delivery decision |
| --- | --- |
| Entry | `BuildGraph(VectorStorage::RABITQ8, max_degree, ef_search)` from nonempty BruteForce; `ENABLE_RABITQ_LITE_BACKEND=ON` is required and defaults OFF |
| Metric/profile | Squared L2 estimates; 8 bits = 3 filter + 5 supplement; four transform rounds, six coordinate-adjustment rounds, error rate 1.9, training seed 47 |
| Lifetime | One fixed centroid and flip model, owned codes and IDs; no online retraining, no persistent raw FP32 vectors |
| Queries | Existing Search/filter contract plus per-call SearchWithOptions; no concurrent calls |
| Mutations | Prepared encoding and local rollback journals; identical complete encodings skip topology changes after validation |
| Persistence | Keep candidate `VSAGLQ01` version 1 separate from FP32/FP16 `VSAGLT01` versions 1/2/3 and experimental `VSLRBQ01` |
| Promotion | Keep candidate on the personal branch until acceptance gaps below close; do not merge benchmark archives into the feature PR |

These are engineering decisions for this candidate, not new externally approved acceptance thresholds. No automatic BruteForce-to-graph switch is added: the caller explicitly pays the construction cost.

## Source evidence and reuse limits

| Source | Reused contract or implementation |
| --- | --- |
| `include/vsag/lite/index.h`, `src/lite/index.cpp` | Owned Index, tl::expected, explicit graph conversion with publication after success; disabled RABITQ8 returns UNSUPPORTED_INDEX_OPERATION |
| `src/quantization/rabitq_quantization/rabitq_quantizer.cpp` | FastEncodeRaBitQ coordinate adjustment; centered split-code IP and distance math |
| `src/simd/kernels/rabitq_pack.h`, `src/simd/kernels/rabitq_compute.h` | Official plane packing and isolated filter kernels; no Full allocator/datacell dependency imported |
| `src/lite/rabitq_codec.h` | Fixed model, transform/inverse, prepare_encoding, split EncodedRecords; caller-owned decode scratch |
| `src/lite/rabitq_filter_ip*.cpp` | Generic fallback; runtime AVX2+FMA or complete AVX512 feature checks with per-file ISA flags |
| `src/lite/rabitq_graph_state.h` | Search/filter traversal, frozen-model mutable state and transactional Add/Update/Remove |
| `src/lite/rabitq_backend.cpp` | Public error translation, model construction, code ownership, identity update check |
| `src/lite/rabitq_snapshot.h` | Actual little-endian format, layout and topology validation |
| `src/lite/rabitq_backend_test.cpp`, `lite/example/rabitq_example.cpp` | API lifecycle, corruption and allocation-fault regressions; executable public usage |

Lite borrows simple official algorithms and kernels. It does not claim the Full fused 16-cluster model, graph implementation or storage ABI is reused unchanged. Quantized estimates and reconstructed vectors are not exact input vectors.

## Model, construction and memory

Build requires `1 <= count <= 1000000`, `0 < dim <= 2^20`, `2 <= degree <= 64`, and `ef >= degree`, subject to container/stream capacity and finite arithmetic checks. Add cannot exceed the candidate one-million-record cap. These are safety limits, not validated practical capacity guarantees.

Current construction scans the source backend row by row to train the centroid/flip model and encode vectors, calls the existing FP32 graph builder for initial topology, then constructs RaBitQ state and publishes it on complete success. Training preserves separate finite-value and centroid passes in the original row order. It needs at most a single decoded row of scratch instead of a copied N-by-D matrix. Add/Update subsequently use the frozen model and quantized neighbor discovery. Initial construction retains the source raw vectors and temporary floating adjacency, but the build-only graph reads source rows rather than owning a second FP32 matrix; its peak still needs separate measurement. Model drift from later insertions remains a quality risk.

Training row pointers are consumed before requesting the next scratch-backed row. Topology construction reuses the existing FP32 graph algorithm with a synchronous read-only source: pair distances use separate row scratch buffers, and no borrowed graph or row pointer escapes the factory. Only owned adjacency is returned and converted to topology; temporary adjacency is released before mutable RaBitQ state construction. The original source backend remains intact until successful publication, including when any intermediate allocation fails.

For dimension D and N records, encoded plane payload per record is `8 * ceil(D/8)` bytes, with six float metadata fields (24 bytes). The model contains D floats and `4 * ceil(D/8)` flip bytes. Runtime additionally owns 8-byte external IDs, an ID/slot hash map, adjacency allocations, capacities and temporary query/journal buffers. Neither the bit count nor snapshot size represents whole-process RSS. Large candidate construction and resident mutation costs must be measured separately.

Decoding uses caller-owned scratch and returns an approximate original-space vector. Save retains model/codes directly; decoding and re-encoding is forbidden as a persistence shortcut. Seed reproducibility is bounded to the recorded implementation/toolchain: exported exact flips and centroid, rather than a promise about standard-library random distribution portability, provide Load consistency.

## Query contract and cost

1. Validate finite FP32 query and dimension. Normalize/transform using the immutable model.
2. Traverse with 3-bit filter estimates. Keep the current uniform entry points and implicit slot ring; visited checks prevent duplicates.
3. Without a filter, reorder retained traversal candidates using the complete 3+5 estimate. With a filter, rank visited accepted external IDs with that estimate; rejected nodes remain traversable.
4. Return quantized squared-L2 estimates ordered by distance, then external ID. These are approximate, not exact FP32 distances. The heuristic lower bound is not a universal recall guarantee.

SearchWithOptions zero uses the stored budget; the effective budget is bounded by the live count and requested result count. Query overrides do not modify construction/mutation defaults or saved settings. k=0 and an empty index after removals return no results. Filters may return fewer than k candidates.

Transform/normalization costs O(D) per query; each filter and supplement evaluation also scales with D, while visited storage scales with N. Graph search caches query_sum once and reuses the coarse filter inner product during complete 3+5-bit scoring. Before each four-record adjacency batch, read-only cache hints prefetch the filter plane cache lines and metadata, following native HGraph RaBitQ filter prefetching. These hints do not change scoring, traversal order, visited state, filtering or persistence, and do not allocate shared query scratch. Benefits depend on dimension, cache and hardware; this is not a blanket latency guarantee. Higher ef cannot be described as free performance optimization.

## CRUD and failure boundaries

| Operation | Current behavior | Limit |
| --- | --- | --- |
| Add | Validate ID/vector; prepare code/query, reserve storage, journal changed rows, publish record; roll back on exceptions | Growth, neighbor discovery and journal allocation still cost work |
| Update | Validate existing ID, prepare once, compare all code planes and metadata; skip identical encoding; journal code/changed rows before relinking | Equal encoding does not mean raw inputs are identical; real distribution changes can degrade graph/model quality |
| Remove | Physical last-slot compaction; repair every incoming reference even for asymmetric graphs; journal code/ID/rows and retain removed map node for rollback | Default has no incoming index and may scan O(total_edges); it is not O(degree) |
| Incoming experiment | Separate optional internal path | Still uses clone fallback for transactions; not enabled through this public delivery |

Public Add/Update/Search return tl::expected. Allocation/capacity failures map to NO_ENOUGH_MEMORY; normal vector/ID validation to INVALID_ARGUMENT; guarded unexpected operation failures to INTERNAL_ERROR. Snapshot parse failures map to INVALID_BINARY and stream write failures use the existing READ_ERROR convention. Remove's bool conflates missing IDs and transaction failure: false preserves original state but cannot report the cause. Document this; do not silently change its public signature.

Build failure keeps the old backend. Failed transactional mutation keeps logical records/topology/model intact. Save failure can leave a partially written stream, so callers needing atomic file replacement must write a temporary file and replace after success. No concurrent-call or atomic filesystem guarantee is added. Allocation fault tests support the rollback contract; they do not prove every external allocator/platform case.

## Exact candidate snapshot layout

All integer fields are little-endian u64 except the 8-byte magic. Floats are IEEE float32 bit patterns in little-endian order. IDs persist signed int64 bit patterns.

| Order | Contents |
| --- | --- |
| 1 | magic VSAGLQ01, version=1, D, N, centroid_count=D, flip_count=4*ceil(D/8) |
| 2 | D centroid floats; flip_count bytes |
| 3 | Per record: norm, code_norm, error, filter_norm, filter_error, lower_bound_error (six floats), 3*ceil(D/8) filter bytes, 5*ceil(D/8) supplement bytes |
| 4 | max_degree, ef_search, ID count=N; N external IDs |
| 5 | offset_count=N+1, neighbor_count=E; N+1 offsets and E neighbor slots |

Total snapshot bytes are `96 + 4D + 4*ceil(D/8) + N*(40 + 8*ceil(D/8)) + 8E`. This excludes filesystem and runtime hash-map/capacity overhead. The serialized records are interleaved; the in-memory filter/supplement arrays are separate contiguous arrays.

Version 1 fixes profile constants implicitly. It does NOT store seed/error rate/bit identifiers as separate fields, contrary to the old proposal. Exact model bytes suffice for Load without retraining. Any future change to fixed codec/transform semantics must use a new recognized format version with explicit compatibility tests; do not reinterpret v1. No migration to VSAGLT01 v4 is scheduled merely to unify magic strings.

Load verifies seekable remaining length before encoded allocations, dimension/count/model layout, finite and valid metadata, unique IDs, valid offsets, degree bounds, neighbor range, no self-links/duplicates, truncation and trailing bytes. It restores codes and topology, not original vectors. Existing floating formats remain separate and unchanged. Disabled-backend behavior and malformed-magic error classification must follow Index::Load as implemented, not a speculative unified loader.

## Measured evidence and remaining acceptance

Evidence comes from the committed studies under `lite/benchmark/results/`; do not label this document a new benchmark run.

| Study | Observation | What it does not establish |
| --- | --- | --- |
| integrated-load-final-20261009, 10k | Fresh-process loaded RSS about 41–66% lower than FP32 across SIFT/GIST/Cohere | Cold I/O, build peak, long changed CRUD or universal latency improvement |
| integrated-100k-pilot-20261009 | Fixed degree16/ef128 RaBitQ Recall@10 SIFT .946 / GIST .748 / Cohere .889; lower loaded RSS | Quality floor compliance at this stored budget |
| integrated-100k-budget-grid-20261009 | Observed-query selection: SIFT ef512 .975; GIST ef2048 .924; Cohere ef2048 .967 | Blind acceptance, exact matched recall, repeated stable timing or optimality |
| CRUD journal regressions | Public lifecycle, snapshot roundtrip and bounded allocation-fault rollback tests pass in prior evidence | Long real whole-vector mutation performance at accepted query settings |

The study floors (.95 SIFT/Cohere, .90 GIST) are declared experiment floors, not community-wide final requirements. Larger ef satisfies those observed floors with slower queries than floating storage. RAM-backed warm uncontrolled loading is not cold-start storage benchmarking. 100k grid stores aggregated quality, so final acceptance must add returned-neighbor evidence rather than pretending old ef128 query files prove high-ef results.

## Remaining work in dependency order

1. Finish an auditable acceptance runner using existing cached inputs: fixed single core, SIFT128/GIST960/Cohere768, 10k and 100k, exact source identity and configuration. Store per-query IDs/distances/hits and CPU/wall samples; independent truth reflects each changed live vector set.
2. Run long mixed Add/changed Update/Remove, including whole-vector changes, fixed-model drift, repeated ID churn, filtered search and post-mutation persistence. No concurrent guarantee is in scope. Record throughput, P50/P99 and quality checkpoints, plus transaction failures and fallback costs. No default budget increase during a run.
3. Compare Lite FP32/FP16/RABITQ8 with Full at declared quality targets under the same single-core protocol. Separate single-insert/update/remove cost from initial build; report build/query CPU, package/snapshot size, load-only RSS and peak separately. Use repeated fresh processes for timing claims. A 1M run is optional capacity characterization after these required small-scale gates, not a prerequisite for the Lite 10k/100k decision.
4. Optimize only identified costs: first a prepared query context caching query_sum and filter results for reorder, then scalar-vs-SIMD differential tests and measured three-distribution comparison. If build peak dominates, evaluate encoding and transferring topology without keeping duplicate graphs, keeping failure publication semantics. Incoming indexing needs its own memory/Remove tradeoff review. These are proposed changes, not implemented by this design update.
5. Freeze documentation, installed example, format compatibility and default-OFF behavior; rerun Release, ASan/UBSan, format/tidy15, candidate-scoped coverage >=90%, corruption/fault and dependency checks. Promote feature-only code to the PR source branch only after explicit authorization.

## Questions to settle with the mentor

- What minimum Recall@10, allowable P99 regression, and memory reduction justify the quantized tradeoff? Compare quality-aligned settings, rather than assuming minimum RSS wins.
- Is the first release explicitly single-threaded, with frozen-model Add/Update and bool Remove limits documented?
- Is the separate candidate format and default-OFF opt-in acceptable for upstream delivery, or should a maintained format be agreed before promotion?

Work on existing CRUD correctness, single-core evidence and query context optimization can proceed without inventing new features while these acceptance choices are discussed. Deferred features: IP/cosine, PCA/MRQ, disk supplement, mmap/zero-copy, online retraining, raw-vector exact reorder, fused clusters and ARM-specific SIMD. No completion date or global optimum is claimed until the acceptance work is measured.

### 2026-10-10 exclusive mutation-stage diagnosis

An isolated single-thread RAM profiler at source bc3e9bd measures changed-vector CRUD without changing production. Fixed 10k/600-query,degree16/maintenance128/query512,three full-ID Update/Remove/Add passes: GIST/Cohere exclusive CPU shares are nearest (including route/scoring)29.20/30.91%, incoming scans19.08/22.21%, neighbor score/sort20.15/17.90%, transformed-code reconstruction13.77/11.93%, encoding6.28/5.97%. Clocks perturb costs; these are diagnostic shares,not production improvements or a Full comparison. Ordered results/snapshot SHA match prior NONE controls; Recall remains.811167/.908167. See `lite/benchmark/results/rabitq-mutation-profile-20261010` for compiled sources,receipts,scope/calibration fixtures and audit180000operations/2400truthstates. Production tests/coverage are inherited,not rerun. Prioritize measured route/scan costs at fixed quality/budget;100k/interleaved CRUD,fresh Full alignment,cold I/O remain open.

### 2026-10-10 rejected blocked transformed-code decoder

A real production candidate adapted native RecoverOrderSQ shift/mask recovery to eight coordinates per plane byte in MutableGraphState::decode_query. Original float division,graph policy,budgets,API/model/snapshot stayed unchanged. Exhaustive256code/tail/unaligned/four-norm bitwise regression and candidate Release6/SAN5 passed. Fixed10k GIST/Cohere600queries,NONE/NONE,three alternating pairs,three full-ID changed UpdateRemoveAdd passes: CRUD median+0.18484%/+1.57367%,all pairs slower in this sample,no gain established. Candidate header/test were restored byte-exact to675aed7; restoredRelease6/SAN5 and final format/tidy15 passed,defaultlibrary SHA1a18379a unchanged. No fresh coverage/OFF/wholeFull/Node result. Evidence `lite/benchmark/results/rabitq-block-decode-20261010` independently audits1080000operations/14400truthstates,paired ordered results/snapshotSHA,183rawmembers30852726bytes and10validation exits. DefaultRecall.811167/.908167 unchanged. Next inspect existing native Batch4 inner-product scoring for graph-maintenance reuse; not yet implemented or measured. Project acceptance remains incomplete; PR2904/2926 unchanged.
