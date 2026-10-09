# Lite RaBitQ 3+5 feasibility boundary

This document records the source-based boundary for a possible standalone Lite
RaBitQ backend. It is an experiment design, not a public API commitment. The
Full HGraph reference measurements are recorded in `README.md` and
`FINAL_REPORT.md`.

## Source evidence

The proposed direction follows the repository's existing implementation rather
than defining a new quantizer:

- `docs/docs/en/src/quantization/rabitq_split.md` defines x+y split storage:
  x filter bits drive traversal, y supplement bits are read for reorder, and
  the final distance uses x+y bits.
- `src/algorithm/hgraph/hgraph_parameter_test.cpp` verifies that external
  `rabitq_bits_per_dim_base=3` and `rabitq_bits_per_dim_precise=5` map to an
  eight-bit RaBitQ quantizer with `rabitq_bits_per_dim_filter=3`.
- `src/quantization/rabitq_quantization/rabitq_quantizer.cpp` trains a centroid
  and random transform, encodes normalized vectors, lays out split bit planes
  and metadata, and combines filter and supplement contributions.
- `src/simd/generic.cpp` and `src/simd/rabitq_simd.h` provide the scalar
  split-code inner product, supplement inner product, and scalar-to-plane pack
  operations together with dispatched SIMD variants.
- `src/datacell/rabitq_split_datacell.h` owns two independent fixed layouts and
  performs filter-only traversal followed by supplement-backed full distance.
- `src/impl/transform/fht_kac_rotate_transformer.cpp` applies four rounds of
  persisted random sign flips and FHT/Kac transforms. Its model is not a dense
  orthogonal matrix.
- `include/vsag/lite/index.h`, `src/lite/backend.h`, and
  `src/lite/graph_backend.cpp` show that Lite currently exposes FP32/FP16
  storage and a single-stage graph distance. Add, Update, Remove, filtered
  Search, and versioned snapshots all operate through this smaller contract.

## Exact 128-dimensional L2 layout

For the measured x=3, y=5 configuration, Full maps the quantizer to total
bits B=8 and filter bits x=3. With dimension d=128, one bit plane is
`ceil(d/8)=16` bytes.

The ordinary split layout derived from `RefreshSplitLayout` is:

| Record | Planes | L2 metadata | Bytes/vector |
| --- | ---: | --- | ---: |
| Filter | 3 x 16 | norm, filter-code norm, lower-bound error, filter error | 64 |
| Supplement | 5 x 16 | full-code norm, vector norm, full error, lower-bound error, filter error | 100 |
| Combined | 8 x 16 | metadata above | 164 |

The combined code payload is 68.0% smaller than a 512-byte FP32 vector and
35.9% smaller than a 256-byte FP16 vector before IDs, graph links, container
capacity, and model state. The model also needs a 128-float centroid and four
128-bit FHT sign masks. These arithmetic sizes explain why the candidate is
plausible, but they are not a prediction of complete Lite snapshot or RSS.

## Dependency decision

### Behavior and small kernels to reuse

- Preserve the official x+y bit ordering, centering, norm/error metadata, and
  lower-bound equations.
- Reuse or minimally extract the repository's generic plane pack and split
  inner-product kernels; add ISA translation units only after the scalar path
  is correct and measured.
- Preserve the official FHT transform shape and persist its sign masks so a
  loaded index reproduces the build-time model.
- Keep the existing Lite error contract, physical remove/fill-hole behavior,
  external-ID filter semantics, and little-endian bounded snapshot parsing.

### Full components that must stay outside Lite

- `Quantizer`/`Computer` CRTP infrastructure, `Allocator`, Full `Stream`, JSON
  parameter factories, DataCell/Layout/IO classes, HGraph/Pyramid, thread
  pools, PCA/MRQ, fused residual clusters, disk IO, and Full serialization.
- The dense random orthogonal matrix path. The measured configuration uses
  FHT; importing the alternative ROM/BLAS dependency would defeat the
  standalone boundary.
