# Copyright 2024-present the vsag project
# SPDX-License-Identifier: Apache-2.0
"""Audit persistent replay and fresh-final-data controls without extracting archive paths."""
import collections
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import struct
import tarfile


def rows(payload):
    return list(csv.DictReader(io.StringIO(payload.decode())))


def quantile(values, fraction):
    return sorted(values)[max(1, math.ceil(len(values) * fraction)) - 1]


def truth(payload):
    assert len(payload) == 600 * 44
    return [set(struct.unpack_from("<10i", payload, i * 44 + 4)) for i in range(600)]


def main():
    root = Path(__file__).resolve().parent
    sha = lambda b: hashlib.sha256(b).hexdigest()
    for line in (root / "SHA256SUMS").read_text().splitlines():
        digest, file = line.split("  ", 1)
        assert sha((root / file).read_bytes()) == digest
    with tarfile.open(root / "raw.tar.gz") as archive:
        payloads = {m.name.removeprefix("./"): archive.extractfile(m).read()
                    for m in archive if m.isfile()}
    for file, digest in json.loads((root / "members.json").read_text()).items():
        assert sha(payloads[file]) == digest
    identity = json.loads((root / "identity.json").read_text())
    assert sha(payloads["measured-graph-crud-quality.cpp"]) == identity["source_sha256"]["lite/benchmark/graph_crud_quality.cpp"]
    assert sha(payloads["measured-prepare.py"]) == identity["source_sha256"]["lite/benchmark/prepare_persistent_crud.py"]
    records = json.loads((root / "rows.json").read_text())
    rebuild = json.loads((root / "rebuild-rows.json").read_text())
    assert len(records) == len(rebuild) == 6
    summary = []
    states = operations = 0
    for record in records + rebuild:
        is_rebuild = record in rebuild
        tag = record["dataset"] + "-" + record["storage"] + ("-rebuild" if is_rebuild else "")
        result = record["result"]
        receipt = json.loads(payloads[record["dataset"] + ".receipt.json"])
        for suffix in ["queries.fvecs", "groundtruth.ivecs", "changed-groundtruth.ivecs"]:
            data = payloads[record["dataset"] + "." + suffix]
            assert len(data) == receipt["files"][suffix]["bytes"]
            assert sha(data) == receipt["files"][suffix]["sha256"]
        assert record["exit"] == 0 and result["query_ef_search"] == "512"
        assert result["max_degree"] == "16" and result["ef_search"] == "128"
        assert int(payloads[tag + ".peak_kib"]) == record["external_peak_rss_kib"]
        metric = {"dataset": record["dataset"], "storage": record["storage"],
                  "kind": "rebuild" if is_rebuild else "maintained",
                  "external_peak_rss_kib": record["external_peak_rss_kib"],
                  "snapshot_bytes": int(result["snapshot_bytes"]),
                  "save_ms": float(result["save_ms"]), "load_ms": float(result["load_ms"])}
        for phase in (["final"] if is_rebuild else ["initial", "final"]):
            path = tag + ".queries.csv" + (".initial" if phase == "initial" else "")
            expected = truth(payloads[record["dataset"] + ("." if phase == "initial" else ".changed-") + "groundtruth.ivecs"])
            hits = rows(payloads[path])
            neighbors = collections.defaultdict(list)
            for item in rows(payloads[path + ".neighbors.csv"]):
                query = int(item["query"])
                assert int(item["rank"]) == len(neighbors[query])
                distance = float.fromhex(item["distance"])
                assert math.isfinite(distance)
                pair = (distance, int(item["id"]))
                if neighbors[query]:
                    assert pair >= neighbors[query][-1]
                neighbors[query].append(pair)
            total = 0
            assert len(hits) == len(neighbors) == 600
            for query, row in enumerate(hits):
                ids = {id for _, id in neighbors[query]}
                assert len(ids) == len(neighbors[query]) == int(row["k"]) == 10
                observed = len(ids & expected[query])
                assert int(row["query"]) == query and observed == int(row["hits"])
                total += observed
                states += 1
            recall = total / 6000
            assert abs(recall - float(result["initial_recall_at_k" if phase == "initial" else "recall_at_k"])) <= 1e-6
            samples = rows(payloads[path + ".latencies.csv"])
            times = [float(x["latency_us"]) for x in samples]
            assert len(times) == 600 and all(math.isfinite(x) and x >= 0 for x in times)
            metric[phase] = {"recall": recall, "p50_us": quantile(times, .5),
                             "p99_us": quantile(times, .99), "qps": 1e6 * len(times) / sum(times)}
            if phase == "final":
                for f, key in [(.5, "search_p50_us"), (.99, "search_p99_us")]:
                    assert abs(quantile(times, f) - float(result[key])) <= 1e-6
        if not is_rebuild:
            sample = rows(payloads[tag + ".queries.csv.operations.csv"])
            assert len(sample) == 90000 and result["persistent_replacements"] == "30000"
            by_kind = collections.defaultdict(list)
            for i, row in enumerate(sample):
                cycle, op = divmod(i, 3)
                id = ((cycle // 10000) * 65537 + (cycle % 10000) * 8191) % 10000
                assert (int(row["cycle"]), int(row["id"]), int(row["operation"])) == (cycle, id, op)
                latency = float(row["latency_us"])
                assert math.isfinite(latency) and latency >= 0
                by_kind[op].append(latency)
                operations += 1
            metric["operations"] = {name: {"count": len(by_kind[i]),
                "p50_us": quantile(by_kind[i], .5), "p99_us": quantile(by_kind[i], .99),
                "api_ops_s": 1e6 * len(by_kind[i]) / sum(by_kind[i])}
                for i, name in enumerate(["update", "remove", "add"])}
            metric["crud_block_ops_s"] = 90000 / (float(result["crud_ms"]) / 1000)
        summary.append(metric)
    assert (states, operations) == (10800, 540000)
    (root / "verified-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print("12 builders, 10800 truth intersections, 540000 scheduled operations, raw quantiles and hashes passed")


if __name__ == "__main__":
    main()
