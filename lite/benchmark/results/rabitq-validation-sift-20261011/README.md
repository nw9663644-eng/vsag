# SIFT100k supplement: reverse-validation scratch, 2026-10-11

This fills the missing SIFT row, without rerunning completed GIST/Cohere pairs.
Exact same libraries as `rabitq-validation-scratch-20261011`: parent109d554
control SHA094bee5176b582bca7b69d3b34ab41b07174c09facf8a03b4275ce28950dc12d,
candidate productiona126a53 SHA0f729af8fd98323988f398d65ac75a9d67431889f2e4f87d05ed227aeba9374a.
Only Python selection/output options and verifier dataset support were extended;
no C++ source/library changed. Candidate diff is retained as candidate.patch.gz.

## Same-protocol three-dataset table

Each dataset:100k,degree16/build128/query512,k10,CPU0,one BLAS/OMP/MKL thread,
five alternating fresh-process pairs each for warm Load and loaded-state Save.
GIST/Cohere rows are inherited from the preceding same-day experiment directory,
not newly rerun alongside SIFT. Save times open+Save+close after Load. RAM input,
not cold disk or durability sync; no build/test overlaps timing.

| Dataset | Warm Load old/new ms | Change | Loaded-state Save old/new ms | Change |
| --- | ---: | ---: | ---: | ---: |
| SIFT128 | 64.789 / 57.914 | -10.61% | 37.750 / 31.654 | -16.15% |
| GIST960 | 104.207 / 93.943 | -9.85% | 71.492 / 62.060 | -13.19% |
| Cohere768 | 95.253 / 87.440 | -8.20% | 62.051 / 53.993 | -12.99% |

SIFT loaded RSS50728→50432KiB, loader peak74508→71376KiB. Index29600672bytes
unchanged. All10 SIFT Save outputs match the input SHA; unlike the preceding
runner, this supplement also records each saved_sha256 in rows.json. All five
SIFT Load pairs and all five Save pairs favor the candidate. This is not a
statistical/general guarantee; RSS contains allocator-retained temporary pages.
The two preparations/measurement protocols should not be confused with saving
immediately after long CRUD or with the previous post-CRUD snapshot state.

## Reproducibility and verification

`python3 lite/benchmark/benchmark_rabitq_validation.py --datasets sift100k --output NEW_DIRECTORY`
refuses existing output. Default datasets remain GIST/Cohere; selecting all three
is supported. Control library path remains the archived pre-rebuild copy on this
host; replay elsewhere must rebuild109d554 in a separate directory and adapt host
paths. Inputs/source/library hashes and22 commands are recorded. Independent
verifier checks20 rows,22 exits, pairing, raw CSV medians, source hashes and saved
SHA values; it also still passes the previous40-row GIST/Cohere archive.

No C++ code changed: Release/SAN/OFF and full-tidy limitation belong to a126a53,
not fresh reruns here. Three new Python preparation unit tests pass; generator
options preserve existing defaults. Large new RAM snapshots are temporary; old
source/data/raw/library files were not removed. This is Lite versus prior Lite,
not native Full, query optimization, long CRUD, or final project completion.

## 中文说明

SIFT已补齐；本轮热加载与已加载状态保存分别下降10.61%和16.15%。上表保留
三数据集，明确GIST/Cohere继承同日上一轮、SIFT为本轮新测。真实改值CRUD另见
兄弟目录`sift-production-100k-crud-20261011`，不能将专项时间拼接成统一生命周期。
