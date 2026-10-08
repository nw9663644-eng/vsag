# Distance-only old-neighbor reuse changes routing coverage

Measured report parent: `69e605f7f084508a5113c43bfa9181bf74ccc82a`. The preceding experiment rejected default adoption of geometry-scored old-neighbor reuse. This follow-up instruments the exact isolated candidate to identify when it activates and how it changes the GIST graph and routing. Production `src/`, `include/`, API, snapshot format, defaults, degree and search budget remain unchanged.

## Diagnostic method

The diagnostic build adds an environment-controlled CSV sink inside the existing experiment macro. For each native FP32 `Update`, it records old neighbors absent from the ANN-selected row, candidates strictly closer than the ANN cutoff, candidates retained after the existing sort/degree truncation, and final rank. No trace is produced unless `VSAG_LITE_SCORED_OLD_TRACE` is set. This instrumentation is single-process diagnostic code and is not proposed for production.

All six candidate cases from `scored-old-candidates-20261008` are replayed once. Their ordered query outputs match the prior candidate byte-for-byte. A second corrected event run supersedes the first attempt, whose summary rows contained one excess CSV delimiter; the verifier rejects shifted rows and reconciles every summary count against candidate-event rows.

## Activation

| Protocol | Dataset | Updates selecting old candidates | Rate | Qualified candidates | Retained candidates |
|---|---|---:|---:|---:|---:|
| Coordinate | SIFT | 391/10,000 | 3.91% | 1,101 | 1,000 |
| Coordinate | Cohere | 1,159/10,000 | 11.59% | 2,638 | 2,436 |
| Coordinate | GIST | 3,460/10,000 | 34.60% | 9,436 | 8,315 |
| Whole vector | SIFT | 75/1,000 | 7.50% | 107 | 104 |
| Whole vector | Cohere | 148/1,000 | 14.80% | 256 | 239 |
| Whole vector | GIST | 146/1,000 | 14.60% | 198 | 190 |

The coordinate-GIST workload activates the rule three to nine times as often as coordinate Cohere/SIFT. Its 8,315 immediately selected edges occur on 3,460 updated sources; 7,974 survive the remaining updates and 7,573 both survive and differ from the baseline final row.

## GIST topology and route mechanism

The fixed candidate and baseline differ in 11,414 neighbor sets: 4,461 updated sources and 6,953 other sources, showing that existing `link/repair` propagation extends beyond directly updated rows. There are 18,166 removed and 18,234 added edges. Incoming degree changes on 15,097 nodes, although zero-incoming nodes improve slightly from 26 to 22.

The key negative signal is directional reachability. From slot0, baseline reaches 89,642 nodes while the candidate reaches 89,202, a loss of 440. Reverse reachability to slot0 remains 99,955 in both graphs. Across the same 300 GIST queries, the candidate visits 6.20 fewer nodes on average and loses nine net truth hits. All 35 truth IDs returned only by the baseline are unvisited by the candidate route; all 26 truth IDs gained by the candidate are visited. Thus the Recall loss is explained by altered route coverage, not by post-visit result truncation.

**Decision:** distance alone is the wrong gate for preserving old neighbors. The next candidate, if pursued, must protect directional coverage or neighbor diversity while keeping degree16/ef128 fixed. A useful gate must reduce coordinate-GIST activation and preserve entry reachability without erasing the small SIFT/Cohere gains. No default implementation is added from this diagnostic.

## Audit

```bash
python3 lite/benchmark/results/scored-old-mechanism-20261008/verify.py
```

The verifier checks archive safety and hashes, the three referenced prior reports, exact source/build identities, Release and ASan+UBSan fixtures, both existing graph-test runs, format/tidy logs, six corrected event streams and exact schedule, candidate-output identity, the full 100k-node candidate topology, baseline topology from the prior audited trace, edge/incoming/reachability deltas, same-query route statistics and truth-ID visitation. Large snapshots, binaries and the 22 MiB topology CSV are excluded; the lossless uint32 topology stream is retained.

This report is pushed only to the personal experiment branch. PR #2904 and #2926 source branches remain frozen.
