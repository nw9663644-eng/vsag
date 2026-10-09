#!/usr/bin/env python3
# Copyright 2024-present the vsag project
# SPDX-License-Identifier: Apache-2.0
"""Measure trusted shared-library ELF closures, including resolved system runtime.

This is not a wheel/container/SDK measurement or a dlopen plugin inventory.
Source ELFs are never modified: identical strip rules apply only to scratch copies.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dependencies(output):
    result = set()
    if "not found" in output:
        raise ValueError("unresolved ELF dependency")
    for line in output.splitlines():
        match = re.search(r"(?:=>\s+)?(/[^\n]+?)\s+\(0x[0-9a-fA-F]+\)", line)
        if match:
            result.add(Path(match.group(1)).resolve(strict=True))
    return result


def measure(root, scratch):
    root = root.resolve(strict=True)
    pending = [root]
    records = {}
    logs = {}
    environment = os.environ.copy()
    environment.pop("LD_PRELOAD", None)
    environment["LD_LIBRARY_PATH"] = str(root.parent)
    while pending:
        path = pending.pop()
        if str(path) in records:
            continue
        payload_hash = digest(path)
        output = subprocess.check_output(["ldd", str(path)], env=environment, text=True)
        resolved = dependencies(output)
        logs[str(path)] = output
        copy = scratch / (str(len(records)) + "-" + path.name)
        shutil.copyfile(path, copy)
        subprocess.run(["strip", "--strip-unneeded", str(copy)], check=True)
        assert digest(path) == payload_hash, "source ELF changed"
        records[str(path)] = {
            "source_bytes": path.stat().st_size, "source_sha256": payload_hash,
            "stripped_bytes": copy.stat().st_size, "stripped_sha256": digest(copy),
            "dependencies": sorted(map(str, resolved)),
        }
        pending.extend(resolved)
    return {
        "root": str(root), "files": records,
        "root_source_bytes": records[str(root)]["source_bytes"],
        "root_stripped_bytes": records[str(root)]["stripped_bytes"],
        "closure_source_bytes": sum(r["source_bytes"] for r in records.values()),
        "closure_stripped_bytes": sum(r["stripped_bytes"] for r in records.values()),
        "ldd": logs,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lite", type=Path, required=True)
    parser.add_argument("--full", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--scratch", type=Path, default=Path("/dev/shm"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    report = {"scope": "shared-library ELF DT_NEEDED closure; system runtime included once "
                       "per resolved realpath; excludes dlopen plugins, executables, headers, "
                       "Python bindings, container, data and index files",
              "strip": subprocess.check_output(["strip", "--version"], text=True).splitlines()[0],
              "ldd": subprocess.check_output(["ldd", "--version"], text=True).splitlines()[0],
              "strip_arguments": ["--strip-unneeded"],
              "script_sha256": digest(Path(__file__))}
    with tempfile.TemporaryDirectory(prefix="vsag-elf-closure-", dir=args.scratch) as temp:
        root = Path(temp)
        for name, path in [("lite", args.lite), ("full", args.full)]:
            folder = root/name
            folder.mkdir()
            report[name] = measure(path, folder)
    report["stripped_closure_reduction_percent"] = (
        1 - report["lite"]["closure_stripped_bytes"] / report["full"]["closure_stripped_bytes"]
    ) * 100
    (args.output/"closure.json").write_text(json.dumps(report, indent=2)+"\n")
    print(json.dumps({name: report[name]["closure_stripped_bytes"]
                      for name in ["lite", "full"]}))
    print(report["stripped_closure_reduction_percent"])


if __name__ == "__main__":
    main()
