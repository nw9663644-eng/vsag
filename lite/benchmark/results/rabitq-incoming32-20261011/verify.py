# Copyright 2024-present the vsag project
# SPDX-License-Identifier: Apache-2.0
"""Independent raw audit; never reruns timing or groundtruth generation."""
import csv
import gzip
import hashlib
import io
import json
import math
import statistics
from pathlib import Path
import struct
import tarfile


def sha(blob):
    return hashlib.sha256(blob).hexdigest()


def table(blob):
    return list(csv.DictReader(io.StringIO(blob.decode())))


def q(values, fraction):
    return sorted(values)[max(1, math.ceil(len(values) * fraction)) - 1]


def derive(root):
    with tarfile.open(root / "raw.tar.gz") as archive:
        raw = {m.name.removeprefix("./"): archive.extractfile(m).read()
               for m in archive if m.isfile()}
    manifests = json.loads((root / "members.json").read_text())
    assert set(raw) == set(manifests)
    assert all(sha(raw[name]) == value for name, value in manifests.items())
    identity = json.loads((root / "identity.json").read_text())
    assert json.loads(raw["identity.json"]) == identity
    header = raw["candidate-state.h"]
    assert sha(raw["control-state.h"]) == identity["control_header_sha256"]
    assert sha(header) == identity["source_sha256"]["src/lite/rabitq_graph_state.h"]
    flag = b"bool use_incoming_adjacency = false"
    assert header.count(flag) == 1
    for variant in ("control", "candidate"):
        original = raw[variant + "-state.h"]
        assert original.count(flag) == 1
        compiled = original.replace(flag, b"bool use_incoming_adjacency = true", 1)
        spec = identity["variants"][variant]
        assert compiled == raw[variant + ".compiled-state.h"]
        assert sha(compiled) == spec["compiled_state_header_sha256"]
        assert spec["incoming_adjacency"] is True
        assert spec["incoming_slot_bits"] == (32 if variant == "candidate" else 64)
        assert spec["public_policy"] == "NONE"
        assert str(Path(spec["library_path"]).parent / "lite/rabitq_graph_state.h").encode() in raw[variant + ".dependencies.txt"]
    validation = json.loads(raw["validation.json"])
    assert validation == json.loads((root / "validation.json").read_text())
    assert validation["production_change"] is True and validation["public_default_changed"] is False
    commands = json.loads(raw["validation-commands.json"])
    assert commands == json.loads((root / "validation-commands.json").read_text())
    assert len(commands) == 10 and all(command["exit"] == command["expected_exit"] for command in commands)
    assert sha(raw["memory-probe.cpp"]) == sha((root / "memory-probe.cpp").read_bytes())
    assert raw["source-rabitq_graph_state.h"] == header
    records = json.loads((root / "rows.json").read_text())
    assert len(records) == 12 and records == json.loads(raw["rows.json"])
    summary = []
    total_ops = total_states = total_probes = 0
    for row in records:
        tag, result = row["tag"], row["result"]
        assert row["exit"] == 0 and result["mutation_mode"] == "all"
        assert (result["base_count"], result["query_count"], result["rounds"], result["crud_ops"],
                result["max_degree"], result["ef_search"], result["query_ef_search"]) == (
                    "10000", "600", "3", "10000", "16", "128", "512")
        command = json.loads(raw[tag + ".command.json"])
        assert command["environment"]["LD_LIBRARY_PATH"] in raw[tag + ".ldd"].decode()
        assert command["environment"]["VSAG_GRAPH_CRUD_MODE"] == "all"
        receipt = json.loads(raw[row["dataset"] + ".receipt.json"])
        for name in ("queries.fvecs", "groundtruth.ivecs", "changed-groundtruth.ivecs"):
            blob = raw[row["dataset"] + "." + name]
            assert len(blob) == receipt["files"][name]["bytes"]
            assert sha(blob) == receipt["files"][name]["sha256"]
        ops = table(raw[tag + ".queries.csv.operations.csv"])
        assert len(ops) == 90000
        for position, sample in enumerate(ops):
            cycle, kind = divmod(position, 3)
            target = (cycle // 10000 * 65537 + cycle % 10000 * 8191) % 10000
            assert (int(sample["cycle"]), int(sample["id"]), int(sample["operation"])) == (cycle, target, kind)
            assert math.isfinite(float(sample["latency_us"])) and float(sample["latency_us"]) >= 0
        total_ops += len(ops)
        item = {"dataset": row["dataset"], "variant": row["variant"], "repeat": row["repeat"],
                "crud_ms": float(result["crud_ms"]), "mutation_ops_s": 90000000 / float(result["crud_ms"]),
                "external_peak_rss_kib": row["external_peak_rss_kib"],
                "build_ms": float(result["build_ms"]), "warm_public_load_ms": float(result["load_ms"]),
                "snapshot_bytes": int(result["snapshot_bytes"]),
                "operations": {}}
        for kind, name in enumerate(("update", "remove", "add")):
            values = [float(s["latency_us"]) for s in ops if int(s["operation"]) == kind]
            item["operations"][name] = {"p50_us": q(values, .5), "p99_us": q(values, .99)}
        for phase in ("initial", "final"):
            prefix = tag + ".queries.csv" + (".initial" if phase == "initial" else "")
            blob = raw[row["dataset"] + (".groundtruth.ivecs" if phase == "initial" else ".changed-groundtruth.ivecs")]
            assert len(blob) == 26400
            assert all(struct.unpack_from("<i", blob, i * 44)[0] == 10 for i in range(600))
            truth = [set(struct.unpack_from("<10i", blob, i * 44 + 4)) for i in range(600)]
            neighbors, hits = table(raw[prefix + ".neighbors.csv"]), table(raw[prefix])
            assert len(neighbors) == 6000 and len(hits) == 600
            total = 0
            for query in range(600):
                part = neighbors[query * 10:(query + 1) * 10]
                assert [(int(s["query"]), int(s["rank"])) for s in part] == [(query, k) for k in range(10)]
                pairs = [(float.fromhex(s["distance"]), int(s["id"])) for s in part]
                assert pairs == sorted(pairs) and all(math.isfinite(v) for v, _ in pairs)
                ids = {i for _, i in pairs}
                assert len(ids) == 10 and all(0 <= i < 10000 for i in ids)
                count = len(ids & truth[query])
                assert (int(hits[query]["query"]), int(hits[query]["hits"]), int(hits[query]["k"])) == (query, count, 10)
                total += count
                total_states += 1
            latencies = table(raw[prefix + ".latencies.csv"])
            values = [float(s["latency_us"]) for s in latencies]
            assert len(values) == 600 and all(math.isfinite(v) and v >= 0 for v in values)
            item[phase] = {"recall": total / 6000, "p50_us": q(values, .5), "p99_us": q(values, .99)}
            assert abs(total / 6000 - float(result["initial_recall_at_k" if phase == "initial" else "recall_at_k"])) < 1e-6
        probes = row["load_probes"]
        assert len(probes) == 6
        probe_groups = {}
        for variant in ("control", "candidate"):
            group = [p for p in probes if p["variant"] == variant]
            assert {p["repeat"] for p in group} == {0, 1, 2}
            values = []
            for probe in group:
                assert probe["exit"] == 0
                data = table(raw[probe["tag"] + ".stdout"])
                assert len(data) == 1 and data[0] == probe["result"]
                assert json.loads(raw[probe["tag"] + ".command.json"])["snapshot_sha256"] == row["snapshot_sha256"]
                p = {key: float(value) if key == "load_ms" else int(value) for key, value in data[0].items()}
                assert p["count"] == 10000 and p["slot_entries"] == 10000
                assert p["dim"] == int(result["dim"])
                plane = (p["dim"] + 7) // 8
                assert int(result["snapshot_bytes"]) == 96 + 4 * p["dim"] + 4 * plane + 10000 * (40 + 8 * plane) + 8 * p["edges"]
                assert p["incoming_edges"] == p["edges"]
                width = 4 if variant == "candidate" else 8
                assert p["incoming_logical_bytes"] == 10000 * 24 + p["edges"] * width
                assert p["incoming_capacity_bytes"] == p["incoming_logical_bytes"]
                p["increment_rss_kib"] = p["resident_rss_kib"] - p["baseline_rss_kib"]
                values.append(p)
                total_probes += 1
            deterministic = ["count", "dim", "edges", "incoming_edges", "incoming_logical_bytes",
                             "incoming_capacity_bytes", "known_logical_bytes", "known_capacity_bytes",
                             "slot_entries", "slot_buckets"]
            assert all(len({p[key] for p in values}) == 1 for key in deterministic)
            probe_groups[variant] = {key: statistics.median([p[key] for p in values]) for key in values[0]}
        for key in ("count", "dim", "edges", "slot_entries", "slot_buckets"):
            assert probe_groups["control"][key] == probe_groups["candidate"][key]
        for category in ("logical", "capacity"):
            assert probe_groups["candidate"]["known_" + category + "_bytes"] - probe_groups["control"]["known_" + category + "_bytes"] == probe_groups["candidate"]["incoming_" + category + "_bytes"] - probe_groups["control"]["incoming_" + category + "_bytes"]
        item["same_snapshot_load_probes"] = probe_groups
        summary.append(item)
    paired = {}
    comparison = {}
    for label in ("gist10k600", "cohere10k600"):
        for repeat in range(3):
            tags = [label + "-" + variant + "-r" + str(repeat) for variant in ("control", "candidate")]
            pair = [r for r in records if r["dataset"] == label and r["repeat"] == repeat]
            assert pair[0]["snapshot_sha256"] == pair[1]["snapshot_sha256"]
            for suffix in ("", ".neighbors.csv", ".initial", ".initial.neighbors.csv"):
                assert raw[tags[0] + ".queries.csv" + suffix] == raw[tags[1] + ".queries.csv" + suffix]
            hits = [table(raw[tag + ".queries.csv"]) for tag in tags]
            delta = [int(b["hits"]) - int(a["hits"]) for a, b in zip(*hits)]
            paired[label + "-r" + str(repeat)] = {"extra_hits": sum(delta), "wins": sum(d > 0 for d in delta),
                "losses": sum(d < 0 for d in delta), "ties": sum(d == 0 for d in delta),
                "mean_recall_delta": sum(delta) / 6000,
                "initial_results_identical": raw[tags[0] + ".queries.csv.initial.neighbors.csv"] == raw[tags[1] + ".queries.csv.initial.neighbors.csv"],
                "final_results_identical": raw[tags[0] + ".queries.csv.neighbors.csv"] == raw[tags[1] + ".queries.csv.neighbors.csv"]}
        groups = [[s for s in summary if s["dataset"] == label and s["variant"] == v] for v in ("control", "candidate")]
        fields = ("crud_ms", "mutation_ops_s", "external_peak_rss_kib", "build_ms",
                  "warm_public_load_ms", "snapshot_bytes")
        comparison[label] = {field: {variant: statistics.median([s[field] for s in group])
                            for variant, group in zip(("control", "candidate"), groups)} for field in fields}
        comparison[label]["final_recall"] = {v: statistics.median([s["final"]["recall"] for s in group])
                                             for v, group in zip(("control", "candidate"), groups)}
        comparison[label]["operations"] = {name: {v: {key: statistics.median([s["operations"][name][key] for s in group])
                                        for key in ("p50_us", "p99_us")}
                                        for v, group in zip(("control", "candidate"), groups)}
                                        for name in ("update", "remove", "add")}
        comparison[label]["crud_change_percent"] = (comparison[label]["crud_ms"]["candidate"] /
                                                     comparison[label]["crud_ms"]["control"] - 1) * 100
    coverage = json.loads((root / "coverage.json").read_text())
    assert coverage["fresh_counters"] is True
    lines = {}
    with tarfile.open(root / "coverage-raw.tar.gz") as archive:
        for member in archive:
            if not member.isfile():
                continue
            for file in json.loads(gzip.decompress(archive.extractfile(member).read()))["files"]:
                name = str(Path(file["file"]))
                for line in file["lines"]:
                    key = (name, line["line_number"])
                    lines[key] = lines.get(key, False) or line["count"] > 0
    for scope, expected in coverage["scopes"].items():
        values = []
        for (name, number), covered in lines.items():
            lite = ("/src/lite/" in name or "/include/vsag/lite/" in name) and not name.endswith("_test.cpp")
            simd = "/src/simd/" in name and not name.endswith("_test.cpp")
            if (scope == "lite" and lite) or (scope == "shared_simd" and simd) or (scope == "combined" and (lite or simd)):
                values.append(covered)
        assert (sum(values), len(values)) == (expected["covered"], expected["total"])
        assert expected["percent"] >= 90
    assert (total_ops, total_states, total_probes) == (1080000, 14400, 72)
    return {"summary": summary, "paired": paired, "comparison": comparison,
            "audited_operations": total_ops, "audited_truth_states": total_states, "audited_load_probes": total_probes}


if __name__ == "__main__":
    root = Path(__file__).resolve().parent
    for line in (root / "SHA256SUMS").read_text().splitlines():
        digest, name = line.split("  ", 1)
        assert sha((root / name).read_bytes()) == digest
    assert derive(root) == json.loads((root / "summary.json").read_text())
    print("1080000 operations,14400 truth states,72 same-snapshot load probes and hashes verified")
