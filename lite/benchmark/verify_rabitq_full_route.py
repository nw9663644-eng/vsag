# Copyright 2024-present the vsag project
# SPDX-License-Identifier: Apache-2.0
"""Recompute route-candidate evidence independently from per-query raw files."""
import csv
import hashlib
import json
import math
from pathlib import Path
import statistics
import struct
import sys

out = Path(sys.argv[1])
identity = json.loads((out / 'identity.json').read_text())
rows = json.loads((out / 'rows.json').read_text())
commands = json.loads((out / 'commands.json').read_text())
assert len(rows) == 30 and len(commands) == 39
assert all(command['exit'] == 0 for command in commands)
for name, digest in identity['sources'].items():
    assert hashlib.sha256((out / ('source-' + Path(name).name)).read_bytes()).hexdigest() == digest
original = (out / 'control-rabitq_graph_state.h').read_text()
candidate = (out / 'candidate-rabitq_graph_state.h').read_text()
begin = original.index('inline GraphSearchResult\ngraph_search_impl(')
end = original.index('inline GraphSearchResult\ngraph_search(', begin)
marker = 'const Candidate next{slot, estimate.distance, estimate.centered_ip};'
assert original[begin:end].count(marker) == 1
expected = original[:begin] + original[begin:end].replace(marker,
    'const Candidate next{slot, full_distance(query, query_norm, code, estimate.centered_ip, query_sum), estimate.centered_ip};') + original[end:]
assert candidate == expected

def csv_rows(path):
    with path.open() as source:
        return list(csv.DictReader(source))

summary = {}
for label in ['sift100k', 'gist100k', 'cohere100k']:
    raw_truth = (out / (label + '.groundtruth.ivecs')).read_bytes()
    assert len(raw_truth) == 4400
    truth = []
    for offset in range(0, len(raw_truth), 44):
        record = struct.unpack_from('<11i', raw_truth, offset)
        assert record[0] == 10 and len(set(record[1:])) == 10
        truth.append(set(record[1:]))
    for name in ['queries.fvecs', 'groundtruth.ivecs']:
        assert hashlib.sha256((out / (label + '.' + name)).read_bytes()).hexdigest() == identity['inputs'][label][name]
    deterministic = {}
    for row in [value for value in rows if value['dataset'] == label]:
        tag = f"{label}-{row['trial']}-{row['variant']}"
        queries = csv_rows(out / (tag + '.queries.csv'))
        neighbors = csv_rows(out / (tag + '.neighbors.csv'))
        assert len(queries) == 100 and len(neighbors) == 1000
        for q, query in enumerate(queries):
            assert int(query['query']) == q
            selected = neighbors[q * 10:(q + 1) * 10]
            ids = []
            for rank, item in enumerate(selected):
                assert int(item['query']) == q and int(item['rank']) == rank
                ids.append(int(item['id']))
                assert math.isfinite(float.fromhex(item['distance']))
            assert len(set(ids)) == 10 and all(0 <= value < 100000 for value in ids)
            assert len(truth[q].intersection(ids)) == int(query['hits'])
            assert 10 <= int(query['visited']) <= 100000
        latencies = sorted(float(query['latency_us']) for query in queries)
        assert all(math.isfinite(value) and value > 0 for value in latencies)
        assert sum(int(query['hits']) for query in queries) / 1000 == row['recall']
        assert latencies[49] == row['p50_us'] and latencies[98] == row['p99_us']
        assert sum(int(query['visited']) for query in queries) / 100 == row['average_visited']
        raw = (out / (tag + '.neighbors.csv')).read_bytes()
        if row['variant'] in deterministic:
            assert deterministic[row['variant']] == raw
        deterministic[row['variant']] = raw
    assert deterministic['control'] == (out / (label + '-native-parity.neighbors.csv')).read_bytes()
    summary[label] = {}
    for variant in ['control', 'candidate']:
        values = [row for row in rows if row['dataset'] == label and row['variant'] == variant]
        assert sorted(row['trial'] for row in values) == list(range(5))
        summary[label][variant] = {key: statistics.median(row[key] for row in values)
            for key in ['recall', 'p50_us', 'p99_us', 'average_visited']}
    summary[label]['p50_change_percent'] = 100 * (summary[label]['candidate']['p50_us'] / summary[label]['control']['p50_us'] - 1)
(out / 'audit.json').write_text(json.dumps(dict(status='PASS', runs=30, queries=3000,
    neighbors=30000, commands=39, summary=summary), indent=2) + '\n')
print(json.dumps(summary, indent=2))
print('PASS: 30 runs, 3000 queries, 30000 neighbors; exact single-site overlay and hashes')
