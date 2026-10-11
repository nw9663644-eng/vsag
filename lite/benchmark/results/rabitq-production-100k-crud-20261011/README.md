# RaBitQ public reverse-adjacency 100k changed-value CRUD (2026-10-11)

## Decision and scope

Source evidence: `MutableGraphState::UpdatePrepared` and `Remove` scan every outgoing
row when `use_incoming_adjacency_` is false. The public RaBitQ backend had left this
existing structure disabled. At 100k, a fixed 30k-replacement workload took about
5.5 minutes per dataset. The candidate enables the already-implemented 32-bit incoming
adjacency in the public RaBitQ builder and on native Load. Existing local transaction
journals remain responsible for failure rollback. No graph edge selection, quantizer,
SIMD kernel, degree, ef, API, snapshot layout, or FP32/FP16 backend changed.

This is **one uninstrumented before/after pair per dataset**, both on the same host
and CPU 0, without concurrent compilation. Baseline is branch HEAD
`629aa345517500f0ba20187e7874117dc812dc7c` before this change; candidate is the
uncommitted source diff at measurement time, bound by `candidate-identity.json`.
Both use GIST960 or normalized Cohere768 100k base rows, 100 existing queries, k=10,
RaBitQ8, degree 16, build ef 128, query ef 512, one BLAS/OpenMP thread. Three rounds
of 10k distinct changed IDs per round execute Update, Remove, Add on each ID in the
existing driver (30k replacements, 90k API mutation calls). Queries are measured
before and after the mutation block, **not interleaved among mutations**. The recipe
mixes 87.5% current row with 12.5% original donor row and renormalizes Cohere.
`prepare_persistent_crud_100k.py` recomputes FP64 exact top-10 truth; both initial
truth files matched the original 100k datasets byte-for-byte. Receipts record base,
query, truth, final truth, and replacement hashes. Inputs and snapshots use `/dev/shm`;
the small receipts, raw latency/neighbor/operation CSVs and command metadata are
persisted here.

## Results

| Dataset | CRUD baseline / candidate ms | API mutations/s baseline / candidate | Recall@10 baseline / candidate | Initial recall |
| --- | ---: | ---: | ---: | ---: |
| GIST960 | 329487.429 / 35222.392 (−89.31%) | 273 / 2555 | .853 / .853 | .859 |
| Cohere768 | 337975.452 / 30192.778 (−91.07%) | 266 / 2981 | .953 / .953 | .937 |

| Dataset | P50 us baseline / candidate | P99 us baseline / candidate | Whole-process peak KiB baseline / candidate | Snapshot bytes |
| --- | ---: | ---: | ---: | ---: |
| GIST960 | 1173.961 / 1181.201 | 1328.536 / 1371.915 | 1017568 / 1022052 (+0.44%) | 112802672 |
| Cohere768 | 1172.902 / 1113.022 | 1381.276 / 1289.929 | 826192 / 830668 (+0.54%) | 93603552 |

| Dataset | Build ms baseline / candidate | Save ms baseline / candidate | Warm Load ms baseline / candidate |
| --- | ---: | ---: | ---: |
| GIST960 | 38216.420 / 39997.557 | 76.121 / 151.724 | 77.177 / 126.204 |
| Cohere768 | 35651.327 / 37049.298 | 71.148 / 138.516 | 72.444 / 114.930 |

Native Save/Load verified ordered IDs and exact float distances after each build.
For each dataset, the before/after initial and final neighbor CSVs are byte-identical,
and the persisted snapshot SHA-256 is identical:

- GIST: `656a77de381cfa97d83335bde5d683577356cf279f38ab4f7c8778293ec99bea`
- Cohere: `0134a2a8691119d2cf74569ec6657a229e9230e13281174ba3af068f47f314e6`

The CRUD gain is substantial in these two runs and directly addresses the full-row
scan. The candidate does **not** improve GIST recall: its .853 is below the earlier
study's .90 research reference, while Cohere .953 exceeds .95. The original 100k
GIST index was already .859 before any mutations; this study does not attribute
the entire gap to CRUD. Query P50/P99 movement is mixed and only 100 queries were
sampled, so there is no supported tail-latency win. Save and warm Load regress in
both individual pairs; rebuilding incoming rows and validating them are plausible
costs but were not isolated here. Peak is whole-process high-water RSS including
input matrices, build and a second loaded index, not isolated index memory. These
are RAM/page-cache loads, not cold-I/O measurements. One pair per dataset is not
a statistical/general guarantee.

## Verification and replay

Release 6/6, ASan/UBSan 5/5, RaBitQ-disabled 4/4 and coverage-build 5/5 tests
passed. The additional regression test passes `use_incoming_adjacency` through the
snapshot loader and checks reconstructed incoming edge counts. Clang-format-15,
clang-tidy-15 exit status and `git diff --check` passed. Gcov reports 92.19% line
coverage for `rabitq_backend.cpp` from the current coverage build; this is not
whole-project coverage. The candidate's measured production sources were unchanged
after timing; only the test source was extended.

`run-reverse-100k.py` regenerates both input sets and executes the candidate from
the repository root into a fresh result directory. It refuses an existing
`candidate-rows.json`; copy the helper to a new sibling result directory before
replay. The baseline was run manually with the same driver and environment from
the original HEAD before rebuilding; its stdout, peak, initial/final query and
all 90k operation latency rows per dataset are preserved. The baseline library
binary hash was not recorded before recompilation, so the tracked source HEAD,
not an archived baseline binary, is the reconstruction reference. The failed
`gist-reverse.*` files are retained: they show an attempt that failed with
`base open failed` before indexing because `/dev/shm` was cleared between SSH
sessions. The successful candidate helper prepares and runs within one session.

Remaining project acceptance: current native Full VSAG configuration/SIMD and
quality-aligned comparisons; true cold loading and complete package footprint;
larger/blind query cohorts for P99; long-run fragmentation and queries interleaved
with mutations; GIST100k recall improvement; Save/Load reverse-reconstruction
optimization. This is Lite versus its prior Lite revision, **not Full VSAG**.
PR #2904/#2926 were not updated.
