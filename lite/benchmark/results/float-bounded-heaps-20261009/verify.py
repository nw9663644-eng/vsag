#!/usr/bin/env python3
# Copyright 2024-present the vsag project
# SPDX-License-Identifier: Apache-2.0
"""Check archived paired snapshots, neighbors, raw quantiles and mutation ledgers."""
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
    pairs = 0
    for name in ["float-bounded-heaps-20261009", "float-bounded-heaps-100k-20261009"]:
        root = parent / name
        rows = json.loads((root / "rows.json").read_text())
        with tarfile.open(root / "raw.tar.gz") as archive:
            for row in rows:
                tag = f"{row['dataset']}-{row['storage']}-{row['trial']}-{row['name']}"
                samples = list(csv.DictReader(io.StringIO(
                    read(archive, tag + ".queries.csv.latencies.csv").decode())))
                assert len(samples) == int(row["build"]["query_count"])
                values = sorted(float(s["latency_us"]) for s in samples)
                for fraction, metric in [(0.5, "search_p50_us"), (0.99, "search_p99_us")]:
                    observed = values[max(1, math.ceil(len(values)*fraction))-1]
                    assert abs(observed - float(row["build"][metric])) <= 1e-6
                assert len(row["loads"]) == 3
            for row in rows:
                if row["name"] != "control":
                    continue
                peer = next(r for r in rows if r["name"] == "lite" and
                            (r["dataset"], r["storage"], r["trial"]) ==
                            (row["dataset"], row["storage"], row["trial"]))
                assert row["snapshot_sha256"] == peer["snapshot_sha256"]
                prefix = f"{row['dataset']}-{row['storage']}-{row['trial']}-"
                a = read(archive, prefix + "control.queries.csv.neighbors.csv")
                b = read(archive, prefix + "lite.queries.csv.neighbors.csv")
                assert a == b
                assert float(row["build"]["recall_at_k"]) == float(peer["build"]["recall_at_k"])
                pairs += 1
    root = parent / "full-small-optimized-quality-20261009"
    rows = json.loads((root / "rows.json").read_text())
    with tarfile.open(root / "raw.tar.gz") as archive:
        for row in rows:
            tag = f"{row['dataset']}-{row['storage']}-{row['trial']}-{row['name']}"
            suffix = ".latencies.csv" if row["name"] == "full" else ".queries.csv.latencies.csv"
            samples = list(csv.DictReader(io.StringIO(read(archive, tag + suffix).decode())))
            assert len(samples) == int(row["build"]["query_count"])
            values = sorted(float(s["latency_us"]) for s in samples)
            for fraction, metric in [(0.5, "search_p50_us"), (0.99, "search_p99_us")]:
                observed = values[max(1, math.ceil(len(values)*fraction))-1]
                assert abs(observed - float(row["build"][metric])) <= 1e-6
            assert len(row["loads"]) == 3
            expected_ef = "128" if row["name"] == "full" else "512"
            assert row["build"]["query_ef_search"] == expected_ef
    assert len(rows) == 36
    root = parent / "float-bounded-heaps-regression-20261009"
    with tarfile.open(root / "raw.tar.gz") as archive:
        for storage in ["fp32", "fp16", "rabitq8"]:
            for extension in ["csv", "snapshots"]:
                assert read(archive, storage + "-control." + extension) == read(
                    archive, storage + "-candidate." + extension)
    print(f"{pairs} paired snapshots/neighbors/raw quantiles and 3 changed-vector ledgers plus 36 native-Full/Lite raw rows passed")


if __name__ == "__main__":
    main()
