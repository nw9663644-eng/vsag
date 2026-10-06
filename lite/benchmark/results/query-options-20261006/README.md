# Native per-query budget API

2026-10-06, base commit e1728c19ed16e9b9ac11dc9d63a5a2d2b83e17d2.

Public SearchOptions{ef_search} and Index::SearchWithOptions provide an override
for one query. Zero uses the configured graph default. Positive budgets clamp
to the live count and are raised to k as necessary. BruteForce ignores the
budget. Existing Search overloads, including Search(..., {}), remain unambiguous.
Optional external-ID filtering keeps the existing semantics. Overrides use local
values and never modify stored graph options or mutation/construction settings.
The externally serialized-call requirement still applies; concurrency support
was not expanded by this change. No snapshot format or public Index layout change.

The benchmark now serializes the ORIGINAL configured budget and calls the new
API with the requested query budget. API summaries append configured_ef_search
and query_ef_search. Optional CRUD keeps the original stored maintenance budget;
post-CRUD quality and reload verification use the requested query budget. This
intentionally corrects earlier experimental measurement behavior that overwrote
the snapshot's budget and therefore also affected mutation work. Historical
ef128 mutation experiments remain unchanged because both values were128; old
measurements with other overrides must not be treated as the new semantics.

## Verification

* Default Release 4/4, experimental online-diversity Release 3/3 and default
  ASan+UBSan 6/6 passed. Updated route-probe fixtures passed in Release and ASan.
* BruteForce, FP32 graph and FP16 graph cover defaults, empty filters, filtering,
  tiny and maximum budgets, k=0, empty indices and invalid query inputs.
* Full-budget searches match an exact reference using representable grid values
  for FP16. Calls with overrides leave snapshots byte-identical, and identical
  subsequent Update/Remove/Add sequences match an untouched loaded twin exactly.
* Coverage fresh unit run: 965/1068 source/internal-header lines, 90.36%; .cpp and
  public-header scope 914/996, 91.77%. This is Lite-only line coverage.
* Independent installed consumer includes only public headers and links vsag::lite.
  It runs graph BuildGraph(4,8), then SearchWithOptions(..., SearchOptions{64}).
* Replay of the previously frozen 600 GIST queries retains API Recall0.950 and
  byte-identical scalar diagnostic rows while explicitly reporting stored128 and
  query512. This is a compatibility replay, not a new unseen quality split or a
  repeated performance study. Single-process native timing is retained for audit.
* Format/tidy15 and diff checks passed. The combined tidy log records two
  test-style findings subsequently corrected; tidy-test-final.log is clean.
  The graph/index implementation and benchmark were clean in the combined pass.

Usage and contracts are in docs/docs/{en,zh}/src/development/lite_first.md;
lite/example/main.cpp demonstrates the installed API. Raw native replay and
query/mutation budget fields are included. SHA256SUMS covers this evidence.
Library source hashes at publication are in metadata.json. Experimental online
neighbor selection remains OFF by default; this new query API is available
independently of that option. PR source branches were not updated.
