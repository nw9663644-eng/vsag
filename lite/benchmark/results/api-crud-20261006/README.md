# CRUD on loaded offline candidate graphs

2026-10-06. Base commit b89cdb031cf1f4e49bce9cd556c54fc7d6163b77 plus
this optional CRUD measurement. Source/binary hashes are in metadata.json.

GIST 10k/100k, CPU 0, uniform entries, ef=128, 100 independent Top-10 queries.
Each configuration has three fresh processes. Each process runs 1,000 cycles;
cycle i selects original slot i*8191 modulo size and its original external ID.
Operations: modify coordinate zero by +0.125, Update modified vector, Update
original vector, Remove, then Add original vector. Every cycle restores the
original dataset, so the existing ground truth remains valid. The ID list and
original vectors are retained independently of mutable backend slot positions.
All operations and live counts are checked. Post-CRUD Save/Load must reproduce
all 100 query results exactly, including each ID and float distance.

The table reports median process-level measurements. CPU time covers the CRUD
loop, including preparation and checks; operation latency includes success checks.
It excludes offline graph transformation, load, quality queries and Save/Load.
This tests existing online CRUD applied to offline-built candidates, not an
online diversity construction policy. Equal ef does not mean equal recall.

| Scale | Mode | Recall before | Recall after | Loop CPU ms | Changed Update P50 us | Restore P50 us | Remove P50 us | Re-add P50 us |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 10k | preserve | 0.811 | 0.803 | 592.490 | 230.965 | 172.896 | 7.500 | 172.766 |
| 10k | diverse_reverse | 0.972 | 0.965 | 790.212 | 327.022 | 229.144 | 12.689 | 231.313 |
| 100k | preserve | 0.729 | 0.732 | 1271.569 | 625.936 | 339.982 | 10.429 | 286.274 |
| 100k | diverse_reverse | 0.903 | 0.907 | 1519.125 | 754.112 | 426.390 | 14.089 | 340.201 |

Candidate query quality remains higher after this short churn, while mutation
CPU cost increases about 33.4% at 10k and 19.5% at 100k. This is a maintenance
tradeoff, not a universal performance improvement. The 1,000 unique IDs touch
10%/1% of the two datasets; it is not long-run or concurrent stability evidence.
Mutation correctness is checked only at serial boundaries and snapshot roundtrip;
recall is approximate quality, not a byte-identical graph requirement. SIFT,
Cohere, large vector displacements and interleaved readers are not covered here.
The +0.125 first-coordinate perturbation is a limited update workload.

Release 4/4 and ASan+UBSan 6/6 passed. Small graph and singleton CRUD fixtures
passed with both builds. The singleton uses the API's minimum legal max_degree=2;
a degree-one snapshot is permitted only by the scalar diagnostic, not API Load.
An ASan GIST10k candidate run completed 50 cycles and exact reload verification.
Format/tidy15 and diff checks passed. All emitted samples recompute the reported
P50 values. Save/Load timings are in-memory stream operations, not cold I/O.

## Reproduction

```text
taskset -c 0 BUILD/lite_graph_route_probe SNAPSHOT DATASET NEW_OUTPUT 128 uniform preserve 2 1000
taskset -c 0 BUILD/lite_graph_route_probe SNAPSHOT DATASET NEW_OUTPUT 128 uniform diverse_reverse 2 1000
```

Run three distinct process outputs and rotate mode order. Original absolute
input paths are in commands.json/repeat-commands.json. Inputs come from the
previous independently prepared GIST datasets and long-CRUD snapshots; `after`
in snapshot names means the incoming-repair implementation. Datasets and
snapshots are retained on the experiment host, not duplicated in this directory.
`.api.csv` contains pre-CRUD quality/timing, `.api.csv.crud.csv` the post-CRUD
quality and mutation summary, and `.samples.csv` every operation latency.
Existing scalar summaries and raw search latencies are included for audit.
SHA256SUMS covers this evidence. Next measure a matched-quality end-to-end
workload and longer churn, and use independent quality queries before designing
an online selection-policy change.
