# Slot-factor routing diagnosis, 2026-10-07

Restoring reference entries recovers one lost Top-10 hit at cycle1099 (query99,
8 to9) and cycle7112 (query12,7 to8). Ring or tie-order restoration alone does
not recover either hit. None of the eight combinations improves the full
10,000-cycle endpoint: all remain .940, below the historical .95 floor.
The library implementation and search budget are unchanged. These observations
justify further stored-topology maintenance work, not adopting a new entry rule.

## Protocol and results

Cohere normalized10k x768 FP32, squared L2,100 existing observed queries,
Top10, degree16, stored ef128, single CPU0. Five snapshots each have a paired
physically reordered control preserving external IDs, vector bytes and stored
external edges. Reference order filters removed IDs and must cover all live IDs.
Masks independently restore reference entries (bit1), implicit ring (bit2) and
equal-distance slot order (bit4); mask0 is the unchanged scalar diagnostic.
All-restored mask7 matches reordered-control mask0 ordered result IDs on all
500 queries. All ten snapshots' mask0 results match public native API ID sets
at runtime; native distance/order equivalence is not asserted.

| Snapshot | Mask0 recall | Entry restored | Ring/ties without entries |
| --- | ---: | ---: | ---: |
| Initial | .960 | .960 | .960 |
| Full churn | .940 | .940 | .940 |
| Cycle1099 postRemove | .957 | .958 | .957 |
| Cycle3000 postAdd | .949 | .949 | .949 |
| Cycle7112 postAdd | .937 | .938 | .937 |

`summary.json` reports per-query wins/losses: only the two indicated events
improve one query; the other states have no per-query hit changes. Equal-distance
comparator encounters are2 to5 per mask/state, not counts of unique tied pairs
or ground-truth ties. No inference that ties never matter follows; the synthetic
fixture demonstrates an actual tie-order result change.

This is an untimed diagnostic, not a CPU improvement measurement. Fixed ef does
not guarantee identical visits or distance evaluations. Legacy API timing sidecars
are archived incidentally and are not performance evidence. All real queries here
have their full recorded truth present; the CLI excludes queries whose full truth
is absent rather than changing the truth set. These are previously observed
queries, not independent holdout acceptance or a general CRUD quality guarantee.

## Reproduce and audit

Build standalone Lite with ENABLE_BENCHMARKS=ON, then run:

```sh
lite_graph_slot_probe SNAPSHOT REFERENCE DATASET OUTPUT.csv
python3 lite/benchmark/test_graph_slot_probe.py build-lite-fragment-release/lite_graph_slot_probe
python3 lite/benchmark/results/slot-factors-20261007/verify.py
```

The diagnostic currently supports nonempty FP32v2 little-endian graph snapshots.
It writes trace and neighbor CSVs and rejects existing output files. The reference
is an earlier snapshot defining order, not a replacement topology. `commands.json`
records15 successful final commands with source/reference hashes; `identity.json`
binds source, binaries, library and dataset to parent60f2241. Large snapshots and
binaries remain on the experiment host; compressed CSVs and the small groundtruth
are archived for offline audit. `ordered-receipts.json` records reordered controls.
`run_final.py` is the host replay recipe; host paths must be supplied to reproduce.

Release and ASan+UBSan fixtures pass, default CTest passes4/4, and final
clang-format15/clang-tidy15 checks pass. Initial tidy style failures and repaired
logs are retained in `checks.json`. Fixtures cover all masks, actual ties, removed
truth exclusion, invalid reference/dimension/truncation/truth/arguments and output
protection. The optional tool reuses the existing diagnostic translation unit with
a separate entry macro and one targeted include lint suppression, avoiding a second
copied search implementation. No src/ or include/ library changes, new public
RaBitQ backend, concurrency guarantee or acceptance-floor relaxation is included.

`run_final.py` and `package.py` are exact historical host scripts, not portable
entry points. The replay needs original exploratory CSVs and commands in the
host directory plus the copied pre-change binary; `exploratory-commands.json`
archives that seed receipt. Use `verify.py` for portable offline verification.
`compile-flags.json` records actual Release and ASan+UBSan compilation commands.

Logs are archived as `.log.gz`; their uncompressed names in command receipts
refer to the original host files.
