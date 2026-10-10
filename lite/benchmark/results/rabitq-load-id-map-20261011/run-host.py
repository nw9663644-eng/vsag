# Copyright 2024-present the vsag project
# SPDX-License-Identifier: Apache-2.0
"""Matched snapshots, default-policy loader only. No query/CRUD timing claims."""
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile

BASE = "e017145b5c0b7dfd05489a84c6259927cdcdbdc9"

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    repo = Path.cwd()
    out = Path(__file__).resolve().parent
    assert not (out / "rows.json").exists(), "refuse overwriting evidence"
    ram = Path(tempfile.mkdtemp(prefix="vsag-load-id-map-", dir="/dev/shm"))
    raw = ram / "raw"
    raw.mkdir()
    env = dict(os.environ, TMPDIR="/dev/shm", OPENBLAS_NUM_THREADS="1",
               OMP_NUM_THREADS="1", MKL_NUM_THREADS="1")
    identity = {"base": BASE, "cpu": 0, "pairs_per_dataset": 15,
                "incoming_adjacency": False, "policy": "NONE",
                "variants": {}, "datasets": {}, "builder_sha256":
                sha(repo / "build-lite-fp16-simd-release/lite_graph_crud_quality")}
    # Freeze every Lite header to the parent; only the duplicated set differs.
    headers = subprocess.check_output(["git", "ls-tree", "-r", "--name-only",
                                      BASE, "src/lite"]).decode().splitlines()
    headers = [p for p in headers if p.endswith(".h")]
    needle = ('    std::unordered_set<int64_t> unique_ids;\n'
              '    for (int64_t id : ids) {\n'
              '        codec_require(unique_ids.insert(id).second, "duplicate mutable snapshot ID");\n'
              '    }\n')
    control_header = subprocess.check_output(
        ["git", "show", BASE + ":src/lite/rabitq_snapshot.h"]).decode()
    assert control_header.count(needle) == 1
    candidate_header = control_header.replace("#include <unordered_set>\n", "").replace(
        needle, "    // MutableGraphState rejects duplicate IDs while building its required slot map.\n")
    assert (repo / "src/lite/rabitq_snapshot.h").read_text() == candidate_header
    (raw / "control-snapshot.h").write_text(control_header)
    (raw / "candidate-snapshot.h").write_text(candidate_header)
    for variant in ("control", "candidate"):
        folder = ram / variant
        (folder / "lite").mkdir(parents=True)
        for name in headers:
            data = subprocess.check_output(["git", "show", BASE + ":" + name])
            if name.endswith("/rabitq_snapshot.h") and variant == "candidate":
                data = candidate_header.encode()
            (folder / "lite" / Path(name).name).write_bytes(data)
        command = ["/usr/bin/c++", "-O3", "-DNDEBUG", "-std=c++17",
                   "-I" + str(folder), "-I" + str(repo / "src"),
                   "-I" + str(repo / "include"), str(out / "memory-probe.cpp"),
                   "-o", str(folder / "probe")]
        with (raw / (variant + ".build.log")).open("w") as log:
            subprocess.run(command, stdout=log, stderr=log, env=env, check=True)
        dep = command[:-2]
        dep.insert(1, "-MM")
        dependencies = subprocess.check_output(dep).decode()
        assert str(folder / "lite/rabitq_snapshot.h") in dependencies
        (raw / (variant + ".dependencies.txt")).write_text(dependencies)
        identity["variants"][variant] = {"command": command, "sha256": sha(folder / "probe"),
            "snapshot_header_sha256": sha(folder / "lite/rabitq_snapshot.h"),
            "header_sha256": {p.name: sha(p) for p in (folder / "lite").iterdir()}}
    (raw / "measured-run-host.py").write_bytes(Path(__file__).read_bytes())
    (raw / "memory-probe.cpp").write_bytes((out / "memory-probe.cpp").read_bytes())
    (raw / "product.patch").write_bytes(subprocess.check_output(
        ["git", "diff", "--", "src/lite/rabitq_snapshot.h", "src/lite/rabitq_backend_test.cpp"]))
    config = json.loads(Path("/home/ubuntu/project/vsag-lite-integrated-100k-20261009/inputs.json").read_text())
    rows = []
    def archive():
        (out / "identity.json").write_text(json.dumps(identity, indent=2) + "\n")
        (out / "rows.json").write_text(json.dumps(rows, indent=2) + "\n")
        files = sorted(p for p in raw.iterdir() if p.is_file())
        with tarfile.open(out / "raw.tar.gz", "w:gz") as tar:
            for path in files:
                tar.add(path, arcname="./" + path.name)
        (out / "members.json").write_text(json.dumps({p.name: sha(p) for p in files},
                                                   indent=2, sort_keys=True) + "\n")
    for label in ("gist", "cohere"):
        directory = Path(config["inputs"][label]["base.fvecs"]["path"].replace(
            "/scale-100000/", "/scale-10000/")).parent
        inputs = {name: {"path": str(directory / name), "sha256": sha(directory / name)}
                  for name in ("base.fvecs", "queries.fvecs", "groundtruth.ivecs")}
        snapshot = ram / (label + ".snapshot")
        command = ["taskset", "-c", "0",
                   str(repo / "build-lite-fp16-simd-release/lite_graph_crud_quality"),
                   str(directory), str(snapshot), "0", "1", str(raw / (label + ".queries.csv"))]
        builder_env = dict(env, VSAG_GRAPH_STORAGE="rabitq8", VSAG_GRAPH_DEGREE="16",
                           VSAG_GRAPH_EF="128", VSAG_GRAPH_QUERY_EF="512")
        with (raw / (label + ".builder.stdout")).open("w") as stdout, (
                raw / (label + ".builder.stderr")).open("w") as stderr:
            subprocess.run(command, env=builder_env, stdout=stdout, stderr=stderr, check=True)
        identity["datasets"][label] = {"inputs": inputs, "snapshot_sha256": sha(snapshot),
            "snapshot_bytes": snapshot.stat().st_size, "builder_command": command,
            "builder_environment": {k: v for k, v in builder_env.items() if k.startswith("VSAG")},
            "builder_result": list(csv.DictReader(io.StringIO(
                (raw / (label + ".builder.stdout")).read_text())))[0]}
        # Fresh child processes; alternating order; warm RAM/page cache, not cold I/O.
        for pair in range(15):
            order = ("control", "candidate") if pair % 2 == 0 else ("candidate", "control")
            for variant in order:
                tag = label + "-" + variant + "-" + str(pair)
                saved = ram / (tag + ".roundtrip")
                command = ["taskset", "-c", "0", str(ram / variant / "probe"),
                           str(snapshot), str(saved)]
                with (raw / (tag + ".stdout")).open("w") as stdout, (
                        raw / (tag + ".stderr")).open("w") as stderr:
                    result = subprocess.run(command, env=env, stdout=stdout, stderr=stderr)
                assert result.returncode == 0
                metrics = list(csv.DictReader(io.StringIO((raw / (tag + ".stdout")).read_text())))
                assert len(metrics) == 1 and sha(saved) == sha(snapshot)
                rows.append({"dataset": label, "variant": variant, "pair": pair, "tag": tag,
                             "command": command, "result": metrics[0], "exit": result.returncode,
                             "roundtrip_sha256": sha(saved)})
                assert saved.resolve().is_relative_to(ram.resolve())
                saved.unlink()  # New output only, after exact round-trip hash.
        archive()
        assert snapshot.resolve().is_relative_to(ram.resolve())
        snapshot.unlink()  # New RAM snapshot only; durable SHA and exact load receipts archived.
        print(label + ": 30 fresh loaders, exact native round trips", flush=True)
    archive()

if __name__ == "__main__":
    main()
