# Copyright 2024-present the vsag project
# SPDX-License-Identifier: Apache-2.0
import csv
import hashlib
import json
from pathlib import Path
import statistics
import sys

root = Path(sys.argv[1])
identity = json.loads((root / 'identity.json').read_text())
commands = json.loads((root / 'commands.json').read_text())
summary = json.loads((root / 'summary.json').read_text())
assert len(summary) == 8 and len(commands) == 18 and all(row['exit'] == 0 for row in commands)
assert hashlib.sha256((root / 'measured-probe.cpp').read_bytes()).hexdigest() == identity['sources']['lite/benchmark/query_allocation_probe.cpp']
for cell in summary:
    tag = cell['dataset'] + '-' + cell['storage']
    with (root / (tag + '.allocations.csv')).open() as source:
        rows = list(csv.DictReader(source))
    assert len(rows) == cell['queries'] == 100
    assert [int(row['query']) for row in rows] == list(range(100))
    assert statistics.median(int(row['ordinary_new_requests']) for row in rows) == cell['median_requests']
    assert statistics.median(int(row['ordinary_new_bytes']) for row in rows) == cell['median_bytes']
    assert {int(row['count_sized_requests']) for row in rows} == {1}
    assert all(int(row['ordinary_new_bytes']) > cell['count'] for row in rows)
    assert (root / (tag + '.neighbors.csv')).read_bytes() == (root / (tag + '-native.csv.neighbors.csv')).read_bytes()
    with (root / (tag + '.neighbors.csv')).open() as source:
        neighbors = list(csv.DictReader(source))
    assert len(neighbors) == 1000
    for q in range(100):
        selected = neighbors[q * 10:q * 10 + 10]
        assert [int(row['rank']) for row in selected] == list(range(10))
        assert all(int(row['query']) == q for row in selected)
        assert len({int(row['id']) for row in selected}) == 10
(root / 'audit.json').write_text(json.dumps(dict(status='PASS', cells=8,queries=800,neighbors=8000,
    ordinary_new_only=True), indent=2) + '\n')
print('PASS8cells800queries8000orderedneighbors18commands')
