# Copyright 2024-present the vsag project
# SPDX-License-Identifier: Apache-2.0
"""Verify retained logs, hashes, matched rounds, and fresh gcov union."""
import csv
import gzip
import hashlib
import io
import json
from pathlib import Path
import statistics
import tarfile

def digest(blob):
    return hashlib.sha256(blob).hexdigest()

def derive(out):
    identity = json.loads((out / "identity.json").read_text())
    rows = json.loads((out / "rows.json").read_text())
    members = json.loads((out / "members.json").read_text())
    with tarfile.open(out / "raw.tar.gz") as tar:
        raw = {m.name.removeprefix("./"): tar.extractfile(m).read()
               for m in tar if m.isfile()}
    assert {n: digest(b) for n, b in raw.items()} == members
    assert len(rows) == 60 and identity["pairs_per_dataset"] == 15
    assert identity["incoming_adjacency"] is False and identity["policy"] == "NONE"
    control = raw["control-snapshot.h"].decode()
    needle = ('    std::unordered_set<int64_t> unique_ids;\n'
              '    for (int64_t id : ids) {\n'
              '        codec_require(unique_ids.insert(id).second, "duplicate mutable snapshot ID");\n'
              '    }\n')
    assert control.count(needle) == 1
    expected = control.replace("#include <unordered_set>\n", "").replace(
        needle, "    // MutableGraphState rejects duplicate IDs while building its required slot map.\n")
    assert raw["candidate-snapshot.h"].decode() == expected
    variants = identity["variants"]
    for variant in variants:
        assert digest(raw[variant + "-snapshot.h"]) == variants[variant]["snapshot_header_sha256"]
        assert "/lite/rabitq_snapshot.h" in raw[variant + ".dependencies.txt"].decode()
    shared = set(variants["control"]["header_sha256"]) - {"rabitq_snapshot.h"}
    assert all(variants["control"]["header_sha256"][p] == variants["candidate"]["header_sha256"][p]
               for p in shared)
    summary = {}
    for dataset in ("gist", "cohere"):
        spec = identity["datasets"][dataset]
        builder = list(csv.DictReader(io.StringIO(raw[dataset + ".builder.stdout"].decode())))
        assert len(builder) == 1 and builder[0] == spec["builder_result"]
        assert int(builder[0]["rounds"]) == 0 and int(builder[0]["base_count"]) == 10000
        dim = 960 if dataset == "gist" else 768
        assert int(builder[0]["dim"]) == dim
        assert spec["snapshot_bytes"] == 96 + 4 * dim + 4 * ((dim + 7) // 8) + 10000 * (
            40 + 8 * ((dim + 7) // 8)) + 8 * 160000
        chosen = [r for r in rows if r["dataset"] == dataset]
        assert len(chosen) == 30
        expected_order = [(p, v) for p in range(15) for v in (
            ("control", "candidate") if p % 2 == 0 else ("candidate", "control"))]
        assert [(r["pair"], r["variant"]) for r in chosen] == expected_order
        for row in chosen:
            metrics = list(csv.DictReader(io.StringIO(raw[row["tag"] + ".stdout"].decode())))
            assert len(metrics) == 1 and metrics[0] == row["result"]
            assert row["exit"] == 0 and row["roundtrip_sha256"] == spec["snapshot_sha256"]
            assert int(row["result"]["count"]) == 10000
            assert int(row["result"]["dim"]) == dim
            assert int(row["result"]["edges"]) == 160000
            assert int(row["result"]["incoming_edges"]) == 0
            assert float(row["result"]["load_ms"]) > 0
        for pair in range(15):
            c, n = [next(r["result"] for r in chosen if r["pair"] == pair and r["variant"] == v)
                    for v in ("control", "candidate")]
            # Only wall time / process allocation state can differ.
            for key in c:
                if key not in ("load_ms", "baseline_rss_kib", "resident_rss_kib", "peak_rss_kib"):
                    assert c[key] == n[key], (dataset, pair, key)
        data = {}
        for variant in ("control", "candidate"):
            results = [r["result"] for r in chosen if r["variant"] == variant]
            data[variant] = {
                "load_ms": statistics.median(float(r["load_ms"]) for r in results),
                "resident_increment_kib": statistics.median(
                    int(r["resident_rss_kib"]) - int(r["baseline_rss_kib"]) for r in results),
                "known_capacity_bytes": int(results[0]["known_capacity_bytes"])}
        data["load_change_percent"] = (data["candidate"]["load_ms"] / data["control"]["load_ms"] - 1) * 100
        data["candidate_faster_pairs"] = sum(
            float(next(r["result"]["load_ms"] for r in chosen if r["pair"] == p and r["variant"] == "candidate"))
            < float(next(r["result"]["load_ms"] for r in chosen if r["pair"] == p and r["variant"] == "control"))
            for p in range(15))
        summary[dataset] = data
    commands = json.loads((out / "validation-commands.json").read_text())
    assert len(commands) == 12 and all(r["exit"] == 0 for r in commands)
    for tag, count in (("release", 6), ("sanitize-final", 5), ("coverage", 5), ("disabled", 4)):
        assert f"100% tests passed, 0 tests failed out of {count}" in raw[tag + "-test.log"].decode()
    lines = {}
    with tarfile.open(out / "coverage-raw.tar.gz") as tar:
        files = [m for m in tar if m.isfile()]
        assert len(files) == 19
        for member in files:
            for f in json.loads(gzip.decompress(tar.extractfile(member).read()))["files"]:
                for line in f["lines"]:
                    key = (f["file"], line["line_number"])
                    lines[key] = lines.get(key, False) or line["count"] > 0
    scopes = {}
    for scope in ("lite", "shared_simd", "combined"):
        selected = []
        for (name, _), covered in lines.items():
            lite = ("/src/lite/" in name or "/include/vsag/lite/" in name) and not name.endswith("_test.cpp")
            simd = "/src/simd/" in name and not name.endswith("_test.cpp")
            if (scope == "lite" and lite) or (scope == "shared_simd" and simd) or (
                    scope == "combined" and (lite or simd)):
                selected.append(covered)
        scopes[scope] = {"covered": sum(selected), "total": len(selected),
                         "percent": sum(selected) * 100 / len(selected)}
        assert scopes[scope]["percent"] >= 90
    assert scopes == json.loads((out / "coverage.json").read_text())["scopes"]
    return {"fresh_loaders": 60, "exact_round_trips": 60, "summary": summary,
            "coverage_scopes": scopes, "raw_members": len(raw),
            "raw_uncompressed_bytes": sum(len(b) for b in raw.values())}

if __name__ == "__main__":
    out = Path(__file__).resolve().parent
    result = derive(out)
    assert result == json.loads((out / "summary.json").read_text())
    for name, value in json.loads((out / "SHA256SUMS").read_text()).items():
        assert digest((out / name).read_bytes()) == value, name
    print(json.dumps(result, indent=2))