- Full raw-vector or FP32 reorder storage. The reference one-bit mode showed
  that retaining FP32 reorder data misses the Lite storage objective.

The entire `RaBitQuantizer` or `RaBitQSplitDataCell` cannot be linked into the
standalone Lite target: their direct contract brings the Full allocator,
transform, parameter, stream, IO, and datacell closure. Only the required
math and byte layout should cross the boundary, with repository provenance
kept in comments and tests.

## Proposed minimal change

The next implementation should remain opt-in under `lite/benchmark` and should
not change `VectorStorage`, `Index`, or snapshot versions.

1. Add a standalone L2-only 3+5 codec probe with a fixed internal model
   representation: dimension, centroid, four FHT sign-mask rounds, and the
   official filter/supplement records.
2. Train once from a batch, encode the batch, and support query transform,
   filter estimate/lower bound, and full 8-bit reorder distance. The probe must
   use a reproducible model input or persist the generated masks; it must not
   claim byte identity with a separately trained Full model.
3. Differentially test plane packing and scalar distances against direct
   decoded-code formulas, including non-multiple-of-eight dimensions, constant
   vectors, zero norm, non-finite input rejection, truncated model/code data,
   and round-trip persistence.
4. Run the existing prepared SIFT 10k/100k inputs in fresh processes and report
   encoded bytes, model bytes, Recall@10, build/search latency, and RSS. Compare
   with the current Lite FP32/FP16 evidence and with the Full reference, while
   keeping algorithm-level comparisons separate.

Only after that probe meets an agreed quality and latency budget should a
feature design extend the graph backend. That later design must add two-stage
traversal/reorder rather than substituting an eight-bit distance everywhere;
otherwise it would not implement the official split search pipeline.

## Excluded from the next implementation

- No change to PR #2904, the public Lite API, `VectorStorage`, or v1/v2/v3
  snapshots.
- No PCA, MRQ, cosine/IP, disk supplement IO, mmap, fused datacell, concurrent
  search, or Full HGraph linkage.
- No SIMD-first implementation and no performance claim from a scalar probe.
- No reuse of the old dirty graph exploration workspace.

## Validation and promotion gates

The experiment must pass clang-format-15, clang-tidy-15, its focused codec
tests, the existing Release Lite CTest suite, malformed-input tests, and
fresh-process round trips. Formal measurements require seven alternating-order
runs at both prepared scales with exact commit and binary hashes and empty
stderr.

Promotion to a public backend remains blocked until the maintainer/mentor
accepts a Recall@10 floor and latency budget, the Lite-specific snapshot and
steady-RSS results materially improve on FP16, and CRUD behavior with a fixed
trained model is specified and tested. The current Full reference supports
continuing the 3+5 experiment; it does not by itself satisfy those gates.

## Prototype gate status at `a99b0e6`

The standalone probe now covers deterministic batch training, FHT masks, fast 8-bit CAQ encoding, 3+5 plane packing, the official L2 lower-bound calculation, candidate pruning, and supplement-only reranking. Its self-test checks deterministic model/code generation, scalar-versus-split inner-product parity, and filtered-versus-full-code Top-10 equality. It also rejects non-finite vectors and malformed, duplicate, or out-of-range SIFT ground truth.

Seven fresh SIFT-100k processes all produced 0.985 Recall@10 and exact Top-10 agreement between filtered search and an exhaustive full-code scan. The filter read the supplement for a mean 0.2273% of records. These results pass the standalone functional and quality gate for this fixed dataset and seed. The probe now also round-trips its FHT model, split payloads, and metadata through an independent bounded little-endian format, with truncation, magic, metadata, size, and trailing-byte rejection. It does not yet pass the public-backend promotion gate: in-memory records still use per-record allocations, and graph integration, CRUD model lifecycle, SIMD filter kernels, and owned-memory measurement remain open. The next bounded implementation is contiguous in-memory storage, followed by graph traversal integration only if the mentor accepts the measured quality floor.

