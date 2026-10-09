#!/usr/bin/env python3
# Copyright 2024-present the vsag project
# SPDX-License-Identifier: Apache-2.0
"""Recompute RaBitQ row training quantiles and paired correctness without extraction."""
import csv
import io
import json
import math
from pathlib import Path
import tarfile


def read(archive, name):
    stream = archive.extractfile("./" + name)
    if stream is None:
        raise RuntimeError("missing raw artifact: " + name)
    return stream.read()


def main():
    parent = Path(__file__).resolve().parent.parent
    pair_count = 0
    for name in ["rabitq-row-training-20261009", "rabitq-row-training-cohere100k-20261009"]:
        root = parent / name
        rows = json.loads((root / "rows.json").read_text())
        with tarfile.open(root / "raw.tar.gz") as archive:
            for row in rows:
                tag = f"{row['dataset']}-{row['storage']}-{row['trial']}-{row['name']}"
                samples = list(csv.DictReader(io.StringIO(
                    read(archive, tag + ".queries.csv.latencies.csv").decode())))
                assert len(samples) == int(row["build"]["query_count"])
                values = sorted(float(sample["latency_us"]) for sample in samples)
                for fraction, metric in [(0.5, "search_p50_us"), (0.99, "search_p99_us")]:
                    observed = values[max(1, math.ceil(len(values) * fraction)) - 1]
                    assert abs(observed - float(row["build"][metric])) <= 1e-6
                assert len(row["loads"]) == 3
                assert int(read(archive, tag + ".peak_kib")) == row["build"]["external_peak_rss_kib"]
            for row in rows:
                if row["name"] != "control":
                    continue
                peer = next(candidate for candidate in rows
                            if candidate["name"] == "lite" and
                            (candidate["dataset"], candidate["storage"], candidate["trial"]) ==
                            (row["dataset"], row["storage"], row["trial"]))
                assert row["snapshot_sha256"] == peer["snapshot_sha256"]
                assert row["build"]["recall_at_k"] == peer["build"]["recall_at_k"]
                prefix = f"{row['dataset']}-{row['storage']}-{row['trial']}-"
                assert read(archive, prefix + "control.queries.csv.neighbors.csv") == read(
                    archive, prefix + "lite.queries.csv.neighbors.csv")
                pair_count += 1
    root = parent / "rabitq-row-training-20261009"
    with tarfile.open(root / "raw.tar.gz") as archive:
        for dim in [128, 768]:
            def allocation_row(variant):
                samples = list(csv.DictReader(io.StringIO(
                    read(archive, f"allocations-{variant}-{dim}.csv").decode())))
                assert len(samples) == 1
                return {key: int(value) for key, value in samples[0].items()}
            control = allocation_row("control")
            candidate = allocation_row("candidate")
            assert control["count"] == candidate["count"] == 2048
            assert control["dim"] == candidate["dim"] == dim
            matrix_bytes = 2048 * dim * 4
            assert control["matrix_bytes"] == candidate["matrix_bytes"] == matrix_bytes
            assert control["ordinary_new_bytes"] - candidate["ordinary_new_bytes"] == matrix_bytes
            assert control["ordinary_new_requests"] - candidate["ordinary_new_requests"] == 1
            assert control["matrix_requests"] == 2 and candidate["matrix_requests"] == 1
        faults = read(archive, "faults.txt").decode().splitlines()
        assert len(faults) == 12
        for line in faults:
            assert "changed_after_failure=0 invalid_snapshot=0 escaped=0" in line
    assert pair_count == 12
    print("12 snapshot/ordered-neighbor pairs, raw P50/P99 and 72 load rows, exact matrix allocation savings and fault summaries passed")


if __name__ == "__main__":
    main()
