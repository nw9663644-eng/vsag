# Optimized Lite versus native Full: similar-quality budget diagnostic

Native reference: installed matching headers/library from d18c82a1f1f23ff84362516e86af5f3cb2e34475, known incremental shared rebuild, NOT fresh all-object build or latest upstream. Native HGraph, NOT old Lite. Library SHA2569aeaa550703f116bef2959769d4f2f03da254b07c906ba941d8186224cc70c72.
Full builder8267dec7fd71f2f44d32816c40bfc1a2fb4e61e4fbb64d9fc40c8b35921b4113; loader2b1b9566ae7522d62793cb19750b611cd17c602b706a5016c5cd153df5b94d0d.
Lite production624252f, graph test selector fixed13b87c3; same measured library as floating old/new trials. identity.json captures invocation and source state at624252f. Only pending graph test selector differed, not production.

Both degree16/construction128, explicit one construction/BLAS/OMP/MKL thread, CPU0, native small memory_io profile, floating redundant raw vectors disabled. Lite queryef512 versus Full128: similar quality floor, NOT same budget or exact matched recall. Native Rabi uses3+5/FHT; selected SIMD support is aligned on EPYC but numerical kernels, rotations and topology are not identical. Full randomized rotations give per-trial recall differences. Three alternating pairs per cell,100queries,k10,zeroCRUD rounds; fresh-loader samples3 each, warm/uncontrolled cache.

Medians:
| Dataset | Storage | Recall Full/Lite | P50 Full/Lite us | P99 Full/Lite us | Load Full/Lite ms | Loaded total RSS Full/Lite KiB |
| --- | --- | --- | --- | --- | --- | --- |
| GIST | FP32 | .966/.971 | 172.116/491.859 | 247.355/641.106 | 30.799/17.823 | 66032/45060 |
| GIST | FP16 | .966/.971 | 162.378/423.121 | 207.586/586.137 | 16.373/11.153 | 46764/26312 |
| GIST | RABITQ8 | .962/.970 | 195.085/489.589 | 290.154/747.344 | 9.530/6.270 | 38084/15580 |
| Cohere | FP32 | .987/.985 | 176.956/480.729 | 226.144/577.017 | 24.842/14.526 | 58384/37536 |
| Cohere | FP16 | .987/.985 | 162.037/442.269 | 198.235/592.517 | 13.691/9.421 | 42984/22556 |
| Cohere | RABITQ8 | .983/.984 | 206.696/506.750 | 269.225/837.843 | 8.215/5.808 | 36180/13788 |

Lite has faster observed warm loading and lower loaded total RSS, but remains2.452.86x slower at query in these cells. Cohere floating recall is still slightly below Full, so this is not an exact equal-quality victory.
Full before-load baseline is~25MiB versus Lite~3.6MiB. Floating incremental vector/index memory is comparable or slightly worse for Lite (e.g. GISTFP32 medians45060-3628=41432KiB versus66032-25044=40988KiB). Do not attribute total RSS savings entirely to layout.

Lite bulk-build external peak RSS is substantially HIGHER: GISTFP32/FP16/Rabi178784/129404/226128KiB versus Full109024/85384/102108; Cohere143984/104420/181820 versus93368/73872/82740. Temporary FP32 construction storage and initial source retention remain optimization targets; this is not a peak-memory win.
Lite snapshots are slightly LARGER (see summary): GIST39,840,064/20,640,064/11,284,416bytes versus Full39,808,753/20,148,057/10,690,798; Cohere32,160,064/16,800,064/9,363,552 versus31,957,337/16,228,737/8,737,002.

Applying the same strip --strip-unneeded to both shared libraries gives Lite306656bytes, Full40463344bytes. Stripped SHA256Litef720240ca6180658e03fb6ca75601c517496ae14c038bb85d69f20767339afbc; Full362f9dd0ffafec75c444a0efa84621463735601f71063490a2d7a1f104715a14. This~99.24% shared-library reduction is NOT complete deployment-package dependency closure.

Reproduce with run_aligned_comparison.py arguments from identity, installed pinned Full, and matching full_dataset_main.cpp/load_memory.cpp runners as documented in ../../ALIGNED_COMPARISON.md. raw.tar.gz preserves all commands, exact parameters, SIMD logs, per-query timings/IDs and input hashes. Snapshot formats/topologies differ; Full/Lite snapshots and neighbors must NOT be required byteequal.
Three fresh loads per process validate persistence; the benchmark has zero changed-value CRUD rounds.100queries is not robust productionP99 and no cold-cache control was performed. GIST/Cohere100k repeats, lasting real changed-value CRUD, isolated-host runs, larger query cohorts, fresh Full rebuild and complete package closure remain outstanding.
