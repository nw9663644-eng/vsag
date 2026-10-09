# Copyright 2024-present the vsag project
# SPDX-License-Identifier: Apache-2.0
"""Compare frozen Lite builds on real datasets without retaining disposable snapshots."""
import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess


def digest(path):
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1048576), b""):
            result.update(chunk)
    return result.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline_build", type=Path)
    parser.add_argument("candidate_build", type=Path)
    parser.add_argument("output", type=Path)
    for dataset in ("sift", "gist", "cohere"):
        parser.add_argument("--" + dataset, type=Path, required=True)
    parser.add_argument("--cpu", type=int, default=0)
    parser.add_argument("--repeats", type=int, default=3)
    args = parser.parse_args()
    if args.repeats < 1 or args.cpu < 0:
        parser.error("CPU and repeat count must be valid")
    root = Path(__file__).resolve().parents[2]
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    datasets = {name: getattr(args, name).resolve() for name in ("sift", "gist", "cohere")}
    versions = [("baseline", args.baseline_build.resolve()),
                ("candidate", args.candidate_build.resolve())]
    binary = output / "compare"
    source = root / "lite/benchmark/graph_crud_quality.cpp"
    subprocess.run(["c++", "-O3", "-DNDEBUG", "-std=c++17", "-I", str(root / "include"),
                    str(source), "-L", str(versions[1][1]), "-lvsag-lite", "-o", str(binary)],
                   check=True)
    identity = {
        "benchmark_sha256": digest(source),
        "binary_sha256": digest(binary),
        "libraries": {name: {"path": str(path), "sha256": digest(path / "libvsag-lite.so")}
                      for name, path in versions},
        "inputs": {name: {file: {"path": str(path / file), "sha256": digest(path / file)}
                          for file in ("base.fvecs", "queries.fvecs", "groundtruth.ivecs")}
                   for name, path in datasets.items()},
        "plan": {"cpu": args.cpu, "repeats": args.repeats, "degree": 16, "ef": 128,
                 "crud_rounds": 0, "cold_io": False},
    }
    (output / "identity.json").write_text(json.dumps(identity, indent=2) + "\n")
    rows = []
    for dataset, path in datasets.items():
        for storage in ("fp32", "fp16", "rabitq8"):
            for trial in range(args.repeats):
                order = versions if trial % 2 == 0 else list(reversed(versions))
                for label, library in order:
                    stem = f"{dataset}-{storage}-{label}-{trial}"
                    snapshot = output / (stem + ".snapshot")
                    environment = dict(os.environ, LD_LIBRARY_PATH=str(library),
                                       VSAG_GRAPH_STORAGE=storage, VSAG_GRAPH_DEGREE="16",
                                       VSAG_GRAPH_EF="128")
                    command = ["/usr/bin/time", "-v", "taskset", "-c", str(args.cpu),
                               str(binary), str(path), str(snapshot), "0", "100",
                               str(output / (stem + ".queries.csv"))]
                    result = subprocess.run(command, env=environment, text=True,
                                            capture_output=True)
                    (output / (stem + ".stdout.csv")).write_text(result.stdout)
                    (output / (stem + ".stderr.txt")).write_text(result.stderr)
                    (output / (stem + ".command.json")).write_text(json.dumps({
                        "argv": command, "library": str(library),
                        "exit_code": result.returncode}, indent=2) + "\n")
                    if result.returncode:
                        raise RuntimeError(result.stderr)
                    row = list(csv.DictReader(io.StringIO(result.stdout)))[0]
                    row.update(dataset=dataset, version=label, trial=trial,
                               snapshot_sha256=digest(snapshot))
                    rows.append(row)
                    (output / "rows.json").write_text(json.dumps(rows, indent=2) + "\n")
                    print(json.dumps(row), flush=True)
                    # Only this freshly generated, reproducible snapshot is discarded.
                    snapshot.unlink()


if __name__ == "__main__":
    main()
