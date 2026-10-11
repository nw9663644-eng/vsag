# Current Lite / pinned native Full acceptance, 2026-10-11

Measured clean Lite source HEAD3298616bac68c631796d61d2f13c39e7311fe33f, production a492b6f. Native Full HGraph is the existing installed incremental shared rebuild at d18c82a1f1f23ff84362516e86af5f3cb2e34475; library SHA9aeaa550703f116bef2959769d4f2f03da254b07c906ba941d8186224cc70c72. All matching installed header hashes were rechecked before measurement. Full runner hashes are recorded in provenance.json. This is native Full, not old Lite, but NOT a latest-upstream fresh build. Existing native runners are reused; no new Full build/test claim.

## Protocol

SIFT128/GIST960/normalized Cohere768,10000 base rows,600 observed queries from source rows[400,1000),k10. GIST/Cohere base/query/truth SHA exactly match the previous expanded experiment. SIFT uses the existing preparation script to recompute exhaustive squared-L2 truth for its selected10k base prefix. Not blind holdout. Source documents and historical tests describe the normalizations and FP32/FP64 truth limits.

Degree16/build128/CPU0/BLAS-OMP-MKL1. Full small profile uses memory_io/compressed graph/no redundant raw floating copy, RaBitQ3+5/FHT. Lite ef512 versus Full128 follows the frozen previous comparison: NOT equal budget or exact-equal recall. Both use SIMD on the same host, but selected instructions/rotations/topology/ordering are not identical. Three alternating fresh-process pairs per cell, three fresh loaders per builder:54 builders,162 loaders. No query warmup; warm uncontrolled page cache, not cold I/O. No compilation or tests concurrent with timed runs. Zero-round CRUD: this measures initial-index build/query/Save/Load, not mutation throughput.

## Current results

Values are medians, Full / Lite. Full randomized RaBitQ recall varies across trials; inspect raw rows rather than selecting the best run.

| Dataset/storage | Recall@10 Full/Lite | P50 us Full/Lite | P99 us Full/Lite | Warm Load ms Full/Lite | Loaded total RSS KiB Full/Lite |
| --- | ---: | ---: | ---: | ---: | ---: |
| SIFT/fp32 | .975833/.997500 | 101.168/179.876 | 129.657/229.834 | 5.460/3.876 | 32792/12512 |
| SIFT/fp16 | .975833/.997500 | 99.098/175.045 | 120.428/215.044 | 3.896/3.205 | 30296/10100 |
| SIFT/rabitq8 | .965833/.992167 | 124.947/221.495 | 152.906/293.924 | 2.984/4.432 | 29768/8480 |
| GIST/fp32 | .971000/.965500 | 228.754/640.474 | 269.954/788.971 | 28.103/16.598 | 66036/45116 |
| GIST/fp16 | .970667/.965500 | 185.136/478.488 | 216.866/625.675 | 15.626/10.543 | 46820/26320 |
| GIST/rabitq8 | .967000/.961000 | 206.014/514.677 | 263.992/680.253 | 9.669/7.663 | 38088/16628 |
| Cohere/fp32 | .981333/.987333 | 213.963/634.125 | 250.993/723.671 | 23.918/14.130 | 58384/37612 |
| Cohere/fp16 | .981167/.987000 | 176.255/451.840 | 209.554/549.106 | 13.434/9.081 | 43104/22616 |
| Cohere/rabitq8 | .978500/.983500 | 197.964/480.107 | 245.394/629.573 | 8.506/6.804 | 36208/14760 |

All nine Lite query P50/P99 cells are slower. The P50 ratio is1.77-2.96x, but recall is different, so these are not strict same-quality speed ratios. No universal query victory is established. Lite loads faster in8/9 cells; SIFT RaBitQ remains slower. Loaded total RSS is smaller in all9, with a Full before-load baseline near25MiB versus Lite3.6MiB. Incremental index RSS must be read separately; do not assign the entire reduction to index layout.

