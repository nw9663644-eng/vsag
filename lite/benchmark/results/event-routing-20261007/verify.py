"""Recompute event controls; rehash remote inputs only when available."""
import csv
import gzip
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parent

def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for part in iter(lambda: stream.read(1048576), b''):
            digest.update(part)
    return digest.hexdigest()

manifest = json.loads((root / 'manifest.json').read_text())
for name, digest in manifest.items():
    assert sha(root / name) == digest, name
summary = []
for path in sorted(root.glob('*.nodes.csv.gz')):
    with gzip.open(path, 'rt') as stream:
        rows = list(csv.DictReader(stream))
    assert len({row['id'] for row in rows}) == len(rows)
    assert all(row['native_returned'] == row['scalar_returned'] for row in rows)
    assert sum(int(row['native_returned']) for row in rows) == 10
    assert sum(int(row['truth']) for row in rows) == 10
    item = dict(name=path.name, count=len(rows),
                hits=sum(int(row['truth']) * int(row['native_returned']) for row in rows),
                truth_visited=sum(int(row['truth']) * int(row['visited']) for row in rows),
                visited=sum(int(row['visited']) for row in rows),
                missed_truth_ids=[int(row['id']) for row in rows
                                  if row['truth'] == '1' and row['visited'] == '0'])
    assert item['hits'] == item['truth_visited']
    route = list(csv.DictReader((root / path.name.replace('.nodes.csv.gz', '.csv')).open()))
    native = list(csv.DictReader((root / path.name.replace('.nodes.csv.gz', '.csv.api.csv')).open()))
    assert len(route) == len(native) == 1
    assert int(route[0]['hits']) == item['hits']
    assert float(native[0]['recall_at_k']) == item['hits'] / 10
    assert int(route[0]['visited_nodes']) == item['visited']
    summary.append(item)
assert len(summary) == 22 and summary == json.loads((root / 'node-summary.json').read_text())
lookup = {item['name'].removesuffix('.nodes.csv.gz'): item for item in summary}
expected = {'cycle-1099-before': 9, 'cycle-1099-remove': 8, 'cycle-1099-add': 8,
            'cycle-1099-remove-original-order': 9, 'cycle-1099-remove-detached': 8,
            'cycle-1099-remove-detached-original-order': 9,
            'cycle-3000-before': 7, 'cycle-3000-remove': 7, 'cycle-3000-add': 6,
            'cycle-3000-add-original-order': 6, 'cycle-3000-add-original-topology': 7,
            'cycle-7112-before': 8, 'cycle-7112-remove': 8, 'cycle-7112-add': 7,
            'cycle-7112-add-original-order': 8, 'cycle-7112-add-original-topology': 7,
            'cycle-3000-restore-6727': 7, 'cycle-3000-single-edge-6727-1707': 7}
for name, hits in expected.items():
    assert lookup[name]['hits'] == hits, name
for source in [482, 573, 7664]:
    assert lookup[f'cycle-3000-restore-{source}']['hits'] == 6
assert lookup['cycle-3000-restore-482-573-6727-7664']['hits'] == 7
assert 1707 in lookup['cycle-3000-add']['missed_truth_ids']
assert 1707 not in lookup['cycle-3000-single-edge-6727-1707']['missed_truth_ids']
for name in ['commands.json', 'control-commands.json', 'row-commands.json', 'inspect-commands.json', 'checks.json']:
    assert all(item['exit'] == 0 for item in json.loads((root / name).read_text())), name
for name in ['single-edge.json', 'single-edge-inspect.json']:
    assert json.loads((root / name).read_text())['exit'] == 0
edge = json.loads((root / 'edge-audit.json').read_text())
assert edge['only_changed_source'] == [6727] and edge['row_length'] == 16
assert edge['only_replaced_edge'] == [6727, 3000, 1707]
assert edge['incoming_1707_removed'] == 2 and edge['incoming_1707_added'] == 1
assert edge['incoming_3000_added'] == 4 and edge['incoming_3000_control'] == 3
host = {}
for name, digest in json.loads((root / 'host-hashes.json').read_text()).items():
    path = Path(name); host[name] = path.exists()
    if path.exists():
        assert sha(path) == digest, name
(root / 'audit.json').write_text(json.dumps(dict(node_exports=len(summary),
    manifest_files=len(manifest), host_files_rehashed=host,
    single_edge_recovery=True, scope='Observed event controls, not quality acceptance or performance'), indent=2) + '\n')
print('22 exports, factor controls, one-edge recovery and available host hashes verified')
