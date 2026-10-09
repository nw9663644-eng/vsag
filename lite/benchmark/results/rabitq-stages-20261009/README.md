# RaBitQ stages, topology I/O and heap admission

The initial snapshot is SIFT100k at e8781f1, degree16/stored ef128, fixed seed47.
Only cached inputs are used. Instrumented overlays retain their compile commands
and modified headers in the three instrumented archives. Production source has
no timers or instrumentation. perf was denied by paranoid4; no kernel setting
or privilege was changed.

Initial diagnostic warm repeated-query phase shares were approximately transform
below1%, route85%, rerank15%. These clock probes perturb execution and omit some
destruction/return overhead; they are NOT product-latency measurements or a
precise exhaustive partition. Stream counting also adds overhead. At100k the
old loader made2,600,141 reads; array I/O makes800,143. Topology read diagnostic
median fell22.443 to4.620ms. Decoding payload, validation, per-row allocation and
ID-map construction remain costs. No validation was removed.

Normal, uninstrumented loaders use seven alternating control/candidate pairs.
Array I/O load median54.624 to37.929ms (-30.6%). RSS40344/40372KiB is essentially
unchanged. Same snapshot, CPU0 and uncontrolled warm cache: NOT cold load.

Normal uninstrumented query-loader pairs use ef512,100 historical queries each,
seven fresh processes per variant. P50 median731.655 to557.188us (-23.8%);
P99 median949.149 to737.253us; recall.975 in every run. Similar loaded RSS.
The separate overlay query exports compare all1000 ordered neighbors (ID and
hexfloat distance) byte-for-byte at ef512; visited/reordered counts also agree.
This is not an independent blind quality evaluation or Full comparison.

Source evidence: native StreamReader::ReadVector for block I/O, and
BasicSearcher::search_impl for admission only when the best heap is undersized
or the node improves its boundary. Lite preserves its existing distance/slot
tie rule and still marks all seen neighbors, including rejected candidates;
filtered complete-code ranking happens before pruning. The old unpruned
template specialization remains an internal regression oracle, not a public
option. Differential tests cover dimensions1/17/128, repeated-vector ties,
non-monotonic external IDs, four budgets, two k values, all-reject/partial/no
filters and changed Update/Remove/Add states.

Release6/6, ASan/UBSan with leaks8/8, coverage6/6 passed. Final production Lite
coverage2590/2735=94.70% over src/lite and include/vsag/lite, merging all
instrumented test TUs (not Full coverage). Format15 passed. Tidy15 for production
and final probe has no user diagnostics; dependency warnings were emitted and
initial probe style/narrowing failures were fixed. Probe bad-argument, zero
budget and output-overwrite checks passed.

Reproduce the stage tool with build_rabitq_stage_probe.py NEW_SCRATCH LIB_STATIC,
then stage_probe SNAPSHOT QUERIES EF REPEATS [NEW_NEIGHBORS]. The generated overlay
is diagnostic-only; its checked markers must match the source version. Native
query benchmarks and load_memory, not overlay timings, establish speed changes.
Raw archives retain metrics, commands, query samples, neighbors and overlay
sources. The large RAM snapshot is not retained after closing the SSH keeper;
its size/hash and full input/library provenance are retained. Rebuild from the
pinned source and cached inputs for another experiment.

Remaining: same-quality native Full remeasurement,100k GIST/Cohere multiple
trials, persistent whole-vector long CRUD, cold page-cache experiments, larger
query cohorts for P99, fresh Full all-object build and complete deployment
dependency closure. Do not claim all project requirements are completed.
