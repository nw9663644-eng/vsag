#!/usr/bin/env python3
# Copyright 2024-present the vsag project
# SPDX-License-Identifier: Apache-2.0
"""Recompute RaBitQ build lifetime quantiles and paired correctness without extraction."""
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
    for name in ["rabitq-build-lifetimes-20261009", "rabitq-build-lifetimes-gist100k-20261009"]:
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
    assert pair_count == 12
    print("12 snapshot/ordered-neighbor pairs, raw P50/P99 and 72 load rows passed")


if __name__ == "__main__":
    main()
