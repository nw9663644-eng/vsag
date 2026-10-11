# Copyright 2024-present the vsag project
# SPDX-License-Identifier: Apache-2.0
"""Run current RaBitQ candidate on reproducible 100k changed-vector inputs."""
import csv
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    repo = Path.cwd()
    out = Path(__file__).resolve().parent
    env = dict(os.environ, OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1",
               MKL_NUM_THREADS="1", LD_LIBRARY_PATH=str(repo / "build-lite-fp16-simd-release"),
               PYTHONPATH="/home/ubuntu/project/vsag-lite-datasets/cohere/python-deps:"
                          "/home/ubuntu/project/vsag-lite-datasets/sift/python-deps")
    builder = repo / "build-lite-fp16-simd-release/lite_graph_crud_quality"
    identity = {
        "head": subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip(),
        "branch": subprocess.check_output(["git", "branch", "--show-current"]).decode().strip(),
        "source_sha256": {name: digest(repo / name) for name in
                          ("src/lite/rabitq_backend.cpp", "src/lite/rabitq_snapshot.h",
                           "src/lite/rabitq_graph_state.h", "lite/benchmark/graph_crud_quality.cpp",
                           "lite/benchmark/prepare_persistent_crud_100k.py")},
        "library_sha256": digest(repo / "build-lite-fp16-simd-release/libvsag-lite.so"),
        "builder_sha256": digest(builder),
        "configuration": {"base_count": 100000, "query_count": 100, "rounds": 3,
                          "crud_ops_per_round": 10000, "degree": 16, "build_ef": 128,
                          "query_ef": 512, "storage": "rabitq8", "cpu": 0,
                          "reverse_adjacency": True},
    }
    assert identity["branch"] == "experiment/lite-rabitq-next-20260926"
    assert not (out / "candidate-rows.json").exists()
    (out / "candidate-identity.json").write_text(json.dumps(identity, indent=2) + "\n")
    with tempfile.TemporaryDirectory(prefix="vsag-crud100k-reverse-", dir="/dev/shm") as temp:
        root = Path(temp)
        inputs = root / "inputs"
        with (out / "candidate-prepare.log").open("w") as log:
            subprocess.run(["taskset", "-c", "0", "python3",
                            "lite/benchmark/prepare_persistent_crud_100k.py", str(inputs)],
                           cwd=repo, env=env, stdout=log, stderr=log, check=True)
        rows = []
        for label in ("gist100k100", "cohere100k100"):
            folder = inputs / label
            tag = "candidate-" + label
            for name in ("receipt.json", "groundtruth.ivecs", "changed-groundtruth.ivecs",
                         "queries.fvecs"):
                shutil.copyfile(folder / name, out / (label + "." + name))
            receipt = json.loads((folder / "receipt.json").read_text())
            assert receipt["base_count"] == 100000 and receipt["query_count"] == 100
            snapshot = root / (tag + ".snapshot")
            query_csv = out / (tag + ".queries.csv")
            run_env = dict(env, VSAG_GRAPH_STORAGE="rabitq8", VSAG_GRAPH_DEGREE="16",
                           VSAG_GRAPH_EF="128", VSAG_GRAPH_QUERY_EF="512",
                           VSAG_GRAPH_CRUD_MODE="all",
                           VSAG_GRAPH_REPLACEMENTS=str(folder / "replacement.fvecs"))
            command = ["/usr/bin/time", "-f", "%M", "-o", str(out / (tag + ".peak_kib")),
                       "taskset", "-c", "0", str(builder), str(folder), str(snapshot),
                       "3", "10000", str(query_csv)]
            (out / (tag + ".command.json")).write_text(json.dumps(
                {"argv": command, "environment": {k: run_env[k] for k in run_env
                 if k.startswith("VSAG_GRAPH") or k in ("LD_LIBRARY_PATH", "OPENBLAS_NUM_THREADS",
                                                        "OMP_NUM_THREADS", "MKL_NUM_THREADS")}},
                indent=2) + "\n")
            with (out / (tag + ".stdout")).open("w") as stdout, \
                 (out / (tag + ".stderr")).open("w") as stderr:
                subprocess.run(command, cwd=repo, env=run_env, stdout=stdout, stderr=stderr,
                               check=True)
            metrics = list(csv.DictReader((out / (tag + ".stdout")).open()))
            assert len(metrics) == 1
            rows.append({"label": label, "metrics": metrics[0],
                         "snapshot_sha256": digest(snapshot),
                         "peak_kib": int((out / (tag + ".peak_kib")).read_text())})
            (out / "candidate-rows.json").write_text(json.dumps(rows, indent=2) + "\n")
            print(label, metrics[0]["recall_at_k"], metrics[0]["crud_ms"], flush=True)
    print("candidate 100k replay finished", flush=True)


if __name__ == "__main__":
    main()
