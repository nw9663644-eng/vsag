# Independent VSAG Lite v0.1

> Phase-2 branch note (2026-09-14): the default Index::Create(dim) still uses
> exact BruteForce and its byte-identical v1 snapshot. Call BuildGraph(degree,
> ef_search) explicitly to publish a standalone single-layer approximate graph
> after a successful build. Graph Add/Update/Remove and Search use the same
> Index API; Save writes v2 for FP32 graphs and v3 for FP16 graphs, including
> vectors, IDs, options and adjacency. Load accepts v1, v2 and v3. Graph snapshots
> are not compatible with Full VSAG.
> The filtered Search overload also applies after BuildGraph: rejected external IDs
> can be traversed to keep the graph connected, but are never returned.
> No concurrent calls, checksum, SQ8 or mmap are provided. The
> remainder of this page documents the original v0.1 default behavior.


This experimental entry point starts with exact FP32 squared-L2 BruteForce and
selective source reuse, rather than conditionally compiling the Full library.
It currently targets Linux x86_64, C++17 and the repository compiler baseline.
The default Full build is unchanged. Run these commands from the repository root:

```sh
cmake -S lite -B build-lite-first -DCMAKE_BUILD_TYPE=Release -DENABLE_TESTS=ON
cmake --build build-lite-first -j2
ctest --test-dir build-lite-first --output-on-failure
cmake --install build-lite-first --prefix "$PWD/install-lite-first"
cmake -S lite/example -B build-lite-consumer -DCMAKE_PREFIX_PATH="$PWD/install-lite-first"
cmake --build build-lite-consumer -j2
./build-lite-consumer/lite_example "$PWD/new-example.lite"
```

The installed consumer only includes `vsag/lite/index.h` and links `vsag::lite`;
it does not link `libvsag.so`. It demonstrates Add, Search, Update, Remove,
Save and Load. Use a new snapshot path for each run. Expected output:

```text
added id=42 squared_l2=0
filtered id=7 squared_l2=48
updated id=42 squared_l2=0
removed id=42 remaining=1
loaded id=7 squared_l2=0
graph query id=7 budget=64
```

Unlike the Full `make` targets, `cmake -S lite` is a separate dependency-isolated
entry point. Tests use the existing pinned Catch2 v3.7.1 configuration. For an
offline build, pass `-DFETCHCONTENT_SOURCE_DIR_CATCH2=/path/to/catch2-v3.7.1`.
The existing Catch2 cases are registered with CTest as `lite_unit` and `lite_scale`.
With tests disabled, no Catch2 download is needed.
The build produces both `libvsag-lite.so` and `libvsag-lite.a`. The shared
target remains `vsag::lite`; the static archive is also installed for embedded
or offline consumers that choose to link it explicitly.

## API and ownership

`vsag::lite::Index::Create(dim)` creates a fixed-dimension index. `Add`, `Update`,
`Search`, `Save`, and static `Load` use the existing `tl::expected` / `vsag::Error`
contract without calling Full's global logger. `Remove` returns a boolean.
Inputs must contain the specified number of finite float32 values. Calls must
be externally serialized. Results own their memory; internal slots are not exposed.

- Single-record Add rejects duplicate IDs; Update rejects absent IDs.
- Graph Update returns without changing adjacency or snapshots when validated FP32 bytes
  or encoded FP16 bits match the stored representation. FP16 range checks still run first;
  FP32 positive and negative zero have distinct byte representations. Same-value Update is
  not a graph repair request. BuildGraph only converts BruteForce to Graph; it does not
  rebuild an index that is already a graph.
- Remove returns false for absent IDs or failed graph repair allocation without changing contents. A removed external ID can be inserted again.
- Add failure leaves logical records unchanged, though reserved capacity may grow.
- Search returns up to `min(k, Size())` entries sorted by squared-L2 then ascending ID.
  BruteForce checks the external ID before computing distance. Graph search may score and
  traverse rejected IDs to preserve connectivity, but never returns them. An empty filter
  accepts every ID; filtering can return fewer than k entries. Valid queries with k=0 or
  an empty index return an empty result.
- FP32 accumulation can overflow to positive infinity for extreme finite inputs;
  those distances tie and are ordered by ID. This is not arbitrary-precision L2.
- NaN/Inf inputs and dimension mismatches are rejected even for k=0.
- Memory allocation failures are translated to Error where caught; constructing
  an error itself may still allocate. No hard real-time or no-throw OOM guarantee.

