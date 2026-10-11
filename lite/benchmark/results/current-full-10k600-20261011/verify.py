# Copyright 2024-present the vsag project
# SPDX-License-Identifier: Apache-2.0
"""Independent raw-query and fresh-loader audit for current Full/Lite runs."""
import collections
import csv
import hashlib
import json
import math
from pathlib import Path
import statistics
import struct
import sys
import tarfile
import tempfile

root = Path(sys.argv[1])
if (root / 'raw.tar.gz').exists():
    members = json.loads((root / 'members.json').read_text())
    temporary = tempfile.TemporaryDirectory(prefix='vsag-full-audit-')
    unpacked = Path(temporary.name)
    observed = set()
    with tarfile.open(root / 'raw.tar.gz') as archive:
        for member in archive:
            assert member.isfile() and '/' not in member.name and member.name not in observed
            observed.add(member.name)
            payload = archive.extractfile(member).read()
            assert hashlib.sha256(payload).hexdigest() == members[member.name]
            (unpacked / member.name).write_bytes(payload)
    assert observed == set(members)
    original_root = root
    root = unpacked
rows = json.loads((root / 'rows.json').read_text())
summary = json.loads((root / 'summary.json').read_text())
identity = json.loads((root / 'identity.json').read_text())
assert len(rows) == 54 and len(summary) == 18
assert identity['arguments']['ef'] == 512 and identity['arguments']['full_ef'] == 128
assert identity['reference_library_sha256'] == '9aeaa550703f116bef2959769d4f2f03da254b07c906ba941d8186224cc70c72'

def read_csv(name):
    with (root / name).open() as source:
        return list(csv.DictReader(source))

audit = []
for row in rows:
    tag = f"{row['dataset']}-{row['storage']}-{row['trial']}-{row['name']}"
    full = row['name'] == 'full'
    latencies = read_csv(tag + ('.latencies.csv' if full else '.queries.csv.latencies.csv'))
    times = sorted(float(item['latency_us']) for item in latencies)
    assert len(times) == 600 == int(row['build']['query_count'])
    assert all(math.isfinite(value) and value >= 0 for value in times)
    for quantile, key in [(0.5, 'search_p50_us'), (.99, 'search_p99_us')]:
        assert abs(times[math.ceil(600 * quantile) - 1] - float(row['build'][key])) < 1e-6
    metadata = json.loads((root / (row['dataset'] + '.dataset.json')).read_text())
    for name in ['queries.fvecs', 'groundtruth.ivecs']:
        data = (root / (row['dataset'] + '.' + name)).read_bytes()
        assert hashlib.sha256(data).hexdigest() == metadata[name]['sha256']
        assert len(data) == metadata[name]['bytes']
    data = (root / (row['dataset'] + '.groundtruth.ivecs')).read_bytes()
    assert len(data) == 600 * 44
    truth = []
    for offset in range(0, len(data), 44):
        record = struct.unpack_from('<11i', data, offset)
        assert record[0] == 10 and len(set(record[1:])) == 10
        truth.append(set(record[1:]))
    groups = collections.defaultdict(list)
    suffix = '.neighbors.csv' if full else '.queries.csv.neighbors.csv'
    for item in read_csv(tag + suffix):
        q = int(item['query'])
        assert 0 <= q < 600 and int(item['rank']) == len(groups[q])
        distance = float.fromhex(item['distance'])
        assert math.isfinite(distance)
        if groups[q]:
            assert distance >= groups[q][-1][1]
        groups[q].append((int(item['id']), distance))
    assert len(groups) == 600
    hits = []
    for q in range(600):
        ids = [item[0] for item in groups[q]]
        assert len(ids) == len(set(ids)) == 10 and all(0 <= value < 10000 for value in ids)
        hits.append(len(set(ids).intersection(truth[q])))
    assert abs(sum(hits) / 6000 - float(row['build']['recall_at_k'])) <= 1e-6
    if not full:
        assert [int(item['hits']) for item in read_csv(tag + '.queries.csv')] == hits
    else:
        parameters = json.loads((root / (tag + '.parameters.json')).read_text())
        assert parameters['build']['index_param']['build_thread_count'] == 1
        assert parameters['build']['index_param']['base_io_type'] == 'memory_io'
    assert int((root / (tag + '.peak_kib')).read_text()) == row['build']['external_peak_rss_kib']
    assert len(row['loads']) == 3
    for sample, expected in enumerate(row['loads']):
        prefix = tag + f'-load-{sample}'
        lines = (root / (prefix + '.stdout')).read_text().splitlines()
        index = next(i for i, line in enumerate(lines) if line.startswith('dim,count,'))
        actual = list(csv.DictReader(lines[index:index + 2]))[0]
        assert all(actual[key] == value for key, value in expected.items() if key != 'external_peak_rss_kib')
        assert int((root / (prefix + '.peak_kib')).read_text()) == expected['external_peak_rss_kib']
    audit.append(dict(tag=tag, recall=sum(hits) / 6000))
for item in summary:
    selected = [row for row in rows if all(row[key] == item[key] for key in ['dataset', 'storage', 'name'])]
    assert len(selected) == 3 and sorted(row['trial'] for row in selected) == [0, 1, 2]
    for key in ['recall_at_k', 'build_ms', 'search_p50_us', 'search_p99_us', 'save_ms', 'snapshot_bytes', 'external_peak_rss_kib']:
        assert abs(statistics.median(float(row['build'][key]) for row in selected) - item[key]) < 1e-6
    for key in ['load_ms', 'loaded_rss_kib', 'process_peak_rss_kib', 'before_create_rss_kib', 'before_load_rss_kib']:
        assert abs(statistics.median(float(load[key]) for row in selected for load in row['loads']) - item[key]) < 1e-6
(locals().get('original_root', root) / 'audit.json').write_text(json.dumps(dict(status='PASS', builders=54,
    queries=32400, neighbors=324000, loads=162, rows=audit), indent=2) + '\n')
print('PASS54builders32400query_truth_intersections324000neighbors162loads')
