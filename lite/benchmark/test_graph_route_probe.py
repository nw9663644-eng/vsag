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
    subprocess.run([binary, '--self-test'], check=True)
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        (root / 'queries.fvecs').write_bytes(struct.pack('<if', 1, 0.0))
        (root / 'groundtruth.ivecs').write_bytes(struct.pack('<ii', 1, 0))
        case = 0

        def run(vectors, links, degree, mode=None, api_repeats=None, entry_mode="uniform", crud_cycles=None, ef_search=128):
            nonlocal case
            case += 1
            source = root / f'{case}.snapshot'
            snapshot(source, vectors, links, degree)
            command = [binary, str(source), str(root), str(root / f'{case}.csv')]
            if mode is not None:
                command += [str(ef_search), entry_mode, mode]
            if api_repeats is not None:
                command += [str(api_repeats)]
            if crud_cycles is not None:
                command += [str(crud_cycles)]
            result = subprocess.run(command, capture_output=True, text=True, check=False)
            if api_repeats is not None and result.returncode == 0:
                with (root / f'{case}.csv.api.csv').open() as output:
                    result.api = next(csv.DictReader(output))
                with (root / f'{case}.csv.api.csv.latencies.csv').open() as output:
                    samples = list(csv.DictReader(output))
                assert len(samples) == int(result.api['query_count']) * api_repeats
                values = sorted(float(row['latency_us']) for row in samples)
                assert abs(values[-1] - float(result.api['search_p99_us'])) < 1e-6

            if crud_cycles is not None and result.returncode == 0:
                with (root / f'{case}.csv.api.csv.crud.csv').open() as output:
                    result.crud = next(csv.DictReader(output))
                with (root / f'{case}.csv.api.csv.crud.csv.samples.csv').open() as output:
                    assert len(list(csv.DictReader(output))) == crud_cycles
            return result

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
        for mode in (None, 'preserve', 'symmetric', 'diverse', 'diverse_repair', 'diverse_reverse', 'diverse_reverse_safe'):
            row = summary(run([0], [[]], 1, mode))
            assert row['zero_out'] == '1' and row['zero_in'] == '1'
            assert row['edge_reachable_from_zero'] == '1'
        # Diversity drops the incoming edge of the far end of a directed star.
        row = summary(run([0, 1, 2], [[], [0], [0]], 2, 'diverse'))
        assert row['zero_in'] == '1'
        row = summary(run([0, 1, 2], [[], [0], [0]], 2, 'diverse_repair'))
        assert row['zero_in'] == '0' and row['edge_reachable_from_zero'] == '3'
        # At degree one the sole incoming edge must not be displaced.
        row = summary(run([0, 1, 2], [[], [0], [0]], 1, 'diverse_repair'))
        assert row['zero_in'] == '1' and row['mean_graph_degree'] == '1.000000'
        # Saturated rows permit replacement only when the displaced target
        # retains another incoming edge; zero in-degree is not connectivity.
        row = summary(run([0, 1, 2, 3], [[], [0], [0], [1]], 1, 'diverse_repair'))
        assert row['zero_in'] == '0' and row['mean_graph_degree'] == '1.000000'
        assert row['edge_reachable_from_zero'] == '2'
        row = summary(run([0, 1, 2, 3], [[1], [0], [3], [2]], 1, 'preserve'))
        assert row['weak_components'] == '2' and row['largest_weak_component'] == '2'
        assert row['reverse_reachable_from_zero'] == '2'
        row = summary(run([0, 1, 2], [[1], [2], []], 1, 'preserve'))
        assert row['weak_components'] == '1' and row['largest_weak_component'] == '3'
        assert row['edge_reachable_from_zero'] == '3'
        assert row['reverse_reachable_from_zero'] == '1'
        # The reverse-fill pipeline preserves a small connected graph
        # without exceeding the degree budget.
        row = summary(run([0, 1, 3], [[1, 2], [2], [0]], 2, 'diverse_reverse'))
        assert row['edge_reachable_from_zero'] == '3'
        assert row['reverse_reachable_from_zero'] == '3'
        assert float(row['mean_graph_degree']) <= 2
        # Saturated disconnected cycles cannot be fixed by append-only repair.
        row = summary(run([0, 1, 2, 3], [[1], [0], [3], [2]], 1, 'diverse_reverse'))
        assert row['weak_components'] == '2' and row['mean_graph_degree'] == '1.000000'
        # An asymmetric edge survives diversity because a closer neighbor
        # occludes its reverse. Spare-capacity fill restores that reverse.
        row = summary(run([0, 1, 3, 4], [[1, 2], [0], [3], [2]], 2, 'diverse_repair'))
        assert row['mean_graph_degree'] == '1.250000'
        row = summary(run([0, 1, 3, 4], [[1, 2], [0], [3], [2]], 2, 'diverse_reverse'))
        assert row['mean_graph_degree'] == '1.500000'
        assert row['edge_reachable_from_zero'] == '4'
        assert row['reverse_reachable_from_zero'] == '4'
        # No two-hop witness exists in these degree-one cycles: preserve them.
        row = summary(run([0, 1, 2, 3], [[1], [0], [3], [2]], 1, 'diverse_reverse_safe'))
        assert row['weak_components'] == '2' and row['mean_graph_degree'] == '1.000000'
        for mode in ('preserve', 'diverse', 'diverse_reverse'):
            result = run([0, 1, 3], [[1, 2], [0, 2], [0, 1]], 2, mode, 2)
            summary(result)
            assert result.api['recall_at_k'] == '1.000000'
            assert result.api['repeats'] == '2'
            assert float(result.api['search_p99_us']) >= float(result.api['search_p50_us'])
        result = run([0], [[]], 1, 'preserve', 0)
        assert result.returncode != 0 and 'API_REPEATS' in result.stderr
        result = run([0], [[]], 1, 'preserve', 2, 'greedy')
        assert result.returncode != 0 and 'uniform ENTRY_MODE' in result.stderr
        for mode in ('preserve', 'diverse_reverse'):
            result = run([0, 1, 3], [[1, 2], [0, 2], [0, 1]], 2, mode, 2,
                         crud_cycles=12)
            summary(result)
            assert result.crud['cycles'] == '12' and result.crud['recall_at_k'] == '1.000000'
        result = run([0], [[]], 2, 'preserve', 1, crud_cycles=4)
        summary(result)
        assert result.crud['recall_at_k'] == '1.000000'
        result = run([0], [[]], 1, 'preserve', 1, crud_cycles=0)
        assert result.returncode != 0 and 'CRUD_CYCLES' in result.stderr
        result = run([0, 1, 3], [[1, 2], [0, 2], [0, 1]], 2, 'preserve', 2,
                     crud_cycles=4, ef_search=1024)
        summary(result)
        assert result.api['configured_ef_search'] == '128'
        assert result.api['query_ef_search'] == '1024'
        assert result.crud['recall_at_k'] == '1.000000'
        result = run([0], [[]], 1, 'invalid')
        assert result.returncode != 0 and 'NEIGHBOR_MODE' in result.stderr
        result = run([], [], 1, 'diverse')
        assert result.returncode != 0 and 'invalid snapshot layout' in result.stderr
    print('Route probe fixtures passed')


if __name__ == '__main__':
    main()
