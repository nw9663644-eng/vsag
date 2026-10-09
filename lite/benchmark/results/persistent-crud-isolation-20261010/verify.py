# Copyright 2024-present the vsag project
# SPDX-License-Identifier: Apache-2.0
"""Independent raw audit for separate persistent mutation paths."""
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
    identity = json.loads((root / "identity.json").read_text())
    assert identity["library_sha256"] == "e9613ace68d6b81f5ff38e4ff86d7f1dfa18fd2effc2131c37729573391d97c4"
    assert sha(payloads["measured-tool.cpp"]) == identity["source_sha256"]["lite/benchmark/graph_crud_quality.cpp"]
    records = json.loads((root / "rows.json").read_text())
    assert len(records) == 8
    summary = []
    mutations = states = 0
    for record in records:
        label = record["dataset"]
        tag = label + "-" + record["storage"] + "-" + record["mode"]
        result = record["result"]
        assert result["mutation_mode"] == record["mode"] and record["exit"] == 0
        assert result["persistent_replacements"] == "30000"
        assert (result["max_degree"], result["ef_search"], result["query_ef_search"]) == ("16", "128", "512")
        metric = {"dataset": label, "storage": record["storage"], "mode": record["mode"],
                  "crud_ms": float(result["crud_ms"]), "snapshot_bytes": int(result["snapshot_bytes"]),
                  "peak_kib": record["external_peak_rss_kib"], "operations": {}}
        assert int(payloads[tag + ".peak_kib"]) == record["external_peak_rss_kib"]
        receipt = json.loads(payloads[label + ".receipt.json"])
        for name in ["queries.fvecs", "groundtruth.ivecs", "changed-groundtruth.ivecs"]:
            data = payloads[label + "." + name]
            assert sha(data) == receipt["files"][name]["sha256"]
            assert len(data) == receipt["files"][name]["bytes"]
        kinds = [0] if record["mode"] == "update" else [1, 2]
        sample = rows(payloads[tag + ".queries.csv.operations.csv"])
        assert len(sample) == 30000 * len(kinds)
        for i, item in enumerate(sample):
            cycle, operation = divmod(i, len(kinds))
            id = (cycle // 10000 * 65537 + cycle % 10000 * 8191) % 10000
            assert (int(item["cycle"]), int(item["id"]), int(item["operation"])) == (cycle, id, kinds[operation])
            value = float(item["latency_us"])
            assert math.isfinite(value) and value >= 0
            mutations += 1
        for kind in kinds:
            values = [float(x["latency_us"]) for x in sample if int(x["operation"]) == kind]
            metric["operations"][str(kind)] = {"p50_us": quantile(values, .5), "p99_us": quantile(values, .99),
                                                "api_ops_s": 1e6 * len(values) / sum(values)}
        for phase in ["initial", "final"]:
            prefix = tag + ".queries.csv" + (".initial" if phase == "initial" else "")
            name = "groundtruth.ivecs" if phase == "initial" else "changed-groundtruth.ivecs"
            data = payloads[label + "." + name]
            assert len(data) == 600 * 44
            truth = [set(struct.unpack_from("<10i", data, q * 44 + 4)) for q in range(600)]
            neighbors = rows(payloads[prefix + ".neighbors.csv"])
            hits = rows(payloads[prefix])
            assert len(hits) == 600 and len(neighbors) == 6000
            total = 0
            for q in range(600):
                sample = neighbors[q * 10:(q + 1) * 10]
                assert [(int(x["query"]), int(x["rank"])) for x in sample] == [(q, i) for i in range(10)]
                pairs = [(float.fromhex(x["distance"]), int(x["id"])) for x in sample]
                assert all(math.isfinite(d) for d, _ in pairs) and pairs == sorted(pairs)
                ids = {id for _, id in pairs}
                assert len(ids) == 10
                observed = len(ids & truth[q])
                assert observed == int(hits[q]["hits"]) and int(hits[q]["query"]) == q
                total += observed
                states += 1
            key = "initial_recall_at_k" if phase == "initial" else "recall_at_k"
            assert abs(total / 6000 - float(result[key])) <= 1e-6
            values = [float(x["latency_us"]) for x in rows(payloads[prefix + ".latencies.csv"])]
            assert len(values) == 600 and all(math.isfinite(x) and x >= 0 for x in values)
            metric[phase] = {"recall": total / 6000, "p50_us": quantile(values, .5), "p99_us": quantile(values, .99)}
            if phase == "final":
                assert abs(metric[phase]["p50_us"] - float(result["search_p50_us"])) <= 1e-6
                assert abs(metric[phase]["p99_us"] - float(result["search_p99_us"])) <= 1e-6
        summary.append(metric)
    # Same initial construction despite different maintenance schedules.
    for label in ["gist10k600", "cohere10k600"]:
        for storage in ["fp32", "rabitq8"]:
            prefix = label + "-" + storage
            for suffix in [".queries.csv.initial", ".queries.csv.initial.neighbors.csv"]:
                assert payloads[prefix + "-update" + suffix] == payloads[prefix + "-replace" + suffix]
    assert (mutations, states) == (360000, 9600)
    assert json.loads((root / "summary.json").read_text()) == summary
    print("8 builders, 360000 mode-specific mutations, 9600 truth intersections, raw quantiles and hashes passed")


if __name__ == "__main__":
    main()
