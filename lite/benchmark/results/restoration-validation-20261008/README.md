# Fixed row-restoration validation across distributions

Measured parent: `120c191408146bbce5a26cc4a82624c1fcedd175`. This extends the [GIST row-restoration ablation](../edge-restoration-20261008/README.md). Before observing this run, `plan.json` froze degree16, ef128, 10,000 distinct first-coordinate `+0.125` updates and comparison masks0/1. Mask0 retains the maintained topology; mask1 restores original outgoing rows only on the updated-source IDs, retaining maintained rows elsewhere. No other masks, budgets or policies were selected in this validation.

## Query history and preparation

SIFT128 and Cohere768 use their previous 100 observed queries, original 100k FP32 snapshots and changed-data truth. GIST960 uses source rows100:400, disjoint from the rows0:100 used to select this restoration intervention. However rows100:400 were already observed in the project's historical holdout experiment, and rows400:1000 in its final experiment. All 1,000 available original GIST queries have been observed historically. This supplement is not a project-wide untouched blind set; the archived historical manifests and source-row hashes preserve that distinction.

GIST's 300 changed-data Top-10 truths were recomputed exhaustively against the same 100k stored vectors with FP64 direct differences and squared-L2 sums, updating coordinate zero with exactly rounded FP32 values. No norm-dot shortcut is used; equal distances use ascending external IDs. Its query bytes match historical source rows100:400 exactly. The portable audit validates the archived truths and returned distances; it does not rerun the whole 300-query exhaustive preparation offline.

Cohere's original stored vectors and queries are normalized, but persistent coordinate updates are not renormalized. These results use squared-L2 on the actual changed representation and are not a cosine-update claim.

## Results at fixed budget

Four native Update traces prepare the SIFT/Cohere maintained topologies under the existing baseline/candidate libraries. Their native neighbors, including distances, exactly reproduce the prior persistent-Update evidence. GIST reuses the previous complete topology evidence. Twelve fresh restoration processes use one common baseline Load/Search library, the existing `edge_restoration_probe.py`, anonymous memory snapshots, CPU0 pinning and explicit library binding. The baseline/candidate labels distinguish topology origins, not different search implementations.

| Dataset | Topology origin | Maintained recall | Restore updated-source recall | Net truth hits | Query wins/losses/ties |
|---|---|---:|---:|---:|---|
| SIFT, 100 queries | Baseline | 0.954 | 0.957 | +3/1000 | 2/0/98 |
| SIFT, 100 queries | Candidate | 0.954 | 0.957 | +3/1000 | 2/0/98 |
| Cohere, 100 queries | Baseline | 0.894 | 0.894 | 0/1000 | 1/1/98 |
| Cohere, 100 queries | Candidate | 0.899 | 0.906 | +7/1000 | 2/2/96 |
| GIST supplement, 300 queries | Baseline | 0.683 | 0.685333 | +7/3000 | 44/38/218 |
| GIST supplement, 300 queries | Candidate | 0.684 | 0.689667 | +17/3000 | 42/29/229 |

All explicit edge counts are unchanged between masks0/1. Mean visited-node changes are approximately +0.55–0.60% for SIFT, +0.19–0.22% for Cohere and +0.18–0.50% for GIST. Scalar traces have zero visited-but-not-returned truth in all cases. These counts do not establish query latency or maintenance CPU gains.

Point estimates remain nonnegative, but gains are small and concentrated. In particular the GIST candidate improvement is about 0.005667 on this supplement, smaller than 0.014 on the selection queries. Preserving old outgoing rows is a direction for further investigation, not an accepted general optimization.

## Exploratory uncertainty

The verifier recomputes 10,000 paired bootstrap resamples with seed20261008 and the exact two-sided sign test on non-tied queries. No interval excludes zero; repeated observation, selection history and multiple comparisons mean these statistics are descriptive rather than confirmatory.

| Dataset/origin | Recall delta bootstrap95% | Sign p |
|---|---|---:|
| SIFT, either | [0, 0.008] | 0.5 |
| Cohere baseline | [-0.003, 0.003] | 1.0 |
| Cohere candidate | [-0.004, 0.025] | 1.0 |
| GIST baseline | [-0.005667, 0.010333] | 0.581114 |
| GIST candidate | [-0.002, 0.013333] | 0.153991 |

These diagnostic ef128 profiles cannot replace the separately documented passing profiles. GIST and Cohere here remain below their separate 0.90/0.95 gates. No budget increase, default adoption, online maintenance implementation, speedup, arbitrary whole-vector update, concurrent CRUD or RaBitQ backend delivery is claimed.

## Evidence audit and execution

```bash
python3 lite/benchmark/results/restoration-validation-20261008/verify.py
```

The standard-library verifier checks all artifact/member SHA256 values, prior-report linkage, frozen-plan identity, historical query rows, topology bounds/order and lossless encoding, native reference agreement, raw returned IDs/ranks/distances and truth intersections. On the host it independently reconstructs all twelve control-snapshot SHA values and checks 20,000 returned scalar distances with FP64 squared-L2. All three input snapshots and available source/binary hashes pass.

There are 2,000 factor/query states and native returned-ID calibrations across 500 unique query rows. The reused slot probe also executes eight equivalent entry/ring/tie masks because snapshot and reference are identical; all 16,000 repeated states have identical results. They are not independent samples. Native ID agreement calibrates output sets, not internal SIMD visit sequences. Missing host checks are explicitly reported off-host; archive paths are never extracted.

SIFT/Cohere topology bundles store, for each source in slot order, the original, baseline and candidate rows. Each row has one little-endian uint32 degree followed by ordered uint32 targets. Reconstructed individual maintained streams and full CSV hashes must match the native trace outputs. GIST topology bytes are linked to the prior archive rather than duplicated. This is evidence encoding, not a new Lite format. Large vector snapshots and binaries are excluded; controls exist only in anonymous memory.

The initial batch stopped on a repeated dataset-directory creation after two SIFT traces and two successful SIFT controls. `run-initial-failed.log` is retained. The corrected host runner validates existing dataset bytes and resumes recorded successful cases without repeating them; all four traces and twelve controls have successful exit receipts. This was an orchestration error, not a native library failure.

C++/driver/library source, API, defaults and CMake are unchanged in this report-only extension. The prior Release/ASan+UBSan fixtures retain their source revision; no new coverage, CTest, format/tidy or sanitizer test is claimed. New validation is the actual trace/control execution and independent data audit above. Host directory: `/home/ubuntu/project/vsag-lite-restoration-validation-20261008`. Historical host scripts depend on existing data and libraries rather than providing a portable download/build pipeline.

Next test sensitivity to larger or whole-vector changes and seek a clearly separate query cohort before implementing an opt-in online policy. Post-hoc row restoration changes retrieval after maintenance, while online retention would also alter subsequent neighbor selection and repair; it must be evaluated separately. Only the personal experiment branch receives this work; PR branches remain frozen.