## Contiguous-storage gate

The in-memory probe now stores all filter planes, supplement planes, and fixed-size metadata in three contiguous owned arrays. It retains no per-record vectors after encoding, verifies fixed record strides, and preserves the `VSLRBQ01` v1 snapshot bytes across load/save. Single fresh-process SIFT-10k/100k checks retained Recall@10 of 0.994/0.985, exact filtered/full agreement, and the previous reorder ratios. The 100k peak RSS was 69,048 KiB, 12.0% below the earlier seven-run median of 78,456 KiB; this is directional rather than a stable performance result because the new value is a single run and source vectors remain resident.

The public-backend promotion gate remains open: graph traversal integration, CRUD behavior for a fixed trained model, SIMD filter kernels, and isolated owned-memory measurement are not yet complete. The next bounded implementation is an experiment-only graph traversal adapter that uses the contiguous records for filter-first exploration and supplement-backed result reorder. It must remain outside `VectorStorage` and public snapshots until its quality and latency are measured and the mentor accepts the promotion boundary.

## Filter-first graph traversal gate

The experiment now reuses the official Lite FP32 graph builder as a reference topology and exports its adjacency into contiguous CSR storage. Search traverses with the 3-bit filter distance and reads the 5-bit supplement only for the final `ef_search=128` candidate set. Snapshot-loaded encoded records produce byte-identical graph results on the same topology.

At SIFT-10k/100k, graph Recall@10 was 0.966/0.940, with mean visited counts of 829.15/1,150.83 and graph-search P50 of 281.383/406.009 us. The corresponding scalar full-scan P50 values were 1,461.610/14,266.271 us. The 100k result is close to the existing public FP32 graph Recall@10 of 0.946, so the traversal experiment passes its bounded quality gate.

This does not yet establish a standalone RaBitQ graph backend. The graph topology is built through temporary FP32 Lite backends, topology persistence is not part of `VSLRBQ01`, CRUD/model lifecycle is unspecified, and the filter kernel is scalar. The next bounded step is to persist and restore the CSR topology with strict validation, then define Add/Update/Remove behavior under one fixed trained model before considering a public `VectorStorage` value.

## High-dimensional GIST gate

The codec now follows the official non-power-of-two `FHTKacRotator` behavior instead of requiring a power-of-two dimension. The 768/960-dimensional self-tests verify norm preservation, deterministic split-code bytes, expected plane sizes, and snapshot round trips. A bounded `lite_prepare_gist` tool converts GIST fbin prefixes and recomputes exact squared-L2 Top-10 for every prefix; it rejects invalid shapes, truncated payloads, and non-finite values.

Using 100 independent queries against 960-dimensional GIST prefixes, exhaustive 8-bit full-code and lower-bound-filtered Recall@10 were both 0.997 at 10k and 100k. For filter-first graph traversal, degree 16 / ef 128 produced Recall@10 of 0.880/0.722. Increasing only ef to 512 produced 0.960/0.872. Degree 32 / ef 512 produced 0.984/0.949, showing that high-dimensional graph connectivity mattered more than deeper traversal alone. At 100k, that last configuration used a 26,400,008-byte CSR topology, 4,939.93 mean visited nodes, 512 supplement reorders per query, 9,139.447 us graph-search P50, 180,568.435 ms graph build time, and 1,408,628 KiB process peak RSS.

This passes the bounded high-dimensional codec and graph-quality experiment gate. It does not justify a public RaBitQ backend yet: topology still comes from a temporary FP32 Lite graph, filter distance is scalar, CSR is not persisted, and fixed-model CRUD semantics remain undefined. Full GIST1M is an optional pressure test, not a current Lite gate; the next implementation priority remains validated topology persistence and CRUD/model lifecycle.

## CSR persistence gate

