# Strict directional old-neighbor gate pilot (2026-10-08)

## Question and minimal candidate

The preceding scored-old mechanism report showed that distance-only reuse loses GIST recall through changed route coverage. This isolated pilot asks whether a stricter directional gate fixes that failure without changing `max_degree`, `ef_search`, entry points, repair, persistence, API, snapshot format, defaults, or production source.

The FP32-only compile-time candidate starts with the same distance requirement (`old_score < current_cutoff`). An old neighbor is admitted only when its pairwise squared-L2 distance to every current ANN neighbor, and to each previously admitted old neighbor, is at least its squared distance to the updated query. This is a conservative alpha-1 occlusion test inspired by Full VSAG's `select_edges_by_heuristic`; it deliberately preserves the existing ANN row as the directional reference rather than applying Full pruning wholesale. FP16 is unchanged.

## Frozen pilot

The pilot reuses the audited GIST coordinate protocol: 100k vectors, 960 dimensions, degree 16, ef 128, CPU 0, 10,000 persistent coordinate updates, 300 already-observed queries, and changed-vector exact ground truth from `scored-old-candidates-20261008`. Two fresh candidate processes produced byte-identical ordered neighbor streams. This is a targeted mechanism pilot, not a blind or cross-dataset validation and not a CPU benchmark.

| variant | changed truth hits / 3000 | recall |
|---|---:|---:|
| default baseline (referenced) | 2049 | 0.683 |
| distance-only scored old (referenced) | 2040 | 0.680 |
| strict directional gate | 2040 | 0.680 |

Against the default baseline, the gate has 9 winning queries, 14 losing queries, 277 ties, and -9 net hits. Against distance-only reuse it has 15 wins, 15 losses, 270 ties, and zero net change. Its ordered output differs in 211 rows from baseline and 295 rows from distance-only reuse, so the gate is active but only redistributes errors.

## Decision

Reject this exact all-ANN directional gate. It does not recover the route-quality loss and will not enter the default implementation or a PR. The result also rules out treating a local alpha-1 occlusion check as sufficient evidence of global connectivity preservation. Any next candidate must target connectivity directly (for example, protected incoming/reachability evidence) and remain fixed-budget.

## Verification

Release and ASan+UBSan isolated builds pass the candidate fixture, the baseline fixture, and the existing graph suite (`545120 assertions in 14 test cases`). The fixture distinguishes an old candidate overlapping an ANN direction from one adding a new direction and confirms FP16/default behavior. `clang-format-15` and `clang-tidy-15` pass. Run `python3 verify.py`; it checks archive safety and hashes, referenced prior evidence, build/source identities, test logs, repeat equality, exact truth intersections, and the comparison above.
