#!/usr/bin/env python3
# Copyright 2024-present the vsag project
# SPDX-License-Identifier: Apache-2.0
"""Linux-only offline row-restoration ablation using the existing slot probe.

MASK bit 0 restores updated-source rows; bit 1 restores other-source rows.
No native Update performance or production maintenance policy is measured.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import struct
import subprocess


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def read_exact(f, n):
    value = f.read(n)
    if len(value) != n:
        raise ValueError('truncated adjacency or snapshot')
    return value


def row(f, code, count, degree, source):
    width = struct.calcsize(code)
    n = struct.unpack('<' + code, read_exact(f, width))[0]
    if n > degree:
        raise ValueError('adjacency exceeds configured degree')
    targets = struct.unpack('<' + code * n, read_exact(f, width * n))
    if len(set(targets)) != n or any(b >= count or b == source for b in targets):
        raise ValueError('invalid adjacency target')
    return targets


def build_control(snapshot, adjacency, cycles, mask, replacement_vectors=None):
    if mask not in range(4):
        raise ValueError('restore mask must be 0..3')
    with Path(snapshot).open('rb') as source, Path(adjacency).open('rb') as edges:
        header = read_exact(source, 64)
        if header[:8] != b'VSAGLT01':
            raise ValueError('invalid snapshot magic')
        version, dim, count, payload, representation, degree, ef = struct.unpack('<7Q', header[8:])
        if (version, representation) != (2, 2) or not (0 < dim <= 4096 and count > 0 and 0 < degree <= 64 and ef > 0):
            raise ValueError('requires valid v2 FP32 graph')
        if payload + 48 != Path(snapshot).stat().st_size:
            raise ValueError('snapshot payload mismatch')
        if not 0 < cycles <= count or math.gcd(count, 8191) != 1:
            raise ValueError('invalid distinct update schedule')
        ids = read_exact(source, 8 * count)
        if struct.unpack('<' + 'q' * count, ids) != tuple(range(count)):
            raise ValueError('evidence encoding requires IDs equal to slots')
        updated = {i * 8191 % count for i in range(cycles)}
        vector_start = 64 + 8 * count
        vector_end = vector_start + 4 * count * dim
        source.seek(vector_end)
        chosen = []
        restored = 0
        for a in range(count):
            original = row(source, 'Q', count, degree, a)
            maintained = row(edges, 'I', count, degree, a)
            restore = bool(mask & (1 if a in updated else 2))
            chosen.append(original if restore else maintained)
            restored += restore
        if source.read(1) or edges.read(1):
            raise ValueError('trailing snapshot or adjacency bytes')
        fd = os.memfd_create('vsag-lite-edge-control', os.MFD_CLOEXEC)
        try:
            new_payload = 16 + count * 16 + count * dim * 4 + 8 * sum(map(len, chosen))
            os.write(fd, b'VSAGLT01' + struct.pack('<7Q', version, dim, count, new_payload,
                                                 representation, degree, ef))
            source.seek(64)
            remaining = vector_end - 64
            while remaining:
                block = read_exact(source, min(1048576, remaining))
                written = os.write(fd, block)
                if written != len(block):
                    raise OSError('short memory snapshot write')
                remaining -= len(block)
            if replacement_vectors is None:
                for a in updated:
                    offset = vector_start + 4 * a * dim
                    before = struct.unpack('<f', os.pread(fd, 4, offset))[0]
                    encoded = struct.pack('<f', before + 0.125)
                    after = struct.unpack('<f', encoded)[0]
                    if not math.isfinite(after) or after == before:
                        raise ValueError('update must change a finite FP32 value')
                    if os.pwrite(fd, encoded, offset) != 4:
                        raise OSError('short coordinate write')
            else:
                with Path(replacement_vectors).open('rb') as replacements:
                    if Path(replacement_vectors).stat().st_size != cycles * (4 + 4 * dim):
                        raise ValueError('replacement file length mismatch')
                    for cycle in range(cycles):
                        if struct.unpack('<I', read_exact(replacements, 4))[0] != dim:
                            raise ValueError('replacement dimension mismatch')
                        data = read_exact(replacements, 4 * dim)
                        values = struct.unpack('<' + 'f' * dim, data)
                        offset = vector_start + 4 * ((cycle * 8191) % count) * dim
                        before = os.pread(fd, 4 * dim, offset)
                        if not all(math.isfinite(x) for x in values) or struct.unpack('<' + 'f' * dim, before) == values:
                            raise ValueError('replacement must change a finite vector')
                        if os.pwrite(fd, data, offset) != len(data):
                            raise OSError('short replacement write')
            for targets in chosen:
                data = struct.pack('<' + 'Q' * (len(targets) + 1), len(targets), *targets)
                if os.write(fd, data) != len(data):
                    raise OSError('short adjacency write')
            assert os.fstat(fd).st_size == new_payload + 48
            receipt = dict(mask=mask, cycles=cycles, count=count, dim=dim, max_degree=degree,
                           ef_search=ef, restored_rows=restored, explicit_edges=sum(map(len, chosen)),
                           input_snapshot_sha256=digest(snapshot), adjacency_sha256=digest(adjacency),
                           control_sha256=digest('/proc/self/fd/' + str(fd)))
            if replacement_vectors is not None:
                receipt['replacement_vectors_sha256'] = digest(replacement_vectors)
            return fd, receipt
        except BaseException:
            os.close(fd)
            raise


def run(snapshot, adjacency, dataset, output, cycles, mask, binary, replacement_vectors=None):
    output = Path(output)
    for suffix in ['', '.neighbors.csv', '.receipt.json']:
        if Path(str(output) + suffix).exists():
            raise ValueError('output already exists')
    fd, receipt = build_control(snapshot, adjacency, cycles, mask, replacement_vectors)
    try:
        path = '/proc/self/fd/' + str(fd)
        command = [str(Path(binary).resolve()), path, path, str(Path(dataset).resolve()), str(output)]
        done = subprocess.run(command, pass_fds=(fd,), check=True)
        receipt.update(command=command, exit=done.returncode, binary_sha256=digest(binary))
        Path(str(output) + '.receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    finally:
        os.close(fd)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('snapshot')
    parser.add_argument('adjacency')
    parser.add_argument('dataset')
    parser.add_argument('output')
    parser.add_argument('cycles', type=int)
    parser.add_argument('mask', type=int, choices=range(4))
    parser.add_argument('binary')
    parser.add_argument('--replacement-vectors')
    args = parser.parse_args()
    run(**vars(args))
