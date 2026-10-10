# Copyright 2024-present the vsag project
# SPDX-License-Identifier: Apache-2.0
"""Host-only fixed-budget Reverse Add local-journal versus full-copy paired replace experiment."""
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
    assert not (out / "rows.json").exists(), "refuse overwriting completed replay"
    ram = Path(tempfile.mkdtemp(prefix="vsag-reverse-add-", dir="/dev/shm"))
    raw = ram / "raw"
    raw.mkdir()
    inputs = ram / "inputs"
    env = dict(os.environ, OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1",
        PYTHONPATH="/home/ubuntu/project/vsag-lite-datasets/cohere/python-deps:/home/ubuntu/project/vsag-lite-datasets/sift/python-deps")
    old = json.loads((repo / "lite/benchmark/results/rabitq-mixed-count-cache-20261010/identity.json").read_text())
    control = old["variants"]["candidate"]
    source_names = ("src/lite/rabitq_graph_state.h", "src/lite/rabitq_backend_test.cpp",
                    "src/lite/graph_allocation_test.cpp", "lite/benchmark/graph_crud_quality.cpp",
                    "lite/benchmark/prepare_persistent_crud.py")
    identity = {"base_head": subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip(),
        "source_sha256": {name: digest(repo / name) for name in source_names},
        "builder_sha256": digest(repo / "build-lite-fp16-simd-release/lite_graph_crud_quality"),
        "default_library_sha256": digest(repo / "build-lite-fp16-simd-release/libvsag-lite.so"),
        "config": {"degree": 16, "construction_ef": 128, "query_ef": 512, "cpu": 0, "mode": "replace",
                   "rounds": 3, "cycles_per_round": 10000, "queries": 600, "trials": 3},
        "variants": {}}
    with tarfile.open(repo / "lite/benchmark/results/rabitq-reverse-add-20261010/raw.tar.gz") as archive:
        (raw / "candidate-state.h").write_bytes(archive.extractfile("./candidate-state.h").read())
    identity["source_sha256"][source_names[0]] = digest(raw / "candidate-state.h")
    assert identity["source_sha256"][source_names[3]] == "145e3ff4058705ce8a072acc05502e7d82097264d5dd9017f31511d95faa27b2"
    assert identity["source_sha256"][source_names[4]] == "51bd78dfbccf3f3202f65b5a0f8b7b8756363c8c9e0015c9a3f984935bee344e"
    for name, dest in ((source_names[1], "validated-test.cpp"), (source_names[2], "allocation-test.cpp"),
                       (source_names[3], "measured-tool.cpp"), (source_names[4], "prepare-inputs.py")):
        shutil.copyfile(repo / name, raw / dest)
    (raw / "control-state.h").write_bytes(subprocess.check_output(
        ["git", "show", "35d1b3d369693455151b14bdfa8a43f84f0287a2:src/lite/rabitq_graph_state.h"]))
    identity["control_header_sha256"] = digest(raw / "control-state.h")
    for variant, displaced in (("control", False), ("candidate", True)):
        folder = ram / variant
        folder.mkdir()
        source, obj, library = folder / "adapter.cpp", folder / "adapter.o", folder / "libvsag-lite.so"
        needle = "state_.ConfigureIncomingProtection(rabitq::IncomingProtection::CACHED);"
        assert control["adapter"].count(needle) == 1
        adapter = control["adapter"].replace("        " + needle + "\n", "", 1)
        source.write_text(adapter)
        (folder / "lite").mkdir()
        original = (raw / ("candidate-state.h" if displaced else "control-state.h")).read_text()
        flag = "bool use_incoming_adjacency = false"
        assert original.count(flag) == 1
        compiled = original.replace(flag, "bool use_incoming_adjacency = true", 1)
        (folder / "lite/rabitq_graph_state.h").write_text(compiled)
        (raw / (variant + ".compiled-state.h")).write_text(compiled)
        command = list(control["compile"])
        command.insert(1, "-I" + str(folder))
        command[command.index("-o") + 1] = str(obj)
        command[-1] = str(source)
        link = list(control["link"])
        link[link.index("-o") + 1] = str(library)
        link = [str(obj) if item.endswith("adapter.o") else item for item in link]
        assert str(obj) in link
        with (raw / (variant + ".build.log")).open("w") as log:
            subprocess.run(command, cwd=repo / "build-lite-fp16-simd-release", env=env, stdout=log, stderr=log, check=True)
            subprocess.run(link, cwd=repo / "build-lite-fp16-simd-release", env=env, stdout=log, stderr=log, check=True)
        identity["variants"][variant] = {"library_path": str(library), "sha256": digest(library),
            "public_policy": "NONE", "reverse_add_journal": displaced, "incoming_adjacency": True, "adapter": adapter, "compile": command, "link": link}
        dep = list(command)
        j = dep.index("-o")
        del dep[j:j + 2]
        dep[dep.index("-c")] = "-MM"
        dependency = subprocess.check_output(dep, cwd=repo / "build-lite-fp16-simd-release")
        assert str(folder / "lite/rabitq_graph_state.h").encode() in dependency
        (raw / (variant + ".dependencies.txt")).write_bytes(dependency)
        identity["variants"][variant]["dependencies_command"] = dep
        identity["variants"][variant]["compiled_state_header_sha256"] = digest(folder / "lite/rabitq_graph_state.h")
    (out / "identity.json").write_text(json.dumps(identity, indent=2) + "\n")
    (raw / "identity.json").write_text(json.dumps(identity, indent=2) + "\n")

    def archive():
        files = sorted(p for p in raw.iterdir() if p.is_file())
        with tarfile.open(out / "raw.tar.gz", "w:gz") as tar:
            for p in files:
                tar.add(p, arcname="./" + p.name)
        (out / "members.json").write_text(json.dumps(
            {p.name: digest(p) for p in files}, indent=2, sort_keys=True) + "\n")

    with (raw / "prepare.log").open("w") as log:
        subprocess.run(["taskset", "-c", "0", "python3", "lite/benchmark/prepare_persistent_crud.py",
            str(inputs), "lite/benchmark/results/query-selection-expanded-20261009/raw.tar.gz"],
            env=env, stdout=log, stderr=log, check=True)
    for label in ("gist10k600", "cohere10k600"):
        for name in ("queries.fvecs", "groundtruth.ivecs", "changed-groundtruth.ivecs", "receipt.json"):
            shutil.copyfile(inputs / label / name, raw / (label + "." + name))
    shutil.copyfile(Path(__file__), raw / "measured-run-host.py")
    archive()  # Persist compact inputs before any builder, without large replacement matrices.
    records = []
    for label, repeat in ((label, repeat) for repeat in range(3) for label in ("gist10k600", "cohere10k600")):
        order = ("control", "candidate") if (repeat + int(label.startswith("cohere"))) % 2 == 0 else ("candidate", "control")
        for variant in order:
            tag = label + "-" + variant + "-r" + str(repeat)
            spec = identity["variants"][variant]
            environment = dict(env, LD_LIBRARY_PATH=str(Path(spec["library_path"]).parent),
                VSAG_GRAPH_STORAGE="rabitq8", VSAG_GRAPH_DEGREE="16", VSAG_GRAPH_EF="128",
                VSAG_GRAPH_QUERY_EF="512", VSAG_GRAPH_CRUD_MODE="replace",
                VSAG_GRAPH_REPLACEMENTS=str(inputs / label / "replacement.fvecs"))
            snapshot = ram / (tag + ".snapshot")
            command = ["/usr/bin/time", "-f", "%M", "-o", str(raw / (tag + ".peak_kib")),
                "taskset", "-c", "0", str(repo / "build-lite-fp16-simd-release/lite_graph_crud_quality"),
                str(inputs / label), str(snapshot), "3", "10000", str(raw / (tag + ".queries.csv"))]
            keys = [k for k in environment if k.startswith("VSAG_GRAPH") or k in
                    ("LD_LIBRARY_PATH", "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")]
            (raw / (tag + ".command.json")).write_text(json.dumps(
                {"argv": command, "environment": {k: environment[k] for k in keys}}, indent=2) + "\n")
            with (raw / (tag + ".ldd")).open("w") as log:
                subprocess.run(["ldd", str(repo / "build-lite-fp16-simd-release/lite_graph_crud_quality")],
                    env=environment, stdout=log, stderr=log, check=True)
            with (raw / (tag + ".stdout")).open("w") as stdout, (raw / (tag + ".stderr")).open("w") as stderr:
                result = subprocess.run(command, env=environment, stdout=stdout, stderr=stderr)
            assert result.returncode == 0, tag
            metrics = list(csv.DictReader(io.StringIO((raw / (tag + ".stdout")).read_text())))
            assert len(metrics) == 1
            records.append({"dataset": label, "variant": variant, "repeat": repeat, "tag": tag, "result": metrics[0], "exit": 0,
                "snapshot_sha256": digest(snapshot),
                "external_peak_rss_kib": int((raw / (tag + ".peak_kib")).read_text())})
            (out / "rows.json").write_text(json.dumps(records, indent=2) + "\n")
            (raw / "rows.json").write_text(json.dumps(records, indent=2) + "\n")
            archive()
            assert snapshot.resolve().is_relative_to(ram.resolve()) and snapshot.is_file()
            snapshot.unlink()  # Only this new RAM snapshot, after native exact Load and SHA receipt.
            print(tag, metrics[0]["recall_at_k"], metrics[0]["crud_ms"], flush=True)
    for label in ("gist10k600", "cohere10k600"):
        for repeat in range(3):
            for suffix in ("", ".neighbors.csv", ".initial", ".initial.neighbors.csv"):
                first = raw / (label + "-control-r" + str(repeat) + ".queries.csv" + suffix)
                second = raw / (label + "-candidate-r" + str(repeat) + ".queries.csv" + suffix)
                assert first.read_bytes() == second.read_bytes()
            pair = [r for r in records if r["dataset"] == label and r["repeat"] == repeat]
            assert pair[0]["snapshot_sha256"] == pair[1]["snapshot_sha256"]
    archive()
    print("Twelve builders finished; initial/final ordered results and snapshots identical", flush=True)


if __name__ == "__main__":
    main()
