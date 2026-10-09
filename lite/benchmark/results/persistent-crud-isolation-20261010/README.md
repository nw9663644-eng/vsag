# Persistent mutation-path isolation

Production library unchanged at c6d6c0b; hash e9613ace... and head/source/builder identity are frozen.
Opt-in VSAG_GRAPH_CRUD_MODE=update or replace requires persistent replacements. update calls only Update;
replace calls Remove then Add of the changed row. all preserves prior protocol. Default CLI/CSV schema unchanged.
When mode is explicitly selected its name is appended to opt-in CSV; per-operation kinds remain0/1/2.
Mode/count/unchanged/nonfinite/missing truth/output protections and SaveLoad exactness tested for all three storages.

Real-data isolation uses FP32/RaBitQ, GIST/Cohere10k, fixed600 observed queries, k10/degree16/construction128/query512.
Three full-ID passes (30000 replacements), same final FP32 replacement recipe/truth as previous experiment.
Cohere replacement normalized as previously documented. One process per case, CPU0/BLAS/OMP1, uncontrolled warm cache.
Only initial/final queries, not interleaved reads; whole-process peaks include original/replacement matrices and staging.
No Full comparison or statistically stable performance benefit claimed; mode CPU costs cover different operation counts.

| Dataset/storage | Initial | Update only | Remove/Add only | Previous combined | Previous fresh-final |
| --- | ---: | ---: | ---: | ---: | ---: |
| gist10k600/fp32 | 0.965500 | 0.927667 | 0.923333 | 0.898167 | 0.949833 |
| gist10k600/rabitq8 | 0.961000 | 0.858667 | 0.849500 | 0.811167 | 0.948500 |
| cohere10k600/fp32 | 0.987333 | 0.970667 | 0.962167 | 0.951167 | 0.965000 |
| cohere10k600/rabitq8 | 0.983500 | 0.935500 | 0.923333 | 0.908167 | 0.961833 |

Previous combined/fresh columns are explicitly inherited, not rerun timings. Same final data and budgets, pinned production has no quality changes.
Both mutation paths lose quality relative to initial; distribution changes mean that difference is not a pure topology effect.
FP32 fresh-final construction is a stronger same-final-data topology reference; Cohere Update-only can exceed fresh construction, so no universal ordering is implied.
RaBitQ fresh-final also retrains the model: graph/model effects not isolated. No sole cause or fix has been established.
RaBitQ both isolated cases remain below historical GIST.90/Cohere.95 study floors, which are not official OSPP thresholds.
Combined loss is lower than either isolated protocol here; this is an observed interaction, not proof of an additive causal decomposition.
Float Update has ensure_incoming protection; RaBitQ does not. This source difference is a testable hypothesis, not yet an accepted fix.
Next isolate frozen-model retrieval ceiling, then test a bounded incoming/connectivity gate without changing degree/query budget.
Do not reintroduce previously rejected unconditional/distance-only old-neighbor reuse.

8 builders, 360000 mutations, 9600 initial/final truth intersections independently audited.
Native SaveLoad ordered ID/float distances checked within each builder; initial results match exactly between isolated modes.
Raw archive contains actual queries/initial+changed truth/operations/neighbors/commands/logs and measured source.
Replacement matrices/final bases are reconstructible from preserved originals, recipe and prepare.py with receipt SHA; not archived matrices.
Only new RAM snapshots were deleted after successful hash/load checks using resolved-path guard; original source/data/raw preserved.
Reproduce preparation with prepare_persistent_crud.py as in preceding experiment, then set mode/env recorded in raw commands.
Run python3 verify.py here to audit all mode-specific operation schedules, truth intersections, quantiles and artifact/member hashes.
Release and ASan/UBSan tool fixtures plus format/tidy15 passed. Library source unchanged: no new CTest/coverage claim.
Project acceptance remains incomplete: stable mutation quality,100k,interleaved reads,cold I/O,fresh/latest Full remain open.
