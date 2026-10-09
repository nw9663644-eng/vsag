#!/usr/bin/env python3
# Copyright 2024-present the vsag project
# SPDX-License-Identifier: Apache-2.0
"""Offline check of paired raw neighbors, query quantiles and load row counts."""
import csv
import io
import json
import math
from pathlib import Path
import tarfile


def read_csv(archive, name):
    stream = archive.extractfile("./"+name)
    if stream is None:
        raise RuntimeError("missing raw artifact: "+name)
    return list(csv.DictReader(io.StringIO(stream.read().decode())))


def main():
    directory = Path(__file__).resolve().parent
    for name in ["rabitq-array-io-20261009", "rabitq-bounded-heaps-20261009"]:
        root = directory.parent/name
        rows = json.loads((root/"rows.json").read_text())
        with tarfile.open(root/"raw.tar.gz") as archive:
            for row in rows:
                tag = f"{row['dataset']}-{row['storage']}-{row['trial']}-{row['name']}"
                samples = read_csv(archive, tag+".queries.csv.latencies.csv")
                assert len(samples) == int(row["build"]["query_count"])
                values = sorted(float(s["latency_us"]) for s in samples)
                for fraction, metric in [(0.5, "search_p50_us"), (0.99, "search_p99_us")]:
                    observed = values[max(1, math.ceil(len(values)*fraction))-1]
                    assert abs(observed-float(row["build"][metric])) <= 1e-6
                assert len(row["loads"]) == 3
            for row in rows:
                if row["name"] != "control":
                    continue
                peer = next(r for r in rows if r["name"] == "lite" and
                            (r["dataset"], r["storage"], r["trial"]) ==
                            (row["dataset"], row["storage"], row["trial"]))
                assert row["snapshot_sha256"] == peer["snapshot_sha256"]
                prefix = f"{row['dataset']}-{row['storage']}-{row['trial']}-"
                a = read_csv(archive, prefix+"control.queries.csv.neighbors.csv")
                b = read_csv(archive, prefix+"lite.queries.csv.neighbors.csv")
                assert a == b
                assert len(a) == int(row["build"]["query_count"])*int(row["build"]["k"])
    with tarfile.open(directory/"raw.tar.gz") as archive:
        assert read_csv(archive, "after-probe.neighbors.csv") == read_csv(
            archive, "route-probe.neighbors.csv")
        for kind in ["query", "load"]:
            for variant in ["control", "candidate"]:
                for trial in range(7):
                    rows = read_csv(archive, f"paired-{kind}-{trial}-{variant}.csv")
                    assert len(rows) == 1
                    if kind == "query":
                        assert rows[0]["quality_ef"] == "512"
                        assert rows[0]["recall_at_k"] == "0.975000"
    print("18 paired snapshots/neighbor exports, raw P50/P99, 14 load and 14 query rows passed")


if __name__ == "__main__":
    main()
