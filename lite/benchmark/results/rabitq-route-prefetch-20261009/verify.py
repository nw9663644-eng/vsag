#!/usr/bin/env python3
# Copyright 2024-present the vsag project
# SPDX-License-Identifier: Apache-2.0
"""Audit route prefetch evidence without extracting archive paths."""
import collections
import csv
import gzip
import hashlib
import io
import json
import math
from pathlib import Path
import statistics
import struct
import tarfile


def rows(payload):
    return list(csv.DictReader(io.StringIO(payload.decode())))


def truth_rows(payload):
    result = []
    offset = 0
    while offset < len(payload):
        count = struct.unpack_from("<i", payload, offset)[0]
        assert count == 10
        offset += 4
        result.append(set(struct.unpack_from("<10i", payload, offset)))
        offset += count * 4
    assert offset == len(payload)
    return result


def main():
    base = Path(__file__).resolve().parent.parent
    names = ["rabitq-route-prefetch-20261009",
             "rabitq-route-prefetch-100k-20261009"]
    pairs = loads = states = 0
    for name in names:
        root = base / name
        for line in (root / "SHA256SUMS").read_text().splitlines():
            digest, file = line.split("  ", 1)
            assert hashlib.sha256((root / file).read_bytes()).hexdigest() == digest
        records = json.loads((root / "rows.json").read_text())
        identity = json.loads((root / "identity.json").read_text())
        assert identity["arguments"]["cpu"] == 0
        assert identity["reference_library_sha256"] == \
            "0ff5757969eba4574686a920996693fbea8986561560a27ebe5bc5f4bdefe415"
        with tarfile.open(root / "raw.tar.gz") as archive:
            def read(file):
                stream = archive.extractfile("./" + file)
                assert stream is not None
                return stream.read()
            for file, digest in json.loads((root / "members.json").read_text()).items():
                assert hashlib.sha256(read(file)).hexdigest() == digest
            for record in records:
                tag = (f"{record['dataset']}-{record['storage']}-"
                       f"{record['trial']}-{record['name']}")
                build = record["build"]
                latency = rows(read(tag + ".queries.csv.latencies.csv"))
                assert len(latency) == int(build["query_count"])
                times = sorted(float(x["latency_us"]) for x in latency)
                assert all(math.isfinite(x) and x >= 0 for x in times)
                for fraction, metric in [(0.5, "search_p50_us"), (0.99, "search_p99_us")]:
                    value = times[max(1, math.ceil(len(times) * fraction)) - 1]
                    assert abs(value - float(build[metric])) <= 1e-6
                assert int(read(tag + ".peak_kib")) == build["external_peak_rss_kib"]
                groundtruth = truth_rows(read(record["dataset"] + ".groundtruth.ivecs"))
                metadata = json.loads(read(record["dataset"] + ".dataset.json"))
                for file in ["queries.fvecs", "groundtruth.ivecs"]:
                    payload = read(record["dataset"] + "." + file)
                    assert len(payload) == metadata[file]["bytes"]
                    assert hashlib.sha256(payload).hexdigest() == metadata[file]["sha256"]
                neighbors = collections.defaultdict(list)
                for result in rows(read(tag + ".queries.csv.neighbors.csv")):
                    query = int(result["query"])
                    assert int(result["rank"]) == len(neighbors[query])
                    distance = float.fromhex(result["distance"])
                    assert math.isfinite(distance)
                    if neighbors[query]:
                        assert distance >= neighbors[query][-1][1]
                    neighbors[query].append((int(result["id"]), distance))
                total_hits = 0
                hits = rows(read(tag + ".queries.csv"))
                assert len(hits) == len(latency) == len(groundtruth)
                for i, hit in enumerate(hits):
                    assert int(hit["query"]) == i
                    ids = [x[0] for x in neighbors[i]]
                    assert len(ids) == int(hit["k"]) == 10
                    assert len(set(ids)) == len(ids)
                    observed = len(set(ids) & groundtruth[i])
                    assert int(hit["hits"]) == observed
                    total_hits += observed
                    states += 1
                assert abs(total_hits / (10 * len(hits)) - float(build["recall_at_k"])) <= 1e-6
                assert len(record["loads"]) == identity["arguments"]["loads"]
                for sample, expected in enumerate(record["loads"]):
                    text = read(tag + f"-load-{sample}.stdout").decode().splitlines()
                    pos = next(i for i, line in enumerate(text) if line.startswith("dim,count,"))
                    actual = rows(("\n".join(text[pos:pos+2]) + "\n").encode())[0]
                    for key, value in actual.items():
                        assert value == expected[key]
                    assert int(read(tag + f"-load-{sample}.peak_kib")) == \
                        expected["external_peak_rss_kib"]
                    loads += 1
            for control in records:
                if control["name"] != "control":
                    continue
                peer = next(x for x in records if x["name"] == "lite" and
                            (x["dataset"], x["storage"], x["trial"]) ==
                            (control["dataset"], control["storage"], control["trial"]))
                assert control["snapshot_sha256"] == peer["snapshot_sha256"]
                tag = f"{control['dataset']}-{control['storage']}-{control['trial']}-"
                for suffix in [".queries.csv", ".queries.csv.neighbors.csv"]:
                    assert read(tag + "control" + suffix) == read(tag + "lite" + suffix)
                pairs += 1
        for summary in json.loads((root / "summary.json").read_text()):
            selected = [x for x in records if
                        (x["dataset"], x["storage"], x["name"]) ==
                        (summary["dataset"], summary["storage"], summary["name"])]
            for metric in ["recall_at_k", "build_ms", "search_p50_us", "search_p99_us",
                           "save_ms", "snapshot_bytes", "external_peak_rss_kib"]:
                value = statistics.median(float(x["build"][metric]) for x in selected)
                assert abs(value - summary[metric]) <= 1e-6
            for metric in ["load_ms", "loaded_rss_kib", "process_peak_rss_kib",
                           "before_create_rss_kib", "before_load_rss_kib"]:
                value = statistics.median(float(s[metric]) for x in selected for s in x["loads"])
                assert abs(value - summary[metric]) <= 1e-6
    root = base / names[0]
    lines = {}
    with tarfile.open(root / "coverage-raw.tar.gz") as archive:
        for member in archive:
            data = json.loads(gzip.decompress(archive.extractfile(member).read()))
            for file in data["files"]:
                path = file["file"]
                if not (("/src/lite/" in path or "/include/vsag/lite/" in path or
                         "/src/simd/kernels/" in path) and "_test.cpp" not in path):
                    continue
                for line in file["lines"]:
                    key = (path, line["line_number"])
                    lines[key] = lines.get(key, False) or line["count"] > 0
    coverage = json.loads((root / "coverage.json").read_text())
    for scope in ["lite", "shared_simd", "combined"]:
        values = [v for (p, _), v in lines.items() if scope == "combined" or
                  (("/src/simd/kernels/" in p) == (scope == "shared_simd"))]
        assert sum(values) == coverage["scopes"][scope]["covered"]
        assert len(values) == coverage["scopes"][scope]["total"]
        assert sum(values) / len(values) >= .9
    assert (pairs, loads, states) == (15, 90, 3000)
    print("15 snapshot/ordered-neighbor pairs, 3000 truth intersections, raw quantiles/"
          "medians, 90 loads, coverage and artifact hashes passed")


if __name__ == "__main__":
    main()
