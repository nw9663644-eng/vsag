# Copyright 2024-present the vsag project
# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import csv
import hashlib
import json
import os
import subprocess

root = Path(__file__).resolve().parent
final = root / 'final'
final.mkdir()
initial = json.loads((root / 'commands.json').read_text())
env = dict(os.environ, LD_LIBRARY_PATH=str(Path.cwd() / 'build-lite-fragment-release'))
commands = []
for row in initial:
    name = row['case']
    cmd = row['command'].copy()
    cmd[-1] = str(final / (name + '.csv'))
    result = subprocess.run(cmd, env=env, capture_output=True)
    (final / (name + '.stdout.log')).write_bytes(result.stdout)
    (final / (name + '.stderr.log')).write_bytes(result.stderr)
    commands.append(dict(row, command=cmd, exit=result.returncode))
    (final / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
    assert result.returncode == 0, result.stderr
    for suffix in ('.csv', '.csv.neighbors.csv'):
        assert (final / (name + suffix)).read_bytes() == (root / (name + suffix)).read_bytes()
    if not name.endswith('-ordered'):
        legacy = ['taskset', '-c', '0', str(root / 'route-probe-before'), cmd[4], cmd[6],
                  str(final / (name + '.legacy.csv')), '128', 'uniform', 'preserve', '1']
        # cmd layout is taskset -c 0 BINARY SNAPSHOT REFERENCE DATASET OUTPUT.
        p = subprocess.run(legacy, env=env, capture_output=True)
        (final / (name + '.legacy.stdout.log')).write_bytes(p.stdout)
        (final / (name + '.legacy.stderr.log')).write_bytes(p.stderr)
        assert p.returncode == 0, p.stderr
        commands.append({'case': name + '-legacy', 'command': legacy, 'exit': p.returncode})
        new = [r for r in csv.DictReader((final / (name + '.csv')).open())
               if r['mask'] == '0' and r['eligible'] == '1']
        old = list(csv.DictReader((final / (name + '.legacy.csv')).open()))
        for r in new:
            match = next(o for o in old if o['query'] == r['query'])
            for key in ('hits', 'truth_visited', 'visited_nodes', 'expanded_nodes',
                        'distance_evaluations'):
                assert r[key] == match[key], (name, r['query'], key)
    print(name, 'final/native/legacy consistency passed', flush=True)
(final / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
paths = [Path('lite/CMakeLists.txt'), Path('lite/benchmark/graph_slot_probe.cpp'),
         Path('lite/benchmark/graph_route_probe.cpp'), Path('lite/benchmark/test_graph_slot_probe.py'),
         Path('build-lite-fragment-release/lite_graph_slot_probe'),
         Path('build-lite-fragment-release/libvsag-lite.so'), root / 'route-probe-before',
         Path('build-lite-baseline-asan/lite_graph_slot_probe'),
         Path(initial[0]['command'][6]) / 'queries.fvecs',
         Path(initial[0]['command'][6]) / 'groundtruth.ivecs']
identity = {'parent': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
            'files': {str(p.resolve()): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}}
(final / 'identity.json').write_text(json.dumps(identity, indent=2) + '\n')
