#!/usr/bin/env python3
# Copyright 2026 Ant Group Co., Ltd.
# SPDX-License-Identifier: Apache-2.0
"""Recompute the rejected retention experiment without running timings."""
import csv
import hashlib
import json
import math
from pathlib import Path
import statistics
import struct

ROOT = Path(__file__).resolve().parent
HOST = Path('/home/ubuntu/project/vsag-lite-two-incoming-20261007')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(name):
    with (ROOT / name).open() as stream:
        return list(csv.DictReader(stream))


def main():
    manifest = json.loads((ROOT / 'artifacts.json').read_text())
    for name, record in manifest.items():
        assert digest(ROOT / name) == record['sha256'], name
    identity = json.loads((ROOT / 'identity.json').read_text())
    for name in ('graph_backend.cpp', 'graph_backend_test.cpp'):
        source = '/home/ubuntu/project/vsag-lite-baseline-v01/src/lite/' + name
        assert digest(ROOT / ('candidate_' + name + '.txt')) == identity['files'][source]
    checks = json.loads((ROOT / 'checks.json').read_text())
    for check in checks:
        if check['name'] == 'candidate-test-before':
            assert check['exit'] != 0
        else:
            assert check['exit'] == 0
    for check in json.loads((ROOT / 'lint-checks.json').read_text()):
        assert check['exit'] == 0
    restored = json.loads((ROOT / 'restoration.json').read_text())
    assert restored['source_parent'] == identity['parent']
    assert all(item['exit'] == 0 for item in restored['checks'])
    truth_path = Path('/home/ubuntu/project/vsag-lite-cohere-normalized-20261006/prepared/scale-10000/groundtruth.ivecs')
    truth = []
    if truth_path.exists():
        data = truth_path.read_bytes()
        offset = 0
        while offset < len(data):
            count = struct.unpack_from('<I', data, offset)[0]
            offset += 4
            truth.append(set(struct.unpack_from('<' + 'I' * count, data, offset)[:10]))
            offset += 4 * count
        assert offset == len(data) and len(truth) == 100
    runs = json.loads((ROOT / 'runs.json').read_text())
    assert len(runs) == 12
    summaries = []
    host_snapshots = []
    for flow in ('build', 'crud'):
        for variant in ('baseline', 'candidate'):
            selected = [r for r in runs if r['flow'] == flow and r['variant'] == variant]
            assert sorted(r['repeat'] for r in selected) == [0, 1, 2]
            recalls, times = [], []
            for run in selected:
                assert run['exit'] == 0
                stem = f"{variant}-{flow}-r{run['repeat']}"
                hit_rows = rows(stem + '.hits.csv')
                assert len(hit_rows) == 100
                assert [int(r['query']) for r in hit_rows] == list(range(100))
                assert all(int(r['k']) == 10 and 0 <= int(r['hits']) <= 10 for r in hit_rows)
                recall = sum(int(r['hits']) for r in hit_rows) / 1000
                assert math.isclose(recall, float(run['metrics']['recall_at_k']))
                neighbors = rows(stem + '.hits.csv.neighbors.csv')
                assert len(neighbors) == 1000
                for query in range(100):
                    group = [r for r in neighbors if int(r['query']) == query]
                    assert [int(r['rank']) for r in group] == list(range(10))
                    ids = {int(r['id']) for r in group}
                    assert len(ids) == 10
                    if truth:
                        assert len(ids & truth[query]) == int(hit_rows[query]['hits'])
                    assert all(math.isfinite(float.fromhex(r['distance'])) for r in group)
                cpu = sum(float(x) for x in (ROOT / (stem + '.time.csv')).read_text().strip().split(','))
                assert math.isclose(cpu, run['whole_cpu_s'])
                assert digest(ROOT / (stem + '.hits.csv')) == run['hits_sha256']
                snapshot = HOST / (stem + '.snapshot')
                available = snapshot.exists()
                if available:
                    assert digest(snapshot) == run['snapshot_sha256']
                host_snapshots.append({'path': str(snapshot), 'available_and_verified': available})
                recalls.append(recall)
                times.append(cpu)
            assert len({r['snapshot_sha256'] for r in selected}) == 1
            summaries.append({'flow': flow, 'variant': variant, 'recalls': recalls,
                              'median_whole_cpu_s': statistics.median(times)})
    assert summaries == json.loads((ROOT / 'summary.json').read_text())
    for variant, final in (('baseline', 940), ('candidate', 942)):
        checkpoints = rows('same-initial-' + variant + '.checkpoints.csv')
        assert len(checkpoints) == 10
        assert int(checkpoints[0]['before_hits']) == 960
        assert int(checkpoints[-1]['cycle']) == 9999
        assert int(checkpoints[-1]['add_hits']) == final
        assert int(checkpoints[-1]['common_queries']) == 100
        assert len(rows('same-initial-' + variant + '.events.csv')) == 10000
    host_inputs = []
    for location, sha in identity['files'].items():
        if '/src/lite/' in location:
            continue  # Prototype copies are checked above; working sources were restored.
        path = Path(location)
        available = path.exists()
        if available:
            assert digest(path) == sha
        host_inputs.append({'path': location, 'available_and_verified': available})
    libraries = {'baseline': HOST / 'before/libvsag-lite.so',
                 'candidate': Path('/home/ubuntu/project/vsag-lite-baseline-v01/build-lite-two-incoming-release/libvsag-lite.so')}
    for variant, path in libraries.items():
        available = path.exists()
        if available:
            assert digest(path) == identity['library_sha256'][variant]
        host_inputs.append({'path': str(path), 'available_and_verified': available})
    repo = ROOT.parents[3]
    for name, sha in restored['sources'].items():
        path = repo / 'src/lite' / name
        if path.exists():
            assert digest(path) == sha
    result = {'artifacts_verified': len(manifest), 'runs_verified': len(runs),
              'truth_hits_recomputed': bool(truth), 'summaries': summaries, 'host_snapshots': host_snapshots,
              'host_inputs': host_inputs, 'decision': 'withdraw prototype; no quality acceptance'}
    (ROOT / 'verification.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'artifacts_verified': len(manifest), 'runs_verified': len(runs),
                      'decision': result['decision']}))


if __name__ == '__main__':
    main()
