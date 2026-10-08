"""Audit the isolated scored-old-neighbor Update experiment."""
import csv
import hashlib
import io
import json
import math
import random
from pathlib import Path
import statistics
import struct
import tarfile

ROOT = Path(__file__).resolve().parent

def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()

def archive(path):
    result = {}
    with tarfile.open(path, 'r:gz') as bundle:
        for member in bundle.getmembers():
            assert member.isfile() and Path(member.name).name == member.name
            assert member.name not in result
            result[member.name] = bundle.extractfile(member).read()
    return result

def rows(data):
    return list(csv.DictReader(io.StringIO(data.decode())))

def truths(data, query_count):
    result = []
    offset = 0
    for _ in range(query_count):
        assert offset + 4 <= len(data)
        count = struct.unpack_from('<I', data, offset)[0]
        offset += 4
        assert count == 10 and offset + 4 * count <= len(data)
        values = set(struct.unpack_from('<' + 'i' * count, data, offset))
        offset += 4 * count
        assert len(values) == count and all(0 <= value < 100000 for value in values)
        result.append(values)
    assert offset == len(data)
    return result

def neighbors(data, query_count):
    parsed = rows(data)
    assert len(parsed) == query_count * 20
    phases = {}
    distance_checks = 0
    for phase_index, phase in enumerate(['initial', 'changed']):
        phase_rows = []
        for query in range(query_count):
            group = parsed[(phase_index * query_count + query) * 10:
                           (phase_index * query_count + query + 1) * 10]
            keys = []
            for rank, row in enumerate(group):
                assert (row['phase'], int(row['query']), int(row['rank'])) == (phase, query, rank)
                item = (float.fromhex(row['distance']), int(row['id']))
                assert math.isfinite(item[0]) and item[0] >= 0 and 0 <= item[1] < 100000
                keys.append(item)
                distance_checks += 1
            assert keys == sorted(keys) and len({item[1] for item in keys}) == 10
            phase_rows.append(keys)
        phases[phase] = phase_rows
    return phases, distance_checks

