"""Recompute test receipts, paired outputs, phase control and emitted coverage."""
from pathlib import Path
import csv
import gzip
import hashlib
import json
import statistics

root = Path(__file__).resolve().parent
for name, digest in json.loads((root / 'sha256.json').read_text()).items():
    assert hashlib.sha256((root / name).read_bytes()).hexdigest() == digest, name
exits = json.loads((root / 'regression-exits.json').read_text())
assert len(exits) == 2 and exits[0]['exit'] != 0 and exits[1]['exit'] == 0
assert '0 > 0' in (root / 'regression-before-final.log').read_text()
assert '108 assertions' in (root / 'regression-final.log').read_text()
assert (root / 'trace-before.csv').read_bytes() == (root / 'trace-before-replay.csv').read_bytes()
first = next(csv.DictReader((root / 'trace-before.csv').open()))
assert (first['cycle'], first['id'], first['phase'], first['new_zero_id'], first['old_outgoing_target']) == ('97', '4527', 'update', '3626', '1')
assert 'no_new_zero_incoming' in (root / 'trace-after.csv').read_text()
assert (root / 'trace-formatted-before.csv').read_bytes() == (root / 'trace-before.csv').read_bytes()
assert (root / 'trace-formatted-after.csv').read_bytes() == (root / 'trace-after.csv').read_bytes()
for name, count in [('ctest-default-final.log', 4), ('ctest-diverse-final.log', 3), ('ctest-asan-final.log', 6)]:
    assert f'100% tests passed, 0 tests failed out of {count}' in (root / name).read_text()
rows = json.loads((root / 'summary.json').read_text())
commands = json.loads((root / 'commands.json').read_text())
assert len(rows) == len(commands) == 12 and all(x['exit'] == 0 for x in commands)
for row, command in zip(rows, commands):
    assert row['name'] == command['name']
    cmd = command['command']; start = cmd.index('taskset')
    assert cmd[start:start + 3] == ['taskset', '-c', '0']
    assert cmd[-3:-1] == (['0', '1'] if row['flow'] == 'build' else ['1', '10000'])
    assert command['LD_LIBRARY_PATH'] + '/libvsag-lite.so' in (root / (row['variant'] + '-ldd.txt')).read_text()
    prefix = root / row['name']
    neighbors = Path(str(prefix) + '.queries.csv.neighbors.csv')
    assert hashlib.sha256(neighbors.read_bytes()).hexdigest() == row['neighbors_sha256']
    assert len(list(csv.DictReader(neighbors.open()))) == 1000
    user, system, wall = map(float, Path(str(prefix) + '.cpu.csv').read_text().split(','))
    assert row['cpu_seconds'] == user + system and row['wall_seconds'] == wall
for metric in json.loads((root / 'audit.json').read_text()):
    selected = [x for x in rows if x['flow'] == metric['flow'] and x['variant'] == metric['variant']]
    assert len(selected) == 3 and len({x['snapshot_sha256'] for x in selected}) == 1
    assert metric['cpu_seconds_median'] == statistics.median(x['cpu_seconds'] for x in selected)
    assert {x['recall_at_k'] for x in selected} == {metric['recall']}
assert len({x['snapshot_sha256'] for x in rows if x['flow'] == 'build'}) == 1
control = json.loads((root / 'slot-control.json').read_text())
assert control['exit'] == 0 and control['all_vector_bytes_equal_by_id'] and control['all_ordered_edges_equal_by_id']
assert control['native']['recall_at_k'] == control['scalar']['recall_at_k'] == '0.934000'
normal = list(csv.DictReader((root / 'after-crud-r0.queries.csv').open()))
reordered = list(csv.DictReader((root / 'slot-control.csv').open()))
assert len(normal) == len(reordered) == 100 and all(x['hits'] == y['hits'] for x, y in zip(normal, reordered))
edges = json.loads((root / 'edge-retention.json').read_text())
assert (edges['common_external_id_edges'], edges['original_edges'], edges['post_edges']) == (90392, 160000, 160000)
assert edges['original_edge_retention'] == 90392 / 160000 and edges['all_vector_bytes_equal_by_id']
coverage = {}
for path in (root / 'gcov').glob('*.json.gz'):
    for file in json.loads(gzip.decompress(path.read_bytes()))['files']:
        if '/src/lite/' in file['file']:
            lines = coverage.setdefault(file['file'], {})
            for row in file['lines']:
                number = row['line_number']; lines[number] = max(lines.get(number, 0), row['count'])
hits = sum(sum(v > 0 for v in x.values()) for x in coverage.values()); total = sum(len(x) for x in coverage.values())
assert (hits, total) == (959, 1062) and hits / total >= 0.90
print('Regression fail/pass, FP32/FP16108 assertions, phase replay, 12 public runs, slot control and >=90% emitted coverage verified; big snapshots not re-read.')
