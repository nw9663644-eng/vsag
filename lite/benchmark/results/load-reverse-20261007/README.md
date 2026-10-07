# Corrected Full reverse-edge load-only comparison, 2026-10-07

Seven fresh processes per mode, CPU0, cyclic rotated order, 28 runs total. Initial pre-CRUD Cohere100k/768dim snapshots, same original normalized base. Existing measured recall: Full compressed/reverse 0.952, Lite default 0.958, diversity 0.961333; common floor0.95, not exactly equal quality. No new query or mutation measurement.

| Profile | Load ms | Loaded RSS KiB | Loaded RSS MiB | Load-stage peak KiB | Snapshot bytes |
|---|---:|---:|---:|---:|---:|
| full | 182.190 | 445008 | 434.58 | 575968 | 313616358 |
| full_reverse | 145.931 | 568320 | 555.00 | 699304 | 316237502 |
| default | 137.407 | 341196 | 333.20 | 341844 | 321600064 |
| diverse | 128.712 | 331892 | 324.11 | 332624 | 317024600 |

Lite default versus Full reverse: loaded RSS -39.96%, load wall -5.84%, load-stage peak -51.12%.

Lite diverse versus Full reverse: loaded RSS -41.60%, load wall -11.80%, load-stage peak -52.43%.

## API and source evidence

The optional loader argument `force-remove` creates Full HGraph with flat storage,
physical deletion support and reverse edges, matching the existing mixed benchmark.
Default/explicit `compressed` retains the old command behavior; Lite rejects the
Full-only profile. HGraph::Deserialize calls deserialize_basic_info, which checks
serialized index parameters against creation parameters. GraphDataCell construction
creates ReverseEdge only when configured. Wrong-profile snapshots fail in the fixture.
No src/include library, storage format or query budget changes were made.

Existing known Full shared library is d18c82a cached incremental build, not clean
latest upstream; shared hash matches the earlier reverse-edge CRUD study.
Source/binary/snapshot hashes and ldd are included. Initial snapshots were already
quality-tested in full-reverse/cohere-matched reports. Do not label this as post-CRUD
loading, a fresh quality study or exactly equal retrieval quality.

## Lifecycle and interpretation

Existing common Linux probe: no source base/query matrices, build, search or save.
Snapshot files pre-read once; uncontrolled warm cache, not cold start. Fresh process
RSS before creation and before load; close input and malloc_trim with index alive
before loaded RSS/peak. Full empty Factory creation excludes load timing; Lite
static Load includes index creation. Full checks count with caller dimension;
Lite also checks restored dimension. Full restored dimension is not independently
verified. Values are whole-process memory; peak covers startup/load, not build.

Full reverse vs compressed differs in flat/compressed storage and deletion support,
not just one flag: the RSS difference cannot be assigned entirely to reverse edges.
Their warm-load ordering does not predict query/CRUD ordering. Lite snapshots here
remain larger, and corrected Full is faster in the previous mixed CRUD study.
This result closes the specific reverse-ON load-memory gap; it does not establish
universal Lite speed, dependency-closed deployment size, cold-start improvement,
concurrent stability or public RaBitQ completion. Diversity stays OFF by default.

## Verification and reproduction

- Full/Lite legacy CLI tests, positive memory/count checks, invalid numbers,
  missing/corrupt snapshots pass. Optional seven profile combinations pass,
  including both correct profiles, both wrong snapshot profiles and unknown flags.
- New tiny reverse-ON fixture uses the existing Full benchmark, 8x16 one-hot,
  initial Recall1 and successful CRUD/snapshot verification. Large files stay on host.
- clang-format15 and clang-tidy15 for both adapters pass. Non-user header warnings
  are suppressed; this is not whole-library lint/coverage or a new Full ASan run.
- Full compile failed during the interrupted prior turn (missing string operator);
  initial log retained, corrected final build and tests pass. No failed measurement
  discarded. Existing Lite binaries compiled during that turn were source-equivalent
  in the Lite preprocessor branch; binary hashes bind actual executables.
- All28 CSV rows reproduce summary fields; rotated order, command/profile and metrics
  verified. audit.json reports median/min/max. sha256.json covers published artifacts.
  Host raw logs have separate hashes; publication removes trailing whitespace.

Use `run.py` from the actual repository root with the recorded input paths and
binaries, choosing a NEW output directory (the host root is encoded in the script).
It writes protocol and hashes before runs, preserves raw stdout/stderr, and extracts
CSV after Full initialization output. `verify.py` audits committed evidence using
only Python standard library; source and binaries remain at their recorded revisions.

Only personal experiment/lite-rabitq-next-20260926 is pushed; PRs remain frozen.
Next profile build and maintenance CPU at fixed quality, then implement justified
changes; do not keep tuning observed final query sets.