## Data organization and reuse

The private implementation owns contiguous FP32 records, external IDs, and an
ID-to-slot map. BruteForce scans and graph construction/search reuse the official
`ComputeL2SqrImpl` kernels through the same runtime distance dispatcher.
On x86_64 GNU/Clang builds, a small runtime dispatcher selects AVX512, AVX2,
SSE4.1, or Generic according to CPU/OS support; dimensions below 16 retain the
Generic path. Other supported toolchains use Generic. Physical removal uses the
same last-record-to-hole principle as Full
BruteForce, but retains capacity for reuse. It does not promise immediate RSS
reduction. The minimal implementation intentionally avoids Full Factory,
InnerIndexInterface, attribute and multi-vector dependencies.

The initial BruteForce backend is still the default. `BuildGraph` constructs a separate
private graph backend and publishes it only after success; graph CRUD and filtered
search remain available. BruteForce snapshots use v1, FP32 graphs use v2, and explicitly
selected FP16 graphs use v3. SQ8 and mmap are not part of the public Lite index.

## Architecture design and compatibility

The standalone boundary is intentionally narrow:

```text
application
    |
    v
vsag::lite::Index             public ownership and error contract
    |
    v
detail::Backend               private CRUD/Search/storage abstraction
    |-------------------|
    v                   v
BruteForceBackend       GraphBackend
FP32 row-major          FP32 or FP16 row-major + adjacency rows
    |                   |
    +---------+---------+
              v
    runtime L2 dispatcher     Generic/SSE/AVX2/AVX512 as available
              |
              v
    versioned owned snapshot  v1 flat / v2 FP32 graph / v3 FP16 graph
```

`lite/CMakeLists.txt` builds only this source closure into shared and static
`vsag-lite` libraries. Lite reuses the repository's `Error`/`tl::expected`
contract and official L2 implementation traits, but does not link the Full
Factory, HGraph, thread pool, allocator orchestration, logging runtime, IO
framework, attribute system, sparse or multi-vector indexes. This keeps the
installed surface to `vsag/lite/index.h` plus the header-only error contract.

The index choices follow the small-data deployment goal:

- BruteForce is the default because it is exact, has no construction phase,
  and keeps the smallest state for small collections.
- The single-layer graph is explicit because it trades construction time,
  snapshot bytes and approximate recall for faster queries. `BuildGraph`
  creates the complete replacement first and publishes it only on success.
- FP16 is an explicit graph storage choice. It reduces vector and snapshot
  bytes, while inputs and results stay FP32. It may change distances and recall,
  so FP32 remains the graph default.

BruteForce stores vectors in one row-major `std::vector<float>`, IDs in a
parallel vector and the external-ID mapping in an `unordered_map`. Graph adds
one bounded outgoing-adjacency vector per slot; FP16 replaces the vector payload
with row-major binary16 words. Capacity grows geometrically. Remove physically
moves the last record into the hole and updates slot references, while retaining
allocated capacity for reuse; it does not promise an RSS drop. Pruning and old
snapshots may contain asymmetric adjacency, so removal scans stored edges rather
than assuming every incoming edge appears in the removed node's outgoing row.

Graph construction temporarily owns both the flat source and the replacement,
so peak memory can exceed either steady state. Search owns its visited bitmap and
candidate queues per call. FP16 decode scratch belongs to the caller inside the
implementation and is reused across serialization iterations. There is no shared
mutable decode buffer, background compaction or internal synchronization.

The compatibility boundary is behavioral rather than ABI compatibility:

| Concern | Lite behavior | Difference from Full |
| --- | --- | --- |
| Errors | `tl::expected<..., vsag::Error>` where applicable | Reuses the contract without the Full runtime |
| IDs and vectors | int64 external IDs, fixed dimension, FP32 call inputs | Single-vector dense squared-L2 only |
| CRUD | Add, Update, physical Remove and Search | No delete markers, attributes or multi-vector operations |
| Filtering | Callback on external IDs | Separate minimal callback type |
| Results | Owned `std::vector<Neighbor>` | Not the Full `Dataset` result ABI |
| Persistence | Seekable C++ streams and Lite v1/v2/v3 | Not Full serialization compatible |
| Concurrency | Calls must be externally serialized | No internal thread pool or concurrent-call guarantee |

Migrating code must therefore adapt construction, result handling and
persistence even when CRUD names and error handling are familiar. Full API/ABI
replacement is not claimed.

