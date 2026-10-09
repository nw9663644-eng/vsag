#!/usr/bin/env python3
# Copyright 2024-present the vsag project
# SPDX-License-Identifier: Apache-2.0
"""Paired, fresh-process Lite/Full or Lite/control measurements.

Snapshots live in a caller-selected scratch filesystem; all raw logs, timings,
neighbors, configurations and snapshot hashes survive in the new output directory.
No cold-cache claim: page cache is uncontrolled. Native Full must use the supplied
matching installed headers/library; this script never builds or downloads Full.
"""
import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import statistics
import struct
import subprocess
import tempfile


def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def table(output, header):
    lines = output.splitlines()
    positions = [i for i, line in enumerate(lines) if line.startswith(header)]
    if len(positions) != 1:
        raise RuntimeError("missing or duplicate CSV header: " + header)
    return next(csv.DictReader(io.StringIO("\n".join(lines[positions[0]:positions[0]+2]))))


def run(cmd, env, stem, header):
    cmd = ["taskset", "-c", str(ARGS.cpu), "/usr/bin/time", "-f", "%M",
           "-o", str(stem)+".peak_kib", *map(str, cmd)]
    completed = subprocess.run(cmd, env=env, text=True, capture_output=True)
    Path(str(stem)+".stdout").write_text(completed.stdout)
    Path(str(stem)+".stderr").write_text(completed.stderr)
    Path(str(stem)+".command.json").write_text(json.dumps(cmd)+"\n")
    completed.check_returncode()
    result = table(completed.stdout, header)
    result["external_peak_rss_kib"] = int(Path(str(stem)+".peak_kib").read_text())
    return result