The experiment now persists the filter-first topology with the trained model and contiguous split records in `VSLRBQ01` version 2. Version 1 remains byte-compatible and code-only. Version 2 stores CSR offsets and neighbors in little-endian order and rejects invalid offset counts, non-zero origins, decreasing or out-of-range ranges, degrees above 64, final edge-count mismatches, out-of-range neighbors, self-loops, duplicates, truncation, and trailing bytes.

Independent SIFT processes saved and loaded 10k/100k snapshots of 2,880,648/28,800,648 bytes. Load time was 6.817/66.843 ms, graph Recall@10 remained 0.966/0.940, and visited/reordered counts were unchanged. The 100k loader peak RSS was 32,176 KiB. Page cache was uncontrolled and each scale was measured once, so these values are functional evidence rather than stable cold-load performance.

This closes the experiment topology-persistence gate without changing public Lite snapshots.

## Fixed-model CRUD gate

The experiment now defines Add, Update, and Remove under one immutable trained RaBitQ model. Add and Update encode with the existing centroid and FHT masks and never retrain them. Neighbor selection uses an exhaustive full-code control path; reverse links use a decoded-code approximation only for bounded degree pruning. This is a correctness-oriented mutation reference, not a claimed ANN build or latency result.

The mutable state keeps external IDs separate from physical slots. Remove follows the official Lite graph backend's last-slot-to-hole compaction and scans every adjacency list because degree pruning can make the graph asymmetric. Update removes all inbound references before replacing the code and relinking. The deterministic self-test performs 180 mixed operations, validates the ID map, bounds, self-loop and duplicate invariants after every operation, and verifies search equality after persistence.

Experiment-only VSLRBQ01 version 3 adds external IDs, graph parameters, and CSR topology to the fixed model and split records. Versions 1 and 2 remain unchanged. Version 3 rejects duplicate IDs, count mismatches, malformed CSR, truncation, and trailing bytes. This does not alter public Lite snapshots or expose a new VectorStorage value.

This closes the bounded CRUD-semantics gate. At this gate, mutation expands CSR into adjacency vectors, pairwise pruning uses decoded codes, and filter execution is still scalar; the later SIMD gate addresses only that final item.

The probe now also has a configurable fixed-count CRUD stability mode. It times Update, Remove, and Add separately, validates the full structure at each batch boundary, separates CSR compaction from graph search, compares graph results with exhaustive full-code search, and verifies exact search equality after every version 3 save/load. RSS is reported both before loading and with original/restored states resident. This measurement path is intended to identify the next bottleneck; it does not turn the scalar mutation reference into a production performance claim.

At cf7a0f08, fixed-count SIFT-10k/100k runs completed 250/60 Update-Remove-Add cycles with exact post-load result equality and no stderr. Median Update/Add P50 increased from 4.118/4.027 ms at 10k to 39.843/39.208 ms at 100k; Remove increased from 0.446 to 4.449 ms. Full-code self Top-1 stayed 1.000, while graph self Top-1 medians were 0.960/0.920. The next implementation reuses the existing filter-first graph traversal for mutation neighbor discovery with the official exploration-depth rule, while retaining exhaustive full-code selection as a candidate-shortage fallback and differential quality oracle. Remove still scans all adjacency lists for asymmetric correctness, but no longer sorts every list after the official erase-and-rewrite operation.

On the same SIFT matrices, the graph-selected path used zero fallbacks. Median Update/Remove/Add P50 improved by 6.67x/4.41x/7.83x at 10k and 13.66x/4.83x/17.78x at 100k. Full-code self Top-1 remained 1.000; graph self Top-1 and graph/full positional medians matched the exhaustive-control medians at both scales. Snapshot size, RSS, and query latency were effectively unchanged. This closes the bounded mutation-neighbor optimization gate for these inputs. Targeted tests additionally cover empty adjacency, low-ef search, empty/one/two-element mutation, last-slot deletion, and non-last-slot compaction without an unexpected fallback.

