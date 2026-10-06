# Common load-only Full/Lite memory probe (2026-10-06)

## Source and lifecycle

New Linux C++17 benchmark load_memory.cpp uses existing Lite Index::Load or Full
Factory::CreateIndex/Deserialize APIs. The same /proc/self/status VmRSS,
getrusage process peak and malloc_trim(0) measurement code is compiled for both.
Public index code, storage policy and snapshot formats are unchanged. Source parent
101e3f6 and working helper/binary hashes are in protocol.json; Full shared library
is the known-source d18c82a rebuild. Full and Lite remain different index designs.

Fresh processes, taskset CPU0, seven runs per configuration; cyclic order rotates
Full/default/diverse. Snapshot files are read once beforehand (warm attempt, no
cache eviction controls). No source base vectors, queries, searches, construction,
save or result arrays are retained. Record before-create RSS, after-empty-create
RSS, load time, then close the input stream and malloc_trim while keeping the index
alive before recording loaded RSS and process peak. Lite static Load creates the
index inside timed Load; Full empty Factory creation is outside the timer.
Full public API checks loaded count, with caller-supplied dimension; Lite also
checks restored dimension. This probe does not independently check Full restored
dimension or rerun retrieval quality. Existing snapshot validation supplies quality.

## Results

Medians across seven runs; raw samples and min/max are in audit.json and CSV files.
RSS and peak are whole-process values in KiB, not allocation counters or index-only
memory. MiB = KiB/1024. Peak here covers only startup and load, not build.

| Mode | Load ms | Loaded RSS KiB | Loaded RSS MiB | Peak KiB | Snapshot bytes |
|---|---:|---:|---:|---:|---:|
| full | 185.732 | 445324 | 434.89 | 576284 | 313616358 |
| default | 138.812 | 341220 | 333.22 | 341876 | 321600064 |
| diverse | 130.028 | 331896 | 324.12 | 332628 | 317024600 |

Lite default: loaded RSS -23.38%, load-stage peak -40.68%, load wall time -25.26% relative to this Full configuration.

Lite diverse: loaded RSS -25.47%, load-stage peak -42.28%, load wall time -29.99% relative to this Full configuration.

## Interpretation and verification

These numbers establish lower whole-process load-only memory for these specific
snapshots/libraries, and faster warm file loads. They do not prove strict cold
start, index-only memory, deployment footprint, other workloads or all architectures.
Snapshot recall differs: Full .952, default .958, diverse .961333, all common .95
floor; quality provenance is in full-cohere/cohere-matched reports, not measured
again by this loader. Full has compressed graph storage and raw-vector retention;
Lite snapshot formats differ. This is not an exact equal-quality/equal-feature
comparison or justification for replacing Full based on memory alone. Full remains
faster on previous retrieval measurements. Historical build-inclusive Full peak
958556 KiB must not be compared to this load-only Lite peak.

New CLI fixtures cover both adapters on 8x16 one-hot snapshots, invalid numeric
arguments, size mismatch, missing and corrupt files. Release and Lite ASan/UBSan
fixtures, clang-format15, clang-tidy15 in both adapters and existing default/diverse
CTest pass; no new library coverage claim. Full ASan was not run. Fixture snapshots
are produced with existing graph_crud_quality/full_rabitq_dataset tools, k1 truth;
test_load_memory.py accepts Full binary, Lite binary and fixture directory.

Published logs remove trailing whitespace; raw-log SHA and host originals preserve
byte provenance. Binary and snapshot hashes are in protocol.json. The new Full
Makefile target initially required explicit reconfiguration, after which it built.
Large fixture/real snapshots and binaries are not committed. Next: actual Full mixed
CRUD under the same restored-data protocol and a unified three-dataset report.
