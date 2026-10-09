# Copyright 2024-present the vsag project
# SPDX-License-Identifier: Apache-2.0
"""Audit full-candidate diagnostic and isolated incoming-protection prototype."""
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


def quantile(v, f):
    return sorted(v)[max(1, math.ceil(len(v) * f)) - 1]


def main():
    base = Path(__file__).resolve().parent.parent
    summary = {}
    mutations = states = 0
    for name in ["rabitq-model-ceiling-20261010",
                 "rabitq-update-incoming-candidate-20261010"]:
        root = base / name
        sha = lambda b: hashlib.sha256(b).hexdigest()
        for line in (root / "SHA256SUMS").read_text().splitlines():
            digest, file = line.split("  ", 1)
            assert sha((root / file).read_bytes()) == digest
        with tarfile.open(root / "raw.tar.gz") as archive:
            data = {m.name.removeprefix("./"): archive.extractfile(m).read()
                    for m in archive if m.isfile()}
        for file, digest in json.loads((root / "members.json").read_text()).items():
            assert sha(data[file]) == digest
        records = json.loads((root / "rows.json").read_text())
        identity = json.loads((root / "identity.json").read_text())
        model = "ceiling" in name
        if model:
            assert identity["library_sha256"] == "e9613ace68d6b81f5ff38e4ff86d7f1dfa18fd2effc2131c37729573391d97c4"
            assert sha(data["measured-tool.cpp"]) == identity["source_sha256"]["lite/benchmark/graph_crud_quality.cpp"]
        else:
            assert sha(data["candidate-header.h"]) == identity["candidate_header_sha256"]
            assert identity["default_enabled"] is False
        assert len(records) == 4
        observed = []
        for record in records:
            label = record["dataset"]
            tag = label + "-" + record["mode" if model else "variant"]
            result = record["result"]
            assert record["exit"] == 0 and result["query_ef_search"] == "512"
            assert result["max_degree"] == "16" and result["ef_search"] == "128"
            receipt = json.loads(data[label + ".receipt.json"])
            for suffix in ["queries.fvecs", "groundtruth.ivecs", "changed-groundtruth.ivecs"]:
                payload = data[label + "." + suffix]
                assert len(payload) == receipt["files"][suffix]["bytes"]
                assert sha(payload) == receipt["files"][suffix]["sha256"]
            metric = {"dataset": label, "case": record["mode" if model else "variant"],
                      "crud_ms": float(result["crud_ms"])}
            sample = rows(data[tag + ".queries.csv.operations.csv"])
            kinds = [0] if not model or record["mode"] == "update" else [1, 2]
            assert len(sample) == 30000 * len(kinds)
            for i, item in enumerate(sample):
                cycle, kind = divmod(i, len(kinds))
                id = (cycle // 10000 * 65537 + cycle % 10000 * 8191) % 10000
                assert (int(item["cycle"]), int(item["id"]), int(item["operation"])) == (cycle, id, kinds[kind])
                v = float(item["latency_us"])
                assert math.isfinite(v) and v >= 0
                mutations += 1
            phases = ["initial", "final"] + (["diagnostic.initial", "diagnostic.final"] if model else [])
            for phase in phases:
                initial = phase.endswith("initial")
                prefix = tag + ".queries.csv" + ("" if phase == "final" else "." + phase)
                payload = data[label + ("." if initial else ".changed-") + "groundtruth.ivecs"]
                assert len(payload) == 600 * 44
                truth = [set(struct.unpack_from("<10i", payload, q * 44 + 4)) for q in range(600)]
                neighbors = rows(data[prefix + ".neighbors.csv"])
                hits = rows(data[prefix])
                assert len(hits) == 600 and len(neighbors) == 6000
                total = 0
                for q in range(600):
                    part = neighbors[q * 10:(q + 1) * 10]
                    assert [(int(x["query"]), int(x["rank"])) for x in part] == [(q, r) for r in range(10)]
                    pairs = [(float.fromhex(x["distance"]), int(x["id"])) for x in part]
                    assert pairs == sorted(pairs) and all(math.isfinite(d) for d, _ in pairs)
                    ids = {id for _, id in pairs}
                    assert len(ids) == 10
                    value = len(ids & truth[q])
                    assert int(hits[q]["query"]) == q and int(hits[q]["hits"]) == value
                    total += value
                    states += 1
                values = [float(x["latency_us"]) for x in rows(data[prefix + ".latencies.csv"])]
                assert len(values) == 600 and all(math.isfinite(x) and x >= 0 for x in values)
                metric[phase] = {"recall": total / 6000, "p50_us": quantile(values, .5),
                                 "p99_us": quantile(values, .99)}
                reference = (record["diagnostic"]["initial_recall" if initial else "final_recall"]
                             if phase.startswith("diagnostic") else
                             result["initial_recall_at_k" if initial else "recall_at_k"])
                assert abs(total / 6000 - float(reference)) <= 1e-6
            observed.append(metric)
            if model:
                assert record["diagnostic"]["budget"] == "10000"
                assert rows(data[tag + ".queries.csv.diagnostic.summary.csv"])[0] == record["diagnostic"]
            else:
                command = json.loads(data[tag + ".command.json"])
                assert command["environment"]["LD_LIBRARY_PATH"] in data[tag + ".ldd"].decode()
        for label in ["gist10k600", "cohere10k600"]:
            if model:
                for phase in ["initial", "final"]:
                    for suffix in ["", ".neighbors.csv"]:
                        assert data[label + "-update.queries.csv.diagnostic." + phase + suffix] == data[label + "-replace.queries.csv.diagnostic." + phase + suffix]
            else:
                for suffix in ["", ".neighbors.csv"]:
                    assert data[label + "-control.queries.csv.initial" + suffix] == data[label + "-candidate.queries.csv.initial" + suffix]
        summary[name] = observed
    assert (mutations, states) == (300000, 14400)
    assert summary == json.loads((base / "rabitq-model-ceiling-20261010/summary.json").read_text())
    print("8 builders, 300000 mutations, 14400 formal/diagnostic truth intersections, raw hashes/schedules/quantiles passed")


if __name__ == "__main__":
    main()
