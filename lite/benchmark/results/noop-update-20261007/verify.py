"""Audit no-op regression, workload boundaries, controls and emitted coverage."""
from pathlib import Path
import csv
import gzip
import hashlib
import json
import statistics

root = Path(__file__).resolve().parent
for name, digest in json.loads((root / 'sha256.json').read_text()).items():
    assert hashlib.sha256((root / name).read_bytes()).hexdigest() == digest, name
raw = json.loads((root / 'raw-sha256.json').read_text())
assert hashlib.sha256(gzip.decompress((root / 'test-before.log.raw.gz').read_bytes())).hexdigest() == raw['test-before.log']
exits = json.loads((root / 'regression-exits.json').read_text())
assert len(exits) == 2 and exits[0]['exit'] != 0 and exits[1]['exit'] == 0
assert '56 assertions' in (root / 'after-test-final.log').read_text()
for name, count in [('ctest-default-final.log', 4), ('ctest-diverse.log', 3), ('ctest-asan.log', 6)]:
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
    prefix = root / row['name']; neighbors = Path(str(prefix) + '.queries.csv.neighbors.csv')
    assert hashlib.sha256(neighbors.read_bytes()).hexdigest() == row['neighbors_sha256']
    assert len(list(csv.DictReader(neighbors.open()))) == 1000
    user, system, wall = map(float, Path(str(prefix) + '.cpu.csv').read_text().split(','))
    assert row['cpu_seconds'] == user + system and row['wall_seconds'] == wall
for metric in json.loads((root / 'audit.json').read_text())['same_value']:
    selected = [x for x in rows if x['flow'] == metric['flow'] and x['variant'] == metric['variant']]
    assert len(selected) == 3 and len({x['snapshot_sha256'] for x in selected}) == 1
    assert metric['cpu_seconds_median'] == statistics.median(x['cpu_seconds'] for x in selected)
    assert {x['recall_at_k'] for x in selected} == {metric['recall']}
assert len({x['snapshot_sha256'] for x in rows if x['flow'] == 'build'}) == 1
changed = json.loads((root / 'changed/summary.json').read_text())
changed_commands = json.loads((root / 'changed/commands.json').read_text())
assert len(changed) == len(changed_commands) == 6 and all(x['exit'] == 0 for x in changed_commands)
for row in changed:
    after = row['after']; initial = row['initial']; prefix = root / ('changed/' + row['name'] + '.csv.api.csv.crud.csv')
    samples = list(csv.DictReader(Path(str(prefix) + '.samples.csv').open()))
    mixed = list(csv.DictReader(Path(str(prefix) + '.mixed.csv').open()))
    assert len(samples) == int(after['cycles']) == 1000 and len(mixed) == int(after['mixed_queries']) == 100
    assert initial['configured_ef_search'] == initial['query_ef_search'] == '128'
    assert after['recall_at_k'] == '0.957000'
for variant, summary in json.loads((root / 'audit.json').read_text())['changed_control'].items():
    assert summary['mutation_cpu_ms_median'] == statistics.median(float(x['after']['crud_loop_cpu_ms']) for x in changed if x['variant'] == variant)
assert 'no_new_zero_incoming' in (root / 'trace-after.csv').read_text()
coverage = {}
for path in (root / 'gcov').glob('*.json.gz'):
    for file in json.loads(gzip.decompress(path.read_bytes()))['files']:
        if '/src/lite/' in file['file']:
            lines = coverage.setdefault(file['file'], {})
            for row in file['lines']:
                number = row['line_number']; lines[number] = max(lines.get(number, 0), row['count'])
hits = sum(sum(v > 0 for v in x.values()) for x in coverage.values()); total = sum(len(x) for x in coverage.values())
assert (hits, total) == (964, 1067) and hits / total >= 0.90
print('56-assertion fail/pass, 12 same-value runs, 6 changed controls, trace, raw log and >=90% emitted coverage verified.')
