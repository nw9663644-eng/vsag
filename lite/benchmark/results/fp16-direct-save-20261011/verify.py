# Copyright 2024-present the vsag project
# SPDX-License-Identifier: Apache-2.0
"""Recompute FP16 Save evidence; no new product performance measurements."""
import csv
import json
import math
from pathlib import Path
import statistics
import sys
import hashlib
import tarfile
import tempfile

root = Path(sys.argv[1])
destination = root
if (root / 'raw.tar.gz').exists():
    members = json.loads((root / 'members.json').read_text())
    temporary = tempfile.TemporaryDirectory(prefix='vsag-fp16-audit-')
    unpacked = Path(temporary.name)
    observed = set()
    with tarfile.open(root / 'raw.tar.gz') as archive:
        for member in archive:
            path = Path(member.name)
            assert member.isfile() and not path.is_absolute() and '..' not in path.parts
            assert member.name not in observed
            observed.add(member.name)
            payload = archive.extractfile(member).read()
            assert hashlib.sha256(payload).hexdigest() == members[member.name]
            target = unpacked / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(payload)
    assert observed == set(members)
    root = unpacked
identity = json.loads((root / 'identity.json').read_text())
commands = json.loads((root / 'commands.json').read_text())
assert len(commands) == 49 and all(row['exit'] == 0 for row in commands)
summary = {}
for label in ['sift', 'gist', 'cohere']:
    directory = root / (label + '-10k')
    rows = json.loads((directory / 'rows.json').read_text())
    assert len(rows) == 6
    for trial in range(3):
        pair = [row for row in rows if row['trial'] == trial]
        assert len(pair) == 2 and {row['name'] for row in pair} == {'control', 'lite'}
        assert pair[0]['snapshot_sha256'] == pair[1]['snapshot_sha256']
        neighbors = []
        for row in pair:
            tag = f"{label}10k600-fp16-{trial}-{row['name']}"
            neighbors.append((directory / (tag + '.queries.csv.neighbors.csv')).read_bytes())
            with (directory / (tag + '.queries.csv.latencies.csv')).open() as source:
                values = sorted(float(value['latency_us']) for value in csv.DictReader(source))
            assert len(values) == 600 and all(math.isfinite(value) for value in values)
            assert abs(values[299] - float(row['build']['search_p50_us'])) < 1e-6
            assert abs(values[593] - float(row['build']['search_p99_us'])) < 1e-6
            assert len(row['loads']) == 1
        assert neighbors[0] == neighbors[1]
    summary[label] = dict(build_then_save_10k_ms={variant: statistics.median(
        float(row['build']['save_ms']) for row in rows if row['name'] == variant)
        for variant in ['control', 'lite']})
save_rows = json.loads((root / 'save-rows.json').read_text())
assert len(save_rows) == 42
for label in ['sift', 'gist', 'cohere']:
    for variant in ['control', 'candidate']:
        rows = [row for row in save_rows if row['dataset'] == label and row['variant'] == variant]
        assert sorted(row['trial'] for row in rows) == list(range(7))
        for row in rows:
            assert row['saved_sha256'] == identity['snapshots'][label]['sha256']
            assert int(row['metrics']['bytes']) == identity['snapshots'][label]['bytes']
            tag = f"{label}-100k-{row['trial']}-{variant}"
            with (root / (tag + '.stdout')).open() as source:
                assert list(csv.DictReader(source))[0] == row['metrics']
        summary[label].setdefault('loaded_state_save_100k_ms', {})[variant] = statistics.median(
            float(row['metrics']['save_ms']) for row in rows)
(destination / 'audit.json').write_text(json.dumps(dict(status='PASS', summary=summary,
    builders10k=18, prepares100k=3, saves100k=42, commands=49), indent=2) + '\n')
print(json.dumps(summary, indent=2))
print('PASS18pairedbuilders42freshsaves49commands')