def main():
    manifest = json.loads((ROOT / 'manifest.json').read_text())
    for name, expected in manifest.items():
        assert Path(name).name == name and digest(ROOT / name) == expected
    raw = archive(ROOT / 'raw.tar.gz')
    members = json.loads((ROOT / 'members.json').read_text())
    assert raw.keys() == members.keys()
    for name, expected in members.items():
        assert hashlib.sha256(raw[name]).hexdigest() == expected

    plan = json.loads(raw['plan.json'])
    assert plan == {
        'parent': '4deb61f3b09f5135f7fcdd45e1ecc59936b03497',
        'candidate': ('FP32 Update only: merge previously unselected old neighbors strictly '
                      'closer under new vector than farthest ANN-selected candidate, then '
                      'retain closest degree'),
        'degree': 16, 'ef': 128, 'repeats': 3,
        'protocols': {'coordinate': {'cycles': 10000}, 'whole': {'cycles': 1000}},
        'query_counts': {'sift': 100, 'cohere': 100, 'gist': 300},
        'cpu': 0, 'no_retuning': True,
        'query_history': 'previously observed; no blind claims',
        'no_default_adoption': True,
    }
    identity = json.loads(raw['identity.json'])
    assert identity['parent'] == plan['parent']
    assert identity['plan_sha256'] == hashlib.sha256(raw['plan.json']).hexdigest()
    parent_hash = hashlib.sha256(raw['parent-graph_backend.cpp']).hexdigest()
    candidate_hash = hashlib.sha256(raw['candidate-graph_backend.cpp']).hexdigest()
    assert parent_hash != candidate_hash
    assert parent_hash in identity['files'].values() and candidate_hash in identity['files'].values()
    patch = raw['candidate.patch'].decode()
    assert 'VSAG_LITE_EXPERIMENT_SCORED_OLD_UPDATE' in patch
    assert 'score < cutoff' in patch and 'K_MAX_DEGREE * 2' in patch
    builds = json.loads(raw['build-receipts.json'])
    assert {item['variant'] for item in builds} == {'release', 'asan'}
    for build in builds:
        assert build['source_sha256'] == candidate_hash
        assert build['parent_source_sha256'] == parent_hash
        flags = build['compile']
        assert '-DVSAG_LITE_EXPERIMENT_SCORED_OLD_UPDATE' in flags
        if build['variant'] == 'asan':
            assert '-fsanitize=address,undefined' in flags
        assert raw[build['variant'] + '-fixture.log'].decode().strip() == 'Scored-old Update fixtures passed'
        assert raw[build['variant'] + '-baseline-fixture.log'].decode().strip() == 'Scored-old Update fixtures passed'
        assert 'All tests passed (545120 assertions in 14 test cases)' in raw[build['variant'] + '-existing-tests.log'].decode()

    runs = json.loads(raw['runs.json'])
    expected_keys = {(protocol, dataset, variant, repeat)
                     for protocol in ['coordinate', 'whole']
                     for dataset in ['sift', 'cohere', 'gist']
                     for variant in ['baseline', 'candidate'] for repeat in range(3)}
    assert len(runs) == 36 and all(run['exit'] == 0 for run in runs)
    assert {(run['protocol'], run['dataset'], run['variant'], run['repeat']) for run in runs} == expected_keys
    assert len(raw['run.log'].decode().splitlines()) == 36
    expected_hits = {
        ('coordinate', 'sift'): (954, 954),
        ('coordinate', 'cohere'): (894, 896),
        ('coordinate', 'gist'): (2049, 2040),
        ('whole', 'sift'): (947, 949),
        ('whole', 'cohere'): (885, 886),
        ('whole', 'gist'): (2264, 2265),
    }
    results = []
    distance_checks = 0
    update_checks = 0
    for protocol in ['coordinate', 'whole']:
        for dataset in ['sift', 'cohere', 'gist']:
            query_count = plan['query_counts'][dataset]
            cycles = plan['protocols'][protocol]['cycles']
            truth = truths(raw[f'input-{protocol}-{dataset}-changed-groundtruth.ivecs'], query_count)
            variant_rows = {}
            cpu = {'baseline': [], 'candidate': []}
            for variant in ['baseline', 'candidate']:
                canonical = None
                for repeat in range(3):
                    stem = f'{protocol}-{dataset}-{variant}-{repeat}'
                    summary = rows(raw[stem + '.csv'])[0]
                    assert (int(summary['cycles']), int(summary['query_count']), int(summary['k']),
                            summary['roundtrip']) == (cycles, query_count, 10, '1')
                    cpu[variant].append(float(summary['mutation_cpu_ms']))
                    parsed, checked = neighbors(raw[stem + '.csv.neighbors.csv'], query_count)
                    distance_checks += checked
                    updates = rows(raw[stem + '.csv.updates.csv'])
                    assert len(updates) == cycles
                    for cycle, row in enumerate(updates):
                        assert (int(row['cycle']), int(row['id'])) == (cycle, cycle * 8191 % 100000)
                        before = float.fromhex(row['original_first'])
                        after = float.fromhex(row['changed_first'])
                        assert math.isfinite(before) and math.isfinite(after)
                        update_checks += 1
                    if protocol == 'coordinate':
                        for row in updates:
                            before = float.fromhex(row['original_first'])
                            expected = struct.unpack('<f', struct.pack('<f', before + 0.125))[0]
                            assert float.fromhex(row['changed_first']) == expected
                    if canonical is None:
                        canonical = parsed
                    else:
                        assert parsed == canonical
                    hits = sum(len({item[1] for item in group} & truth[q])
                               for q, group in enumerate(parsed['changed']))
                    assert abs(float(summary['changed_recall']) - hits / (query_count * 10)) < 5e-7
                    ldd = raw[stem + '.ldd.log'].decode()
                    expected_path = ('vsag-lite-scored-old-candidates-20261008/release/libvsag-lite.so'
                                     if variant == 'candidate' else
                                     'vsag-lite-baseline-v01/build-lite-fragment-release/libvsag-lite.so')
                    assert expected_path in ldd and raw[stem + '.log'] == b''
                variant_rows[variant] = canonical
            assert variant_rows['baseline']['initial'] == variant_rows['candidate']['initial']
            base_hits = [len({item[1] for item in group} & truth[q])
                         for q, group in enumerate(variant_rows['baseline']['changed'])]
            cand_hits = [len({item[1] for item in group} & truth[q])
                         for q, group in enumerate(variant_rows['candidate']['changed'])]
            assert (sum(base_hits), sum(cand_hits)) == expected_hits[(protocol, dataset)]
            delta = [candidate - baseline for baseline, candidate in zip(base_hits, cand_hits)]
            rng = random.Random(20261008)
            bootstrap = sorted(sum(rng.choices(delta, k=query_count)) / (query_count * 10)
                               for _ in range(10000))
            wins = sum(value > 0 for value in delta)
            losses = sum(value < 0 for value in delta)
            nonzero = wins + losses
            sign_p = (min(1.0, 2 * sum(math.comb(nonzero, i)
                                      for i in range(min(wins, losses) + 1)) / (2 ** nonzero))
                      if nonzero else 1.0)
            base_ids = [{item[1] for item in group} for group in variant_rows['baseline']['changed']]
            cand_ids = [{item[1] for item in group} for group in variant_rows['candidate']['changed']]
            base_cpu = statistics.median(cpu['baseline'])
            cand_cpu = statistics.median(cpu['candidate'])
            results.append({
                'protocol': protocol, 'dataset': dataset, 'query_count': query_count,
                'baseline_recall': sum(base_hits) / (query_count * 10),
                'candidate_recall': sum(cand_hits) / (query_count * 10),
                'net_hits': sum(delta), 'wins': wins, 'losses': losses,
                'ties': query_count - wins - losses,
                'gained_truth': sum(max(0, value) for value in delta),
                'lost_truth': sum(max(0, -value) for value in delta),
                'output_different_queries': sum(a != b for a, b in zip(
                    variant_rows['baseline']['changed'], variant_rows['candidate']['changed'])),
                'symmetric_id_difference': sum(len(a ^ b) for a, b in zip(base_ids, cand_ids)),
                'exploratory_paired_bootstrap_95': [bootstrap[249], bootstrap[9749]],
                'two_sided_sign_p': sign_p,
                'baseline_mutation_cpu_median_ms': base_cpu,
                'candidate_mutation_cpu_median_ms': cand_cpu,
                'candidate_cpu_delta_percent': (cand_cpu / base_cpu - 1.0) * 100,
            })
    assert all(result['exploratory_paired_bootstrap_95'][0] <= 0 <=
               result['exploratory_paired_bootstrap_95'][1] for result in results)
    print(json.dumps({
        'pass_checks': True,
        'runs': len(runs),
        'distance_rows_checked': distance_checks,
        'update_rows_checked': update_checks,
        'query_history': plan['query_history'],
        'default_source_changed': False,
        'decision': 'reject for default adoption; no stable quality or CPU benefit',
        'results': results,
    }, indent=2))

if __name__ == '__main__':
    main()
