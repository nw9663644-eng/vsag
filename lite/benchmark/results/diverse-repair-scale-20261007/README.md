# 100k changed-update and mixed-workload validation, 2026-10-07

The unchanged [direction-aware refill candidate](../diverse-repair-20261007/README.md)
has small recall gains at100k after10,000 changed-update cycles, with increased
mutation-block CPU. Keep it as an experimental patch, not a default optimization.
No library source, public API, query budget or PR branch is changed here.

## Protocol

Both variants start from the exact same archived100k FP32 snapshot per dataset:
SIFT128d, GIST960d and normalized Cohere768d, degree16, stored/query ef128.
Historical initial snapshots are deliberate controls, not fresh builds of this HEAD.
Binary and library hashes bind the same candidate/baseline used in the10k report;
explicit LD_LIBRARY_PATH and ldd receipts identify each library. CPU affinity is0.
The existing route probe loads the stored graph without rebuilding its topology.

Each cycle chooses a distinct original ID by slot `(i*8191)%100000`, modifies
vector coordinate0 by+.125, restores its original vector, removes it and re-adds
it. Queries occur after the four operations, when all vectors again match original
truth. This exercises real changed Update calls but does not validate retrieval
while a vector remains changed, concurrent mutation or persistent-update truth.
All queries are the existing100 observed queries, reused cyclically; query events
are not additional independent queries. No new holdout is consumed.

Pilot:1,000 cycles (1% live IDs), query every10 cycles, three repeats;
also query every cycle once per variant/dataset. Extended:10,000 cycles (10% IDs),
query every10 cycles, three repeats. There are42 successful fresh processes,
204,000 total cycles /816,000 mutation calls across variants and repetitions,
and25,800 mixed query events. This is not full100k churn or build-time validation.
Order is reversed in the middle replicate. No builds/other experiments overlap.

## Results

At1,000 cycles, final recall is identical in both variants: SIFT .956, GIST .742,
Cohere .892. At10,000 cycles, all three repeats produce the following recalls:

| Data | Post-cycle baseline / candidate | Mixed baseline / candidate | Median mutation CPU ms baseline / candidate | Change |
| --- | --- | --- | --- | ---: |
| SIFT | .948 / .950 | .9521 / .9529 | 5921.464 /6010.654 | +1.51% |
| GIST | .723 / .726 | .7293 / .7312 | 11562.919 /12024.328 | +3.99% |
| Cohere | .897 / .900 | .8924 / .8937 | 10391.814 /10717.489 | +3.13% |

Mutation-block CPU excludes queries but includes scratch-vector preparation,
operation timing and loop bookkeeping; it is not isolated kernel time. Mixed-loop
and query CPU plus P50/P99 samples are recorded separately in `comparison.json`.
Three repetitions do not establish universal/statistically significant performance
changes. Whole-process time/RSS in the extended raw archive includes diagnostic
graph loading, scalar scans, multiple Index instances and serialization buffers;
it is not deployment load-RSS or standalone library memory evidence.

The original10k repair advantage does not translate into a large100k gain here.
There is no established CPU benefit. This does not prove the candidate is useless
or that its cost is unacceptable in every workload, but it does not justify default
adoption. Historical10k .95 targets are not silently redefined for100k.

## Verification and limits

Successful runner exits include size/result-count checks and exact ordered ID and
float-distance equality before/after Save-Load on every final query. Raw samples
permit independent reconstruction of operation medians, mixed P50/P99 and counts;
initial scalar traces match initial native aggregate recall. Post-cycle and mixed
recalls remain runner aggregates: per-query post/mixed IDs are not exported by
this existing runner, so the offline audit cannot recompute those truth hits.
No new sanitizer, unit coverage, concurrency guarantee or Full comparison is claimed.
Production `src/` and `include/` remain unchanged.

```sh
python3 lite/benchmark/results/diverse-repair-scale-20261007/verify.py
```

`pilot/` and `extended/` hold protocols, commands, identities, summaries and raw
hash indexes. Their raw CSV/stdout/stderr files are in corresponding tar.gz archives;
the verifier reads members without extracting paths. All archived hashes, operation
and latency samples, summary medians and available host input hashes are checked.
Snapshot headers confirm100k/degree16/ef128; candidate patch is copied unchanged.
Large input snapshots remain on the host. Host scripts use recorded absolute paths,
not a portable end-to-end reproduction command. No new large snapshots were written,
and no historical data was deleted (host disk was99% full at start).

Next define the quality/cost tradeoff before adoption, add post/mixed per-query
truth evidence and persistent changed-vector validation, then consider complete
100k churn if justified. Keep the remaining final query partition untouched until
candidate selection is frozen; do not inflate ef or relax gates to hide losses.