The experiment now dispatches the official centered 3-bit inner-product kernel through standalone Generic/AVX2/AVX512 translation units. On the same fixed-count matrices, Update/Add/graph-search P50 improved by 1.29x/1.32x/1.57x at 10k and 1.08x/1.10x/1.42x at 100k, with unchanged median quality and zero fallbacks. The probe retains Lite-only linkage. This closes the scalar-filter risk for the measured x86 host, while ARM SIMD, adjacency-vector mutation memory, and a maintainer-approved public backend contract remain open.

## Isolated mutable-state memory gate

The probe now loads a version 3 mutable snapshot in a fresh process and reports
component-level logical/capacity bytes before any dataset or temporary FP32
graph builder is created. Seven-process medians at SIFT-10k/100k were
3,103,312/31,195,840 known owned-capacity bytes and 7,792/43,556 KiB current
RSS. The corresponding snapshot sizes were 2,943,408/29,595,936 bytes and
median load times were 10.257/101.869 ms.

At both scales, adjacency capacity equaled adjacency logical bytes after load.
The 100k state contained 1,599,408 edges and 15,195,264 adjacency-capacity
bytes, including the outer adjacency-vector objects. The known-capacity total
excludes `std::unordered_map` nodes and buckets; the loader separately reported
100,000 entries and 172,933 buckets. These results explain why the earlier
mixed-process `state_rss` was not a measurement of the mutable backend alone
and provide no current evidence that reserved adjacency capacity or
fragmentation warrants a flat-storage rewrite.

This closes the isolated owned-memory measurement gate for the experiment.
The highest-priority remaining decision is a maintainer/mentor-approved public
RaBitQ backend contract: configuration and selection, fixed-model lifecycle,
search/reorder behavior, persistence/versioning, CRUD guarantees, and
compatibility with the existing Lite API. A future inbound-edge index or Remove
optimization should be justified with a workload showing that Remove is the
dominant cost; ARM SIMD and batch-four full-scan work remain optional follow-up
experiments.

## Internal codec extraction: first backend integration step (2026-10-08)

The existing model training, FHT/Kac transform, fast 8-bit encoding, 3+5 packing,
metadata and contiguous code storage now live in `src/lite/rabitq_codec.h`.
The benchmark probe includes that shared internal module rather than defining a
second codec. Header functions are inline so multiple consumers link safely.
SIMD selection, graph maintenance, public configuration and snapshot parsing have
not moved in this step. There is still no public RaBitQ backend.

`python3 lite/benchmark/test_rabitq_codec_module.py` compares the extracted code
with the frozen pre-extraction implementation at `03c2357`. It checks identical
centroids, sign masks, scalar/filter/supplement bytes and all six float metadata
fields for 28 records across dimensions 1/7/8/17/128/768/960, including a two
translation-unit linkage check, replacement, hole compaction and bounds rejection.
Use `--sanitize` for ASan+UBSan. The original codec probe self-test also passes.
These are functional regression checks, not a new performance or coverage claim.

The next implementation must adapt a fixed trained model and mutable graph state
to the Lite backend contract, preserve caller-owned decode scratch semantics,
and define an independently versioned encoded snapshot before exposing selection.
Existing public FP32/FP16 formats must remain compatible. Public RaBitQ distances
are quantized estimates and must not be documented as exact original-vector L2.

中文：本轮仅完成正式接入所需的内部编码模块拆分与复用，编码结果逐字节回归一致；尚未开放RaBitQ配置、正式后端或公共快照。下一步是固定模型与可变图状态的后端适配、调用者解码缓冲区及独立版本持久化，不能将本轮当作正式接入完成或新性能成绩。

## Caller-owned vector reconstruction gate (2026-10-08)

