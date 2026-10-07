"""Verify paired semantics, CPU summaries, library bindings and emitted coverage."""
from pathlib import Path
import csv
import gzip
import hashlib
import json
import statistics

root = Path(__file__).resolve().parent
for name, digest in json.loads((root / 'sha256.json').read_text()).items():
    assert hashlib.sha256((root / name).read_bytes()).hexdigest() == digest, name
metrics = json.loads((root / 'audit.json').read_text())
for label in ['exploratory', 'final']:
    directory = root / label
    rows = json.loads((directory / 'summary.json').read_text())
    commands = json.loads((directory / 'commands.json').read_text())
    assert len(rows) == len(commands) == 24
    for row, command in zip(rows, commands):
        assert row['name'] == command['name'] and command['exit'] == 0
        start = command['command'].index('taskset')
        assert ['taskset', '-c', '0'] == command['command'][start:start + 3]
        library = command['LD_LIBRARY_PATH']
        assert ('old-' + row['mode'] in library) == (row['variant'] == 'old')
        binding = (directory / f"{row['mode']}-{row['variant']}-ldd.txt").read_text()
        assert library + '/libvsag-lite.so' in binding
        prefix = directory / row['name']
        for suffix, key in [('.queries.csv', 'hits_sha256'),
                            ('.queries.csv.neighbors.csv', 'neighbors_sha256')]:
            assert hashlib.sha256(Path(str(prefix) + suffix).read_bytes()).hexdigest() == row[key]
        neighbors = list(csv.DictReader(Path(str(prefix) + '.queries.csv.neighbors.csv').open()))
        assert len(neighbors) == 1000
        assert [(int(x['query']), int(x['rank'])) for x in neighbors] == [(q, r) for q in range(100) for r in range(10)]
        assert all(float.fromhex(x['distance']) >= 0 for x in neighbors)
        user, system, wall = map(float, Path(str(prefix) + '.cpu.csv').read_text().split(','))
        assert row['cpu_seconds'] == user + system and row['wall_seconds'] == wall
    for mode in ['default', 'diverse']:
        for flow in ['build', 'crud']:
            selected = [x for x in rows if x['mode'] == mode and x['flow'] == flow]
            assert len(selected) == 6
            for key in ['snapshot_sha256', 'neighbors_sha256', 'hits_sha256', 'recall_at_k']:
                assert len({x[key] for x in selected}) == 1
            values = {v: statistics.median(x['cpu_seconds'] for x in selected if x['variant'] == v) for v in ['old', 'new']}
            metric = next(x for x in metrics if x['label'] == label and x['mode'] == mode and x['flow'] == flow)
            assert metric['cpu_seconds'] == values
            assert abs(metric['change_percent'] - 100 * (values['new'] / values['old'] - 1)) < 1e-12
coverage = {}
for path in (root / 'exploratory/gcov').glob('*.json.gz'):
    for file in json.loads(gzip.decompress(path.read_bytes()))['files']:
        if '/src/lite/' in file['file'] or file['file'].endswith('/include/vsag/lite/index.h'):
            lines = coverage.setdefault(file['file'], {})
            for line in file['lines']:
                number = line['line_number']
                lines[number] = max(lines.get(number, 0), line['count'])
count = sum(len(x) for x in coverage.values())
hits = sum(sum(v > 0 for v in x.values()) for x in coverage.values())
summary = json.loads((root / 'exploratory/coverage.json').read_text())
assert (hits, count) == (summary['covered'], summary['total'])
assert hits / count >= 0.90
print('48 paired runs: exact neighbors/hits, recorded snapshot hashes, CPU medians, bindings and fresh >=90% coverage verified.')
