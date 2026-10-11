#!/usr/bin/env python3
# Copyright 2024-present the vsag project
# SPDX-License-Identifier: Apache-2.0
"""Audit archived raw rows, medians, pairing and measured source hashes."""
import csv
import hashlib
import io
import json
from pathlib import Path
import statistics
import sys

root = Path(sys.argv[1])
rows = json.loads((root / 'rows.json').read_text())
summary = json.loads((root / 'summary.json').read_text())
identity = json.loads((root / 'identity.json').read_text())
datasets = list(identity['snapshots'])
assert datasets and set(datasets).issubset({'sift100k', 'gist100k', 'cohere100k'})
assert identity['trials'] == 5
assert len(rows) == 20 * len(datasets)
commands = json.loads((root / 'commands.json').read_text())
assert len(commands) == 1 + 21 * len(datasets)
assert all(command['exit'] == 0 for command in commands)
for relative, digest in identity['sources'].items():
    assert hashlib.sha256((root / ('source-' + Path(relative).name)).read_bytes()).hexdigest() == digest
wins = {}
for dataset in datasets:
    for operation in ['load', 'save']:
        metric = operation + '_ms'
        selected = [row for row in rows if row['dataset'] == dataset and row['operation'] == operation]
        assert len(selected) == 10
        medians = {}
        for variant in ['control', 'candidate']:
            group = [row for row in selected if row['variant'] == variant]
            assert sorted(row['trial'] for row in group) == list(range(5))
            for row in group:
                tag = f"{dataset}-{row['trial']}-{variant}-{operation}"
                raw = next(csv.DictReader(io.StringIO((root / (tag + '.stdout')).read_text())))
                assert raw == row['metrics']
                assert int(raw['count']) == 100000
                assert int(raw['bytes' if operation == 'save' else 'snapshot_bytes']) == identity['snapshots'][dataset]['bytes']
                if operation == 'save' and 'saved_sha256' in row:
                    assert row['saved_sha256'] == identity['snapshots'][dataset]['sha256']
            medians[variant] = statistics.median(float(row['metrics'][metric]) for row in group)
            assert medians[variant] == summary[dataset][operation + ':' + metric][variant]
        expected = 100 * (medians['candidate'] / medians['control'] - 1)
        assert abs(expected - summary[dataset][operation + ':' + metric]['change_percent']) < 1e-9
        wins[dataset + ':' + operation] = sum(
            float(next(row for row in selected if row['trial'] == trial and row['variant'] == 'candidate')['metrics'][metric]) <
            float(next(row for row in selected if row['trial'] == trial and row['variant'] == 'control')['metrics'][metric])
            for trial in range(5))
print(json.dumps(dict(rows=len(rows), commands=len(commands), source_hashes='pass',
                     paired_candidate_wins=wins), indent=2))
