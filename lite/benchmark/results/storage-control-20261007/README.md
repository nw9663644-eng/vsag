# Storage-only changed-vector control

Measured parent: `24601b707ddd2834850e900470077539555553e7`. This control separates changed vector bytes from graph-topology maintenance in the [persistent Update replay](../persistent-update-20261007/README.md). It is a diagnostic tool and does not change the Lite library or adopt the repair candidate.

## Minimal control

The opt-in command is:

```bash
lite_graph_route_probe --storage-only-update SNAPSHOT DATASET_DIR NEW_OUTPUT_CSV CYCLES
```

It copies the original FP32 snapshot in memory, applies the exact same distinct-slot schedule and first-coordinate `+0.125` values as the native Update replay, and loads the patched snapshot through public `Index::Load`. No `Index::Update`, Remove, Add or graph rebuild is called. A full byte comparison permits differences only in the first four vector bytes of scheduled slots and rejects any metadata, ID, other vector-coordinate or adjacency change. A `.control.csv` receipt records snapshot bytes checked, bytes changed, and Save/Load success. No modified large snapshot is written to disk.

The mode reuses the same changed-data ground truth, stored ef128, 100 observed queries and raw neighbor output. It reports mutation CPU as zero because snapshot copying and byte patching are a diagnostic construction, not an API performance measurement. Existing output paths, including the control receipt, are refused.

## Fixed 100k results

SIFT128, GIST960 and normalized Cohere768 use the same initial 100k snapshots, 10,000 changed IDs, queries and truth as the preceding Update replay. Baseline and candidate libraries return byte-identical control neighbors because their search implementation and loaded initial topology are the same.

| Dataset | Storage-only recall | Native baseline Update | Native candidate Update | Baseline net hits | Candidate net hits |
|---|---:|---:|---:|---:|---:|
| SIFT | 0.956 | 0.954 | 0.954 | -2 | -2 |
| GIST | 0.741 | 0.736 | 0.736 | -5 | -5 |
| Cohere | 0.889 | 0.894 | 0.899 | +5 | +10 |

Per-query native Update versus storage-only: SIFT baseline/candidate each have 4 wins, 4 losses and 92 ties; GIST baseline has 14/19/67 and candidate 13/18/69; Cohere baseline has 6/2/92 and candidate 7/2/91. Thus topology maintenance slightly reduces aggregate hits for this SIFT/GIST perturbation but improves Cohere, with the direction-aware candidate adding another five Cohere hits. A single geometry rule is not uniformly beneficial across these distributions.

These paired hit counts are diagnostic outcomes on one update schedule and an already observed query set. They do not prove statistical significance, generalize to whole-vector or application-specific updates, or establish the candidate as the default. The initial/changed-data truth difference is held constant across each pair, so the paired delta isolates the topology produced by Update from the unchanged original topology for this protocol.

## Verification

Each of six controls checks 10,000 scheduled coordinates and every snapshot byte. Snapshot sizes are 65,600,064 bytes for SIFT, 398,400,064 for GIST and 321,600,064 for Cohere; changed-byte counts are respectively 10,000, 38,549 and 39,882, while every other byte is identical. All controls pass public Load, 100 changed-data queries, Save/Load and exact ordered ID/distance roundtrip.

The portable standard-library audit:

```bash
python3 lite/benchmark/results/storage-control-20261007/verify.py
```

checks SHA256, 60,000 coordinate patches, 12,000 returned control distances against original host vectors plus changed coordinates when snapshots are available, control receipts, paired per-query hits and linkage to the previous report evidence. It verifies baseline/candidate control neighbors are identical. Off-host it explicitly reports unavailable snapshot/source checks. Archive members are read without path extraction.

Release and ASan+UBSan storage/native fixtures, existing route/slot fixtures, clang-format15 and clang-tidy15 route/slot checks passed. No library coverage or new library CTest result is claimed because no `src/` or `include/` code changed.

`raw.tar.gz` includes control and prior Update summaries/neighbors, changed truth/query bytes, receipts, commands, identities and test logs. `manifest.json` and `members.json` bind all published evidence. Host-only scripts preserve absolute historical dependencies and are not a portable download/build pipeline. Large snapshots, binaries and private instructions are excluded. Host directory: `/home/ubuntu/project/vsag-lite-storage-control-20261007`.

The next implementation decision should focus on why GIST loses routing hits under both Update policies while Cohere benefits. The current candidate remains optional; increasing ef or degree would hide the fixed-budget behavior rather than address it. Only the personal experiment branch is updated, with PR branches frozen.

Measured source/binary hashes remain in `identity.json`. Final validation hashes are separately recorded in `final-identity.json`; the usage string was clarified after measurement. The verifier reports whether measured files still match the current host and independently checks the final files.
