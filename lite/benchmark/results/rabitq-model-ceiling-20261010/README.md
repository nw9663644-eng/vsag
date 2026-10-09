# Frozen-model full-candidate diagnostic

Production remains c6d6c0b (head8a1f2d2), library e9613ace..., not native Full.
Formal query ef512 is unchanged; VSAG_GRAPH_DIAGNOSTIC_EF=N emits separate
initial/final query/hit/hex-distance/timing files and a diagnostic summary.
The no-filter graph traversal includes a connected bidirectional slot ring.
At ef=N the retained set reaches N before its stopping condition can apply,
so every record receives the complete encoded estimate. This is a scorer ceiling,
not exact FP32 search, a new default, or a faster accepted query configuration.

Fixed GIST/Cohere10k,600 historically observed queries,k10,degree16,construction128,
CPU0/BLAS/OMP1; same three-pass whole-row recipe/truth as earlier persistent tests.
Four processes: update-only and Remove/Add-only per dataset. Diagnostic work warms
query state and increases whole-process cost: no speed or memory comparison claimed.

| Dataset | Formal final Update / RemoveAdd | Diagnostic initial | Diagnostic final both modes |
| --- | --- | --- | --- |
| GIST | .858667 / .849500 | .995667 | .996500 |
| Cohere | .935500 / .923333 | .996167 | .995500 |

Diagnostic ordered ID/hex-distance and hit CSVs are byte-exact between modes,
initial and final. This strongly supports maintenance routing coverage as the
main gap for this frozen workload; it does not prove every future model/dataset
is immune to quantization error or that one missing incoming rule is sole cause.
Do not substitute diagnostic recall for ef512 acceptance.

See the adjacent rabitq-update-incoming-candidate-20261010 prototype study.
Run python3 verify.py here to audit BOTH evidence directories:8builders,300000
mutations,14400 formal/diagnostic truth intersections,raw schedules/quantiles/hashes.
Actual queries/truth,commands/env,measured tool/fixture and validation logs archived.
Replacements can be reconstructed from preserved originals,prepare_persistent_crud.py
and receipt SHA; replacement matrices/final bases are not archived here.
Snapshots are hashed then deleted after successful SaveLoad ordered-result checks
only inside verified new RAM scratch. Source/original data/old raw remain.
Reproduce with frozen prepare script; set diagnostic ef to10000 and modes as recorded.
Release/SAN tool fixtures and format/tidy15 passed; no new default CTest/coverage claim.
100k,interleaved queries,cold I/O,fresh/latest Full and stable mutation-quality acceptance remain open.
