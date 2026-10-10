# Copyright 2024-present the vsag project
# SPDX-License-Identifier: Apache-2.0
"""Offline diagnostic audit; no benchmark rerun or independent exhaustive GT."""
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import struct
import tarfile


def sha(blob):
    return hashlib.sha256(blob).hexdigest()


def table(blob):
    return list(csv.DictReader(io.StringIO(blob.decode())))


def audit(root):
    for line in (root / "SHA256SUMS").read_text().splitlines():
        digest, name = line.split("  ", 1)
        assert sha((root / name).read_bytes()) == digest
    with tarfile.open(root / "raw.tar.gz") as archive:
        data = {m.name.removeprefix("./"): archive.extractfile(m).read() for m in archive if m.isfile()}
    manifest = json.loads((root / "members.json").read_text())
    assert set(manifest) == set(data)
    assert all(sha(data[name]) == digest for name, digest in manifest.items())
    identity = json.loads((root / "identity.json").read_text())
    spec = identity["variants"]["profile"]
    assert spec["public_policy"] == "NONE"
    assert sha(data["formatted-state.h"]) == spec["compiled_state_header_sha256"]
    folder = str(Path(spec["library_path"]).parent)
    for name in ("lite/rabitq_graph_state.h", "lite/rabitq_codec.h", "mutation-profile.h"):
        assert (folder + "/" + name).encode() in data["profile.dependencies.txt"]
    assert sha(data["candidate-state.h"]) == identity["source_sha256"]["src/lite/rabitq_graph_state.h"]
    rows = json.loads((root / "rows.json").read_text())
    profiles = json.loads((root / "profiles.json").read_text())
    assert len(rows) == 2
    historical = root.parent / "rabitq-link-scratch-20261010"
    old = json.loads((historical / "rows.json").read_text())
    counts = {"mutations": 0, "truth_states": 0}
    summary = {}
    with tarfile.open(historical / "raw.tar.gz") as previous:
        for row in rows:
            tag, label, result = row["tag"], row["dataset"], row["result"]
            ref = next(v for v in old if v["dataset"] == label and v["variant"] == "control" and v["repeat"] == 0)
            assert row["exit"] == 0 and row["snapshot_sha256"] == ref["snapshot_sha256"]
            assert result["max_degree"] == "16" and result["ef_search"] == "128"
            assert result["query_ef_search"] == "512" and result["mutation_mode"] == "all"
            command = json.loads(data[tag + ".command.json"])
            assert command["environment"]["LD_LIBRARY_PATH"] in data[tag + ".ldd"].decode()
            receipt = json.loads(data[label + ".receipt.json"])
            for name in ("queries.fvecs", "groundtruth.ivecs", "changed-groundtruth.ivecs"):
                assert sha(data[label + "." + name]) == receipt["files"][name]["sha256"]
            operations = table(data[tag + ".queries.csv.operations.csv"])
            assert len(operations) == 90000
            for i, value in enumerate(operations):
                cycle, op = divmod(i, 3)
                target = (cycle // 10000 * 65537 + cycle % 10000 * 8191) % 10000
                assert (int(value["cycle"]), int(value["id"]), int(value["operation"])) == (cycle, target, op)
                assert float(value["latency_us"]) >= 0 and math.isfinite(float(value["latency_us"]))
            counts["mutations"] += len(operations)
            for initial in (True, False):
                prefix = tag + ".queries.csv" + (".initial" if initial else "")
                old_prefix = ref["tag"] + ".queries.csv" + (".initial" if initial else "")
                for suffix in ("", ".neighbors.csv"):
                    assert data[prefix + suffix] == previous.extractfile("./" + old_prefix + suffix).read()
                truth = data[label + (".groundtruth.ivecs" if initial else ".changed-groundtruth.ivecs")]
                assert len(truth) == 600 * 44
                neighbors, hits = table(data[prefix + ".neighbors.csv"]), table(data[prefix])
                assert len(neighbors) == 6000 and len(hits) == 600
                total = 0
                for q in range(600):
                    assert struct.unpack_from("<i", truth, q * 44)[0] == 10
                    gt = set(struct.unpack_from("<10i", truth, q * 44 + 4))
                    part = neighbors[q * 10:(q + 1) * 10]
                    assert [(int(v["query"]), int(v["rank"])) for v in part] == [(q, r) for r in range(10)]
                    found = {int(v["id"]) for v in part}
                    assert len(found) == 10
                    hit = len(found & gt)
                    assert int(hits[q]["hits"]) == hit
                    total += hit
                if not initial:
                    assert abs(total / 6000 - float(result["recall_at_k"])) < 1e-6
                counts["truth_states"] += 600
            stderr = data[tag + ".stderr"].decode()
            stages = table(stderr.split("PROFILE_BEGIN\n")[1].split("PROFILE_END")[0].encode())
            assert stages == profiles[label] and len(stages) == 24
            for op in ("add", "update", "remove"):
                subset = [v for v in stages if v["op"] == op]
                outer = next(v for v in subset if v["stage"] == "adapter")
                assert int(outer["calls"]) == 30000
                assert abs(sum(float(v["cpu_exclusive_us"]) for v in subset) -
                           float(outer["cpu_inclusive_us"])) < .01
                assert all(float(v["cpu_exclusive_us"]) >= 0 for v in subset)
            total = sum(float(v["cpu_exclusive_us"]) for v in stages)
            summary[label] = {stage: {"cpu_s": sum(float(v["cpu_exclusive_us"]) for v in stages if v["stage"] == stage) / 1e6,
                "percent": sum(float(v["cpu_exclusive_us"]) for v in stages if v["stage"] == stage) * 100 / total}
                for stage in sorted({v["stage"] for v in stages})}
    assert json.loads((root / "summary.json").read_text()) == summary
    validations = json.loads((root / "validation.json").read_text())
    assert all(v["exit"] == 0 for v in validations["commands"])
    assert validations["production_header_sha256"] == identity["source_sha256"]["src/lite/rabitq_graph_state.h"]
    assert validations["default_library_sha256"] == identity["default_library_sha256"]
    print(json.dumps({"verified": counts, "profile_percent": summary}, indent=2))


if __name__ == "__main__":
    audit(Path(__file__).resolve().parent)
