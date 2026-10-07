"""Recompute post-CRUD/mixed recall from native neighbor IDs and archived truth."""
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import struct
import tarfile

ROOT = Path(__file__).resolve().parent

def main():
    manifest = json.loads((ROOT / 'manifest.json').read_text())
    for name, digest in manifest.items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name
    with tarfile.open(ROOT / 'raw.tar.gz', 'r:gz') as archive:
        raw = {}
        for member in archive.getmembers():
            assert member.isfile() and '/' not in member.name and member.name not in raw
            raw[member.name] = archive.extractfile(member).read()
    members = json.loads((ROOT / 'members.json').read_text())
    assert set(raw) == set(members)
    for name, digest in members.items():
        assert hashlib.sha256(raw[name]).hexdigest() == digest, name
    def rows(name):
        return list(csv.DictReader(io.StringIO(raw[name].decode())))
    runs = json.loads(raw['runs.json'])
    assert len(runs) == 6 and all(run['exit'] == 0 for run in runs)
    assert {(r['dataset'], r['variant']) for r in runs} == {
        (d, v) for d in ['sift', 'gist', 'cohere'] for v in ['baseline', 'candidate']}
    for variant in ['baseline', 'candidate']:
        assert 'Reverse replacement fixtures passed' in raw[variant + '-persistent.log'].decode()
        assert ('build-lite-fragment-release' if variant == 'baseline' else
                'build-lite-diverse-repair-release') in raw[variant + '-ldd.log'].decode()
    for name in ['lite-crud-evidence-test.log', 'lite-crud-asan-test.log']:
        assert 'Route probe fixtures passed' in raw[name].decode()
    assert 'slot-factor fixtures passed' in raw['lite-crud-slot-test.log'].decode()
    results = []
    total_events = 0
    for run in runs:
        dataset = run['dataset']
        data = raw[dataset + '-groundtruth.ivecs']
        truth = []
        offset = 0
        while offset < len(data):
            k, = struct.unpack_from('<i', data, offset)
            assert k == 10
            truth.append(set(struct.unpack_from('<' + 'i' * k, data, offset + 4)))
            offset += 4 + k * 4
        assert offset == len(data) and len(truth) == 100
        prefix = run['name'] + '.csv.api.csv.crud.csv'
        summary = rows(prefix)[0]
        for kind, count, field in [('post', 100, 'recall_at_k'),
                                   ('mixed', 1000, 'mixed_recall_at_k')]:
            evidence = rows(prefix + '.' + kind + '.neighbors.csv')
            assert len(evidence) == count * k
            hits = 0
            for event in range(count):
                group = evidence[event * k:(event + 1) * k]
                query = event % len(truth)
                keys = []
                ids = []
                for rank, row in enumerate(group):
                    assert int(row['event']) == event and int(row['query']) == query
                    assert int(row['cycle']) == ((event + 1) * 10 if kind == 'mixed' else 10000)
                    assert int(row['rank']) == rank
                    distance = float.fromhex(row['distance'])
                    assert math.isfinite(distance) and distance >= 0
                    identifier = int(row['id'])
                    assert 0 <= identifier < 100000
                    ids.append(identifier)
                    keys.append((distance, identifier))
                assert len(set(ids)) == k and keys == sorted(keys)
                hits += len(set(ids) & truth[query])
            recall = hits / (count * k)
            assert abs(recall - float(summary[field])) <= 5e-7
            assert summary[field] == run['metrics'][field]
            results.append(dict(dataset=dataset, variant=run['variant'], kind=kind,
                                events=count, hits=hits, recall=recall))
            total_events += count
    identity = json.loads(raw['identity.json'])
    available = all(Path(name).is_file() for name in identity['files'])
    if available:
        for name, digest in identity['files'].items():
            h = hashlib.sha256()
            with Path(name).open('rb') as source:
                for block in iter(lambda: source.read(1048576), b''):
                    h.update(block)
            assert h.hexdigest() == digest, name
    print(json.dumps(dict(pass_checks=True, events=total_events,
                          host_inputs_available=available, results=results), indent=2))

if __name__ == '__main__':
    main()