The internal codec now supplies `Model::InverseTransform` and
`decode(model, encoded_view, scratch)`. The inverse reverses the four sign/FHT
rounds, alternating truncated blocks and Kac walk, including odd dimensions and
the final non-power-of-two scaling. Reconstruction reads the 3+5 scalar code,
restores centered scale/centroid, and applies that inverse. Scratch belongs to
the caller; there is no model-owned mutable decoding buffer. Returned pointers
remain valid only while that caller's scratch storage is unchanged/alive.

The value is a quantized reconstruction, not the original FP32 input and not
an assertion that Euclidean distance to that reconstruction equals the RaBitQ
distance estimate. This is the required boundary for a future
`Backend::VectorAt(slot, scratch)` adapter. Encoded persistence must save the
model, code planes and metadata directly, never use decoded values as a lossless
snapshot payload. Rebuilding or converting from this representation would be
lossy and needs an explicit API/documentation decision.

Tests extend the frozen byte-identity regression with transform/inverse round
trips, independent scalar-byte reconstruction checked in transformed space,
separate scratch ownership, malformed sign masks, zero code norm and infinite
norm rejection. Release and ASan+UBSan pass for 28 records across seven dimensions;
the original probe self-test also passes. No public backend, new format, quality
or performance claim is introduced by this internal step. No fresh whole-library
coverage figure is claimed; final library promotion still requires its coverage
gate and lifecycle tests.

中文：内部解码及调用者自有缓冲区已实现并验证，解决未来VectorAt适配需要的逆变换和所有权问题。重建向量是近似值，不能冒充原始输入，也不能据此重新编码保存；正式持久化必须直接保存模型和编码。正式后端、配置和公共快照仍待接入。

## Shared mutable graph gate (2026-10-08)

`src/lite/rabitq_graph_state.h` now owns the fixed-model graph search and mutable
state previously defined in the codec probe. The standalone Generic/AVX2/AVX512
3-bit filter dispatch is also under `src/lite`; the opt-in probe target keeps
its existing per-file ISA flags. Model/code storage, external IDs, directed
adjacency, optional inbound adjacency and mutation repair use the same measured
implementation. The internal state does not import benchmark paths, filesystem
operations or `getrusage`. An optional CPU clock callback preserves benchmark
scan accounting; without a callback CPU scan counters stay zero. The probe's
small wrapper supplies its existing process CPU clock.

CSR expansion now rejects missing/nonzero origins, invalid end boundaries,
decreasing and out-of-range offsets before iterator arithmetic. This is a safe
internal construction boundary, not a new public snapshot version.

`python3 lite/benchmark/test_rabitq_graph_module.py` compares the extracted
state with frozen `ec990a2` definitions using 360 paired Update/Remove/Add
operations, directed topology and nonsequential/negative external IDs. It checks
IDs, code planes, all metadata, ordered edges, visited/reordered counts and
ordered query distances after every cycle, with inbound adjacency both enabled
and disabled. It also covers duplicate insertion, empty/singleton states,
last-slot deletion and malformed CSR offsets. Add `--sanitize` for ASan+UBSan.
The probe's existing persistence/CRUD self-test remains available and passes.
These tests do not establish production latency, new whole-library coverage,
public ABI support or readiness of all error paths.

Remaining integration work is concrete: adapt this state to `Backend`, support
external-ID filtering and per-call search budgets, avoid compacting the complete
adjacency into CSR for every production search, translate failures at API
boundaries, and persist model/code/state through an encoded format. Configuration
must not expose RaBitQ until these lifecycle paths work together. Existing
FP32/FP16 defaults and snapshot versions remain unchanged.

中文：本轮将已有固定模型图检索和可变CRUD状态提取为Lite内部模块，SIMD距离分派同步迁到src/lite，探针复用同一实现；计时回调避免正式模块依赖实验计时器。360次新旧逐操作对照及损坏CSR边界回归用于证明拆分没有改变已测行为。尚未开放正式RaBitQ后端；下一步是Backend适配、过滤/查询预算、去除每次查询全图CSR重建及编码持久化。

