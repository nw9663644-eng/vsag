# Copyright 2024-present the vsag project
# SPDX-License-Identifier: Apache-2.0
"""Prepare reproducible real changed-vector CRUD inputs for two 100k datasets."""
import argparse
import hashlib
import json
from pathlib import Path
import struct

import numpy as np


SOURCES = {
    "gist100k100": Path("/home/ubuntu/project/vsag-lite-datasets/gist/"
                        "prepared-10k-100k/scale-100000"),
    "cohere100k100": Path("/home/ubuntu/project/vsag-lite-cohere-normalized-20261006/"
                          "prepared/scale-100000"),
}


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_fvecs(path):
    with path.open("rb") as source:
        dim = struct.unpack("<i", source.read(4))[0]
    assert 0 < dim <= 4096
    rows = np.memmap(path, dtype="<f4", mode="r").reshape(-1, dim + 1)
    assert np.all(rows[:, 0].view("<i4") == dim)
    return rows[:, 1:].copy()


def write_fvecs(path, vectors):
    with path.open("wb") as out:
        prefix = struct.pack("<i", vectors.shape[1])
        for row in vectors:
            out.write(prefix)
            out.write(row.astype("<f4", copy=False).tobytes())


def truth(base, queries):
    vectors = base.astype(np.float64)
    ids = np.arange(len(base))
    result = []
    for query in queries:
        differences = vectors - query.astype(np.float64)
        distances = np.einsum("ij,ij->i", differences, differences)
        top = np.lexsort((ids, distances))[:10]
        result.append(struct.pack("<i10i", 10, *top))
    return b"".join(result)


def prepare(root, label, source, rounds, crud_ops):
    output = root / label
    output.mkdir()
    base_path = source / "base.fvecs"
    queries_path = source / "queries.fvecs"
    base = read_fvecs(base_path)
    queries = read_fvecs(queries_path)
    assert len(base) == 100000 and len(queries) == 100
    assert base.shape[1] == queries.shape[1]
    assert np.all(np.isfinite(base)) and np.all(np.isfinite(queries))
    initial = truth(base, queries)
    assert initial == (source / "groundtruth.ivecs").read_bytes(), label + " initial truth mismatch"
    current = base.copy()
    replacement_path = output / "replacement.fvecs"
    with replacement_path.open("wb") as out:
        prefix = struct.pack("<i", base.shape[1])
        for cycle in range(rounds):
            ids = (cycle * 65537 + np.arange(crud_ops, dtype=np.int64) * 8191) % len(base)
            assert len(np.unique(ids)) == crud_ops
            donors = (ids + 7919 * (cycle + 1)) % len(base)
            changed = (np.float32(.875) * current[ids] +
                       np.float32(.125) * base[donors]).astype("<f4")
            if label.startswith("cohere"):
                norms = np.sqrt(np.sum(changed.astype(np.float64) ** 2, axis=1))
                changed = (changed.astype(np.float64) / norms[:, None]).astype("<f4")
            assert np.all(np.isfinite(changed))
            assert np.all(np.any(changed != current[ids], axis=1))
            for row in changed:
                out.write(prefix)
                out.write(row.tobytes())
            current[ids] = changed
    final = truth(current, queries)
    (output / "base.fvecs").symlink_to(base_path)
    (output / "queries.fvecs").symlink_to(queries_path)
    (output / "groundtruth.ivecs").write_bytes(initial)
    (output / "changed-groundtruth.ivecs").write_bytes(final)
    files = ["base.fvecs", "queries.fvecs", "groundtruth.ivecs",
             "changed-groundtruth.ivecs", "replacement.fvecs"]
    receipt = {
        "label": label, "source": str(source), "base_count": len(base),
        "query_count": len(queries), "dim": base.shape[1], "rounds": rounds,
        "crud_ops_per_round": crud_ops, "metric": "squared_l2",
        "schedule": "(round*65537+operation*8191)%N",
        "recipe": "FP32 .875*current+.125*original donor; donor=(id+7919*(round+1))%N; Cohere FP64 renorm to FP32",
        "truth": "FP64 direct differences/einsum; distance then ID lexsort top10",
        "numpy_version": np.__version__,
        "files": {name: {"bytes": (output / name).stat().st_size,
                          "sha256": sha256(output / name)} for name in files},
    }
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(label, "prepared", flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--crud-ops", type=int, default=10000)
    args = parser.parse_args()
    assert args.rounds > 0 and 0 < args.crud_ops <= 100000
    args.output.mkdir(exist_ok=False)
    for label, source in SOURCES.items():
        prepare(args.output, label, source, args.rounds, args.crud_ops)


if __name__ == "__main__":
    main()
