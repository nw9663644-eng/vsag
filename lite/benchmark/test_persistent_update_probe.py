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
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        source = root / 'initial.snapshot'
        snapshot(source, [0.0, 0.0625, 1.0], [[1, 2], [0, 2], [0, 1]], 2)
        (root / 'queries.fvecs').write_bytes(struct.pack('<if', 1, 0.0))
        (root / 'groundtruth.ivecs').write_bytes(struct.pack('<ii', 1, 0))
        (root / 'changed-groundtruth.ivecs').write_bytes(struct.pack('<ii', 1, 1))
        def run(output, count='1'):
            return subprocess.run([binary, '--persistent-update', str(source), str(root),
                                   str(output), count], capture_output=True, text=True)
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
        for count in ['0', '4', '-1', '1x', '999999999999999999999999']:
            assert run(root / ('bad-' + count + '.csv'), count).returncode != 0
        for suffix in ['', '.neighbors.csv', '.updates.csv']:
            target = root / ('protected-' + str(len(suffix)) + '.csv')
            marker = Path(str(target) + suffix)
            marker.write_text('keep\n')
            assert run(target).returncode != 0 and marker.read_text() == 'keep\n'
        (root / 'changed-groundtruth.ivecs').write_bytes(struct.pack('<ii', 1, 999))
        assert run(root / 'bad-id.csv').returncode != 0
        (root / 'changed-groundtruth.ivecs').write_bytes(struct.pack('<iiii', 1, 1, 1, 1))
        assert run(root / 'bad-shape.csv').returncode != 0
        (root / 'changed-groundtruth.ivecs').unlink()
        assert run(root / 'missing.csv').returncode != 0
    print('Persistent update probe fixtures passed')


if __name__ == '__main__':
    main()
