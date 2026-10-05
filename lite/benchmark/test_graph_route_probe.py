"""Regression fixtures for the standalone offline route probe.

Usage: python3 test_graph_route_probe.py /path/to/lite_graph_route_probe
"""
import csv
import io
from pathlib import Path
import struct
import subprocess
import sys
import tempfile


def snapshot(path, vectors, links, degree):
    count = len(vectors)
    payload = struct.pack('<QQ', degree, 128)
    payload += struct.pack('<' + 'Q' * count, *range(count))
    payload += struct.pack('<' + 'f' * count, *vectors)
    for row in links:
        payload += struct.pack('<Q', len(row))
        payload += struct.pack('<' + 'Q' * len(row), *row)
    path.write_bytes(b'VSAGLT01' + struct.pack('<QQQQQ', 2, 1, count, len(payload), 2) + payload)


def main():
    binary = str(Path(sys.argv[1]).resolve())
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        (root / 'queries.fvecs').write_bytes(struct.pack('<if', 1, 0.0))
        (root / 'groundtruth.ivecs').write_bytes(struct.pack('<ii', 1, 0))
        case = 0

        def run(vectors, links, degree, mode=None):
            nonlocal case
            case += 1
            source = root / f'{case}.snapshot'
            snapshot(source, vectors, links, degree)
            command = [binary, str(source), str(root), str(root / f'{case}.csv')]
            if mode is not None:
                command += ['128', 'uniform', mode]
            return subprocess.run(command, capture_output=True, text=True, check=False)

        def summary(result):
            assert result.returncode == 0, result.stderr
            return next(csv.DictReader(io.StringIO(result.stdout)))

        # Collinear complete graph: diversity must retain a connected chain,
        # whereas nearest selection retains the complete graph at degree two.
        for mode, expected_degree in [('preserve', 2), ('symmetric', 2), ('diverse', 4 / 3)]:
            row = summary(run([0, 1, 3], [[1, 2], [0, 2], [0, 1]], 2, mode))
            assert abs(float(row['mean_graph_degree']) - expected_degree) < 1e-6
            assert row['zero_in'] == '0' and row['edge_reachable_from_zero'] == '3'
            assert row['recall_at_k'] == '1.000000'

        # Incoming-only candidates must become eligible, without inventing self edges.
        row = summary(run([0, 1, 3], [[1], [2], []], 2, 'symmetric'))
        assert row['zero_out'] == '0' and row['edge_reachable_from_zero'] == '3'
        for mode in (None, 'preserve', 'symmetric', 'diverse'):
            row = summary(run([0], [[]], 1, mode))
            assert row['zero_out'] == '1' and row['zero_in'] == '1'
            assert row['edge_reachable_from_zero'] == '1'
        result = run([0], [[]], 1, 'invalid')
        assert result.returncode != 0 and 'NEIGHBOR_MODE' in result.stderr
        result = run([], [], 1, 'diverse')
        assert result.returncode != 0 and 'invalid snapshot layout' in result.stderr
    print('Route probe fixtures passed')


if __name__ == '__main__':
    main()
