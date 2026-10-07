# Event-specific graph routing controls (2026-10-07)

Three previously identified Cohere10k churn losses have different explanations. Two recover under a slot-order control; one recovers under a single stored-edge control. No library policy, API, snapshot format or search budget is changed. These are diagnostic results on observed queries, not a new quality gate or performance improvement.

## Source and replay

Parent `15e0c0c9b7f3341829ffb5dc9473b263c6cd3514`. The existing `GraphBackend::SearchImpl` explores stored adjacency plus physical-slot ring neighbors and uniform slot entries. `Remove` moves the last slot and repairs local adjacency; `Add` inserts reverse edges and prunes saturated rows while protecting last incoming edges. Therefore these causes need separate controls before changing link policy.

The archived host-only `replay.cpp` includes the existing mutation trace reader under a renamed main, calls the existing Backend methods, and writes the same FP32 v2 graph layout for nine states: before/Remove/Add at cycles1099,3000,7112. `inspect.cpp` includes the existing route probe under a renamed main; it exports scalar visited nodes and independently loads each snapshot through public Index::Load/Search. Every scalar/public returned ID set matches across all22 states/controls. These wrappers use the recorded remote paths and existing source checkout; they are archived diagnostic programs, not newly installed production commands.

Cohere normalized10k768, original observed queries99/0/12, top10 L2, default diversity OFF, degree16, maintenance/query128, CPU0. Query rows are sliced unchanged from the same prepared100-query input. Removed IDs are excluded from the selected truth sets. Snapshots and executables stay on the remote host; hashes, compile commands, run commands/exits, per-query CSVs, native API output and compressed per-node exports are published. Source and input identity, not source freshness of upstream main, is established.

## Factor controls

| Cycle / query | Before / Remove / Add hits | Restore old order with current edges | Restore old edges with current order |
| --- | --- | --- | --- |
|1099 /99|9 /8 /8|Remove recovers9|Detached old edges remain8|
|3000 /0|7 /7 /6|Add remains6|Add recovers7|
|7112 /12|8 /8 /7|Add recovers8|Add remains7|

For Remove1099, original order means the before-state order with the deleted ID omitted, retaining the exact post-Remove external-ID adjacency. The alternative detached graph retains the original adjacency minus deleted incident edges under current post-Remove slot order. Combining detached edges and original surviving order also yields9. Thus repair changes are not necessary for this particular loss, and changing order recovers it. Slot controls change ring, entry selection and slot tie order together; they do not isolate a ring-only cause.

For Add3000/7112, before and after contain exactly the same IDs and vector bytes. One control retains post-Add ordered external-ID edges but restores pre-cycle slot order. Another retains current slot order but restores pre-cycle ordered external-ID adjacency. All controls reread and check vector bytes, edge order, degree bounds, unique IDs and valid non-self slot references. None exceeds degree16 or budget128.

Missing truth is unvisited, rather than visited then mis-ranked. At1099, ID9348 becomes unvisited; at3000, ID1707; at7112, ID4725. Existing misses remain. Scalar/public ID-set equality is checked, not claimed exact floating-point distance or rank-order equality. No measured speedup is derived from the diagnostic latency files.

## One-edge attribution at cycle3000

Add drops four survivor edges:482→1295,573→3219,6727→1707,7664→5819. Restoring each old row separately only recovers query0 for source6727; restoring all four also yields7. A stronger control replaces only `6727→3000` with `6727→1707` at the same adjacency position. Every other ordered edge, ID slot and vector byte is identical; the row stays degree16. Public/scalar hits recover6→7 and truth1707 is visited again.

The incoming count of1707 falls2→1; it never becomes orphaned. The single-edge control reduces3000 incoming4→3, also nonzero. Native selected FP32 kernel distances from6727 are0.3021757603 to1707 and0.3002210855 to3000. The replacement favors a closer neighbor but loses a useful route within the fixed budget. This demonstrates the limitation of protecting only the final incoming edge. It does not establish that every closer-neighbor replacement is harmful, or that globally protecting two incoming edges is beneficial.

## Validation and next experiment

All22 public snapshot loads/searches succeed and match scalar returned ID sets; raw node exports independently reproduce hits/visited counts and lost truth IDs. Format/tidy15 pass for the two host wrappers. Initial inspect wrapper compilation dereferenced expected<unique_ptr<Index>> incorrectly; it was corrected to `(*index)->Search`, final build and all inspections pass. This was a diagnostic-wrapper build error, not a library defect. No library code changed, so no new library coverage or ASan claim; prior regression results retain their scope.

Verify the report with `python3 lite/benchmark/results/event-routing-20261007/verify.py`. It recomputes compressed exports, factor results, one-edge recovery and artifact hashes. Available host snapshots/binaries/inputs are rehashed; unavailable host files are explicitly reported and not represented as reread. Big inputs are not committed.

Next test a general, opt-in incoming-retention control before touching defaults: protect penultimate incoming links during saturated-row replacement, evaluate fixed-budget full-ID CRUD quality and single-core cost, then check other distributions and held-out queries. Treat slot-order sensitivity separately. Do not hardcode IDs/query-specific edges or add permanent per-deletion whole-graph reorder. Only the personal development branch is updated; PR sources stay frozen.

Original host log/CSV hashes are recorded separately from normalized publication artifacts; changed-survivor-edges.csv uses LF in the report instead of the host CSV writer's CRLF. The data values are unchanged.
