# RaBitQ removal: skip unchanged adjacency rows

Source evidence: MutableGraphState::Remove previously scans each row repeatedly for removed/last slots, erase and remap.
Minimal change uses one find_if to skip unchanged rows; affected rows retain identical backup/erase/remap order.
The legacy loop remains a test-only template specialization. No reverse edges/model/repair policy/API/budget/snapshot changes.
Still O(total_edges) worst case, not an asymptotic improvement. Removal allocation rollback remains mandatory.

Control is 2fea8f9 old Lite, not native Full. GIST/Cohere10k, fixed600 observed queries, degree16/construction128/query512/k10.
Three full-ID passes, 30000 whole-row changed Update/Remove/re-add cycles per builder, frozen same data/truth as persistent-whole-crud-20261009.
One paired trial per dataset: GIST control first, Cohere candidate first. CPU0/BLAS/OMP/MKL1, no query warmup, uncontrolled warm cache/shared VM.

| Dataset | Remove P50 old/new us | P50 change | Remove P99 old/new us | P99 change | CRUD block change |
| --- | --- | ---: | --- | ---: | ---: |
| gist10k600 | 236.844/110.177 | -53.48% | 315.023/180.577 | -42.68% | -13.86% |
| cohere10k600 | 250.414/118.828 | -52.55% | 319.303/182.866 | -42.73% | -13.94% |

Two exact snapshot SHA pairs; initial/final ordered ID/hex-distance and hit CSVs are identical.
Raw API throughput roughly doubles for Remove, but this single pair is descriptive, not significant/universal proof.
Update/Add not changed; their incidental timing differences cannot be attributed to this optimization.
Final recall remains GIST.811167/Cohere.908167, failing prior study floors; this is NOT a quality repair.
Lower query latency at degraded quality must not be called a speed win. Native Full comparison was not rerun.
Four builders, 360000 API operations, 4800 initial/final truth intersections independently audited.
Each builder verifies native Save/Load exact ordered results; small RAM snapshots hashed then removed after successful checks.
Original base/source/raw preserved. Query/truth bytes archived; replacement matrices reconstructed by published prepare_persistent_crud.py
and preserved originals with receipt SHA validation, not stored in this archive.

Validation: Release6/6, ASan/UBSan5/5, Coverage5/5, default RaBitQ OFF4/4;
fresh Lite2682/2820=95.11%, shared SIMD174/176=98.86%. Not whole native Full coverage.
Format/tidy15 passed including Lite header-filter; external warnings suppressed; Node docs checker not run.
Run python3 verify.py to check all raw schedules/truth/latencies/paired semantics/coverage/hashes.
For reproduction, run the same frozen three-pass preparation and commands/env in raw.tar.gz with pinned libraries.
Next priority remains isolating persistent-maintenance quality loss without increasing budgets or changing study thresholds.
