# Direction-aware refill candidate, 2026-10-07

An isolated FP32 repair candidate improves full-churn recall in three10k datasets,
including300 independently reserved Cohere queries. It remains an experimental
patch: independent Cohere recall .948 is below .95, and larger-scale and mixed
workload costs remain unverified. The active library was restored to parent
`a7313cd`; no default adoption or complete acceptance is claimed.

## Source evidence and minimal change

Lite `GraphBackend::repair` preserves valid old links and fills gaps from the
removed/updated node's old outgoing candidates, ordered only by source distance.
Full `src/impl/pruning_strategy.cpp::select_edges_by_heuristic` accepts candidates
when alpha*pairwise distance is not below source distance. The isolated macro
`VSAG_LITE_EXPERIMENT_DIVERSE_REPAIR` applies alpha1 only to FP32 repair refill:
retain all existing links; prefer candidates not occluded by those links or newly
accepted candidates; fill any remaining gap from rejected candidates by original
distance order. Degree and candidate pool remain unchanged. This is a bounded
refill adaptation, not Full's complete graph algorithm or proof of route redundancy.

Initial Add/link/search/entries/ring/tie behavior, FP16, SIMD, snapshot/API/CMake
options and query budgets are unchanged. Additional pairwise distances can raise
maintenance cost. The archived patch and full prototype sources make this candidate
reviewable and reapplicable; neither production source nor tests retain it.

## Fixed protocol and results

Degree16, construction/maintenance/query ef128, diversity-nearest OFF, FP32
squared L2, Top10, CPU0, same public quality runner and explicit library paths.
One full-churn round applies10,000 same-value Update/Remove/Add cycles, with
all live IDs/vectors restored by the end. Primary Cohere uses normalized768d;
SIFT128d and GIST960d retain their existing prepared10k subset ground truth.
Three fresh-process primary repetitions alternate variant/order. Cross-dataset
runs are single-process observations, not replicated performance conclusions.

| Data / queries | Initial recall | Baseline after churn | Candidate after churn |
| --- | ---: | ---: | ---: |
| Cohere observed100 | .960 | .940 | .950 |
| Cohere reserved300 | .958333 | .940 | .948 |
| SIFT observed100 | .985 | .979 | .984 |
| GIST observed100 | .916 | .874 | .884 |

Primary build recall and snapshot bytes are identical across both variants and
three repeats. Churn recall is .940/.950 in each repeat. Whole-process CPU
medians4.46/4.54s (+1.8%); candidate sample5.87s is retained, not discarded.
CPU includes input, build, queries, Save/Load and output; mutation CPU is not
isolated. SIFT single churn CPU2.31/2.60s, GIST5.93/5.88s; these single runs do
not support broad cost improvement or statistical performance conclusions.

Cohere rows100–399 were reserved before this candidate (`prior-query-split.json`),
prepared from the same source and normalized base. Source query IDs are disjoint
from observed rows0–99. These300 queries were not used to select/tune the candidate;
they are now observed validation, not a reusable untouched final holdout. Final
reserved rows400–999 remain unused here. No parameter retuning followed results.
Validation gains24/3000 hits:26 queries win,8 lose,266 tie; paired bootstrap95%
mean difference [.002333,.014]. SIFT and GIST paired intervals cross zero.
Intervals/sign tests are descriptive and do not establish cross-distribution
acceptance or account for previous candidate searches.

Seven loaded-snapshot checks verify native/scalar returned ID sets for1,300
query-state pairs. Reference=self makes all eight diagnostic masks identical;
native equality is recorded for mask0 only. Native scalar distance/order equality
is not asserted. No new throughput, concurrent CRUD, changed-vector Update,
100k acceptance or public RaBitQ delivery is implied.

## Verification and reproduction

Candidate CTest3/3, repaired fixture184 assertions, default fixture184 assertions,
final clang-format15/clang-tidy15 pass. Fixtures distinguish independent directions
from collinear fallback, preserve old links/degree, validate reverse adjacency,
no self-links/duplicates/out-of-range edges, and unchanged FP16 behavior.
After archiving/restoring the prototype files, default CTest4/4 passes.
No new sanitizer or coverage result is claimed for the unadopted library patch.

```sh
python3 lite/benchmark/results/diverse-repair-20261007/verify.py
# On a clean matching parent, inspect then apply candidate.patch.
# Configure standalone lite with tests/benchmarks and CMAKE_CXX_FLAGS set to
# -DVSAG_LITE_EXPERIMENT_DIVERSE_REPAIR; leave nearest-diversity OFF.
```

Commands, identities/input hashes, compile flags, raw CSV/log gzip, small truth,
source copies, paired summary and historical host scripts are archived. Large
snapshots/binaries/data stay on the host. The verifier recomputes truth hits and
native receipts; host hash checks report availability explicitly. Host scripts use
absolute paths and historical receipts, not portable replay entry points.

Initial default build used a nonexistent target; tidy missed fixture reserve;
validation setup omitted existing NumPy/PyArrow paths. The first validation summary
expected a nonexistent eligible column after a successful query; it was corrected
using the actual schema and resumed that successful initial receipt. Logs remain.
These are tooling/setup errors, not product errors. Existing dataset python-deps
are supplied via PYTHONPATH; no dependencies changed.

Next test this fixed candidate on100k and mixed read/write workloads, including
mutation CPU/memory, independent queries and changed-vector Update before
production integration. Do not relax the floor or inflate query ef.
