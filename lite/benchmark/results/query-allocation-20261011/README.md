# Public Lite query allocation diagnostic, 2026-10-11

Production source/library remains f4abfa098d3df3ed9ff7279077900d38a602be9d; no src/include modification. This closes a missing diagnostic, not a new product speedup or whole-project acceptance. Earlier RaBitQ stage/typed-heap/admission/prefetch optimizations are not repeated here.

## Measurement

CPU0/thread1, initial graphs, FP16/RaBitQ8, degree16/build128/query512/k10,100 existing source queries. Three datasets at10k plus GIST100k:8cells/800 queries. One warmup pass per loaded index. Instrumented public SearchWithOptions counts ordinary C++ new/new[] requests on the calling thread, with exported executable allocation symbols; output and loading are outside the recording interval. No latency claim: instrumentation and allocator replacement perturb execution. Does not capture direct malloc/calloc, aligned new, other threads, frees, peak/live bytes or all OS allocation traffic. Requested cumulative bytes are NOT RSS or persistent memory.

| Dataset | FP16 median requests / bytes per query | RaBitQ median requests / bytes per query |
| --- | ---: | ---: |
| SIFT10k | 25 / 75920 | 31 / 76832 |
| GIST10k | 25 / 77584 | 31 / 80160 |
| Cohere10k normalized | 25 / 77200 | 31 / 79392 |
| GIST100k | 25 / 167584 | 31 / 170160 |

Every query has exactly one request equal to the number of indexed rows in bytes. This is consistent with the uint8 visited(Size(),0) in GraphBackend::SearchImpl and RaBitQ graph_search_impl. The same queries/storage at10k→100k add90000 median requested bytes, while request count is unchanged. This identifies allocation scaling, not allocator CPU share or a causal explanation of the Full latency gap.

All800 instrumented queries match the ordinary native builder's8000 ordered IDs and hex distances byte-for-byte; each builder independently performs Save/Load checks. identity.json pins library/source/input SHA and temporary snapshot SHA/size. No new groundtruth is recomputed or new recall improvement claimed. New RAM snapshots are temporary; originals and raw results are preserved.

## Source evidence and next minimal candidate

Native src/impl/searcher/basic_searcher.cpp accepts reusable VisitedList and query computer state. Current Lite creates visited, encoded/transformed query and heap vectors per public query. QueryHeap has no Reserve method. In both GraphBackend and RaBitQ routes, a full best heap still push(next) then pop(), transiently reaching ef+1. At ef512 this can cause vector capacity growth from512→1024. The current request totals are consistent with heap growth, but this probe records sizes/counts, not allocation backtraces; do not assert all remaining bytes are conclusively attributed to heaps.

Next evaluate reserving only the bounded best-heap capacity (ef+1) in isolation, preserving push/pop order and ties, before any persistent workspace ownership change. Keep candidate heap growth unchanged initially; no degree/ef adjustment. Require exact ordered-result/filter/CRUD parity and uninstrumented paired latency across distributions. Working-space reuse would additionally need lifetime, reentrancy, allocation-failure and externally serialized-call semantics validation. Do not assume this candidate is adopted or will improve recall; GIST100k RaBitQ quality remains a separate topology problem.

## Verification and limits

verify.py recomputes8 raw medians, checks800 query counters,8000 ordered neighbors,18 recorded command exits and measured source hash. Probe source formatting uses version15. First source-only tidy15 failed on two unnamed sized-delete parameters; final source only adds unused parameter comments. measured-probe.cpp retains the measured version and its identity hash. The final source-only tidy result is separately retained; it is not a fresh whole-library lint. Production Release/SAN/OFF/coverage evidence is inherited unchanged from f4abfa0, not rerun here. This new diagnostic is not sanitizer-tested and does not satisfy fresh whole-library coverage.

Scripts assume the recorded server paths; rerun into a fresh output directory using run.py and the existing production builder/library, and preserve its exact source/tool identities. Only personal branch is pushed; PR2904/2926 remain unchanged. Full current comparison,100k repetition across all datasets, larger-query tails and interleaved changed-value CRUD remain incomplete.
