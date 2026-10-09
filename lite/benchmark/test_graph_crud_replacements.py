# Copyright 2024-present the vsag project
# SPDX-License-Identifier: Apache-2.0
"""Validate persistent whole-row replay using the benchmark binary argument."""
import csv
import io
import math
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile


def vectors(rows):
    return b"".join(struct.pack("<i", len(row)) + struct.pack("<%df" % len(row), *row)
                    for row in rows)


def main():
    binary = str(Path(sys.argv[1]).resolve())
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        base = [[float(i == j) for j in range(17)] for i in range(8)]
        (root / "base.fvecs").write_bytes(vectors(base))
        (root / "queries.fvecs").write_bytes(vectors(base))
        (root / "groundtruth.ivecs").write_bytes(
            b"".join(struct.pack("<ii", 1, i) for i in range(8)))
        (root / "changed-groundtruth.ivecs").write_bytes(
            b"".join(struct.pack("<ii", 1, (i - 2) % 8) for i in range(8)))
        schedule = [(round * 65537 + op * 8191) % 8
                    for round in range(2) for op in range(8)]
        replacement = [base[(id + cycle // 8 + 1) % 8]
                       for cycle, id in enumerate(schedule)]
        source = root / "replacement.fvecs"
        source.write_bytes(vectors(replacement))
        environment = dict(os.environ, VSAG_GRAPH_REPLACEMENTS=str(source),
                           VSAG_GRAPH_DEGREE="7", VSAG_GRAPH_EF="32")
        def run(tag, rounds="2", ops="8", evidence=True):
            command = [binary, str(root), str(root / (tag + ".snap")), rounds, ops]
            if evidence:
                command.append(str(root / (tag + ".csv")))
            return subprocess.run(command, env=environment, capture_output=True, text=True)
        for storage in ["fp32", "fp16", "rabitq8"]:
            environment["VSAG_GRAPH_STORAGE"] = storage
            result = run(storage)
            assert result.returncode == 0, result.stderr
            row = next(csv.DictReader(io.StringIO(result.stdout)))
            assert row["initial_recall_at_k"] == row["recall_at_k"] == "1.000000"
            assert int(row["persistent_replacements"]) == 16
            operations = list(csv.DictReader((root / (storage + ".csv.operations.csv")).open()))
            assert len(operations) == 48
            for cycle, id in enumerate(schedule):
                chunk = operations[cycle * 3:cycle * 3 + 3]
                assert [(int(x["cycle"]), int(x["id"]), int(x["operation"])) for x in chunk] == [
                    (cycle, id, op) for op in range(3)]
                assert all(math.isfinite(float(x["latency_us"])) and
                           float(x["latency_us"]) >= 0 for x in chunk)
            neighbors = list(csv.DictReader((root / (storage + ".csv.neighbors.csv")).open()))
            assert [int(x["id"]) for x in neighbors] == [(i - 2) % 8 for i in range(8)]
        for suffix in [".operations.csv", ".initial", ".initial.latencies.csv",
                       ".initial.neighbors.csv"]:
            tag = "protected-" + str(len(suffix))
            marker = root / (tag + ".csv" + suffix)
            marker.write_text("keep")
            assert run(tag).returncode != 0 and marker.read_text() == "keep"
        assert run("zero", rounds="0").returncode != 0
        assert run("short", ops="7").returncode != 0
        assert run("no-evidence", evidence=False).returncode != 0
        source.write_bytes(vectors([base[id] for id in schedule]))
        assert run("unchanged").returncode != 0
        source.write_bytes(vectors([[float("nan")] * 17 for _ in schedule]))
        assert run("nonfinite").returncode != 0
        source.write_bytes(vectors(replacement))
        original_truth = (root / "groundtruth.ivecs").read_bytes()
        (root / "groundtruth.ivecs").write_bytes(struct.pack("<ii", 1, 0))
        assert run("initial-truth-short").returncode != 0
        (root / "groundtruth.ivecs").write_bytes(original_truth)
        (root / "changed-groundtruth.ivecs").unlink()
        assert run("missing-truth").returncode != 0
    print("PASS: persistent FP32/FP16/RaBitQ whole-row replay, timing and protections")


if __name__ == "__main__":
    main()
