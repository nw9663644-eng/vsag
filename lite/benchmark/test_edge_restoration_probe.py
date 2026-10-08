#!/usr/bin/env python3
# Copyright 2024-present the vsag project
# SPDX-License-Identifier: Apache-2.0
"""Test row-selection factors, exact snapshot bytes and native calibration."""
import csv
import json
import os
from pathlib import Path
import struct
import sys
import tempfile
from edge_restoration_probe import build_control, run
from test_graph_route_probe import snapshot


def main():
    binary = str(Path(sys.argv[1]).resolve())
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp); source = root / 'initial'; edges = root / 'final.u32'
        original = [[1], [2], [0]]; maintained = [[2], [0], [1]]
        snapshot(source, [0.0, 0.0625, 1.0], original, 2)
        packed = b''.join(struct.pack('<II', 1, r[0]) for r in maintained)
        edges.write_bytes(packed)
        (root / 'queries.fvecs').write_bytes(struct.pack('<if', 1, 0.0))
        (root / 'groundtruth.ivecs').write_bytes(struct.pack('<ii', 1, 1))
        for mask in range(4):
            fd, receipt = build_control(source, edges, 1, mask)
            try:
                data = os.pread(fd, os.fstat(fd).st_size, 0)
                assert data[:32] == source.read_bytes()[:32]
                assert data[40:64 + 3 * 8] == source.read_bytes()[40:64 + 3 * 8]
                assert struct.unpack_from('<3f', data, 64 + 3 * 8) == (0.125, 0.0625, 1.0)
                assert struct.unpack_from('<Q', data, 32)[0] + 48 == len(data)
                pos = 64 + 3 * 8 + 3 * 4
                for a in range(3):
                    n = struct.unpack_from('<Q', data, pos)[0]; pos += 8
                    row = list(struct.unpack_from('<' + 'Q' * n, data, pos)); pos += 8 * n
                    assert row == (original[a] if mask & (1 if a == 0 else 2) else maintained[a])
                assert pos == len(data) and receipt['restored_rows'] == (int(bool(mask & 1)) + 2 * int(bool(mask & 2)))
            finally:
                os.close(fd)
            output = root / ('mask-' + str(mask) + '.csv')
            run(source, edges, root, output, 1, mask, binary)
            evidence = list(csv.DictReader(Path(str(output) + '.neighbors.csv').open()))
            assert len(evidence) == 8 and all(r['id'] == '1' and float.fromhex(r['distance']) == 0.0625 ** 2 for r in evidence)
            states = list(csv.DictReader(output.open()))
            assert len(states) == 8 and all(r['hits'] == r['truth_visited'] == '1' for r in states)
            assert states[0]['baseline_native_ids_equal'] == '1'
            assert json.loads(Path(str(output) + '.receipt.json').read_text())['exit'] == 0
        for suffix in ['', '.neighbors.csv', '.receipt.json']:
            output = root / ('protected-' + str(len(suffix)))
            marker = Path(str(output) + suffix); marker.write_text('keep\n')
            try:
                run(source, edges, root, output, 1, 0, binary)
                raise AssertionError('overwrite accepted')
            except ValueError:
                assert marker.read_text() == 'keep\n'
        cases = [(0, 0), (4, 0), (-1, 0), (1, 4)]
        for cycles, mask in cases:
            try:
                fd, _ = build_control(source, edges, cycles, mask)
                os.close(fd); raise AssertionError('invalid schedule accepted')
            except ValueError:
                pass
        for data in [packed[:-1], packed + b'x', struct.pack('<II', 1, 0) + packed[8:],
                     struct.pack('<II', 1, 3) + packed[8:], struct.pack('<III', 2, 1, 1) + packed[8:],
                     struct.pack('<I', 3) + packed[4:]]:
            edges.write_bytes(data)
            try:
                fd, _ = build_control(source, edges, 1, 0)
                os.close(fd); raise AssertionError('invalid adjacency accepted')
            except ValueError:
                pass
    print('Edge restoration fixtures passed')


if __name__ == '__main__':
    main()
