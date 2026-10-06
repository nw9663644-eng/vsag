# SIFT query-budget selection and reserved-query confirmation

Measured library/benchmark source: `fd67861a7f91a9eef4a42a3978d10375d0682230`. Only SIFT preparation gains a query-offset option in this increment; no library code or build flags change. `environment.txt` hashes are the identical executables/libraries used in the preceding experiment. No new C++ regression/coverage run is claimed.

## Protocol and separation

Use the same actual online-built SIFT 100k FP32 snapshots as `../sift-online-20261006`, degree 16, construction/maintenance ef 128. Default uses the default library; diversity uses the opt-in library. No offline transformation. The first 100 SIFT queries were already observed. New validation rows [100,400) select budgets; final rows [400,700) were prepared/evaluated only after `frozen.json` and its SHA were written. Final query vectors have no byte-identical overlap with the first 400. Final results are now observed and must not be reused as a new blind set. Eight final rows independently recomputed in FP64 match the prepared exact Top-10; this is a sample audit, not a full independent proof.

`protocol.json` precedes selection. Choose the smallest tested ef with validation Recall@10 >= 0.955, allowing margin over the final 0.95 gate. Default grid 64/96/128/160/192/256; diversity 32/48/64/96/128/192. All tested points are retained under `validation/`. Default 192 scored 0.950333 but missed the declared margin; default 256 scored 0.963333 and was selected. Diversity 64 scored 0.949; 96 scored 0.969333 and was selected. These coarse grids do not establish globally optimal budgets. An actual application targeting exactly 0.95 may choose differently.

Frozen final ef: default 256, diversity 96; maintenance stays 128. Final protocol repeats the preceding mixed workload: 2000 cycles, four actual mutation calls per cycle (changed first coordinate +0.125 Update, restore Update, Remove, Add), 2000 distinct IDs, CPU 0, query after complete restored cycle. Read:mutation-call ratios 1:4 and 1:40, three fresh processes per mode/cadence with alternating mode order. Final 300 queries cycle deterministically for mixed reads; repeated events are not independent query samples. No concurrency. Exact Save/Load ID/distance checks pass in all 12 runs.

## Results

Medians of three processes; replicate ranges are in `summary.json`.

| Metric | Default ef256 | Diversity ef96 |
| --- | ---: | ---: |
| Initial final-query Recall@10 | 0.968667 | 0.977667 |
| After 2000 cycles Recall@10, either cadence | 0.966333 | 0.976333 |
| Mixed CPU ms, reads:mutations 1:4 | 2160.586 | 1944.176 |
| Maintenance CPU ms, 1:4 | 1227.982 | 1467.197 |
| Query CPU ms, 1:4 | 928.277 | 473.155 |
| Mixed query P50/P99 us, 1:4 | 477.128 / 665.955 | 243.084 / 321.802 |
| Mixed CPU ms, reads:mutations 1:40 | 1315.469 | 1498.993 |
| Maintenance CPU ms, 1:40 | 1215.245 | 1449.369 |
| Query CPU ms, 1:40 | 99.061 | 48.438 |
| Mixed query P50/P99 us, 1:40 | 501.759 / 671.165 | 247.093 / 315.214 |

Both modes pass the final 0.95 floor; diversity has approximately one percentage point higher final recall. This is a comparison of configurations selected for a common quality gate, not exactly equal recall. Query P50 is about 1.96x / 2.03x faster, while maintenance CPU is about 19.5% / 19.3% higher. Total mixed CPU decreases 10.0% at 1:4 but increases 14.0% at 1:40. The selected SIFT configuration benefits the more query-intensive workload, but does not provide universal end-to-end savings. Construction cost (single-build +16%) remains additional and is excluded from these loaded-snapshot mixed timings. Neither SIFT configuration is a Full VSAG baseline.

Keep the experimental policy OFF by default. Before recommending adoption, validate Cohere and matching Full configurations and document the query/maintenance tradeoff. No policy auto-switch or new feature follows from this result alone. The short 2%-ID churn and small changed-vector perturbation do not prove arbitrary updates or long-term graph stability. CPU fields use process CPU time, not utilization percentage; load from a populated memory stream is not cold-load performance.

## Reproduction and retained evidence

`commands-prepare.json`, `commands-frontier.json`, `commands-final.json` record exact commands; preparation requires numpy/h5py (server dependencies in `/home/ubuntu/project/vsag-lite-datasets/sift/python-deps`). `frontier.py`, `final.py`, `audit.py` record the scripts used at the server path `/home/ubuntu/project/vsag-lite-sift-matched-20261006`. Preparation refuses existing output. Dataset vectors and large snapshots stay on the remote server; per-stage manifests and snapshot hashes are committed. Timing/event CSVs, aggregate API/scalar results, logs and min/max are split into `validation/` and `final/`. `frozen.sha256` records the pre-final budget checksum.

Checks performed: `test_prepare_sift.py` validates offset, exact truth with ID tie ordering, original prefix compatibility, negative/out-of-range rejection and overwrite prevention; final raw-latency counts/P50/P99 and quality floors pass `python3 lite/benchmark/results/sift-matched-20261006/final/verify.py`; nonoverlap and eight FP64 truth checks pass `audit.py`; SHA256 and git diff checks pass. This is only a private-fork update; PR branches remain frozen.