def main():
    out = Path(ARGS.output).resolve()
    out.mkdir(parents=True, exist_ok=False)
    lite = Path(ARGS.lite_build).resolve()
    control = Path(ARGS.control_library).resolve() if ARGS.control_library else None
    full = Path(ARGS.full_library).resolve() if ARGS.full_library else None
    if (control is None) == (full is None):
        raise ValueError("supply exactly one control-library or full-library")
    meta = {"arguments": vars(ARGS), "page_cache": "warm_uncontrolled",
            "blas_threads": 1, "omp_threads": 1,
            "query_warmup_rounds": 0, "construction_ef": 128, "degree": 16,
            "lite_library_sha256": digest(lite/"libvsag-lite.so"),
            "reference_library_sha256": digest(control if control else full),
            "native_full_profile": "small" if full else None,
            "cpu": subprocess.check_output(["lscpu"], text=True),
            "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
            "git_diff": subprocess.check_output(["git", "diff"], text=True),
            "script_sha256": digest(Path(__file__)),
            "lite_builder_sha256": digest(lite/"lite_graph_crud_quality"),
            "lite_loader_sha256": digest(lite/"lite_load_memory")}
    (out/"identity.json").write_text(json.dumps(meta, indent=2)+"\n")
    rows = []
    for dataset_text in ARGS.dataset:
        label, directory = dataset_text.split("=", 1)
        dataset = Path(directory).resolve()
        with open(dataset/"base.fvecs", "rb") as stream:
            dim = struct.unpack("<i", stream.read(4))[0]
        count = (dataset/"base.fvecs").stat().st_size // (4+4*dim)
        dataset_meta = {name: {"bytes": (dataset/name).stat().st_size,
                             "sha256": digest(dataset/name)}
                        for name in ["base.fvecs", "queries.fvecs", "groundtruth.ivecs"]}
        (out/(label+".dataset.json")).write_text(json.dumps(dataset_meta, indent=2)+"\n")
        for storage in ARGS.storage:
            for trial in range(ARGS.trials):
                names = ["control", "lite"] if control else ["full", "lite"]
                if trial % 2:
                    names.reverse()
                hashes, neighbors = {}, {}
                with tempfile.TemporaryDirectory(prefix="vsag-aligned-", dir=ARGS.scratch) as scratch:
                    for name in names:
                        tag = f"{label}-{storage}-{trial}-{name}"
                        stem = out/tag
                        snapshot = Path(scratch)/(tag+".snapshot")
                        env = os.environ.copy()
                        env.update(VSAG_GRAPH_STORAGE=storage, VSAG_GRAPH_DEGREE="16",
                                   VSAG_GRAPH_EF="128", VSAG_GRAPH_QUERY_EF=str(ARGS.ef),
                                   VSAG_FULL_PROFILE="small", OPENBLAS_NUM_THREADS="1",
                                   OMP_NUM_THREADS="1", MKL_NUM_THREADS="1")
                        if name == "control":
                            env["LD_LIBRARY_PATH"] = str(control.parent)
                        elif name == "lite":
                            env["LD_LIBRARY_PATH"] = str(lite)
                        if name == "full":
                            mode = "rabitq3x5" if storage == "rabitq8" else storage
                            env["VSAG_LOAD_FULL_MODE"] = mode
                            builder = [ARGS.full_builder, dataset, snapshot, mode,
                                       ARGS.full_ef if ARGS.full_ef else ARGS.ef, 0]
                            header = "mode,base_count,"
                            loader = ARGS.full_loader
                        else:
                            builder = [lite/"lite_graph_crud_quality", dataset, snapshot, 0, 1,
                                       str(stem)+".queries.csv"]
                            header = "base_count,query_count,"
                            loader = lite/"lite_load_memory"
                        metrics = run(builder, env, stem, header)
                        if name != "full" and metrics["storage"] != storage:
                            raise RuntimeError("runner storage differs from requested storage")
                        hashes[name] = digest(snapshot)
                        neighbor_source = (Path(str(snapshot)+".neighbors.csv") if name == "full"
                                           else Path(str(stem)+".queries.csv.neighbors.csv"))
                        if name == "full":
                            for suffix in [".latencies.csv", ".parameters.json", ".neighbors.csv"]:
                                source = Path(str(snapshot)+suffix)
                                if source.exists():
                                    shutil.copyfile(source, str(stem)+suffix)
                        if not neighbor_source.exists():
                            raise RuntimeError("missing raw neighbors")
                        neighbors[name] = digest(neighbor_source)
                        loads = []
                        for sample in range(ARGS.loads):
                            loads.append(run([loader, snapshot, dim, count], env,
                                             out/(tag+f"-load-{sample}"), "dim,count,"))
                        row = {"dataset": label, "storage": storage, "trial": trial, "name": name,
                               "snapshot_sha256": hashes[name], "build": metrics, "loads": loads}
                        rows.append(row)
                        (out/"rows.json").write_text(json.dumps(rows, indent=2)+"\n")
                        print(tag, metrics["recall_at_k"], metrics["search_p50_us"],
                              statistics.median(float(x["load_ms"]) for x in loads), flush=True)
                if control and hashes["control"] != hashes["lite"]:
                    raise RuntimeError("I/O optimization changed snapshot bytes")
                if control and neighbors.get("control") != neighbors.get("lite"):
                    raise RuntimeError("I/O optimization changed neighbors")
    summary = []
    for key in sorted({(r["dataset"], r["storage"], r["name"]) for r in rows}):
        selected = [r for r in rows if (r["dataset"], r["storage"], r["name"]) == key]
        item = dict(zip(["dataset", "storage", "name"], key))
        for metric in ["recall_at_k", "build_ms", "search_p50_us", "search_p99_us",
                       "save_ms", "snapshot_bytes", "external_peak_rss_kib"]:
            item[metric] = statistics.median(float(r["build"][metric]) for r in selected)
        for metric in ["load_ms", "loaded_rss_kib", "process_peak_rss_kib",
                       "before_create_rss_kib", "before_load_rss_kib"]:
            item[metric] = statistics.median(float(s[metric]) for r in selected for s in r["loads"])
        summary.append(item)
    (out/"summary.json").write_text(json.dumps(summary, indent=2)+"\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lite-build", required=True)
    parser.add_argument("--control-library")
    parser.add_argument("--full-library")
    parser.add_argument("--full-builder")
    parser.add_argument("--full-loader")
    parser.add_argument("--dataset", action="append", required=True, help="label=directory")
    parser.add_argument("--storage", nargs="+", default=["fp32", "fp16", "rabitq8"],
                        choices=["fp32", "fp16", "rabitq8"])
    parser.add_argument("--output", required=True)
    parser.add_argument("--scratch", default="/dev/shm")
    parser.add_argument("--trials", type=int, default=3)
    parser.add_argument("--loads", type=int, default=3)
    parser.add_argument("--ef", type=int, default=128)
    parser.add_argument("--full-ef", type=int, help="explicit separate Full query budget")
    parser.add_argument("--cpu", type=int, default=0)
    ARGS = parser.parse_args()
    if min(ARGS.trials, ARGS.loads, ARGS.ef) < 1:
        parser.error("trials, loads and ef must be positive")
    if ARGS.full_ef is not None and ARGS.full_ef < 1:
        parser.error("full-ef must be positive")
    if ARGS.full_library and not (ARGS.full_builder and ARGS.full_loader):
        parser.error("Full mode requires matching builder and loader")
    main()
