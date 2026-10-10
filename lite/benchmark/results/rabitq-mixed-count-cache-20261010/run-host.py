# Copyright 2024-present the vsag project
# SPDX-License-Identifier: Apache-2.0
"""Frozen host experiment; invoke from the measured repository in one SSH session."""
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    repo = Path.cwd()
    out = Path(__file__).resolve().parent
    identity = json.loads((out / "identity.json").read_text())
    assert digest(repo / "src/lite/rabitq_graph_state.h") == identity["source_sha256"]["src/lite/rabitq_graph_state.h"]
    assert digest(repo / "build-lite-fp16-simd-release/lite_graph_crud_quality") == identity["builder_sha256"]
    assert not (out / "rows.json").exists(), "refuse overwriting completed run"
    for label, spec in identity["variants"].items():
        assert digest(Path(spec["library_path"])) == spec["sha256"]
    ram = Path(tempfile.mkdtemp(prefix="vsag-mixed-count-", dir="/dev/shm"))
    inputs = ram / "inputs"
    environment = dict(os.environ, OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1",
        PYTHONPATH="/home/ubuntu/project/vsag-lite-datasets/cohere/python-deps:/home/ubuntu/project/vsag-lite-datasets/sift/python-deps")
    with (out / "prepare.log").open("w") as log:
        subprocess.run(["taskset", "-c", "0", "python3", "lite/benchmark/prepare_persistent_crud.py",
            str(inputs), "lite/benchmark/results/query-selection-expanded-20261009/raw.tar.gz"],
            stdout=log, stderr=log, env=environment, check=True)
    for label in ("gist10k600", "cohere10k600"):
        for name in ("queries.fvecs", "groundtruth.ivecs", "changed-groundtruth.ivecs", "receipt.json"):
            shutil.copyfile(inputs / label / name, out / (label + "." + name))
    records = []
    for label, order in (("gist10k600", ("control", "candidate")), ("cohere10k600", ("candidate", "control"))):
        for variant in order:
            tag = label + "-" + variant
            spec = identity["variants"][variant]
            env = dict(environment, LD_LIBRARY_PATH=str(Path(spec["library_path"]).parent),
                VSAG_GRAPH_STORAGE="rabitq8", VSAG_GRAPH_DEGREE="16", VSAG_GRAPH_EF="128",
                VSAG_GRAPH_QUERY_EF="512", VSAG_GRAPH_CRUD_MODE="all",
                VSAG_GRAPH_REPLACEMENTS=str(inputs / label / "replacement.fvecs"))
            snapshot = ram / (tag + ".snapshot")
            command = ["/usr/bin/time", "-f", "%M", "-o", str(out / (tag + ".peak_kib")),
                "taskset", "-c", "0", str(repo / "build-lite-fp16-simd-release/lite_graph_crud_quality"),
                str(inputs / label), str(snapshot), "3", "10000", str(out / (tag + ".queries.csv"))]
            keys = [key for key in env if key.startswith("VSAG_GRAPH") or key in (
                "LD_LIBRARY_PATH", "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")]
            (out / (tag + ".command.json")).write_text(json.dumps(
                {"argv": command, "environment": {k: env[k] for k in keys}}, indent=2) + "\n")
            with (out / (tag + ".ldd")).open("w") as log:
                subprocess.run(["ldd", str(repo / "build-lite-fp16-simd-release/lite_graph_crud_quality")],
                    env=env, stdout=log, stderr=log, check=True)
            with (out / (tag + ".stdout")).open("w") as stdout, (out / (tag + ".stderr")).open("w") as stderr:
                result = subprocess.run(command, env=env, stdout=stdout, stderr=stderr)
            assert result.returncode == 0, tag
            metric = list(csv.DictReader(io.StringIO((out / (tag + ".stdout")).read_text())))
            assert len(metric) == 1
            records.append({"dataset": label, "variant": variant, "result": metric[0], "exit": result.returncode,
                "snapshot_sha256": digest(snapshot), "external_peak_rss_kib": int((out / (tag + ".peak_kib")).read_text())})
            (out / "rows.json").write_text(json.dumps(records, indent=2) + "\n")
            # Builder already ran native Save/Load exact checks; only delete its new RAM snapshot.
            assert snapshot.resolve().is_relative_to(ram.resolve()) and snapshot.is_file()
            snapshot.unlink()
            print(tag, metric[0]["recall_at_k"], metric[0]["crud_ms"], flush=True)
    for label in ("gist10k600", "cohere10k600"):
        pair = [r for r in records if r["dataset"] == label]
        assert pair[0]["snapshot_sha256"] == pair[1]["snapshot_sha256"]
        for phase in ("", ".initial"):
            for suffix in ("", ".neighbors.csv"):
                assert (out / (label + "-control.queries.csv" + phase + suffix)).read_bytes() == (
                    out / (label + "-candidate.queries.csv" + phase + suffix)).read_bytes()
    print("All four paired snapshots and ordered results identical", flush=True)


if __name__ == "__main__":
    main()
