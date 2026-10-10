# Rejected blocked transformed-code decode (2026-10-10)

Measured parent675aed761cd9e8687d2fb12fbe9e7a036be3e12d, personal experiment/lite-rabitq-next-20260926.
The production candidate is REJECTED and both header/test restored byte-exact to parent.
No production optimization win,quality repair,Full comparison or project completion.

## Source evidence and candidate

Native src/quantization/rabitq_quantization/rabitq_quantizer.cpp::RecoverOrderSQ
restores bit planes with shift/mask; DecodeFusedSplitCode establishes the high/low plane convention.
Official source URL: https://github.com/antgroup/vsag/blob/main/src/quantization/rabitq_quantization/rabitq_quantizer.cpp
The pinned local official quantizer source is archived with its checksum; online main is context,not an exact version claim.
The adaptation adds decode_query_planes: eight coordinates per plane byte,load3MSB-first high/5LSB-first low bytes,
branchless bit recovery,then the ORIGINAL subtraction/division. No reciprocal approximation.
MutableGraphState::decode_query alone uses this helper; original-space decode/inverse rotation and query search are unchanged.
No persistent cache,API,snapshot,model,degree/ef,graph selection,journal or protection-policy change.
The exhaustive regression covers256 codes,dimensions0/1/7/8/9/.../961,padding set,unaligned plane starts,
output guards,four norms and memcmp against scalar read_plane_code.
This is actual layout-aware production code tried and tested,not a benchmark parameter change.

## Frozen uninstrumented end-to-end protocol and rejection

Default NONE versus NONE,10k GIST/Cohere,600 historical observed queries,k10,degree16,maintenance128/query512,
CPU0,BLAS/OMP/MKL1. Three full-ID changed-vector Update/Remove/Add passes per builder,
90000 operations each. Three alternating pairs/dataset,12freshbuilders total. No concurrent compilation/tests while timing.
Leading RAM -I overlays and pre-timing -MM dependency/hash receipts bind each exact header.
These are new candidate measurements,not a rerun of the previous stack-scratch/profile experiment.

| dataset | control CRUD median ms | candidate median ms | change | final Recall |
| --- | ---: | ---: | ---: | ---: |
| GIST | 25352.048256 | 25398.909808 | +0.18484% | .811167 |
| Cohere | 22407.592686 | 22760.214861 | +1.57367% | .908167 |

Pair changes GIST+.16334/+.18484/+.20656%;Cohere+1.63956/+.14053/+2.06651%.
All pairs are slower in this sample. No gain established; this is not statistical significance,
a universal regression or proof of a specific instruction/CPU cause.
Do NOT adopt based merely on fewer source-level reads or branches.
All paired initial/final hits,ordered ID/hex distances and whole snapshot SHA identical.
Every builder independently Save/Loads its own final ordered search exactly.
Unchanged recall still fails prior study floors; no improved-quality claim.
Query/load timing is incidental to a maintenance-only candidate,not a query optimization win.

## Tests/restoration

Candidate Release6/6 and ASan/UBSan5/5 pass,including exhaustive decode and existing allocation rollback.
After restoration Release6/6/defaultASanUBSan5/5 pass; final clang-format/tidy15 pass.
Candidate formatted15 before timing; no independent candidate tidy/coverage claim.
No fresh coverage,RaBitQ-OFF,wholeFull or Node documentation checker run.
Previous parent coverage95.16% is inherited unchanged production,not a new result.
Final default library SHA must match recorded restored parent1a18379a28b8e7d276b054b3a1a323cc28ecfae2a8d7b5ba965539ddd67be22f.

verify.py audits1080000mutation schedule rows,14400truthstates,raw quantiles/throughput/medians,
paired ordered results/snapshot receipts,source bindings,10validation exits and artifact hashes.
Raw contains exact old/candidate/final headers,tests,patch,native source,compile/link/ldd/argv,
measured runner,validation script,actual queries/truth and successful logs.
Large replacements reconstruct from preserved base+recipe+SHA,not archived.
New RAM snapshots deleted only after nativeLoad/SHA receipts; offline audit cannot reread them or independently regenerate exhaustive GT.
No old source/data/raw deleted. RAM libraries are not claimed persistent.
PR2904/2926 branches/metadata unchanged; only personal evidence will be pushed.

## Replay / next scope

Measured run-host.py expects candidate source,not the restored parent,so final helper replays from exact raw candidate header/test.
Copy to NEW empty result directory,run against matching repo/objects/preserved datasets; never overwrite existing rows.
Replay adaptation is syntax-checked,not a new timing run; original measured runner remains raw.
Next examine native four-way inner-product scoring reuse in link/repair,where existing Batch4 single-estimate-bit fixtures
already supply an equivalence starting point. Do not claim that proposed candidate has been implemented or measured here.
Compact incoming maintenance,route quality,100k persistent/interleavedCRUD,freshFull alignment and cold I/O remain open.
