# Typed RaBitQ search heaps (2026-10-09)

## Source evidence and minimal change

Baseline is the pushed `a917787ac1953b03ab5e625c12eccea4ce1ea651`
library. The candidate is that commit plus the accompanying
`rabitq_graph_state.h` change. `perf` sampling on GIST 10k showed the coarse
AVX512 filter as the largest self-time consumer, followed by graph traversal,
supplement reranking and heap maintenance. The old heap declarations stored
`better` and `farther` as function pointers, so standard heap operations could
not inline those tiny tie-aware comparisons.

The candidate replaces only those function-pointer comparator types with empty
`Better` and `Farther` function objects. It does not change the distance
formula, query transform, graph traversal budget, graph topology, tie rules,
encoding, public API or snapshot format. The external-ID ranking comparator is
capturing and remains unchanged. Batch traversal, Batch4 filtering, degree/ef
tuning and Full VSAG comparison are intentionally excluded from this commit.

## Fixed real-data comparison

Release GCC 11.4, taskset CPU0, RABITQ8, degree 16, ef 128, 10,000 base
vectors, 100 historical queries, k=10, no CRUD rounds. Three alternating
fresh-process trials were run per dataset and version. Cells below are medians
of three runs. Page cache is uncontrolled; this is not a cold-load experiment.

| Dataset | P50 baseline -> candidate (us) | P99 baseline -> candidate (us) | P50 change | Recall |
| --- | ---: | ---: | ---: | ---: |
| SIFT | 139.128 -> 113.987 | 217.105 -> 187.016 | -18.1% | 0.978 |
| GIST | 249.623 -> 231.075 | 433.890 -> 401.251 | -7.4% | 0.914 |
| Cohere | 258.304 -> 228.555 | 385.851 -> 348.292 | -11.5% | 0.961 |

All nine paired query CSV files are byte-identical, including returned IDs,
rank order and distances. Recall and snapshot bytes are unchanged. This is an
old-Lite versus modified-Lite comparison, not a Full VSAG comparison, and it
does not show that RaBitQ is faster than FP16 or FP32.

`identity.json` pins the source head, source-diff digest, benchmark, measured
libraries and inputs. `rows.json` contains every process result;
`neighbor-audit.json` records pairwise output hashes; `raw.tar.gz` contains
stdout, stderr, argv and every query row. `SHA256SUMS` covers the archive and
derived evidence.

## Validation

Release tests passed 5/5. ASan+UBSan with leak detection passed 5/5. A fresh
coverage run additionally included the quantization probe self-test and passed
6/6. Scoped line coverage was 1114/1152 (96.7%): `rabitq_graph_state.h`
736/768 (95.8%), `rabitq_codec.h` 303/308 (98.4%), and
`rabitq_compute.h` 75/76 (98.7%). `clang-format-15 --dry-run --Werror`,
`git diff --check`, and `clang-tidy-15` on `rabitq_backend.cpp` passed.

## Next decision

After removing indirect heap comparisons, the coarse 3-bit AVX512 filter is
still the largest sampled hotspot. Full VSAG has a Batch4 lower-bound path, but
Lite's graph walk is dynamically scheduled, so adopting it requires an explicit
candidate batching and ordering design rather than a direct call substitution.
That design and an aligned Lite-versus-Full comparison belong in later commits.
