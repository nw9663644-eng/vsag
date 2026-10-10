# Copyright 2024-present the vsag project
# SPDX-License-Identifier: Apache-2.0
"""Offline audit; does not rerun benchmarks or the exhaustive truth generator."""
import csv
import gzip
import hashlib
import io
import json
import math
from pathlib import Path
import struct
import tarfile


def sha(data):
    return hashlib.sha256(data).hexdigest()


def table(data):
    return list(csv.DictReader(io.StringIO(data.decode())))


def quantile(values, fraction):
    return sorted(values)[max(1, math.ceil(len(values) * fraction)) - 1]


def audit(root):
    for line in (root / "SHA256SUMS").read_text().splitlines():
        digest, name = line.split("  ", 1)
        assert sha((root / name).read_bytes()) == digest
    with tarfile.open(root / "raw.tar.gz") as archive:
        data = {m.name.removeprefix("./"): archive.extractfile(m).read()
                for m in archive if m.isfile()}
    assert set(data) == set(json.loads((root / "members.json").read_text()))
    for name, digest in json.loads((root / "members.json").read_text()).items():
        assert sha(data[name]) == digest
    identity = json.loads((root / "identity.json").read_text())
    validation = json.loads(data["validation-commands.json"])
    assert len(validation) == 10 and all(row["exit"] == 0 for row in validation)
    assert sha(data["measured-state.h"]) == identity["source_sha256"]["src/lite/rabitq_graph_state.h"]
    builds = json.loads(data["identity.json"])["variants"]
    assert sha(data["previous-state.h"]) == identity["previous_header_sha256"]
    records = json.loads((root / "rows.json").read_text())
    assert len(records) == 4
    summary = []
    mutations = states = 0
    for record in records:
        label, variant = record["dataset"], record["variant"]
        tag = label + "-" + variant
        result = record["result"]
        assert record["exit"] == 0
        assert result["query_ef_search"] == "512" and result["ef_search"] == "128"
        assert result["max_degree"] == "16" and result["mutation_mode"] == "all"
        assert identity["variants"][variant]["sha256"] == builds[variant]["sha256"]
        command = json.loads(data[tag + ".command.json"])
        assert command["environment"]["LD_LIBRARY_PATH"] in data[tag + ".ldd"].decode()
        assert command["environment"]["VSAG_GRAPH_CRUD_MODE"] == "all"
        receipt = json.loads(data[label + ".receipt.json"])
        for name in ("queries.fvecs", "groundtruth.ivecs", "changed-groundtruth.ivecs"):
            blob = data[label + "." + name]
            assert len(blob) == receipt["files"][name]["bytes"]
            assert sha(blob) == receipt["files"][name]["sha256"]
        # Large replacement matrices are regenerated from the preserved base and recipe.
        assert label + ".replacement.fvecs" not in data
        operations = table(data[tag + ".queries.csv.operations.csv"])
        assert len(operations) == 90000
        for position, row in enumerate(operations):
            cycle, operation = divmod(position, 3)
            target = (cycle // 10000 * 65537 + cycle % 10000 * 8191) % 10000
            assert (int(row["cycle"]), int(row["id"]), int(row["operation"])) == (cycle, target, operation)
            assert math.isfinite(float(row["latency_us"])) and float(row["latency_us"]) >= 0
        values = [float(row["latency_us"]) for row in operations]
        metric = {"dataset": label, "variant": variant, "crud_ms": float(result["crud_ms"]),
                  "operations": {name: {"p50_us": quantile([float(r["latency_us"]) for r in operations if int(r["operation"]) == kind], .5),
                                       "p99_us": quantile([float(r["latency_us"]) for r in operations if int(r["operation"]) == kind], .99)}
                                 for kind, name in enumerate(("update", "remove", "add"))},
                  "mutation_ops_s": len(values) * 1000 / float(result["crud_ms"]),
                  "snapshot_bytes": int(result["snapshot_bytes"]),
                  "external_peak_rss_kib": record["external_peak_rss_kib"]}
        mutations += len(operations)
        for initial in (True, False):
            prefix = tag + ".queries.csv" + (".initial" if initial else "")
            blob = data[label + (".groundtruth.ivecs" if initial else ".changed-groundtruth.ivecs")]
            assert len(blob) == 600 * 44
            assert all(struct.unpack_from("<i", blob, i * 44)[0] == 10 for i in range(600))
            truth = [set(struct.unpack_from("<10i", blob, i * 44 + 4)) for i in range(600)]
            neighbors, hits = table(data[prefix + ".neighbors.csv"]), table(data[prefix])
            assert len(neighbors) == 6000 and len(hits) == 600
            total = 0
            for q in range(600):
                part = neighbors[q * 10:(q + 1) * 10]
                assert [(int(r["query"]), int(r["rank"])) for r in part] == [(q, k) for k in range(10)]
                pairs = [(float.fromhex(r["distance"]), int(r["id"])) for r in part]
                assert pairs == sorted(pairs) and all(math.isfinite(v) for v, _ in pairs)
                ids = {i for _, i in pairs}
                assert len(ids) == 10 and all(0 <= i < 10000 for i in ids)
                count = len(ids & truth[q])
                assert (int(hits[q]["query"]), int(hits[q]["hits"]), int(hits[q]["k"])) == (q, count, 10)
                total += count
                states += 1
            latencies = table(data[prefix + ".latencies.csv"])
            assert len(latencies) == 600
            vals = [float(row["latency_us"]) for row in latencies]
            assert all(math.isfinite(v) and v >= 0 for v in vals)
            phase = "initial" if initial else "final"
            metric[phase] = {"recall": total / 6000, "p50_us": quantile(vals, .5),
                             "p99_us": quantile(vals, .99)}
            assert abs(total / 6000 - float(result["initial_recall_at_k" if initial else "recall_at_k"])) < 1e-6
            if not initial:
                assert metric[phase]["p50_us"] == float(result["search_p50_us"])
                assert metric[phase]["p99_us"] == float(result["search_p99_us"])
        summary.append(metric)
    for label in ("gist10k600", "cohere10k600"):
        pair = [r for r in records if r["dataset"] == label]
        assert pair[0]["snapshot_sha256"] == pair[1]["snapshot_sha256"]
        for phase in ("", ".initial"):
            for suffix in ("", ".neighbors.csv"):
                assert data[label + "-candidate.queries.csv" + phase + suffix] == data[label + "-control.queries.csv" + phase + suffix]
    coverage = json.loads((root / "coverage.json").read_text())
    assert coverage["fresh_counters"] is True
    lines = {}
    with tarfile.open(root / "coverage-raw.tar.gz") as archive:
        for member in archive:
            if not member.isfile():
                continue
            obj = json.loads(gzip.decompress(archive.extractfile(member).read()))
            for file in obj["files"]:
                name = str(Path(file["file"]))
                for line in file["lines"]:
                    key = (name, line["line_number"])
                    lines[key] = lines.get(key, False) or line["count"] > 0
    for scope, expected in coverage["scopes"].items():
        vals = []
        for (name, number), covered in lines.items():
            lite = ("/src/lite/" in name or "/include/vsag/lite/" in name) and not name.endswith("_test.cpp")
            simd = "/src/simd/" in name and not name.endswith("_test.cpp")
            if (scope == "lite" and lite) or (scope == "shared_simd" and simd) or (scope == "combined" and (lite or simd)):
                vals.append(covered)
        assert (sum(vals), len(vals)) == (expected["covered"], expected["total"])
        assert expected["percent"] >= 90
    assert (mutations, states) == (360000, 4800)
    return summary


if __name__ == "__main__":
    root = Path(__file__).resolve().parent
    observed = audit(root)
    assert observed == json.loads((root / "summary.json").read_text())
    print("4 builders, 360000 Update/Remove/Add operations, 4800 truth intersections, paired snapshots/ordered results, fresh coverage and hashes passed")
