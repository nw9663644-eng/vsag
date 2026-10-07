# Two-incoming retention: rejected after full churn

Measured source parent: `1ee9ec8f113e0bd261beb7781686eb4740efe339`.
The prototype is archived here and withdrawn from the library and its unit tests.
Default sources were restored byte-for-byte to the measured parent, rebuilt,
and passed 4/4 CTest cases. This commit adopts no new graph retention policy.

## Source evidence and minimal hypothesis

The preceding [event routing controls](../event-routing-20261007/README.md)
identified a single edge whose loss reduced fixed-budget recall even though its
old target still had one incoming edge. In `GraphBackend::link`, the existing
safe-to-drop check permits removing an old candidate with more than one incoming
edge. This experiment raised that preference to more than two under a private
compile macro. New-target handling, the degree-bound fallback, `ensure_incoming`,
delete layout, entry points, SIMD and query budgets were unchanged. The fallback
can still reduce a node from two incoming edges to one: this is not a global
minimum-incoming invariant. No API or CMake option was added.

## Protocol and results

Cohere normalized 10,000 base vectors, 768 dimensions, FP32 L2, top 10,
100 existing observed queries, degree 16, construction/maintenance/search budget
128, diversity OFF. CPU affinity was core 0. Both variants used the same public
CRUD runner with explicit library binding; `ldd` logs, compile commands and
input/source/library hashes are archived. Three repeats of each build-only and
build-plus-10,000 same-value Update/Remove/Add flow ran in separate processes,
with variant/flow order reversed in the middle repeat. No concurrent builds ran
in the timing interval. Each flow verifies API operations and Save/Load results.

| Flow | Baseline recall | Candidate recall | Baseline CPU median | Candidate CPU median |
| --- | ---: | ---: | ---: | ---: |
| Build only | 0.960 | 0.972 | 2.01 s | 2.08 s |
| Build + 10,000 CRUD cycles | 0.940 | 0.939 | 4.92 s | 5.01 s |

Recall was identical across the three repeats within each cell. CPU is user plus
system time for the whole process, including input staging, queries, persistence
and output; it is not isolated mutation cost. Resolution is 0.01 seconds. These
small descriptive median increases (3.48% and 1.83%) are not a statistical
slowdown claim. There is no demonstrated CPU benefit.

An additional internal mutation trace starts both variants from the exact same
baseline-build-r0 snapshot. Initial checkpoint hits are 960/1000 for both; final
hits are 940/1000 baseline and 942/1000 candidate. Diagnostic queries and edge
scans make this unsuitable for timing comparison. The candidate remains below
the historical Cohere 0.95 quality floor. These queries are observed diagnostics,
not a new holdout or acceptance across SIFT/GIST/Cohere. A one-hit difference
in the primary experiment is not evidence of a general statistical regression.

## Validation and decision

The final four-node fixture checks the specific pruning preference, bounded
degree, reverse-link consistency and search. Both builds pass 28 assertions.
A candidate-compiled test against the old library fails intentionally, proving
the policy difference rather than a baseline product defect. The initial
three-node fixture had an incorrect incoming-count expectation because it
omitted incoming edges from the new node's outgoing row; its failure logs are
retained. It was replaced, not used as evidence of a product bug.

Default CTest passed 4/4 and candidate 3/3 (quantization probe disabled in the
candidate build). clang-format-15 and clang-tidy-15 passed both prototype files.
No new ASan or coverage result is claimed. The library prototype and conditional
test were removed after this negative result; `restoration.json` binds the
restored sources and successful build/tests. Candidate binaries remain only as
host experiment artifacts, not the active default implementation.

Do not adopt this threshold as the default. Next investigate retention of
connections that preserve alternative routes and slot-sensitive maintenance,
then validate a minimal rule with fixed budgets and independent queries before
expanding datasets. Raising an incoming-count threshold alone is unsupported.

## Reproduction and evidence

`run.py` records the primary commands. Apply `candidate.patch` to the measured
parent for an isolated reconstruction; build using the macro flags in
`compile-flags.json` and `configure.log`. `checks.json` records secondary trace
commands. Keep baseline and candidate libraries separate and bind each explicitly.
No binaries, large snapshots or private handoff files are committed. Original
snapshots remain in `/home/ubuntu/project/vsag-lite-two-incoming-20261007`.
`artifacts.json` records original and whitespace-normalized text hashes.
Run `python3 verify.py` to recompute results and audit available host artifacts;
missing host inputs are reported as unavailable, never as verified.
