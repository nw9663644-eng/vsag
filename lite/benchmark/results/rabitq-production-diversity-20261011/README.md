# RaBitQ long CRUD graph repair (2026-10-11)

## Source evidence and decision

The previous public Lite RaBitQ policy preserves valid graph edges during mutation
but fills missing edges by source distance alone. On fixed 10k persistent changed-value
CRUD, the default fell to Recall@10 0.811167 on GIST960 and 0.908167 on normalized
Cohere768. The internal cached safe-link candidate alone raised them to 0.899167 and
0.947000, just below the study's 0.90/0.95 long-CRUD targets. Native VSAG HGraph
uses candidate diversity when selecting edges. Lite's compressed codes need their
own inexpensive pairwise estimate.

The production change enables cached incoming counts for safe link pruning and,
only when repair has more candidates than free edge slots, selects replacements
with a one-bit code-code diversity test. It uses the most significant RaBitQ filter
plane, normalized by dimension and both stored norms, then fills any remaining
slots in the old distance order. Invalid tail bits are masked. No original FP32
vectors or reverse-adjacency index are retained. Public API, build graph, search
distance, quantizer, snapshot format, and degree limit are unchanged. The internal
policy is restored after Load via the backend constructor.

Two exploratory float-vector pairwise versions also crossed the recall targets,
but cost approximately 80-95% more CRUD time in one paired trial each. A one-bit
trial gave greater recall with 8-12% CRUD overhead, so only that variant was
promoted to production source. The three exploratory raw archives and scripts are
in sibling directories `rabitq-repair-diversity-20261011`,
`rabitq-repair-filter-diversity-20261011`, and
`rabitq-repair-onebit-diversity-20261011`; those are screening data, not
three-trial production evidence.

## Fixed-parameter production comparison

Control is commit `572165d6661c4a000e616fdd1a0241b517539d8c`, public
RaBitQ NONE policy. Candidate is the three production source changes in this
commit. Same tool and input manifests, GIST960/Cohere768 10k base and 600
observed queries, k=10, graph degree 16, build ef=128, query ef=512, CPU 0,
single BLAS/OpenMP thread. Three sequential alternating pairs per dataset,
30,000 real changed-value replacements per builder (90,000 Update/Remove/Add calls).
Every builder saves and natively reloads its snapshot. Initial ordered neighbors
and initial recall were identical within each pair; post-CRUD topology is meant
to differ. Each number below is the median of three independent runs.

| Dataset | Recall@10 control / candidate | CRUD ms control / candidate | Query P50 us control / candidate | Query P99 us control / candidate |
| --- | ---: | ---: | ---: | ---: |
| GIST960 | 0.811167 / 0.927000 | 26811.076 / 29440.616 (+9.81%) | 480.697 / 546.735 (+13.74%) | 580.716 / 677.742 (+16.71%) |
| Cohere768 | 0.908167 / 0.958833 | 23993.003 / 25696.767 (+7.10%) | 458.658 / 514.056 (+12.08%) | 548.416 / 598.073 (+9.05%) |

| Dataset | Initial recall both | Snapshot bytes both | Whole-process peak KiB control / candidate | Build ms control / candidate |
| --- | ---: | ---: | ---: | ---: |
| GIST960 | 0.961000 | 11284416 | 219444 / 219468 | 1738.880 / 1757.636 |
| Cohere768 | 0.983500 | 9363552 | 176648 / 176692 | 1619.601 / 1677.933 |

The change clears the two recall targets at fixed parameters but does not improve
query latency or memory. The small Save/Load differences in `rows.json` are
uncontrolled warm-cache timings, not a demonstrated loading improvement.
Peak includes the whole builder process and input preparation. Snapshot bytes
are exactly equal. This is Lite versus its prior Lite revision, not Full VSAG.

## Query budget study

The same production library was run under each query budget. At ef=384,
three independent runs per dataset gave identical recall. The first is in
`rabitq-diversity-ef-sweep-20261011`; two repeats are in
`rabitq-diversity-ef384-repeat-20261011`. At ef=256 only one screening run
was made, since both recalls failed the targets.

| Dataset | Query ef | Recall@10 | Query P50 us median | Query P99 us median |
| --- | ---: | ---: | ---: | ---: |
| GIST960 | 384 | 0.910167 | 420.578 | 524.026 |
| Cohere768 | 384 | 0.950833 | 372.231 | 463.208 |
| GIST960 | 256 | 0.877167 | 279.892 | 330.852 |
| Cohere768 | 256 | 0.935167 | 266.102 | 312.461 |

For this exact data and three-round CRUD workload, ef=384 is a useful
configuration: recall remains above 0.90/0.95 and P50 is 12.51%/18.84%
below the old Lite ef=512 medians. This cross-configuration observation
does not replace the fixed-parameter comparison. Cohere has only 0.000833
recall margin above 0.95, so it is not a general default recommendation.

## Verification and replay

Release 6/6, ASan/UBSan 5/5, RaBitQ-off 4/4, and coverage-build 5/5 passed.
Clang-format-15, clang-tidy-15 and `git diff --check` passed. Scoped production
RaBitQ source line coverage was 1779/1825 = 97.5%. The new unit test checks
one-bit distances and masked tails at dimensions 1, 7, 8, 9 and 17.

`run-host.py` is the paired production replay. It pins the old control commit
and refuses to overwrite an existing `rows.json`; copy it to a fresh result
directory on the same host, build the candidate source, then run it from the
repository root. The script requires the existing cached source datasets and
`lite/benchmark/results/query-selection-expanded-20261009/raw.tar.gz`.
`identity.json` records source/object/library hashes and compile/link commands.
`raw.tar.gz` contains input receipts, ground-truth files, ordered neighbors,
query latencies, operation CSVs, logs, commands, and measured source copies.
`members.json` checks individual archived files. The two ef scripts likewise
record their commands, stdout, latency CSVs, and snapshot hashes.

The /dev/shm snapshots were verified by native Load and SHA, then removed by
the benchmark driver; original datasets and raw results remain. These runs do
not establish 100k changed-value CRUD behavior, long-run fragmentation, true
cold I/O, or a current Lite versus native Full VSAG package/load/memory win.
Those remain project acceptance work. The production branch is experimental;
PR #2904/#2926 are not updated by this result.
