# Copyright 2024-present the vsag project
# SPDX-License-Identifier: Apache-2.0
"""Audit exact removal pairs and raw API latency records."""
import gzip
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import struct
import tarfile


def rows(data):
    return list(csv.DictReader(io.StringIO(data.decode())))


def quantile(values, fraction):
    return sorted(values)[max(1, math.ceil(len(values) * fraction)) - 1]


def main():
    root = Path(__file__).resolve().parent
    sha = lambda data: hashlib.sha256(data).hexdigest()
    for line in (root / "SHA256SUMS").read_text().splitlines():
        digest, file = line.split("  ", 1)
        assert sha((root / file).read_bytes()) == digest
    with tarfile.open(root / "raw.tar.gz") as archive:
        payloads = {m.name.removeprefix("./"): archive.extractfile(m).read()
                    for m in archive if m.isfile()}
    for file, digest in json.loads((root / "members.json").read_text()).items():
        assert sha(payloads[file]) == digest
    records = json.loads((root / "rows.json").read_text())
    assert len(records) == 4
    identity = json.loads((root / "identity.json").read_text())
    assert identity["control_library_sha256"] == "e63099bdbe37133b27bddab8a82d69da5cf33bed72c8e3c304e7ab1c4d159558"
    summary = []
    operations = states = 0
    for record in records:
        tag = record["dataset"] + "-" + record["variant"]
        command = json.loads(payloads[tag + ".command.json"])
        assert command["environment"]["LD_LIBRARY_PATH"] in payloads[tag + ".ldd"].decode()
        assert record["exit"] == 0
        metric = {"dataset": record["dataset"], "variant": record["variant"],
                  "crud_ms": float(record["result"]["crud_ms"]), "operations": {}}
        evidence = rows(payloads[tag + ".queries.csv.operations.csv"])
        assert len(evidence) == 90000
        for i, item in enumerate(evidence):
            cycle, kind = divmod(i, 3)
            id = (cycle // 10000 * 65537 + cycle % 10000 * 8191) % 10000
            assert (int(item["cycle"]), int(item["id"]), int(item["operation"])) == (cycle, id, kind)
            value = float(item["latency_us"])
            assert math.isfinite(value) and value >= 0
            operations += 1
        for i, name in enumerate(["update", "remove", "add"]):
            values = [float(x["latency_us"]) for x in evidence if int(x["operation"]) == i]
            metric["operations"][name] = {"p50_us": quantile(values, .5),
                "p99_us": quantile(values, .99), "api_ops_s": 1e6 * len(values) / sum(values)}
        receipt = json.loads(payloads[record["dataset"] + ".receipt.json"])
        for phase in ["initial", "final"]:
            prefix = tag + ".queries.csv" + (".initial" if phase == "initial" else "")
            truth_name = "groundtruth.ivecs" if phase == "initial" else "changed-groundtruth.ivecs"
            truth_data = payloads[record["dataset"] + "." + truth_name]
            assert sha(truth_data) == receipt["files"][truth_name]["sha256"]
            truth = [set(struct.unpack_from("<10i", truth_data, q * 44 + 4)) for q in range(600)]
            neighbors = rows(payloads[prefix + ".neighbors.csv"])
            hits = rows(payloads[prefix])
            assert len(neighbors) == 6000 and len(hits) == 600
            total = 0
            for q in range(600):
                sample = neighbors[q * 10:(q + 1) * 10]
                assert [(int(x["query"]), int(x["rank"])) for x in sample] == [(q, k) for k in range(10)]
                pairs = [(float.fromhex(x["distance"]), int(x["id"])) for x in sample]
                assert all(math.isfinite(d) for d, _ in pairs) and pairs == sorted(pairs)
                ids = {id for _, id in pairs}
                assert len(ids) == 10
                observed = len(ids & truth[q])
                assert observed == int(hits[q]["hits"])
                total += observed
                states += 1
            key = "initial_recall_at_k" if phase == "initial" else "recall_at_k"
            assert abs(total / 6000 - float(record["result"][key])) <= 1e-6
            metric[phase + "_recall"] = total / 6000
        summary.append(metric)
    for label in ["gist10k600", "cohere10k600"]:
        peers = [x for x in records if x["dataset"] == label]
        assert peers[0]["snapshot_sha256"] == peers[1]["snapshot_sha256"]
        for suffix in [".queries.csv", ".queries.csv.neighbors.csv",
                       ".queries.csv.initial", ".queries.csv.initial.neighbors.csv"]:
            assert payloads[label + "-control" + suffix] == payloads[label + "-candidate" + suffix]
    assert (operations, states) == (360000, 4800)
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
    expected = json.loads((root / "summary.json").read_text())
    assert expected == summary
    print("2 exact snapshot/ordered-result pairs, 360000 operations, 4800 truth intersections and raw API quantiles/hashes passed")


if __name__ == "__main__":
    main()
