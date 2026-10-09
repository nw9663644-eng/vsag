# Copyright 2024-present the vsag project
# SPDX-License-Identifier: Apache-2.0
"""Frozen three-pass whole-row replay; requires NumPy, existing base and query archive."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import tarfile

import numpy as np


def digest(payload):
    return hashlib.sha256(payload).hexdigest()


def fvecs(rows):
    data = np.empty((len(rows), rows.shape[1] + 1), dtype="<f4")
    data[:, 0].view("<i4")[:] = rows.shape[1]
    data[:, 1:] = rows
    return data.tobytes()


def decode(payload):
    dim = struct.unpack_from("<i", payload)[0]
    data = np.frombuffer(payload, dtype="<f4").reshape(-1, dim + 1)
    assert np.all(data[:, 0].view("<i4") == dim)
    return data[:, 1:].copy()


def exact_truth(base, queries):
    vectors = base.astype(np.float64)
    result = []
    for query in queries:
        differences = vectors - query.astype(np.float64)
        distances = np.einsum("ij,ij->i", differences, differences)
        ids = np.lexsort((np.arange(len(base)), distances))[:10]
        result.append(struct.pack("<i10i", 10, *ids))
    return b"".join(result)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("archive", type=Path)
    args = parser.parse_args()
    args.output.mkdir(exist_ok=False)
    originals = {
        "gist10k600": "/home/ubuntu/project/vsag-lite-datasets/gist/prepared-10k-100k/scale-10000/base.fvecs",
        "cohere10k600": "/home/ubuntu/project/vsag-lite-cohere-normalized-20261006/prepared/scale-10000/base.fvecs",
    }
    with tarfile.open(args.archive) as archive:
        inputs = {m.name.removeprefix("./"): archive.extractfile(m).read()
                  for m in archive if m.isfile() and
                  any(m.name.endswith(s) for s in
                      [".queries.fvecs", ".groundtruth.ivecs", ".dataset.json"])}
    for label, original in originals.items():
        root = args.output / label
        root.mkdir()
        payload = Path(original).read_bytes()
        metadata = json.loads(inputs[label + ".dataset.json"])
        assert digest(payload) == metadata["base.fvecs"]["sha256"]
        base = decode(payload)
        assert len(base) == 10000
        query_payload = inputs[label + ".queries.fvecs"]
        queries = decode(query_payload)
        assert len(queries) == 600
        initial_truth = exact_truth(base, queries)
        assert initial_truth == inputs[label + ".groundtruth.ivecs"]
        current = base.copy()
        replacements = []
        for round in range(3):
            ids = (round * 65537 + np.arange(len(base)) * 8191) % len(base)
            assert len(np.unique(ids)) == len(base)
            donors = (ids + 7919 * (round + 1)) % len(base)
            changed = (np.float32(0.875) * current[ids] +
                       np.float32(0.125) * base[donors]).astype("<f4")
            if label.startswith("cohere"):
                norms = np.sqrt(np.sum(changed.astype(np.float64) ** 2, axis=1))
                changed = (changed.astype(np.float64) / norms[:, None]).astype("<f4")
            assert np.all(np.isfinite(changed))
            assert np.all(np.any(changed != current[ids], axis=1))
            replacements.append(changed)
            current[ids] = changed
        (root / "base.fvecs").symlink_to(original)
        data = {"queries.fvecs": query_payload, "groundtruth.ivecs": initial_truth,
                "changed-groundtruth.ivecs": exact_truth(current, queries),
                "replacement.fvecs": fvecs(np.concatenate(replacements))}
        for name, payload in data.items():
            (root / name).write_bytes(payload)
        receipt = {"label": label, "base_path": original, "base_sha256": metadata["base.fvecs"]["sha256"],
                   "base_count": len(base), "query_count": len(queries), "dim": base.shape[1],
                   "rounds": 3, "crud_ops": len(base), "metric": "squared_l2",
                   "recipe": "FP32 .875*current + .125*original donor; Cohere FP64 norm then FP32; donor=(id+7919*(round+1))%N",
                   "schedule": "(round*65537+operation*8191)%N",
                   "truth": "FP64 direct differences/einsum, distance then ID lexsort top10",
                   "numpy_version": np.__version__,
                   "files": {n: {"bytes": len(b), "sha256": digest(b)} for n, b in data.items()}}
        (root / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
        print(label, "prepared", flush=True)


if __name__ == "__main__":
    main()