## Snapshot v1

The binary format is separate from Full VSAG. All numeric fields are little endian:

| Offset | Field |
| --- | --- |
| 0 | 8 bytes `VSAGLT01` |
| 8 | uint64 version = 1 |
| 16 | uint64 dimension |
| 24 | uint64 record count |
| 32 | uint64 payload bytes = count * (8 + 4 * dimension) |
| 40 | uint64 representation = 1 (IEEE754 FP32, squared-L2) |
| 48 | count signed int64 IDs encoded as two's-complement bits |
| 48 + 8 * count | contiguous row-major FP32 values |

Load requires a seekable stream and consumes its remaining bytes, rejecting
truncation, trailing bytes, invalid sizes/versions, duplicate IDs and non-finite
values before publishing a new index. It bulk-reads contiguous IDs, vectors and
each graph adjacency row directly into their final owned containers. Version 3 binary16
vectors are also read directly into final FP16 storage and checked for finite exponent
fields without an FP32 staging copy. Non-little-endian hosts convert payload values in
place. Loading does not mutate an existing
index. This is an owned-memory load, not mmap or zero-copy. There is no checksum:
valid-looking bit corruption cannot always be detected.
Save writes at the current output position; the caller owns flushing/closing,
atomic replacement, permissions and crash durability. Partial output may remain
after failure. Write failures currently use existing `READ_ERROR` because the
shared ErrorType has no separate write-error code.

## Verification and limitations