## Internal query contract gate (2026-10-08)

Mutable-state search and mutation neighbor discovery now traverse adjacency
vectors directly through the same range-based search implementation as CSR.
`GetGraph()` still compacts explicitly for persistence/inspection, but ordinary
search no longer allocates and copies the complete edge payload first. This is
an implementation-level removal of whole-topology work; no percentage latency
or CPU improvement is claimed without a new matched measurement.

`MutableGraphState::SearchWithOptions(query, k, budget, filter)` supplies the
future backend adapter's per-call contract. Zero budget uses the stored default;
positive budget is clamped to `[min(k, Size()), Size()]`. It does not mutate
construction or persisted settings. A filter receives external IDs and true
means allowed. Rejected nodes remain traversable. Filtered search ranks visited
allowed nodes with the full 8-bit estimate and may return fewer than k results.
This can differ from unfiltered search, which reranks the coarse ef shortlist;
an allow-all callback is not promised bit-identical results for every graph.
The new contract breaks full-distance ties by external ID. Legacy `Search`
retains its measured slot-tie behavior for existing experiment comparisons.

Regression checks retain exact IDs/codes/topology/query results across 360
paired mutations with the pre-extraction implementation. Additional checks cover
reject-all routing, accepted nonsequential/negative external IDs, callback count,
zero k, low/high budget clamping, unchanged defaults, throwing callbacks and
external-ID ties on identical vectors. Release and ASan+UBSan pass; the probe's
existing self-test also passes. Callback exceptions propagate at this internal
boundary; the future public Index adapter must translate them into its existing
`tl::expected` error contract. This is not public RaBitQ API availability or a
new whole-library coverage/quality/performance result.

中文：内部查询已支持外部ID过滤及单次预算，并去掉检索和维护选邻前全图CSR复制。拒绝节点仍可遍历，结果用8bit估计排序，距离相同按外部ID排序；单次预算不改持久化配置。原实验Search保留旧槽位平局语义以便回归；allow-all过滤与未过滤近似路径不承诺始终完全相同。下一步正式Backend适配、异常翻译和编码Save/Load，公共后端仍未开放。

## Public API opt-in functional candidate (2026-10-08)

The first public-API candidate now implements `VectorStorage::RABITQ8` through
`Index::BuildGraph` when `ENABLE_RABITQ_LITE_BACKEND=ON`. The fixed-model backend
supports Add/Update/Remove, external-ID filtered Search, per-query budgets and
owned encoded Save/Load. It uses the independent `VSAGLQ01` v1 format; disabled
builds reject selection and the new format. Existing v1/v2/v3 Lite formats retain
normal handling. This supersedes earlier statements that no public selection is
available, but does not supersede the outstanding performance promotion gates.

