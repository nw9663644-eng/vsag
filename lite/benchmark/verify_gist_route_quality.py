# Copyright 2024-present the vsag project
# SPDX-License-Identifier: Apache-2.0
"""Audit truth rows against archived GT and formal native hit counts."""
import csv
import hashlib
import json
from pathlib import Path
import struct
import sys

root = Path(sys.argv[1])
identity = json.loads((root / 'identity.json').read_text())
assert len(identity['commands']) == 2 and all(row['exit'] == 0 for row in identity['commands'])
for name, digest in identity['sources'].items():
    assert hashlib.sha256((root / ('source-' + Path(name).name)).read_bytes()).hexdigest() == digest
for name in ['queries.fvecs', 'groundtruth.ivecs']:
    assert hashlib.sha256((root / name).read_bytes()).hexdigest() == identity['inputs'][name]
with (root / 'trace.queries.csv').open() as source:
    queries = list(csv.DictReader(source))
with (root / 'trace.truth.csv').open() as source:
    evidence = list(csv.DictReader(source))
with (root / 'prepare.queries.csv').open() as source:
    formal = list(csv.DictReader(source))
truth = (root / 'groundtruth.ivecs').read_bytes()
assert len(queries) == len(formal) == 100 and len(evidence) == 1000 and len(truth) == 4400
totals = {key: 0 for key in ['formal_hits', 'visited_truth', 'visited_rerank_hits', 'all_codes_hits']}
missing_route = missing_visited = 0
for query_id, row in enumerate(queries):
    expected = struct.unpack_from('<11i', truth, query_id * 44)
    group = evidence[query_id * 10:(query_id + 1) * 10]
    assert expected[0] == 10 and [int(item['id']) for item in group] == list(expected[1:])
    assert int(row['query']) == query_id and int(row['formal_hits']) == int(formal[query_id]['hits'])
    for key, column in [('formal_hits', 'formal'), ('visited_truth', 'visited'),
                        ('visited_rerank_hits', 'visited_rerank'), ('all_codes_hits', 'all_codes')]:
        count = sum(int(item[column]) for item in group)
        assert count == int(row[key])
        totals[key] += count
    for item in group:
        assert not int(item['formal']) or int(item['visited'])
        assert not int(item['visited_rerank']) or int(item['visited'])
        if not int(item['formal']):
            missing_route += not int(item['visited'])
            missing_visited += bool(int(item['visited']))
assert missing_route + missing_visited == 1000 - totals['formal_hits']
result = dict(audit='pass', queries=100, truth_rows=1000, hits=totals,
    formal_missing_not_visited=missing_route, formal_missing_visited=missing_visited,
    average_visited=sum(int(row['visited_nodes']) for row in queries) / 100)
print(json.dumps(result, indent=2))