| Dataset/storage | Build ms Full/Lite | Whole builder peak KiB Full/Lite | Snapshot bytes Full/Lite | Save ms Full/Lite |
| --- | ---: | ---: | ---: | ---: |
| SIFT/fp32 | 828.544/569.074 | 42500/27864 | 5766017/6560064 | 3.398/4.382 |
| SIFT/fp16 | 829.502/552.344 | 37528/22872 | 3144565/4000064 | 2.831/13.161 |
| SIFT/rabitq8 | 942.186/633.927 | 37816/21896 | 2203618/2960672 | 2.201/3.438 |
| GIST/fp32 | 1782.274/1536.745 | 111056/127644 | 39808753/39840064 | 14.210/16.739 |
| GIST/fp16 | 1609.817/1421.431 | 88800/105788 | 20148057/20640064 | 8.480/40.773 |
| GIST/rabitq8 | 1470.533/1849.817 | 102920/105696 | 10691074/11284416 | 5.404/6.268 |
| Cohere/fp32 | 1705.426/1466.238 | 95124/104528 | 31957337/32160064 | 11.282/14.889 |
| Cohere/fp16 | 1701.127/1346.881 | 76320/85880 | 16228737/16800064 | 6.893/36.004 |
| Cohere/rabitq8 | 1534.054/1764.078 | 87376/85480 | 8737006/9363552 | 4.783/5.813 |

Whole builder peak includes input buffers and Save/Load verification; not an isolated index-stage peak. Lite snapshots and Save time are worse in every cell. Lite FP16 Save is a clear optimization target. This does not establish its exact bottleneck; inspect conversion/buffering and validation before changing code. High-dimensional build peak is still unfavorable except Cohere RaBitQ in this cohort. Improvements versus older Lite must not be inferred from this Full comparison.

## Runtime footprint

Current stripped DT_NEEDED shared-library closure: Lite6123112bytes, Full98428088bytes,93.7791% reduction. Copies only were stripped using the same strip command; source ELFs are unmodified. Recursive closure counts each resolved realpath once, including common runtime libraries/loader; excludes executables, headers, dlopen plugins, Python wheels, containers, data and snapshots. It is NOT a complete deployment package. elf/closure.json records library hashes, resolutions and per-file accounting. Closure was measured after all timing completed.

## Evidence, replay and boundaries

run-current-full.py prepares temporary RAM inputs and runs the existing paired driver in one SSH session, refuses an existing result directory, checks reference library/header hashes and matching GIST/Cohere inputs. It records current runner hashes. identity.json pins Lite library/driver/builder/loader and all command arguments; provenance.json pins the existing Full and describes its build boundary. Its new_tests field was recorded before the subsequent independent audit; audit.json provides completed audit status.

raw.tar.gz retains1041 generated records with members.json hashes, including command/stdout/stderr/peak, configuration, ordered IDs/distances, per-query times, prepared queries/truth and input hashes. Original uncompressed records stay on server; no old sources/data/results were deleted. Only newly created temporary RAM directories are cleaned automatically. Stored snapshot hashes are provenance, not retained snapshot bytes; native builders perform ordered Save/Load checks during their runs.

Run `python3 verify.py PATH_TO_THIS_DIRECTORY`. Archive-member hashes,32400 truth intersections,324000 neighbors, raw quantiles,54 builder medians and162 loader records pass. The verifier does not rerun exhaustive groundtruth or Full tests. Production C++ is unchanged this turn; Release6/SAN8/Cov-build6 evidence is inherited from a492b6f, not new tests/coverage.600 observed queries and3 trials are not robust production-tail statistics.

Current acceptance conclusion: deployment footprint and loaded total memory advantages are supported for this native reference; most warm loads improve. Query/Save/snapshot/build-peak advantages are not universal. Latest fresh native Full,100k aligned repeat matrix, interleaved changed-value CRUD, quality-floor selection and full deployment-package closure remain incomplete. PR2904/2926 were not updated. Next minimal code investigation: FP16 Save conversion/buffering, while preserving byte compatibility, finite-value checks and stream-error behavior.