`[lite]` covers CRUD, independent-reference search and malformed snapshots.
The opt-in `[lite-scale]` case runs a 100,000 x 128 synthetic end-to-end workflow;
it is a correctness smoke test, not a realistic retrieval benchmark or a claim
of performance improvement. The separate [benchmark PR #2926](https://github.com/antgroup/vsag/pull/2926)
compares the same exact FP32 BruteForce workload at 10k and 100k x 128,
using seven alternating Full/Lite runs on one machine. The figures below
come from its generated-data comparison at commit `d729426`; shared-library
sizes are measured after `strip`, and RSS is the median process-lifetime
peak reported by `getrusage(RUSAGE_SELF)`.

| Measure | Full | Lite |
| --- | ---: | ---: |
| Stripped shared library (bytes) | 40,463,344 | 39,488 |
| 10k process peak RSS (KiB) | 164,416 | 12,112 |
| 100k process peak RSS (KiB) | 214,200 | 72,912 |
| 100k Search P50 (us) | 2,401 | 4,392 |

The RSS figures include the benchmark's data buffers, CRUD, queries and
temporary allocations; they are not index-object memory. At 100k, Lite's
search, Save and warm Load are slower than Full. See #2926 for the complete
configuration, raw-result workflow and limitations. Strict cold load and
graph-index comparisons remain work.

A follow-up seven-run alternating comparison on the same AMD EPYC host measures
the scalar Lite build against the runtime-dispatched SIMD build. Search results
kept identical IDs and order for all 640 inspected Top-10 rows; the largest
absolute distance difference was `9.54e-6`.

| Dataset | Scalar Search P50 (us) | SIMD Search P50 (us) | Scalar peak RSS (KiB) | SIMD peak RSS (KiB) |
| --- | ---: | ---: | ---: | ---: |
| 10k x 128 | 436.0 | 100.1 | 12,108 | 12,120 |
| 100k x 128 | 4,344.0 | 3,331.8 | 72,908 | 72,924 |

The stripped Lite shared library changed from 39,488 to 47,704 bytes. These are
single-machine medians for this exact workload, not general performance claims.

For source coverage add `-DENABLE_COVERAGE=ON` to a Debug build, run the tests,
and collect gcov results. Only report actually measured coverage; Full coverage
is not implied. The installed consumer above checks that the new target can be
used without linking `libvsag.so`. Full API/ABI replacement, bindings, sparse vectors,
WARP, SQ8, mmap and concurrent calls are out of scope.

## FP16 graph storage

Call `BuildGraph(VectorStorage::FP16, max_degree, ef_search)` to store graph vectors as IEEE binary16 while keeping the existing FP32 input and search API. The original `BuildGraph(max_degree, ef_search)` remains FP32. `ActiveVectorStorage()` reports the active representation. FP16 graphs use snapshot version 3; versions 1 and 2 remain readable and unchanged. Loading does not require the save host ISA because the stored representation is portable little-endian binary16. Version 3 values are bulk-read directly into final FP16 storage, validated by their binary16 exponent fields, and byte-swapped in place when required. Values outside the finite FP16 range are rejected when the graph is built or updated.


## Per-query graph budget

`SearchWithOptions(query, dim, k, SearchOptions{ef_search}, filter)` supplies a
budget for one graph query. Zero uses the configured default; positive values
are clamped to the live count and raised to the requested result count when
necessary. BruteForce ignores this option and remains exact. The optional
filter has the same external-ID semantics as Search. Existing Search calls,
including empty filters, are unchanged.

```cpp
vsag::lite::SearchOptions options{512};
auto result = index->SearchWithOptions(query, dim, 10, options);
```

The override does not change BuildGraph/Add/Update/Remove budgets or Save output.
Snapshots retain their configured default. The consumer example builds with
budget8 then queries with budget64. Calls still require external serialization;
this feature does not add a concurrent-call guarantee. Bigger query budgets
spend more work and may improve recall, but do not guarantee a quality target.

## Opt-in 8-bit RaBitQ candidate

Build the standalone target with `-DENABLE_RABITQ_LITE_BACKEND=ON` to enable
`BuildGraph(VectorStorage::RABITQ8, degree, ef_search)`. The option is OFF by
default. Disabled builds return `UNSUPPORTED_INDEX_OPERATION` for this selection;
the original flat index remains intact. This candidate requires a nonempty flat
training set, dimension at most 1,048,576, at most 1,000,000 live records, degree
2–64 and ef at least degree. The deterministic training seed is currently 47.

Inputs remain finite FP32 L2 vectors. The backend owns a fixed trained centroid,
four FHT/Kac sign-mask rounds and 3+5 split code planes. Add/Update use the fixed
model without retraining. Search traverses 3-bit filter estimates and ranks
candidates with 8-bit estimates. These are approximate distances, not exact
original-vector squared L2. Filtering accepts external IDs when the callback
returns true; rejected nodes remain traversable. Per-call budgets do not change
stored defaults. Filtered and unfiltered approximate paths need not return
identical rows even with an allow-all callback.

Save writes independent little-endian `VSAGLQ01` version 1 model/code/ID/graph
payloads, never decoded-and-reencoded vectors. Load preserves query results and
remains mutable, including after removing all records. Only enabled builds load
this candidate format. Existing `VSAGLT01` v1/v2/v3 retain their original paths;
experimental `VSLRBQ01` snapshots are not accepted as this candidate format.
Streams must be seekable. Header sizes are checked against remaining bytes before
large allocations. No checksum, atomic file replacement or concurrent calls are
provided. Extreme finite values that overflow model/transform arithmetic fail
without replacing the existing index.

Duplicate Add and absent Update/Remove IDs are checked before transaction copying.
Update encodes the requested vector and compares both planes plus all six metadata
fields against the stored record. Identical complete encodings return without
changing topology or snapshot bytes; plane identity alone is not sufficient.
This still performs encoding and can fail on allocation or internal arithmetic.
For a real change, the prepared normalized query and full code are moved into
the transaction; the mutation path does not normalize or encode that input again.

**Default public CRUD uses local rollback transactions.** Remove backs up the
hole/last code and ID, retains the removed map node, and journals affected rows.
On failure it restores lengths within retained capacity and reinserts the node
without exceeding the map's old load; no rollback allocation is required.
Public Add prepares codes
and neighbors, reserves geometric container growth, then journals touched rows.
Failure erases the inserted ID, truncates appended lengths and restores old rows;
capacity/bucket growth can remain, but logical contents are preserved. Normal
buffer expansion can still copy existing data. Public Update instead
journals the replaced code and each adjacency row before its first write. Failure
restores codes and swaps saved rows without allocating; IDs/model/container sizes
are unchanged by Update. It still scans directed adjacency for inbound references
and can journal many rows in a high-indegree case. The experimental inbound-index
state uses the full-copy Add/Update/Remove fallback. This reduces mutation copying but does not make
all CRUD constant-time or remove temporary mutation memory. This is a correctness candidate, not a validated
performance improvement. Remove's bool result cannot distinguish a missing ID
from allocation failure; either failure retains the state. Error construction
itself can allocate, as with the existing Lite error contract. Build retains
temporary FP32 vectors and a temporary FP32 graph; peak build RSS is not steady
quantized RSS. Three-distribution quality/performance and long-CRUD acceptance
remain pending. Do not infer those results from older standalone probe numbers.

Use the opt-in `lite_rabitq_example` build target for the public API lifecycle.

The integrated 10k SIFT/GIST/Cohere pilot is recorded in `lite/benchmark/results/integrated-storage-pilot-20261009`. It establishes a snapshot-size reduction at the measured settings, but queries and whole-process peak memory are worse than FP32. Historical queries and short churn do not replace100k, fresh-process isolated RSS or long changed-vector acceptance. Read the experiment report for raw evidence and measured-version boundaries.

A fresh-process10k loaded-only study is recorded at `lite/benchmark/results/integrated-load-final-20261009`: RaBitQ loaded RSS is about41–66% below FP32 on these three distributions, with no original base matrix resident. Load/first-query regressions remain; these are warm-uncontrolled RAM measurements, not cold I/O or100k/long-CRUD acceptance. The report separates current-image VmHWM from the launcher-affected getrusage high-water metric.

The integrated100k pilot records lower loaded RaBitQ RSS but quality failures at stored degree16/ef128. A separate observed-query grid meets the study floors at SIFT ef512 and GIST/Cohere ef2048 for RaBitQ, with slower queries than floating modes. See `lite/benchmark/results/integrated-100k-pilot-20261009` and `integrated-100k-budget-grid-20261009`. This selection is not blind final acceptance, exact equal-recall timing or a new default; long changed-vector CRUD and Full comparisons remain pending.


[RaBitQ architecture, snapshot layout and remaining acceptance](lite_rabitq_design.md).

## Mutation failure and RaBitQ distance computation

Published FP32 and FP16 graphs use a local mutation journal. Allocation failure
in Add or Update preserves logical records and adjacency; Remove returns false
and preserves contents if its graph repair cannot allocate. Reserved capacity
may grow. Only affected rows and the overwritten records are backed up, rather
than copying the entire graph. Private BuildGraph construction is discarded on
failure and enables journaling before publishing the completed graph.

RaBitQ computes the query sum once per search or maintenance query. Its 5-bit
supplement calls Full's shared scalar and SIMD kernels with runtime
AVX2/AVX512 selection and a scalar fallback. SIMD uses the native fused multiply-add
and vector reduction, so distance rounding can differ from the former scalar
dimension-order accumulation. Tests cover independent scalar estimates, unaligned
inputs, plane tails, query quality and mutation rollback. Encoding, persistence
and search budgets are unchanged. A speed improvement over the previous Lite implementation does not
establish parity with Full VSAG or with FP32/FP16.

## Expanded native-reference acceptance and ELF scope

The current Lite/native HGraph 600-query-per-dataset study is recorded in `lite/benchmark/results/acceptance-full-expanded-r1-20261009`. It uses a pinned installed Full reference, not old Lite, with explicit source/header/binary provenance. Query budgets differ (Lite512/Full128); this is not an exact matched-recall or same-budget comparison. The study records warm-load/total-RSS advantages but slower queries, larger snapshots and higher construction peaks. These observed queries are regression data, not blind holdout or long changed-vector CRUD acceptance.

`python3 lite/benchmark/measure_elf_closure.py --lite LITE_SO --full FULL_SO --output NEW_OUTPUT --scratch /dev/shm` measures trusted shared-library ELF DT_NEEDED closures. It resolves recursive dependencies, counts each realpath once (including common system runtime), and applies identical `strip --strip-unneeded` only to scratch copies; originals are not changed. This scope excludes executables, headers, Python bindings, containers and dynamically loaded plugins. The recorded reduction is not a complete wheel/container/SDK size claim. Run `python3 lite/benchmark/test_measure_elf_closure.py` for dependency/deduplication/copy-only fixtures.

Query-local graph heaps preserve the existing admission and traversal order.
After unfiltered FP32/FP16 traversal ends, Lite takes the owned retained buffer,
selects the best k candidates, and sorts only that prefix by distance then
external ID. RaBitQ scores the same retained candidates directly instead of
popping the entire coarse heap; its scoring formula and final ID tie-break are
unchanged. Filtered search keeps its existing path. This follows the native
DistanceHeap retained-buffer access pattern, without changing ef, topology,
the public API, or snapshots. The paired regression evidence is in
`lite/benchmark/results/query-selection-expanded-20261009`; its control is
old Lite, not Full VSAG.
