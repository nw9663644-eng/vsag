"""Audit native persistent updates, archived truth and optional host vector distances."""
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import struct
import tarfile

ROOT = Path(__file__).resolve().parent

def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1048576), b''):
            h.update(block)
    return h.hexdigest()

def records(data, dtype, dim):
    width = 4 + 4 * dim
    assert len(data) % width == 0
    result = []
    for start in range(0, len(data), width):
        assert struct.unpack_from('<i', data, start)[0] == dim
        result.append(struct.unpack_from('<' + dtype * dim, data, start + 4))
    return result

def main():
    for name, value in json.loads((ROOT / 'manifest.json').read_text()).items():
        assert digest(ROOT / name) == value, name
    with tarfile.open(ROOT / 'raw.tar.gz', 'r:gz') as archive:
        raw = {}
        for member in archive.getmembers():
            assert member.isfile() and '/' not in member.name and member.name not in raw
            raw[member.name] = archive.extractfile(member).read()
    members = json.loads((ROOT / 'members.json').read_text())
    assert raw.keys() == members.keys()
    for name, value in members.items():
        assert hashlib.sha256(raw[name]).hexdigest() == value
    rows = lambda name: list(csv.DictReader(io.StringIO(raw[name].decode())))
    prepared = {r['dataset']: r for r in json.loads(raw['prepared.json'])}
    runs = json.loads(raw['runs.json'])
    assert len(runs) == 6 and all(r['exit'] == 0 for r in runs)
    assert {(r['dataset'], r['variant']) for r in runs} == {
        (d, v) for d in ['sift', 'gist', 'cohere'] for v in ['baseline', 'candidate']}
    available = all(Path(r['snapshot']).is_file() for r in prepared.values())
    if available:
        for record in prepared.values():
            assert digest(Path(record['snapshot'])) == record['snapshot_sha256']
    results = []
    checked_distances = 0
    for run in runs:
        dataset = run['dataset']; info = prepared[dataset]
        name = dataset + '-' + run['variant']
        dim = info['dim']; count = info['count']; cycles = info['cycles']
        assert count == 100000 and cycles == 10000
        queries = records(raw[dataset + '-queries.fvecs'], 'f', dim)
        truths = [records(raw[dataset + '-' + f], 'i', 10)
                  for f in ['groundtruth.ivecs', 'changed-groundtruth.ivecs']]
        assert len(queries) == len(truths[0]) == len(truths[1]) == 100
        for truth in truths:
            assert all(len(set(row)) == 10 and all(0 <= i < count for i in row) for row in truth)
        assert info['changed_truth_queries'] == sum(set(a) != set(b) for a, b in zip(*truths))
        updates = rows(name + '.csv.updates.csv')
        assert len(updates) == cycles
        changed = {}
        for cycle, row in enumerate(updates):
            identifier = int(row['id'])
            assert int(row['cycle']) == cycle and identifier == cycle * 8191 % count
            before = float.fromhex(row['original_first']); after = float.fromhex(row['changed_first'])
            expected = struct.unpack('<f', struct.pack('<f', before + 0.125))[0]
            assert math.isfinite(after) and after == expected and before != after
            assert math.isfinite(float(row['latency_us'])) and float(row['latency_us']) >= 0
            changed[identifier] = after
        assert len(changed) == cycles
        neighbors = rows(name + '.csv.neighbors.csv')
        assert len(neighbors) == 2000
        summary = rows(name + '.csv')[0]
        assert summary == run['summary'] and summary['roundtrip'] == '1'
        source = Path(info['snapshot']).open('rb') if available else None
        cache = {}
        hits_by_phase = []
        for phase_index, phase in enumerate(['initial', 'changed']):
            hits = 0
            for q in range(100):
                group = neighbors[phase_index * 1000 + q * 10:phase_index * 1000 + (q + 1) * 10]
                keys = []
                for rank, row in enumerate(group):
                    assert row['phase'] == phase and int(row['query']) == q and int(row['rank']) == rank
                    identifier = int(row['id']); distance = float.fromhex(row['distance'])
                    assert 0 <= identifier < count and math.isfinite(distance) and distance >= 0
                    keys.append((distance, identifier))
                    if source:
                        if identifier not in cache:
                            source.seek(64 + 8 * count + 4 * identifier * dim)
                            cache[identifier] = struct.unpack('<' + 'f' * dim, source.read(4 * dim))
                        vector = cache[identifier]
                        first = changed.get(identifier, vector[0]) if phase_index else vector[0]
                        exact = (float(queries[q][0]) - first) ** 2
                        exact += sum((float(queries[q][d]) - float(vector[d])) ** 2 for d in range(1, dim))
                        assert math.isclose(distance, exact, rel_tol=3e-6, abs_tol=1e-6), (name, phase, q, identifier, distance, exact)
                        checked_distances += 1
                assert keys == sorted(keys) and len({i for _, i in keys}) == 10
                hits += len({i for _, i in keys} & set(truths[phase_index][q]))
            field = phase + '_recall'
            assert abs(hits / 1000 - float(summary[field])) < 5e-7
            hits_by_phase.append(hits)
        if source:
            for row in updates:
                identifier = int(row['id'])
                source.seek(64 + 8 * count + 4 * identifier * dim)
                assert struct.unpack('<f', source.read(4))[0] == float.fromhex(row['original_first'])
            source.close()
        results.append(dict(dataset=dataset, variant=run['variant'], initial_hits=hits_by_phase[0], changed_hits=hits_by_phase[1], mutation_cpu_ms=float(summary['mutation_cpu_ms'])))
    identity = json.loads(raw['identity.json'])
    source_available = all(Path(p).is_file() for p in identity['files'])
    if source_available:
        for name, value in identity['files'].items():
            assert digest(Path(name)) == value
    print(json.dumps(dict(pass_checks=True, query_states=1200, updates=60000,
                          host_snapshots_available=available, distance_checks=checked_distances,
                          host_sources_available=source_available, results=results), indent=2))

if __name__ == '__main__':
    main()