Initial mutations copy the complete state before changing it. This is an
explicit correctness-first tradeoff, not a scalable final CRUD implementation.
Three-distribution final quality/performance, mutation transaction cost and
steady-memory measurements still need to be run on this integrated candidate.
See canonical [English](../../docs/docs/en/src/development/lite_first.md#opt-in-8-bit-rabitq-candidate)
and [Chinese](../../docs/docs/zh/src/development/lite_first.md#可选8bit-rabitq候选后端)
documentation and [integration evidence](results/rabitq-backend-integration-20261008/README.md).

## Invalid-ID and identical-encoding fast paths (2026-10-08)

Public RaBitQ Add rejects duplicate IDs before cloning a transaction; Update and
Remove reject absent IDs before cloning. Update compares both 3+5 planes and all
six metadata fields using exact stored bytes. Identical encodings retain the
entire snapshot unchanged and do not request topology repair. Encoding still
allocates scratch and may fail. Genuine changes still copy the state; the
precheck currently adds an encoding pass for changed updates, so changed-update
cost requires measurement and a prepared-code reuse step before broad speed
claims. Legacy experimental MutableGraphState::Update semantics are unchanged.

See [bounded fast-path evidence](results/rabitq-fast-prechecks-20261008/README.md).
The same-value synthetic measurement is not SIFT/GIST/Cohere acceptance and not
a claim that full transaction copying has been removed from changed CRUD.

中文：重复ID/缺失ID前置检查及完整编码同值早退已接入；同值更新不改图或快照，两组位平面相同但元数据不同仍算真实变更。真实改值继续全状态复制，当前多一次预编码，后续需复用准备好的编码并优化真实变更事务。不要将同值合成试验速度推广为整个CRUD优化。

## Prepared encoding reuse (2026-10-08)

`prepare_encoding` retains normalized query scratch and the complete encoded
record. The adapter uses that record for no-op checks and moves the same bundle
into the cloned state's `UpdatePrepared` for real changes. Model transforms,
normalization and the 8-bit encoding pass are not repeated for the input.
Internal preparation must use the unchanged fixed model; shape, finite query
and metadata validation precede topology changes. Public signatures and encoded
format are unchanged. Full state-copy transaction costs remain.

Historical codec byte tests and 360 paired graph mutations still pass. Dedicated
fixtures compare ordinary and prepared Update snapshots across five dimensions,
and reject malformed preparation before changing state. External allocation
injection checks 86 current failure points; the lower count follows removal of
redundant allocations, not omission of cases. See [bounded changed-update evidence](results/rabitq-prepared-update-20261008/README.md).

中文：真实更新复用前置检查已生成的归一化查询和完整编码，避免重复变换/编码；格式和公共签名不改，事务全状态复制成本仍未消除。准备结果必须来自固定模型，尺寸/有限查询/元数据在改图前验证；当前86个分配失败点原状态保持。

## Journaled public Update (2026-10-09)

The default public mutable state now updates through a touched-row journal. It
backs up only the replaced code and adjacency rows before first writes. On any
exception, code bytes/metadata are restored and rows are swapped back without
allocation; fallback counters and scan timings are restored too. Model/IDs/slot
map/container sizes are never changed by this operation. Journaling covers
inbound erasure, new outgoing rows, reverse-link pruning and repair. Add/Remove
retain full-state transaction copies; the experimental incoming-index mode uses
a full-copy Update fallback. Full adjacency scanning and high-indegree costs
remain. Public API and encoded format are unchanged.

See [journaled Update evidence](results/rabitq-update-journal-20261009/README.md)
for 200 continuous copied/journaled state comparisons, 180 complex-graph failure
points, and a bounded same-state synthetic CPU comparison. This is not final
SIFT/GIST/Cohere acceptance or a promise of allocator/CPU improvements in every
workload.

中文：默认公开Update已改为旧编码与受影响邻接行的回滚日志，异常时无分配恢复，ID/模型/容器尺寸不变。新增/删除和实验incoming模式仍全复制；Update仍扫描全部入边，高入度成本未解决。通过200次逐状态对照和180复杂失败点；后续优先新增/删除事务及三数据分布验证。

## Journaled public Add (2026-10-09)

Public Add no longer clones the complete state on every call. It prepares code
and neighbors, pre-reserves geometric growth, inserts the ID, then appends records
and journals old rows before linking. Failure restores old rows, truncates each
record/ID/adjacency length and erases the new ID without allocating. Reserved
capacity and hash buckets may remain larger after failure. Normal container
expansion still moves buffers; only unconditional whole-state transaction copying
is removed. Experimental incoming adjacency uses the copy fallback; Remove is
unchanged. See [bounded Add evidence](results/rabitq-add-journal-20261009/README.md).

中文：公开新增已移除每次整状态复制，失败可恢复原逻辑内容与快照，但容器扩容和失败后保留容量仍存在。通过连续增长逐字节对照及复杂分配失败测试；删除仍全复制，incoming实验模式仍回退复制。标准三分布验收尚未完成。
