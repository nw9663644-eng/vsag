"""Audit edge changes and paired truth visits without extracting archive paths."""
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
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1048576), b''):
            h.update(block)
    return h.hexdigest()

def main():
    for name, value in json.loads((ROOT / 'manifest.json').read_text()).items():
        assert Path(name).name == name and digest(ROOT / name) == value, name
    with tarfile.open(ROOT / 'raw.tar.gz', 'r:gz') as archive:
        raw = {}
        for member in archive.getmembers():
            assert member.isfile() and Path(member.name).name == member.name and member.name not in raw
            raw[member.name] = archive.extractfile(member).read()
    members = json.loads((ROOT / 'members.json').read_text())
    assert raw.keys() == members.keys()
    for name, value in members.items():
        assert hashlib.sha256(raw[name]).hexdigest() == value, name
    rows = lambda name: list(csv.DictReader(io.StringIO(raw[name].decode())))
    info = json.loads(raw['prepared.json'])
    count, dim, cycles = info['count'], info['dim'], info['cycles']
    assert (count, dim, cycles) == (100000, 960, 10000)
    updated = {i * 8191 % count for i in range(cycles)}
    conversion = json.loads(raw['edge-conversion.json'])
    def topology(name):
        receipt = conversion[name]
        data = raw[receipt['packed_name']]
        assert hashlib.sha256(data).hexdigest() == receipt['packed_sha256']
        links = []
        offset = 0
        for a in range(count):
            n = struct.unpack_from('<I', data, offset)[0]; offset += 4
            assert n <= 16
            row = list(struct.unpack_from('<' + 'I' * n, data, offset)); offset += 4 * n
            assert len(set(row)) == n and all(0 <= b < count and a != b for b in row)
            links.append(row)
        assert offset == len(data)
        csv_data = 'source,rank,target\n' + ''.join(f'{a},{rank},{b}\n' for a, row in enumerate(links) for rank, b in enumerate(row))
        assert hashlib.sha256(csv_data.encode()).hexdigest() == receipt['csv_sha256']
        return links
    initial = topology('initial-edges.csv')
    snapshot = Path(info['snapshot'])
    available = snapshot.is_file()
    if available:
        assert digest(snapshot) == info['snapshot_sha256']
        with snapshot.open('rb') as f:
            assert f.read(8) == b'VSAGLT01'
            version, dimension, size, payload, representation, degree, ef = struct.unpack('<7Q', f.read(56))
            assert (version, dimension, size, representation, degree, ef) == (2, dim, count, 2, 16, 128)
            assert payload + 48 == snapshot.stat().st_size
            assert struct.unpack('<' + 'q' * count, f.read(8 * count)) == tuple(range(count))
            f.seek(64 + 8 * count + 4 * count * dim)
            for links in initial:
                n = struct.unpack('<Q', f.read(8))[0]
                assert list(struct.unpack('<' + 'Q' * n, f.read(8 * n))) == links
            assert not f.read(1)
    width = 4 + 4 * dim
    queries = []
    for q in range(100):
        assert struct.unpack_from('<i', raw['queries.fvecs'], q * width)[0] == dim
        queries.append(struct.unpack_from('<' + 'f' * dim, raw['queries.fvecs'], q * width + 4))
    assert len(raw['queries.fvecs']) == 100 * width
    truths = []
    for q in range(100):
        assert struct.unpack_from('<i', raw['changed-groundtruth.ivecs'], q * 44)[0] == 10
        truth = struct.unpack_from('<10i', raw['changed-groundtruth.ivecs'], q * 44 + 4)
        assert len(set(truth)) == 10 and all(0 <= i < count for i in truth)
        truths.append(set(truth))
    assert len(raw['changed-groundtruth.ivecs']) == 4400
    provenance = json.loads(raw['previous-evidence.json'])
    for report, hashes in provenance.items():
        previous = ROOT.parent / report
        for name, value in hashes.items():
            assert digest(previous / name) == value
        with tarfile.open(previous / 'raw.tar.gz', 'r:gz') as archive:
            prior = {m.name: archive.extractfile(m).read() for m in archive.getmembers()}
        for variant in ['baseline', 'candidate']:
            label = 'update' if report.startswith('persistent') else 'control'
            assert raw[label + '-' + variant + '.neighbors.csv'] == prior['gist-' + variant + '.csv.neighbors.csv']
    identity = json.loads(raw['identity.json'])
    sources_available = all(Path(p).is_file() for p in identity['files'])
    if sources_available:
        for p, value in identity['files'].items():
            assert digest(Path(p)) == value, p
    runs = json.loads(raw['runs.json'])
    assert len(runs) == 2 and all(r['exit'] == 0 for r in runs)
    assert {r['variant'] for r in runs} == {'baseline', 'candidate'}
    summaries = []
    distance_checks = 0
    for variant in ['baseline', 'candidate']:
        final = topology(variant + '.csv.final-edges.csv')
        final_sets = [set(row) for row in final]
        expected_delta = {('removed', a, b) for a, row in enumerate(initial) for b in row if b not in final_sets[a]}
        initial_sets = [set(row) for row in initial]
        expected_delta.update(('added', a, b) for a, row in enumerate(final) for b in row if b not in initial_sets[a])
        observed = set()
        categories = {}
        for row in rows(variant + '.csv.edges.csv'):
            action, a, b = row['action'], int(row['source']), int(row['target'])
            item = (action, a, b)
            assert item not in observed
            observed.add(item)
            assert row['source_updated'] == str(int(a in updated))
            assert row['target_updated'] == str(int(b in updated))
            key = action + ':' + row['source_updated'] + row['target_updated']
            categories[key] = categories.get(key, 0) + 1
        assert observed == expected_delta
        native = rows(variant + '.csv.neighbors.csv')
        assert native == rows('update-' + variant + '.neighbors.csv')
        original_native = rows('control-' + variant + '.neighbors.csv')
        route_rows = rows(variant + '.csv.routes.csv')
        evidence = rows(variant + '.csv.route-truth.csv')
        traced = rows(variant + '.csv.trace-neighbors.csv')
        assert len(route_rows) == 200 and len(evidence) == len(traced) == 2000
        phases = {}
        returned_by_phase = {}
        source = snapshot.open('rb') if available else None
        vectors = {}
        for phase_index, phase in enumerate(['maintained', 'original']):
            hits, unvisited, visited_missing, returned_sets = [], 0, 0, []
            for q in range(100):
                neighbors = traced[phase_index * 1000 + q * 10:phase_index * 1000 + (q + 1) * 10]
                keys = []
                for rank, row in enumerate(neighbors):
                    assert row['phase'] == phase and int(row['query']) == q and int(row['rank']) == rank
                    identifier, distance = int(row['id']), float.fromhex(row['distance'])
                    assert 0 <= identifier < count and math.isfinite(distance) and distance >= 0
                    keys.append((distance, identifier))
                    if source:
                        if identifier not in vectors:
                            source.seek(64 + 8 * count + 4 * identifier * dim)
                            vector = list(struct.unpack('<' + 'f' * dim, source.read(4 * dim)))
                            if identifier in updated:
                                vector[0] = struct.unpack('<f', struct.pack('<f', vector[0] + 0.125))[0]
                            vectors[identifier] = vector
                        exact = sum((float(a) - float(b)) ** 2 for a, b in zip(queries[q], vectors[identifier]))
                        assert math.isclose(distance, exact, rel_tol=3e-6, abs_tol=1e-6)
                        distance_checks += 1
                assert keys == sorted(keys) and len({i for _, i in keys}) == 10
                returned = {i for _, i in keys}
                reference = (native if phase == 'maintained' else original_native)[1000 + q * 10:1000 + (q + 1) * 10]
                assert returned == {int(r['id']) for r in reference}, (variant, phase, q)
                truth_rows = evidence[phase_index * 1000 + q * 10:phase_index * 1000 + (q + 1) * 10]
                assert {int(r['id']) for r in truth_rows} == truths[q]
                for r in truth_rows:
                    assert r['phase'] == phase and int(r['query']) == q and r['visited'] in ['0', '1']
                    assert int(r['returned']) == int(int(r['id']) in returned)
                    assert int(r['returned']) <= int(r['visited'])
                route = route_rows[phase_index * 100 + q]
                assert route['phase'] == phase and int(route['query']) == q
                hit = len(returned & truths[q]); hits.append(hit); returned_sets.append(returned)
                seen = sum(int(r['visited']) for r in truth_rows)
                assert int(route['hits']) == hit and int(route['visited_truth']) == seen
                assert 0 < int(route['expanded']) <= int(route['visited_nodes']) <= count
                assert route['early_stop'] in ['0', '1']
                unvisited += 10 - seen; visited_missing += seen - hit
            phases[phase] = dict(hits=sum(hits), unvisited_truth=unvisited, visited_not_returned=visited_missing,
                                 mean_visited_nodes=sum(int(r['visited_nodes']) for r in route_rows[phase_index*100:(phase_index+1)*100])/100)
            returned_by_phase[phase] = returned_sets
        if source:
            source.close()
        lost = [(q, i) for q in range(100) for i in (returned_by_phase['original'][q] - returned_by_phase['maintained'][q]) & truths[q]]
        gained = [(q, i) for q in range(100) for i in (returned_by_phase['maintained'][q] - returned_by_phase['original'][q]) & truths[q]]
        incoming = [[0] * count, [0] * count]
        for n, links in enumerate([initial, final]):
            for row in links:
                for b in row:
                    incoming[n][b] += 1
        summaries.append(dict(variant=variant, phases=phases, edge_changes=categories,
                              changed_rows=sum(a != b for a, b in zip(initial, final)),
                              changed_edge_sets=sum(set(a) != set(b) for a, b in zip(initial, final)),
                              lost_truth=len(lost), gained_truth=len(gained),
                              lost_truth_zero_final_incoming=sum(incoming[1][i] == 0 for _, i in lost),
                              lost_truth_incoming_decreased=sum(incoming[1][i] < incoming[0][i] for _, i in lost)))
    print(json.dumps(dict(pass_checks=True, host_snapshot_verified=available, host_sources_verified=sources_available,
                          query_states=400, truth_visits=4000, distance_checks=distance_checks, results=summaries), indent=2))

if __name__ == '__main__':
    main()
