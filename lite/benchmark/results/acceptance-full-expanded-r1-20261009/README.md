# Expanded performance acceptance: current Lite versus pinned native Full

Lite source3f27573a7a45ee6f44bb8f3b53cb55b601fc3cc1 (query prefetch + borrowed construction). Native Full HGraph source d18c82a1f1f23ff84362516e86af5f3cb2e34475; exact shared-library SHA9aeaa550703f116bef2959769d4f2f03da254b07c906ba941d8186224cc70c72. This is a native reference, NOT old Lite, but remains an installed incremental rebuild, NOT a fresh latest-upstream build. Native runners are rebuilt from the current benchmark source against matching installed headers; source/header/binary hashes are recorded.

Degree16/construction128, explicit single construction/BLAS/OMP/MKL thread, CPU0. Native small profile: memory_io, compressed graph, no redundant floating raw copy; RaBitQ3+5/FHT. Both support AVX2/AVX512 on this recorded EPYC, but selected kernels/rotations/topology/numerical ordering are not identical. Three alternating process pairs per cell, three fresh-loader processes per builder, query k10, no warmup, warm uncontrolled page cache. Lite ef512 versus Full128 was frozen from prior similar-quality diagnostics: NOT same-budget or exact-equal-recall.

Each dataset uses600 source queries[400,1000), six times the old100-query cohort, with exact squared-L2 truth recomputed for its10k base prefix. Cohere is normalized as documented; all600 cosine/L2 TopK rounding audits agree. Parts of these query ranges were previously observed in other diagnostics: NOT blind holdout or a new distribution. No parameters were selected after inspecting this cohort.

| Dataset/storage | Recall Full/Lite | P50 Full/Lite us | P99 Full/Lite us |
| --- | --- | --- | --- |
| cohere10k600/fp16 | 0.981167/0.987000 | 155.617/429.661 | 180.346/488.159 |
| cohere10k600/fp32 | 0.981333/0.987333 | 172.977/518.128 | 202.706/627.476 |
| cohere10k600/rabitq8 | 0.979833/0.983500 | 186.836/470.380 | 227.016/592.008 |
| gist10k600/fp16 | 0.970667/0.965500 | 171.126/475.530 | 204.865/586.687 |
| gist10k600/fp32 | 0.971000/0.965500 | 182.787/569.727 | 223.625/722.625 |
| gist10k600/rabitq8 | 0.966833/0.961000 | 194.095/510.109 | 248.275/639.615 |

| Dataset/storage | Warm load Full/Lite ms | Loaded total RSS Full/Lite KiB | Build peak Full/Lite KiB | Snapshot Full/Lite bytes |
| --- | --- | --- | --- | --- |
| cohere10k600/fp16 | 13.391/8.446 | 42968/22624 | 76208/85852 | 16228737/16800064 |
| cohere10k600/fp32 | 23.886/14.013 | 58384/37576 | 94996/109176 | 31957337/32160064 |
| cohere10k600/rabitq8 | 8.057/5.350 | 36092/13692 | 84156/85436 | 8737146/9363552 |
| gist10k600/fp16 | 15.905/10.425 | 46812/26320 | 88496/105732 | 20148057/20640064 |
| gist10k600/fp32 | 29.291/16.756 | 66052/45152 | 110992/132120 | 39808753/39840064 |
| gist10k600/rabitq8 | 9.496/5.991 | 38056/15672 | 102900/105720 | 10690914/11284416 |

## Findings and failed gates

Lite warm loading and total loaded RSS are smaller in all six cells. However Lite P50 is2.52-3.12x native Full, and P99 is also worse. GIST Lite Recall is0.52-0.58 percentage points below Full; Cohere Lite is0.37-0.60 points above Full. No exact-equal-quality query victory is established. Native RaBitQ rotation randomness varies trial recall; all raw rows are preserved. Three trials and600 queries still do not establish production-tail statistics.

Loaded total RSS includes a Full baseline near25MiB versus Lite near3.6MiB. Inspect before-load and incremental RSS in rows: do not attribute the whole reduction to vector layout. Build peak is still higher for Lite in every cell; source staging and rollback-safe source retention remain structural optimization targets. Lite snapshots are larger in every cell, especially RaBitQ. This validates some footprint/load advantages, NOT complete performance acceptance.

Only zero-round CRUD was used. Existing whole-vector golden tests are not a long-lasting persistent CRUD benchmark; mutation throughput, long changed-value quality,100k final quality, cold I/O and latest fresh Full remain outstanding. No C++ production code or PR2904/2926 changed during this experiment.

## Runtime ELF footprint

Identical strip --strip-unneeded on scratch copies only:
- Lite root: 310768 bytes; recursive closure: 6098448 bytes.
- Full root: 40463344 bytes; recursive closure: 98428088 bytes.
- Closure reduction: 93.8042%.

Closure counts each resolved realpath once, including common system runtime libraries and the loader. It is the DT_NEEDED shared-library closure, NOT a wheel/container/SDK, executable set, dlopen plugin inventory or general distributable package. No source ELF was stripped/modified, and no OS/Full/Lite binaries are committed. closure.json retains ldd resolution, raw/stripped byte counts and hashes for every file. measure_elf_closure.py reproduces it; fixtures test missing-dependency rejection, paths with spaces, cycles/deduplication and copy-only stripping.

## Evidence and reproduction

identity.json records exact driver arguments, input/library/runner hashes and clean source HEAD. provenance.json records installed headers and limitations. preparation-and-run.txt contains the actual commands. Prepared queries/truth/manifests and source ID mappings are archived; original full base sources remain on server with hashes. The first attempt lost RAM inputs between SSH sessions before any builder ran; its identity and preparation logs are retained separately. Successful regenerated inputs and all benchmarks ran in one SSH session, with prepared metadata copied to durable storage first.

raw.tar.gz retains commands/stdout/stderr/peak RSS/configuration/ordered neighbors/per-query timings, prepared query/truth/manifest data and validation logs. Native Full/Lite snapshots differ and must NOT be compared byte-for-byte or required to produce identical neighbors. Each builder independently requires exact ordered Save/Load search equality; scratch snapshots are cleaned by the existing driver, so offline audit verifies recorded SHA, not a fresh snapshot byte reread.

Run python3 lite/benchmark/results/acceptance-full-expanded-r1-20261009/verify.py: artifact/tar hashes,21600 truth intersections across36builders, raw P50/P99 and medians,108 load records and ELF accounting. It does not rerun exhaustive groundtruth or strip binaries offline. Rerun inputs and timing using the recorded commands, scripts and pinned source libraries. The ELF script requires trusted native ELFs, ldd/strip and a new output directory. Python fixtures and native query-budget fixtures pass; inherited C++ test results are from unchanged3f27573, not a new Full suite or new coverage run.

Next code work should address query cost and build staging ownership without lowering recall, with the same frozen600-query reference retained as observed regression data. Keep a separate untouched cohort for any future blind quality claim.
