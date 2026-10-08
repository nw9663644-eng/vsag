# Opt-in RaBitQ backend integration: functional evidence

2026-10-08, parent source `63745c5d8d285908fb7c4c59f4a6dc859ae80549`
plus the source hashes recorded in `verification.json`. This is a public-API
functional candidate, not a new benchmark or completed performance acceptance.

## Source evidence and minimal change

The adapter follows `include/vsag/lite/index.h`, `src/lite/backend.h`, the
existing Graph expected-error contract and standalone build. The measured
RaBitQ model/code/search/mutable state is reused from the extracted internal
modules; official split layout and FHT provenance remain in the feasibility
report. Public `BuildGraph(RABITQ8)` is opt-in, trains once from nonempty flat
data, and uses a fixed model afterward. Encoded persistence is independent
`VSAGLQ01` v1; it never reencodes reconstructed vectors. Existing Lite formats
remain separate. Full allocator/IO/quantizer/graph dependencies are not linked.

| Validation | Actual result | Scope |
|---|---|---|
| Release CTest | 5/5 pass | Lite API, flat/scale/graph and quantization tests |
| ASan+UBSan CTest | 7/7 pass | Above plus existing RaBitQ probes |
| New public API cases | 2118 assertions / 6 cases | Lifecycle, corruption, errors, reconstruction, inbound adjacency |
| Fresh gcov line coverage | 2149/2284 = 94.09% | Lite src/include; test bodies and vendor code excluded |
| Dynamic/static external consumers | 87 injected allocation failures each, exact unchanged snapshots | Add/Update/Remove transaction failures |
| Sanitized external consumer | Same 87 failure points pass | ASan+UBSan linked library |
| Backend disabled | Selection rejected; flat records retained | Default-off fresh Release build |
| Original codec regression | 28 exact records / 7 dimensions pass | Model/code/metadata and decoding ownership |
| Original graph regression | 360 paired mutations pass | Legacy behavior, filters, budgets, IDs and ties |
| Public example | Loaded external ID9, estimated L2=0 | CRUD, filtering, Save/Load via Index |
| Format/tidy | clang-format-15 / clang-tidy-15 pass after repairs | Edited C++ TUs; dependency warnings remain |

Coverage merges gcov executable lines across library objects and the unit
consumer's instrumented internal-header fixtures. It is Lite-scope coverage,
not a claim that the entire Full repository was newly measured. The local build
coverage JSON and test logs are copied here. Public consumers use only the
installed-style public include boundary and standalone library.

## Reproduction

```bash
cmake -S lite -B BUILD -DCMAKE_BUILD_TYPE=Release -DENABLE_TESTS=ON -DENABLE_RABITQ_LITE_BACKEND=ON -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
cmake --build BUILD -j2
ctest --test-dir BUILD --output-on-failure
BUILD/lite_rabitq_example
python3 lite/benchmark/test_rabitq_candidate.py BUILD
python3 lite/benchmark/test_rabitq_candidate.py BUILD --static
```

Use the pinned local Catch2 override on offline hosts. Add sanitizers at configure
time and `--sanitize` for the consumer. Configure a separate OFF build and run
the consumer with `--disabled` to verify the default-off boundary. Re-run unit
cases with coverage instrumentation; coverage is not inherited across changes.

## Limitations and failures retained

Initial mutations make an O(index state) transaction copy to preserve the old
state on failure. This costs temporary memory and CPU, and must be optimized
before claiming performance acceptance. Training also builds a temporary FP32
graph. Inputs are FP32 L2; returned RaBitQ distances are estimates, not exact
original distances. No concurrent guarantee or checksum is added. The candidate
has dimension/count caps and independent versioned format documented in the
canonical bilingual pages. Large-scale quality, high-dimensional memory and
long-CRUD performance were not rerun here; older probe numbers are not integrated
backend results. Existing PR source branches were not changed.

Initial coverage was 87.5%, then meaningful internal reconstruction/inbound tests
raised it past 90%. A new fixture initially compared a pointer and a resized
buffer in one expression with unspecified evaluation order; it was corrected
into sequenced statements. First sanitizer CTest included a stale, unrebuilt
probe and failed; rebuilding it made all seven pass. First tidy invocation lacked
a compilation database; after generating it, four test-style diagnostics were
fixed and checks rerun. Those failed invocations are not counted as passed.

中文：本轮是正式Lite接口可选功能接入，不是最终性能验收。初版增删改完整复制状态，已通过87个分配失败点的原状态保持检查，但成本尚待优化；旧独立探针性能不可冒充接入版数据。默认关闭、旧格式兼容、模型与编码直接持久化；三个数据分布最终复测及长期CRUD仍待完成。
