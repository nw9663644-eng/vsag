# Full physical-delete correctness diagnostic (2026-10-06)
> Follow-up: the prior physical-delete profile omitted `use_reverse_edges`. The 2026-10-06 full-reverse report records the corrected configuration and control tests. These historical failures remain valid for the explicitly recorded reverse-edges-OFF profile; they are not evidence that Full with reverse edges enabled has the same defect.

This diagnostic blocks treating the currently installed Full physical-delete
profile as a valid matched-quality CRUD performance reference. It does not
establish a defect in the latest upstream VSAG or in the Lite library.

## Findings

The prior six restored-data CRUD runs had two short query events per cadence-1
run. At cycles 711 and 889, the respective queried Cohere rows 110 and 288 returned
one neighbor instead of ten. The new opt-in diagnostic retries the same query on
the same live graph, without intervening mutations, at ef_search 128, 512 and
100000. Both events still return one neighbor and zero Top-10 truth hits at every
budget. The returned IDs 15610 and 73608 equal the ID removed and readded in that
cycle. Raising the search budget is not a remedy for these observed events.
A graph routing/reachability problem is an inference; its exact connection to
the deletion crash below is not proven.

A separate tiny API reproducer uses 8 one-hot FP32 vectors of dimension 16:

| Operation before query | Repeats | Outcome |
|---|---:|---|
| Remove ID 0 physically | 3 | All SIGSEGV (-11) |
| Update/restore ID 0, then physically remove it | 3 | All SIGSEGV (-11) |
| Physically remove last ID 7 | 3 | All exit 0 |
| Physically remove ID 0, then add its original vector | 3 | All exit 0 |

The failing query requests k=1 at ef_search=128. There is no concurrent use and
no caller pointer lifetime change. The delete API returned success and the live
count was seven. GDB observed the search distance batch's neighbor slots
{1,3,7,6,2,5}; slot 7 is invalid after compaction to seven vectors. Its code
pointer was null, causing an AVX512 FP32 batch distance dereference. This
isolates a stale-slot symptom after non-last physical deletion. The exact faulty
repair statement has not yet been established; switching ISA would not repair
an invalid graph slot. No Full library fix is included in this change.

## Source evidence

- include/vsag/index.h: explicit FORCE_REMOVE is a supported API mode.
- src/algorithm/hgraph/hgraph_modify.cpp: force_remove_one repairs graph edges,
  moves the last slot into the removed slot, reduces total_count, and the caller
  shrinks data storage. Full UpdateVector(force=true) does not rewire like Lite.
- src/datacell/graph_datacell.h: GraphDataCell::Move updates adjacency and reverse
  edges; SparseGraphDataCell implements upper-layer Move separately.
- src/algorithm/hgraph/hgraph_search.cpp: SearchWithRequest selects the route
  entry then searches the bottom graph with max(ef_search,k).
- minimal-gdb.log: FlattenDataCell query / BasicSearcher / HGraph search leads to
  ComputeBatch4Impl at compute_batch4.h:87 with null codes3.

The shared library is the same previously measured cached incremental d18c82a
build. This is not a clean rebuild or a latest-main audit. Provenance hashes
bind the actual shared library, final diagnostic runner, minimal reproducer,
source and original data. Tiny vectors are generated in the reproducer itself.

## Run

The existing runner retains legacy and mixed CLI behavior. Optional trailing
`diagnose` is restricted to the existing FP32 mixed protocol:

```sh
full_rabitq_dataset_benchmark DATASET SNAPSHOT fp32 128 1 1000 1 diagnose
```

The .diagnostic.csv records cycle, query row, retry budget, returned count, hits
and first external ID. Diagnostics add extra queries within the mixed loop:
**neither whole-loop CPU nor timing from this run is a performance comparison**.
A stderr marker makes this limitation explicit. Normal non-diagnostic runs do
not execute these retries. Existing recall denominator and quality floor remain
unchanged. API errors still fail; no silent fallback to marked deletion occurs.

Compile the standalone deletion probe against the exact recorded installation:

```sh
c++ -g -O0 -Wall -Wextra -Wpedantic -std=c++17 \
  -isystem /home/ubuntu/project/vsag-full-known-install-20261006/include \
  delete_reproducer.cpp \
  -Wl,-rpath,/home/ubuntu/project/vsag-full-known-install-20261006/lib \
  /home/ubuntu/project/vsag-full-known-install-20261006/lib/libvsag.so.0.0.0 \
  -o delete_reproducer
./delete_reproducer remove
./delete_reproducer last-remove
./delete_reproducer restored
gdb -batch -ex run -ex bt -ex 'frame 4' -ex 'p id_count' -ex 'p *idx@6' \
  --args ./delete_reproducer remove
```

controls.py records process return codes and preserves all twelve outputs. The
script disables new core files for its subprocesses. GDB exit 0 alone does not
mean the inferior succeeded: the retained signal and stack establish its crash.

## Validation and next action

test_full_mixed.py passes both cadences, all four successful restored-data API
operations, live counts, raw hit/percentile accounting, old CLI behavior,
diagnostic output and eight invalid CLI combinations. clang-format-15 and
clang-tidy-15 pass for the final runner; the reproducer is formatted and compiled
with strict warnings. This is not Full sanitizer coverage or whole-repository
coverage. The exploratory phase-query runner also crashed on tiny and Cohere
inputs; its logs are retained, but that unsafe stage-query mode was removed from
the final benchmark. Only same-restored-state budget retries remain.

Next: confirm compaction/edge repair in an isolated Full diagnostic build before
using physical-delete results for acceptance. Do not spend more time calibrating
on final Cohere queries or declare equal-quality speedup. Use existing valid
Lite CRUD results and independently valid Full query/load evidence in the project
report, clearly labeling Full physical-delete comparison as blocked by this
correctness finding. No issue/comment/PR update is published by this task.

Only the personal experiment/lite-rabitq-next-20260926 branch is updated.
PR #2904 and #2926 source branches remain frozen.
