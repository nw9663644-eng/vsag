#!/usr/bin/env python3
# Copyright 2024-present the vsag project
# SPDX-License-Identifier: Apache-2.0
"""Small real-process regression for the paired measurement driver."""
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile


def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: test_aligned_comparison.py LITE_BUILD CONTROL_LIBRARY")
    driver = Path(__file__).with_name("run_aligned_comparison.py")
    with tempfile.TemporaryDirectory(prefix="vsag-aligned-test-") as temporary:
        root = Path(temporary)
        dataset = root / "dataset"
        dataset.mkdir()
        def write_records(name, values, scalar):
            with open(dataset/name, "wb") as stream:
                for row in values:
                    stream.write(struct.pack("<i", len(row)))
                    stream.write(struct.pack("<"+scalar*len(row), *row))
        write_records("base.fvecs", [[float(i)]*16 for i in range(32)], "f")
        write_records("queries.fvecs", [[2.25]*16, [20.25]*16], "f")
        write_records("groundtruth.ivecs", [[2, 3], [20, 21]], "i")
        output = root / "result"
        command = [sys.executable, str(driver), "--lite-build", sys.argv[1],
                   "--control-library", sys.argv[2], "--dataset", "fixture="+str(dataset),
                   "--output", str(output), "--scratch", temporary, "--trials", "1",
                   "--loads", "1", "--ef", "8"]
        subprocess.run(command, check=True)
        rows = json.loads((output/"rows.json").read_text())
        assert len(rows) == 6
        for row in rows:
            assert row["build"]["storage"] == row["storage"]
            assert row["build"]["query_ef_search"] == "8"
            assert row["build"]["ef_search"] == "128"
        for storage in ["fp32", "fp16", "rabitq8"]:
            pair = [r for r in rows if r["storage"] == storage]
            assert pair[0]["snapshot_sha256"] == pair[1]["snapshot_sha256"]
        rerun = subprocess.run(command, capture_output=True)
        assert rerun.returncode != 0, "must reject an existing output directory"
        for scratch in root.glob("vsag-aligned-*"):
            assert not scratch.is_dir(), "snapshot scratch should be cleaned"
    print("storage, per-query budget, unchanged construction, paired snapshots and output guards passed")


if __name__ == "__main__":
    main()
