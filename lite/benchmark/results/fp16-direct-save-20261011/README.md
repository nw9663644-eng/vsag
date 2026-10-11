# FP16 Save: persist owned binary16 rows directly, 2026-10-11

## Change and source evidence

Old `Index::Save` called `GraphBackend::VectorAt`, decoding every stored binary16 element to FP32, then called `encode_fp16` on every element to emit the same v3 bytes. The graph already owns contiguous `fp16_vectors_`. New internal `Backend::FP16VectorAt` returns a borrowed immutable row when available; GraphBackend supplies its existing storage. Save writes that row directly on little-endian hosts and explicitly packs little-endian bytes on big-endian hosts. The old conversion path remains as a fallback for an internal FP16 backend without direct storage access.

This follows native `src/storage/stream_writer.h::WriteVector`'s existing contiguous payload-write approach; no Full format or allocator is imported. No public API/ABI, graph edge selection, quantization, query budget, snapshot version/layout, Load validation, mutation transaction or stream-error handling changes. Storage validity continues to be checked at ingestion/restore; persistence does not introduce unchecked externally supplied raw codes.

Control source17de273ae57052c34e4f00ecc9c6cbb41c95c81e, archived shared-library SHA d288c3ee31a7fe8fd6ac6d23faa63f8c11e3694a6f6aec5b16dab3449fb9f232. identity.json pins measured dirty candidate diff and shared-library hash before commit. Raw control/candidate libraries are retained on server, not committed. All production changes precede measurement and testing; no source changes after timing.

## Byte-preserving performance results

Same host/CPU0/thread1, FP16, degree16/build128/query512/k10. These are current versus prior Lite, NOT Full. No build/test/lint overlaps timing. Values are medians, not best runs.

| Dataset | 10k build-then-Save control/new ms, 3 alternating pairs | 100k loaded-state Save control/new ms, 7 alternating fresh-process pairs |
| --- | ---: | ---: |
| SIFT128 | 12.535699 / 3.503860 | 118.349484 / 31.799275 |
| GIST960 | 41.549504 / 11.573433 | 396.836042 / 105.334399 |
| Cohere768 normalized | 36.719409 / 10.434342 | 355.773980 / 96.169235 |

Observed reductions are approximately72% for10k build-then-Save and73% for100k loaded-state Save. The protocols must not be mixed:10k uses600 observed queries and full builders,100k prepares one initial snapshot using100 historical queries then times open+Save+close in fresh processes after Load (Load excluded). No post-CRUD, query speedup, strict cold-I/O or durable-sync claim. Existing native builders independently validate ordered Save/Load search results.

All9 paired10k snapshot SHA and ordered600-query neighbor files are exact. All42 new100k Save output SHA equal the input snapshot SHA; sizes unchanged. The runner deletes only its own new SHA-verified temporary output and its newly created temporary directories; original source/data/results/libraries are untouched. Raw per-query quantiles and loader records remain archived. No cross-format/nativeFull snapshot equality is required.

The previous native Full report had FP16 Save times2.831/8.480/6.893ms at10k SIFT/GIST/Cohere. This new Lite-only study narrows the observed gap but does NOT establish a current paired Full speedup, because Full was not rerun in this experiment. Latest native Full/SIMD/quality-aligned100k comparison remains outstanding.

## Correctness, tests and coverage boundaries

New unit fixture enumerates all63488 finite binary16 encodings, including signed zero/subnormals/max finite values, proves legacy encode(decode(bits)) equals each original code, verifies exact little-endian vector bytes and Save/Load/Save snapshot equality. Existing corrupt/truncated/non-finite snapshots, short/throwing streams, CRUD and allocation-failure tests remain active.

Release6/6, ASan+UBSan8/8 (leaks/halt enabled), coverage-build6/6 and RaBitQ-off/default4/4 pass. Format15 and source-only tidy15 for index.cpp/graph_backend.cpp pass without user-code diagnostics; dependency/header warnings are suppressed, not a whole-repo/full-header lint claim. Tested on x86_64 little endian; actual big-endian execution was not available.

Current gcov library-object views: index.cpp233/281=82.92%, graph_backend.cpp693/721=96.12%, combined926/1002=92.42%. These are the two changed production CPP files, NOT whole-library coverage; counters were not globally reset and header/TU union is not claimed. The per-file index number is below90%; the project's threshold is library aggregate, but a fresh complete aggregate audit remains to be collected for final delivery. Test-suite passage must not be mislabeled as coverage percentage.

Independent verifier recomputes10k raw P50/P99, checks18 builders/9 paired snapshot and ordered-neighbor equalities/18 loaders, and recomputes42 fresh Save medians/SHA/bytes/49 runner command exits. It does not reread snapshots after temporary cleanup. Source diff/input hashes/snapshot SHA/command logs/library identities make replay possible using run.py and the existing paired/save tools. They assume the recorded server paths; adapt paths and rebuild the pinned control for another machine.

Only personal experiment branch is pushed; PR2904/2926 are unchanged. Next focus remains query routing/graph quality and final nativeFull comparison; GIST100k RaBitQ recall, interleaved changed-value CRUD, larger tails and package closure are not resolved by this persistence optimization.
