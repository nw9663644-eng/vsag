#!/usr/bin/env python3
# Copyright 2024-present the vsag project
# SPDX-License-Identifier: Apache-2.0
"""Verify independent slot factors using equivalent relabelled snapshots."""
import csv
from pathlib import Path
import struct
import subprocess
import sys
import tempfile


def snapshot(path, ids, dim=4):
    count = len(ids)
    vectors = [0.0] * (count * dim)
    slots = {id: slot for slot, id in enumerate(ids)}
    # Fixed external-ID edges; reorder only physical storage.
    links = [[slots[(id + 3) % count], slots[(id + 5) % count]] for id in ids]
    payload = 16 + count * (16 + dim * 4) + 8 * sum(map(len, links))
    data = b'VSAGLT01' + struct.pack('<7Q', 2, dim, count, payload, 2, 2, 4)
    data += struct.pack('<' + 'q' * count, *ids)
    data += struct.pack('<' + 'f' * len(vectors), *vectors)
    for row in links:
        data += struct.pack('<Q', len(row)) + struct.pack('<' + 'Q' * len(row), *row)
    path.write_bytes(data)


def records(path, rows, code):
    path.write_bytes(b''.join(struct.pack('<I', len(row)) +
                             struct.pack('<' + code * len(row), *row) for row in rows))


def read(path):
    with path.open() as stream:
        return list(csv.DictReader(stream))


def main():
    executable = str(Path(sys.argv[1]).resolve())
    with tempfile.TemporaryDirectory(prefix='lite-slot-fixture-') as directory:
        root = Path(directory)
        order = [12, 7, 10, 15, 8, 5, 0, 13, 4, 11, 6, 9, 2, 1, 14, 3]
        snapshot(root / 'physical', order)
        snapshot(root / 'reference', list(range(16)))
        records(root / 'queries.fvecs', [[0.0] * 4, [0.0] * 4], 'f')
        records(root / 'groundtruth.ivecs', [[0, 1, 2, 3], [0, 1, 2, 999]], 'i')
        commands = []

        def run(name, graph, reference, success):
            output = root / (name + '.csv')
            cmd = [executable, str(graph), str(reference), str(root), str(output)]
            result = subprocess.run(cmd, capture_output=True, text=True)
            commands.append((name, result.returncode))
            assert (result.returncode == 0) == success, (name, result.stderr)
            return output, cmd

        physical, physical_cmd = run('physical', root / 'physical', root / 'reference', True)
        logical, _ = run('logical', root / 'reference', root / 'reference', True)
        rows = read(physical)
        assert len(rows) == 16 and {int(r['mask']) for r in rows} == set(range(8))
        valid = [r for r in rows if r['eligible'] == '1']
        assert len(valid) == 8 and all(int(r['tie_comparisons']) > 0 for r in valid)
        assert valid[0]['baseline_native_ids_equal'] == '1'
        assert all(r['eligible'] == '0' and r['hits'] == '0' for r in rows[8:])
        a = read(Path(str(physical) + '.neighbors.csv'))
        b = read(Path(str(logical) + '.neighbors.csv'))
        ids = lambda data, mask: [int(r['id']) for r in data if int(r['mask']) == mask]
        assert ids(a, 7) == ids(b, 0), 'all restored factors differ from physical reordering'
        assert ids(a, 0) != ids(a, 4), 'fixture did not exercise tie-order override'
        original = physical.read_bytes()
        assert subprocess.run(physical_cmd, capture_output=True).returncode != 0
        assert physical.read_bytes() == original
        sidecar = root / 'blocked.csv.neighbors.csv'
        sidecar.write_text('preserve\n')
        run('blocked', root / 'physical', root / 'reference', False)
        assert sidecar.read_text() == 'preserve\n' and not (root / 'blocked.csv').exists()
        snapshot(root / 'short-reference', list(range(8)))
        run('uncovered', root / 'physical', root / 'short-reference', False)
        snapshot(root / 'wrong-dim', list(range(16)), 3)
        run('wrong-dim', root / 'physical', root / 'wrong-dim', False)
        (root / 'broken').write_bytes(b'VSAGLT01')
        run('truncated', root / 'broken', root / 'reference', False)
        records(root / 'groundtruth.ivecs', [[0, 0, 1, 2], [0, 1, 2, 3]], 'i')
        run('duplicate-truth', root / 'physical', root / 'reference', False)
        assert subprocess.run([executable], capture_output=True).returncode != 0
        print('slot-factor fixtures passed:', commands)


if __name__ == '__main__':
    main()
