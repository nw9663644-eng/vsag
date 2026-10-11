# Copyright 2024-present the vsag project
# SPDX-License-Identifier: Apache-2.0
"""Replay production one-bit repair with two lower query budgets."""
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    repo = Path.cwd()
    out = Path(__file__).resolve().parent
    assert not (out / "rows.json").exists()
    prior = repo / "lite/benchmark/results/rabitq-production-diversity-20261011"
    with (prior / "identity.json").open() as source:
        identity = json.load(source)
    candidate = repo / "build-lite-fp16-simd-release/libvsag-lite.so"
    assert candidate.is_file() and digest(candidate) == identity["default_library_sha256"]
    ram = Path(tempfile.mkdtemp(prefix="vsag-diversity-ef-", dir="/dev/shm"))
    inputs = ram / "inputs"
    tool = repo / "build-lite-fp16-simd-release/lite_graph_crud_quality"
    assert digest(tool) == identity["builder_sha256"]
    env = dict(os.environ, OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1",
               PYTHONPATH="/home/ubuntu/project/vsag-lite-datasets/cohere/python-deps:/home/ubuntu/project/vsag-lite-datasets/sift/python-deps",
               LD_LIBRARY_PATH=str(candidate.parent), VSAG_GRAPH_STORAGE="rabitq8",
               VSAG_GRAPH_DEGREE="16", VSAG_GRAPH_EF="128", VSAG_GRAPH_CRUD_MODE="all")
    with (out / "prepare.log").open("w") as log:
        subprocess.run(["taskset", "-c", "0", "python3", "lite/benchmark/prepare_persistent_crud.py",
                        str(inputs), "lite/benchmark/results/query-selection-expanded-20261009/raw.tar.gz"],
                       env=env, stdout=log, stderr=log, check=True)
    rows = []
    for ef in (384, 256):
        for label in ("gist10k600", "cohere10k600"):
            tag = f"{label}-ef{ef}"
            run_env = dict(env, VSAG_GRAPH_QUERY_EF=str(ef),
                           VSAG_GRAPH_REPLACEMENTS=str(inputs / label / "replacement.fvecs"))
            snapshot = ram / f"{tag}.snapshot"
            command = ["/usr/bin/time", "-f", "%M", "-o", str(out / f"{tag}.peak_kib"),
                       "taskset", "-c", "0", str(tool), str(inputs / label), str(snapshot),
                       "3", "10000", str(out / f"{tag}.queries.csv")]
            (out / f"{tag}.command.json").write_text(json.dumps(
                {"argv": command, "environment": {key: value for key, value in run_env.items()
                    if key.startswith("VSAG_GRAPH") or key in
                    ("LD_LIBRARY_PATH", "OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS",
                     "MKL_NUM_THREADS")}}, indent=2) + "\n")
            with (out / f"{tag}.stdout").open("w") as stdout, (
                    out / f"{tag}.stderr").open("w") as stderr:
                result = subprocess.run(command, env=run_env, stdout=stdout, stderr=stderr)
            assert result.returncode == 0, tag
            metric = list(csv.DictReader(io.StringIO((out / f"{tag}.stdout").read_text())))
            assert len(metric) == 1
            rows.append({"dataset": label, "query_ef": ef, "result": metric[0],
                         "snapshot_sha256": digest(snapshot),
                         "peak_rss_kib": int((out / f"{tag}.peak_kib").read_text())})
            (out / "rows.json").write_text(json.dumps(rows, indent=2) + "\n")
            assert snapshot.is_file() and snapshot.parent == ram
            snapshot.unlink()
            print(tag, metric[0]["recall_at_k"], metric[0]["search_p50_us"],
                  metric[0]["search_p99_us"], flush=True)
    with tarfile.open(out / "raw.tar.gz", "w:gz") as archive:
        for path in sorted(out.iterdir()):
            if path.is_file() and path.name != "raw.tar.gz":
                archive.add(path, arcname=path.name)


if __name__ == "__main__":
    main()
