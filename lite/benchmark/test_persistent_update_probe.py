"""Persistent-update replay fixtures; run with the route-probe binary path."""
import csv
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
from test_graph_route_probe import snapshot


def main():
    binary = str(Path(sys.argv[1]).resolve())
    mode = sys.argv[2] if len(sys.argv) > 2 else '--persistent-update'
    trace = len(sys.argv) > 3 and sys.argv[3] == 'trace'
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        source = root / 'initial.snapshot'
        snapshot(source, [0.0, 0.0625, 1.0], [[1, 2], [0, 2], [0, 1]], 2)
        (root / 'queries.fvecs').write_bytes(struct.pack('<if', 1, 0.0))
        (root / 'groundtruth.ivecs').write_bytes(struct.pack('<ii', 1, 0))
        (root / 'changed-groundtruth.ivecs').write_bytes(struct.pack('<ii', 1, 1))
        def run(output, count='1'):
            return subprocess.run([binary, mode, str(source), str(root),
                                   str(output), count] + (['trace'] if trace else []), capture_output=True, text=True)
        output = root / 'result.csv'
        result = run(output)
        assert result.returncode == 0, result.stderr
        row = next(csv.DictReader(output.open()))
        assert row['initial_recall'] == row['changed_recall'] == '1.000000'
        assert row['roundtrip'] == '1' and row['cycles'] == '1'
        neighbors = list(csv.DictReader(Path(str(output) + '.neighbors.csv').open()))
        assert [(r['phase'], int(r['id'])) for r in neighbors] == [('initial', 0), ('changed', 1)]
        assert [float.fromhex(r['distance']) for r in neighbors] == [0.0, 0.0625 ** 2]
        updates = list(csv.DictReader(Path(str(output) + '.updates.csv').open()))
        assert len(updates) == 1 and updates[0]['id'] == '0'
        assert float.fromhex(updates[0]['original_first']) == 0
        assert float.fromhex(updates[0]['changed_first']) == 0.125
        if mode == '--storage-only-update':
            receipt = next(csv.DictReader(Path(str(output) + '.control.csv').open()))
            assert receipt['coordinates'] == '1' and receipt['other_bytes_equal'] == '1'
            assert int(receipt['checked_bytes']) == source.stat().st_size
            assert 0 < int(receipt['changed_bytes']) <= 4
            assert row['mutation_cpu_ms'] == '0.000000'
            marker = root / 'control-only.csv.control.csv'
            marker.write_text('keep\n')
            assert run(root / 'control-only.csv').returncode != 0
            assert marker.read_text() == 'keep\n'
        if trace:
            routes = list(csv.DictReader(Path(str(output) + '.routes.csv').open()))
            assert [(r['phase'], r['hits'], r['visited_truth']) for r in routes] == [
                ('maintained', '1', '1'), ('original', '1', '1')]
            evidence = list(csv.DictReader(Path(str(output) + '.route-truth.csv').open()))
            assert all(r['id'] == '1' and r['visited'] == r['returned'] == '1' for r in evidence)
            traced = list(csv.DictReader(Path(str(output) + '.trace-neighbors.csv').open()))
            assert all(r['id'] == '1' and float.fromhex(r['distance']) == 0.0625 ** 2 for r in traced)
            for suffix in ['.edges.csv', '.routes.csv', '.route-truth.csv', '.trace-neighbors.csv', '.final-edges.csv']:
                target = root / ('trace-protected-' + str(len(suffix)) + '.csv')
                marker = Path(str(target) + suffix)
                marker.write_text('keep\n')
                assert run(target).returncode != 0 and marker.read_text() == 'keep\n'
        for count in ['0', '4', '-1', '1x', '999999999999999999999999']:
            assert run(root / ('bad-' + count + '.csv'), count).returncode != 0
        for suffix in ['', '.neighbors.csv', '.updates.csv']:
            target = root / ('protected-' + str(len(suffix)) + '.csv')
            marker = Path(str(target) + suffix)
            marker.write_text('keep\n')
            assert run(target).returncode != 0 and marker.read_text() == 'keep\n'
        if trace:
            sparse = root / 'sparse.snapshot'
            initial = [[(i + 1) % 8] for i in range(8)]
            snapshot(sparse, [float(i) for i in range(8)], initial, 2)
            (root / 'changed-groundtruth.ivecs').write_bytes(struct.pack('<ii', 1, 0))
            edge_output = root / 'edge.csv'
            done = subprocess.run([binary, mode, str(sparse), str(root),
                                   str(edge_output), '1', 'trace'], capture_output=True, text=True)
            assert done.returncode == 0, done.stderr
            edges = list(csv.DictReader(Path(str(edge_output) + '.edges.csv').open()))
            expected = {(i, j) for i, row in enumerate(initial) for j in row}
            for edge in edges:
                source_id, target_id = int(edge['source']), int(edge['target'])
                assert edge['source_updated'] == str(int(source_id == 0))
                assert edge['target_updated'] == str(int(target_id == 0))
                pair = (source_id, target_id)
                if edge['action'] == 'removed':
                    assert pair in expected
                    expected.remove(pair)
                else:
                    assert edge['action'] == 'added' and pair not in expected
                    expected.add(pair)
            if mode == '--persistent-update':
                assert any(e['action'] == 'removed' for e in edges)
                assert any(e['action'] == 'added' for e in edges)
            else:
                assert not edges
            final = list(csv.DictReader(Path(str(edge_output) + '.final-edges.csv').open()))
            actual = {(int(e['source']), int(e['target'])) for e in final}
            assert actual == expected and len(actual) == len(final)
            assert all(a != b for a, b in actual)
            for i in range(8):
                ranks = [int(e['rank']) for e in final if int(e['source']) == i]
                assert ranks == list(range(len(ranks))) and len(ranks) <= 2
        (root / 'changed-groundtruth.ivecs').write_bytes(struct.pack('<ii', 1, 999))
        assert run(root / 'bad-id.csv').returncode != 0
        (root / 'changed-groundtruth.ivecs').write_bytes(struct.pack('<iiii', 1, 1, 1, 1))
        assert run(root / 'bad-shape.csv').returncode != 0
        (root / 'changed-groundtruth.ivecs').unlink()
        assert run(root / 'missing.csv').returncode != 0
    print('Persistent update probe fixtures passed')


if __name__ == '__main__':
    main()
