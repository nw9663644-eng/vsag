# CPU0 build and maintenance diagnostic, 2026-10-07

Source parent d8e12eccb93152561d9ae856283bf9add821ce41; no library or API edits.
Cohere10k/768dim normalized FP32, existing 100 observed pilot queries, L2 Top10,
degree16 and construction/maintenance/query128. Same source dataset, two existing
Release libraries (default OFF/diversity ON). CPU0. Sampling199Hz cpu-clock:u,
DWARF8192; two fresh processes per mode/flow, reversed mode/flow order on repeat.
Eight recordings, 7944 exported samples; zero lost samples reported in all eight.

## Workload and quality boundary

Build flow stages vectors in BruteForce, then BuildGraph, query and Save/Load.
CRUD flow additionally visits every original ID once using (i*8191)%10000,
performing same-vector Update, Remove and Add original: 10000 cycles/30000 calls.
The multiplier is coprime to10000, so this is 100% distinct-ID churn, not the
previous 1%100k protocol. No concurrent reader or changed-vector displacement.
All operation success/live-count and exact post-roundtrip query checks pass.
Content is restored but topology can change. The same observed queries are used
for quality regression, not fresh blind selection.

| Mode | Build-only Recall@10 | After100%churn Recall@10 | Interpretation |
|---|---:|---:|---|
| default | 0.960 | 0.933 | Below0.95 floor used in prior Cohere studies; needs quality diagnosis |
| diversity | 0.982 | 0.960 | Higher retained recall with additional maintenance cost |

Both sampling repetitions and the separate stat runs reproduce these values.
This diagnostic protocol did not predeclare a new acceptance gate. The0.933
finding is negative evidence, not a change to prior studies' passes. Do not
promote diversity by CPU alone or claim long-run quality stable for default.
The benchmark verifies its 100 returned query sequences after reload, not every
possible query. Input+data consistency is checked through existing API checks;
recall below1 is expected for ANN, but the observed degradation requires follow-up.

## Conditional stack attribution

Samples with BuildGraph frames are classified first, then Update/Remove/graph Add,
flat staging, query, other. A graph Add below BuildGraph remains build; other Add
is reinsertion. This avoids counting construction insertion as online Add twice.
The first exported frame is self cost, ancestors give API-path membership.
Percentages below are conditional on identified phase samples, not isolated wall
time or exact function duration. Inlining, missing/truncated unwinds and sampling
variance can misattribute frames; unclassified samples stay Other. Kernel CPU is
excluded from cpu-clock:u. Remove/query have few samples; do not rank their internals.

| Mode | API path | Samples across two flows/two repeats | Distance self share |
|---|---|---:|---:|
| default | BuildGraph | 1515 | 51.29% |
| default | Update | 1170 | 52.14% |
| default | GraphAdd | 822 | 52.07% |
| default | Remove | 45 | 26.67% |
| diverse | BuildGraph | 1730 | 50.87% |
| diverse | Update | 1294 | 55.49% |
| diverse | GraphAdd | 973 | 52.72% |
| diverse | Remove | 39 | 23.08% |

The AVX512 distance kernel is the largest self hotspot in build/update/reinsert.
SearchImpl's visit lambda, heap adjustment, closer/farther comparison also appear
among leading symbols. Distance dominance does not prove SIMD arithmetic is the
bottleneck: random vector fetches and candidate count contribute to that kernel's
sample time. Cache-miss events alone cannot attribute stalls or prove memory bandwidth.
Full symbols and call chains are in self reports and losslessly compressed stack exports.

## Separate counter runs

One fresh process per mode/flow with perf stat (not simultaneous with sampling).
These counters cover whole process: input IO, staging, build, optional CRUD, query,
save/load and teardown. Hardware counters include user/kernel by default. No
isolated phase CPU ratio or repeated-run performance estimate is claimed.

| Run | Task-clock ms | Cycles | Instructions | IPC | CPUs utilized |
|---|---:|---:|---:|---:|---:|
| default-build-stat | 2094.85 | 7740825124 | 12995189311 | 1.68 | 0.998 |
| default-crud-stat | 7023.40 | 25935246452 | 36543050004 | 1.41 | 0.999 |
| diverse-build-stat | 2454.46 | 9070767236 | 14014569363 | 1.55 | 0.999 |
| diverse-crud-stat | 7925.36 | 29249057180 | 39759106133 | 1.36 | 1.000 |

Selected programs use approximately one CPU (0.998..1.000); this confirms CPU0
single-core saturation for this workload, not an all-system CPU-use claim.
Generic cache-misses, faults, context switches/migrations and PMU running percent
are retained raw; reported running percentages are100%. Startup before taskset
can contribute a migration, so zero migrations is not claimed. Cloud PMU semantics
and frequency are platform-specific; IPC is descriptive, not a cross-host score.

## Source evidence and next minimal change

GraphBackend::nearest calls Search, requests up to max(4*count, ef_search), then
retains/prunes candidates. Add/Update install neighbors through link; link prunes
bounded lists and maintains incoming edges. SearchImpl computes distance once per
visited slot and uses priority queues with function-pointer closer/farther comparators.
Therefore the next low-risk candidate is typed/inlinable comparator dispatch with
unchanged ordering/tie semantics, measured before/after. It must pass exact output
and snapshot equivalence, filter/FP16/SIMD/error/CRUD regressions, sanitizer and
same-config quality checks. It is a hypothesis; no such optimization is made here.
Do not lower maintenance/query budget to manufacture CPU gains. Full-delete/source
semantics, serialization and concurrency are outside this diagnostic change.

Separately investigate100%churn quality on default at fixed query budgets and a
new held-out set before adopting topology repair. This study uses10k only; confirm
hotspots at100k and another distribution before broad architecture changes.

## Reproduction and evidence

run.py/stat.py use recorded absolute paths and NEW output prefixes; do not overwrite
original evidence. They execute perf via sudo because perf_event_paranoid remains4.
The kernel-specific Ubuntu perf tools were missing and installed; no system-wide
perf security setting, library flags or CPU frequency governor was changed.
Raw perf.data/snapshots stay in /home/ubuntu/project/vsag-lite-cpu-profile-20261007;
exports are gzip-lossless, raw hashes separate from publication-normalized text.
Provenance binds actual binaries/libraries/source/data and original perf.data.
The first analyzer check failed because perf report abbreviates sample counts to1K;
it was corrected to check exact counts in record stderr, without changing recordings.

verify.py re-derives stack attribution from compressed exports, checks samples,
commands, quality fields, counter statistics and manifest hashes. No new C++ test,
coverage, sanitizer or global optimum claim: library code did not change. Existing
benchmark API/count/roundtrip checks ran in all12 successful processes.
Only personal branch is published; PR #2904 and #2926 remain unchanged.
