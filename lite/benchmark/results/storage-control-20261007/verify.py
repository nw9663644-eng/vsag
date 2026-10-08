"""Pair unchanged-topology controls with archived native Update outcomes."""
import contextlib
import csv
import io
import json
import struct
import tarfile
import verify_neighbors

ROOT = verify_neighbors.ROOT

def main():
    captured = io.StringIO()
    with contextlib.redirect_stdout(captured):
        verify_neighbors.main()
    audit = json.loads(captured.getvalue())
    with tarfile.open(ROOT / 'raw.tar.gz', 'r:gz') as archive:
        raw = {m.name: archive.extractfile(m).read() for m in archive.getmembers()}
    previous = ROOT.parent / 'persistent-update-20261007'
    receipt = json.loads(raw['previous-evidence.json'])
    for name, value in receipt['sha256'].items():
        assert verify_neighbors.digest(previous / name) == value
    with tarfile.open(previous / 'raw.tar.gz', 'r:gz') as archive:
        previous_raw = {m.name: archive.extractfile(m).read() for m in archive.getmembers()}
    for name, data in raw.items():
        if name.startswith('update-'):
            assert data == previous_raw[name[len('update-'):]], name
    rows = lambda name: list(csv.DictReader(io.StringIO(raw[name].decode())))
    prepared = {r['dataset']: r for r in json.loads(raw['prepared.json'])}
    paired = []
    for dataset in ['sift', 'gist', 'cohere']:
        controls = []
        truth_data = raw[dataset + '-changed-groundtruth.ivecs']
        truths = [set(struct.unpack_from('<10i', truth_data, q * 44 + 4)) for q in range(100)]
        for variant in ['baseline', 'candidate']:
            name = dataset + '-' + variant
            control = rows(name + '.csv.neighbors.csv')
            controls.append(control)
            receipt = rows(name + '.csv.control.csv')[0]
            assert receipt['coordinates'] == '10000'
            assert receipt['other_bytes_equal'] == receipt['roundtrip'] == '1'
            assert 0 < int(receipt['changed_bytes']) <= 40000
            assert rows(name + '.csv')[0]['mutation_cpu_ms'] == '0.000000'
            old = rows('update-' + name + '.csv.neighbors.csv')
            old_summary = rows('update-' + name + '.csv')[0]
            assert len(old) == len(control) == 2000 and old[:1000] == control[:1000]
            hits = [[], []]
            for q in range(100):
                for i, evidence in enumerate([control, old]):
                    group = evidence[1000 + q * 10:1000 + (q + 1) * 10]
                    assert all(r['phase'] == 'changed' and int(r['query']) == q and int(r['rank']) == rank
                               for rank, r in enumerate(group))
                    identifiers = [int(r['id']) for r in group]
                    assert len(set(identifiers)) == 10
                    hits[i].append(len(set(identifiers) & truths[q]))
            assert abs(sum(hits[1]) / 1000 - float(old_summary['changed_recall'])) < 5e-7
            deltas = [b - a for a, b in zip(*hits)]
            paired.append(dict(dataset=dataset, variant=variant, control_recall=sum(hits[0])/1000,
                               update_recall=sum(hits[1])/1000, wins=sum(d > 0 for d in deltas),
                               losses=sum(d < 0 for d in deltas), ties=sum(d == 0 for d in deltas),
                               net_hits=sum(deltas)))
        assert controls[0] == controls[1], dataset
    audit['paired'] = paired
    audit['control_neighbors_identical_across_libraries'] = True
    print(json.dumps(audit, indent=2))

if __name__ == '__main__':
    main()
