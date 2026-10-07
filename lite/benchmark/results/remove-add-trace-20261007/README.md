# Remove/Add phase diagnostics (2026-10-07)

The full same-value churn regression remains below its historical Cohere recall floor: 0.960 initially and 0.940 after 10,000 cycles. This change adds a diagnostic benchmark, not a library optimization or a new acceptance result.

## Source and protocol

Measured parent: `f98da57f5f3804daf2eb628644c15eb5dfb2f1c9`. `GraphBackend::Remove` detaches incoming/outgoing edges, compacts the last slot, and repairs affected nodes; `Add` searches for neighbors and inserts reverse links, potentially pruning saturated rows. Same-value Update now preserves the stored representation and graph. The probe uses the existing private Backend interface and restores the existing FP32 v2 snapshot; it does not implement another ANN algorithm.

Cohere normalized 10k, 768 dimensions, 100 previously observed queries, L2 top-10; default diversity OFF, degree 16, construction/maintenance/query budget 128. CPU 0. Snapshot, query/truth, source, executable and library SHA256 plus commands and exit codes are recorded in protocol-final.json. No parameter selection or new holdout evaluation. Two final fresh processes (r2/r3) reproduce all 10,000 event rows and ten checkpoint rows byte-for-byte. Earlier r0/r1 used the same probe before stricter malformed-snapshot size validation and include cleanup; final outputs also equal r0/r1.

Each cycle uses original external ID `(cycle * 8191) % N`, same-vector Update, Remove, Add(original). The probe requires that this schedule is a permutation. The optional event CSV tests one query per cycle, starting at `cycle % query_count` and choosing the first query whose top-k truth does not contain the removed ID. All three phases test that same query. A query of -1 means no eligible query; its hit fields are zero and it must not be treated as a measured query. Checkpoints test all eligible queries. Counts and API successes are checked after each modification.

Edges are counted using external IDs among surviving nodes, excluding every edge incident to the deleted ID. Thus physical slot renumbering and normal incident-edge removal/addition are not falsely counted as survivor-edge changes. Edge statistics exclude the implicit slot ring used by Search, so phase changes cannot yet be attributed solely to stored-edge pruning.

## Results

Ten checkpoints (cycles 0, 1, 10, 97, 100, 500, 1000, 2000, 5000, 9999) show survivor-edge changes, but no immediate hit changes on their common query sets. They were insufficient to locate quality-changing operations.

The rolling-query trace finds 13 changed cycles. Remove loses one hit seven times and gains one once; Add loses one twice and gains one seven times. Their signed sums are -6 and +5 across the sampled events. These sums are NOT a decomposition of the end-to-end recall drop: different queries are sampled each cycle, and most queries are not checked at most cycles.

| Cycle | ID | Query | Before / Remove / Add hits | Observation |
| --- | --- | --- | --- | --- |
| 1099 | 1909 | 99 | 9 / 8 / 8 | First sampled loss occurs during Remove |
| 2148 | 4268 | 48 | 10 / 9 / 10 | Add recovers a Remove loss |
| 3000 | 3000 | 0 | 7 / 7 / 6 | Loss occurs during Add |
| 7112 | 4392 | 12 | 8 / 8 / 7 | Second sampled Add loss |

Both mutation phases can change route quality on queries whose truth is unaffected by the deleted vector. These concrete events are useful targets for follow-up controls; they do not establish a unique faulty repair/link statement, and approximate top-k loss is not itself an API correctness failure.

## Validation and boundaries

Final Release and ASan/UBSan fixtures pass: an eight-node exact clique checks deleted-truth exclusion, external-ID edge invariance through last-slot moves, all eight rolling event records, unchanged legacy checkpoint output, no eligible query, invalid CLI/input/truth ID, malformed count overflow, and refusing existing event output. Final Release CTest passes 4/4. clang-format-15 and clang-tidy-15 pass for the new C++ target; tidy suppresses third-party/non-user warnings. This is not a new whole-library coverage run; library code is unchanged and prior coverage results retain their original scope.

The tool is optional under ENABLE_BENCHMARKS:

```bash
lite_graph_mutation_trace INITIAL_FP32_SNAPSHOT DATASET [EVENT_CSV]
python3 lite/benchmark/test_graph_mutation_trace.py TRACE_BINARY GRAPH_CRUD_QUALITY_BINARY
python3 lite/benchmark/results/remove-add-trace-20261007/verify.py
```

The current snapshot reader is for the existing little-endian host's FP32 v2 graph format, not a replacement public loader, FP16 diagnostic or general portable parser. Extra searches/edge scans make these runs unsuitable for CPU performance claims. No concurrency, Full implementation, API, storage format, degree, or search budget changes. Raw snapshots and executables remain on the remote host; published verification hashes source files and reported artifacts and checks receipts, but does not pretend to reread unavailable big host inputs. Original log hashes and whitespace-normalized publication hashes are separate.

Next: replay the first sampled Remove loss and both Add losses with per-query visited nodes and changed external-ID edges. Distinguish stored-edge changes from implicit-ring/entry changes before proposing a minimal retention rule; validate any candidate at the same budget and on new held-out queries. Only the personal development branch is updated; PR source branches remain frozen.
