"""Recompute trace findings and hashes; explicitly record host input availability."""
import collections
import csv
import hashlib
import json
from pathlib import Path
import struct

root = Path(__file__).resolve().parent

def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1048576), b''):
            digest.update(chunk)
    return digest.hexdigest()

for name, expected in json.loads((root / 'manifest.json').read_text()).items():
    assert sha(root / name) == expected, name
protocol = json.loads((root / 'protocol-final.json').read_text())
assert protocol['parent'] == 'f98da57f5f3804daf2eb628644c15eb5dfb2f1c9'
assert len(protocol['runs']) == 2
for run in protocol['runs']:
    assert run['exit'] == 0 and run['command'][:3] == ['taskset', '-c', '0']
for check in json.loads((root / 'checks.json').read_text()):
    assert check['exit'] == 0
for prefix in ['events', 'checkpoints']:
    reference = (root / f'{prefix}-r2.csv').read_bytes()
    for repeat in [0, 1, 3]:
        assert reference == (root / f'{prefix}-r{repeat}.csv').read_bytes()
rows = [{key: int(value) for key, value in row.items()}
        for row in csv.DictReader((root / 'events-r2.csv').open())]
assert len(rows) == 10000
changed = []
for cycle, row in enumerate(rows):
    assert row['cycle'] == cycle and row['id'] == cycle * 8191 % 10000
    assert 0 <= row['query'] < 100 and row['k'] == 10
    assert all(0 <= row[key] <= 10 for key in ['before_hits', 'remove_hits', 'add_hits'])
    row['remove_delta'] = row['remove_hits'] - row['before_hits']
    row['add_delta'] = row['add_hits'] - row['remove_hits']
    if row['remove_delta'] or row['add_delta']:
        changed.append(row)
assert changed == json.loads((root / 'changed-events.json').read_text())
summary = {'rows': len(rows), 'changed_rows': len(changed),
           'distribution': {stage: {str(key): value for key, value in
                collections.Counter(row[stage + '_delta'] for row in changed
                    if row[stage + '_delta']).items()} for stage in ['remove', 'add']},
           'sampled_remove_delta': sum(row['remove_delta'] for row in changed),
           'sampled_add_delta': sum(row['add_delta'] for row in changed)}
assert summary == json.loads((root / 'summary.json').read_text())
checkpoints = [{key: int(value) for key, value in row.items()}
               for row in csv.DictReader((root / 'checkpoints-r2.csv').open())]
assert [row['cycle'] for row in checkpoints] == [0, 1, 10, 97, 100, 500, 1000, 2000, 5000, 9999]
for row in checkpoints:
    assert row['before_hits'] == row['remove_hits'] == row['add_hits']
    assert row['remove_edges'] == row['before_edges'] - row['remove_dropped'] + row['remove_added']
    assert row['add_edges'] == row['remove_edges'] - row['add_dropped'] + row['add_added']
assert checkpoints[0]['before_hits'] == 960 and checkpoints[-1]['add_hits'] == 940
host = {}
for name, expected in protocol['files'].items():
    path = Path(name)
    host[name] = path.exists()
    if path.exists():
        assert sha(path) == expected, name
truth_path = Path(next(name for name in protocol['files'] if name.endswith('groundtruth.ivecs')))
if truth_path.exists():
    raw = truth_path.read_bytes()
    assert len(raw) == 100 * 44
    truth = []
    for offset in range(0, len(raw), 44):
        record = struct.unpack_from('<11i', raw, offset)
        assert record[0] == 10
        truth.append(set(record[1:]))
    for row in rows:
        assert row['id'] not in truth[row['query']]
    for row in checkpoints:
        assert row['common_queries'] == sum(row['id'] not in item for item in truth)
audit = {'summary': summary, 'host_files_rehashed': host,
         'truth_exclusion_rechecked': truth_path.exists(), 'manifest_files':
         len(json.loads((root / 'manifest.json').read_text()))}
(root / 'audit.json').write_text(json.dumps(audit, indent=2) + '\n')
print(json.dumps(summary))
print('trace artifacts and available host inputs verified')
