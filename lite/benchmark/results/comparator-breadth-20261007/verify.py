"""Audit breadth pairs, CPU medians and routing diagnosis from published evidence."""
from pathlib import Path
import csv
import hashlib
import json
import math
import statistics

root = Path(__file__).resolve().parent
for name, digest in json.loads((root / 'sha256.json').read_text()).items():
    assert hashlib.sha256((root / name).read_bytes()).hexdigest() == digest, name
rows = json.loads((root / 'summary.json').read_text())
commands = json.loads((root / 'commands.json').read_text())
pairs = json.loads((root / 'pairs.json').read_text())
assert len(rows) == len(commands) == 24 and len(pairs) == 12
protocol = json.loads((root / 'protocol.json').read_text())
for variant in ['old', 'new']:
    assert 'libvsag-lite.so =>' in (root / (variant + '-ldd.txt')).read_text()
for row, command in zip(rows, commands):
    assert command['exit'] == 0 and row['name'] == command['name']
    cmd = command['command']; start = cmd.index('taskset')
    assert cmd[start:start + 3] == ['taskset', '-c', '0']
    assert cmd[-3:-1] == (['0', '1'] if row['flow'] == 'build' else ['1', '1000'])
    expected_library = 'old-default' if row['variant'] == 'old' else 'build-lite-fragment-release'
    assert command['LD_LIBRARY_PATH'].endswith(expected_library)
    assert command['LD_LIBRARY_PATH'] + '/libvsag-lite.so' in (root / (row['variant'] + '-ldd.txt')).read_text()
    prefix = root / row['name']
    for suffix, key in [('.queries.csv', 'hits_sha256'), ('.queries.csv.neighbors.csv', 'neighbors_sha256')]:
        assert hashlib.sha256(Path(str(prefix) + suffix).read_bytes()).hexdigest() == row[key]
    neighbors = list(csv.DictReader(Path(str(prefix) + '.queries.csv.neighbors.csv').open()))
    assert len(neighbors) == 1000
    assert [(int(x['query']), int(x['rank'])) for x in neighbors] == [(q, r) for q in range(100) for r in range(10)]
    count, dimension = (100000, 128) if row['case'] == 'sift100k' else (10000, 960)
    assert (int(row['base_count']), int(row['dim'])) == (count, dimension)
    assert all(0 <= int(x['id']) < count and math.isfinite(float.fromhex(x['distance'])) and float.fromhex(x['distance']) >= 0 for x in neighbors)
    user, system, wall = map(float, Path(str(prefix) + '.cpu.csv').read_text().split(','))
    assert row['cpu_seconds'] == user + system and row['wall_seconds'] == wall
for pair in pairs:
    selected = [x for x in rows if (x['case'], x['flow'], x['repeat']) == (pair['case'], pair['flow'], pair['repeat'])]
    assert len(selected) == 2 and pair['stream_byte_equal'] is True
    assert all(x['snapshot_sha256'] == pair['snapshot_sha256'] and x['neighbors_sha256'] == pair['neighbors_sha256'] for x in selected)
for metric in json.loads((root / 'audit.json').read_text()):
    selected = [x for x in rows if x['case'] == metric['case'] and x['flow'] == metric['flow']]
    assert len(selected) == 6
    for key in ['snapshot_sha256', 'neighbors_sha256', 'hits_sha256', 'recall_at_k']:
        assert len({x[key] for x in selected}) == 1
    values = {v: statistics.median(x['cpu_seconds'] for x in selected if x['variant'] == v) for v in ['old', 'new']}
    assert metric['cpu_seconds'] == values
    assert abs(metric['change_percent'] - 100 * (values['new'] / values['old'] - 1)) < 1e-12
for row in json.loads((root / 'quality/summary.json').read_text()):
    traces = list(csv.DictReader((root / ('quality/' + row['name'] + '.csv')).open()))
    native = next(csv.DictReader((root / ('quality/' + row['name'] + '.csv.api.csv')).open()))
    previous = list(csv.DictReader((root.parent / ('comparator-20261007/final/' + row['name'] + '-new-r0.queries.csv')).open()))
    assert len(traces) == len(previous) == 100
    assert all(x['query'] == y['query'] and x['hits'] == y['hits'] for x, y in zip(traces, previous))
    missing = sum(int(x['truth_not_visited']) for x in traces)
    excluded = sum(int(x['visited_not_returned']) for x in traces)
    assert (missing, excluded) == (row['truth_not_visited_total'], row['visited_not_returned_total'])
    assert excluded == 0 and row['native_prior_hits_match']
    assert abs(sum(int(x['hits']) for x in traces) / 1000 - float(native['recall_at_k'])) < 1e-12
    assert native['configured_ef_search'] == native['query_ef_search'] == '128'
print('24 runs / 12 exact-pair receipts, neighbors/hits, CPU medians and four native-matched route traces verified; removed snapshots are not re-compared.')
