# Copyright 2024-present the vsag project
# SPDX-License-Identifier: Apache-2.0
"""Host replay. Run from measured repo after building the default Release targets.
Inputs/dependencies use recorded host paths. Never overwrites the default adapter.
OUTPUT must not exist; dataset preparation + runs stay within this SSH session.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(exist_ok=False)
    repo = Path.cwd()
    root = Path(__file__).resolve().parent
    identity = json.loads((root / "identity.json").read_text())
    header = repo / "src/lite/rabitq_graph_state.h"
    assert hashlib.sha256(header.read_bytes()).hexdigest() == identity["source_sha256"]["src/lite/rabitq_graph_state.h"]
    builder = repo / "build-lite-fp16-simd-release/lite_graph_crud_quality"
    assert hashlib.sha256(builder.read_bytes()).hexdigest() == identity["builder_sha256"]
    with tarfile.open(root / "raw.tar.gz") as tar:
        builds = json.loads(tar.extractfile("./build-variants.json").read())
    ram = Path(tempfile.mkdtemp(prefix="vsag-count-replay-", dir="/dev/shm"))
    inputs = ram / "inputs"
    env = os.environ.copy()
    env.update(OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1",
               PYTHONPATH="/home/ubuntu/project/vsag-lite-datasets/cohere/python-deps:/home/ubuntu/project/vsag-lite-datasets/sift/python-deps")
    subprocess.run(["taskset", "-c", "0", "python3", "lite/benchmark/prepare_persistent_crud.py",
                    str(inputs), "lite/benchmark/results/query-selection-expanded-20261009/raw.tar.gz"],
                   env=env, check=True)
    build = repo / "build-lite-fp16-simd-release"
    for mode, spec in builds.items():
        folder = ram / mode
        folder.mkdir()
        source, obj, library = folder / "adapter.cpp", folder / "adapter.o", folder / "libvsag-lite.so"
        source.write_text(spec["adapter"])
        command = list(spec["compile"])
        command[command.index("-o") + 1] = str(obj)
        command[-1] = str(source)
        subprocess.run(command, cwd=build, env=env, check=True)
        link = list(spec["link"])
        link[link.index("-o") + 1] = str(library)
        link = [str(obj) if "rabitq_backend" in item and item.endswith(".o") else item for item in link]
        subprocess.run(link, cwd=build, env=env, check=True)
        (output / (mode + ".library-sha256")).write_text(hashlib.sha256(library.read_bytes()).hexdigest() + "\n")
    for label, order in (("gist10k600", ("recount", "cached")), ("cohere10k600", ("cached", "recount"))):
        for mode in order:
            tag = label + "-" + mode
            snapshot = ram / (tag + ".snapshot")
            environment = dict(env, LD_LIBRARY_PATH=str(ram / mode), VSAG_GRAPH_STORAGE="rabitq8",
                               VSAG_GRAPH_DEGREE="16", VSAG_GRAPH_EF="128", VSAG_GRAPH_QUERY_EF="512",
                               VSAG_GRAPH_CRUD_MODE="update", VSAG_GRAPH_REPLACEMENTS=str(inputs / label / "replacement.fvecs"))
            command = ["/usr/bin/time", "-f", "%M", "-o", str(output / (tag + ".peak_kib")),
                       "taskset", "-c", "0", str(builder), str(inputs / label), str(snapshot),
                       "3", "10000", str(output / (tag + ".queries.csv"))]
            (output / (tag + ".command.json")).write_text(json.dumps({"argv": command, "environment": {
                key: environment[key] for key in ("LD_LIBRARY_PATH", "VSAG_GRAPH_STORAGE", "VSAG_GRAPH_DEGREE",
                "VSAG_GRAPH_EF", "VSAG_GRAPH_QUERY_EF", "VSAG_GRAPH_CRUD_MODE", "VSAG_GRAPH_REPLACEMENTS")}}, indent=2) + "\n")
            with (output / (tag + ".stdout")).open("w") as stdout, (output / (tag + ".stderr")).open("w") as stderr:
                subprocess.run(command, env=environment, stdout=stdout, stderr=stderr, check=True)
            (output / (tag + ".snapshot-sha256")).write_text(hashlib.sha256(snapshot.read_bytes()).hexdigest() + "\n")
    # Preserve compact generated inputs and receipts; not the large replacement matrices.
    with tarfile.open(output / "inputs.tar.gz", "w:gz") as tar:
        for label in ("gist10k600", "cohere10k600"):
            for name in ("receipt.json", "queries.fvecs", "groundtruth.ivecs", "changed-groundtruth.ivecs"):
                tar.add(inputs / label / name, arcname=label + "." + name)
    print("Replay complete; RAM inputs/snapshots are not a persistent deliverable.")


if __name__ == "__main__":
    main()
