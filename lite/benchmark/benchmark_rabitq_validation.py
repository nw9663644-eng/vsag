#!/usr/bin/env python3
# Copyright 2024-present the vsag project
# SPDX-License-Identifier: Apache-2.0
"""Paired warm Load and loaded-state Save; no Full/query/CRUD speed claim."""
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import statistics
import subprocess
import tempfile

REPO = Path('/home/ubuntu/project/vsag-lite-baseline-v01')
BUILD = REPO / 'build-lite-fp16-simd-release'
OUT = REPO / 'lite/benchmark/results/rabitq-validation-scratch-20261011'
CONTROL = Path('/home/ubuntu/project/vsag-validate-control-20261011')
OUT.mkdir(exist_ok=False)
COMMANDS = []

def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            digest.update(block)
    return digest.hexdigest()

def run(tag, command, env=None):
    result = subprocess.run(list(map(str, command)), cwd=REPO, env=env,
                            capture_output=True, text=True)
    (OUT / (tag + '.stdout')).write_text(result.stdout)
    (OUT / (tag + '.stderr')).write_text(result.stderr)
    COMMANDS.append(dict(tag=tag, argv=list(map(str, command)), exit=result.returncode))
    (OUT / 'commands.json').write_text(json.dumps(COMMANDS, indent=2) + '\n')
    if result.returncode:
        raise RuntimeError(tag + ' failed')
    return result.stdout

identity = dict(parent='109d554f70c1ea46cecf05a232a18515fa766ce5', trials=5,
                cpu=0, threads=1, snapshots={}, inputs={}, sources={}, libraries={})
for name, library in [('control', CONTROL), ('candidate', BUILD)]:
    identity['libraries'][name] = sha(library / 'libvsag-lite.so')
for relative in ['src/lite/rabitq_graph_state.h', 'src/lite/rabitq_backend_test.cpp',
                 'src/lite/rabitq_backend.cpp', 'src/lite/rabitq_snapshot.h']:
    path = REPO / relative
    identity['sources'][relative] = sha(path)
    (OUT / ('source-' + path.name)).write_bytes(path.read_bytes())
(OUT / 'candidate.patch').write_bytes(subprocess.check_output(
    ['git', 'diff', '--', 'src/lite/rabitq_graph_state.h', 'src/lite/rabitq_backend_test.cpp'],
    cwd=REPO))
(OUT / 'control-rabitq_graph_state.h').write_bytes(subprocess.check_output(
    ['git', 'show', identity['parent'] + ':src/lite/rabitq_graph_state.h'], cwd=REPO))
rows = []
with tempfile.TemporaryDirectory(prefix='vsag-validation-', dir='/dev/shm') as directory:
    scratch = Path(directory)
    probe = scratch / 'save-probe'
    run('compile-save-probe', ['/usr/bin/c++', '-O3', '-DNDEBUG', '-std=c++17',
        '-I' + str(REPO / 'include'), REPO / 'lite/benchmark/rabitq_save_probe.cpp',
        '-L' + str(BUILD), '-Wl,-rpath,' + str(BUILD), '-lvsag-lite', '-o', probe])
    for label, dim, root in [
        ('gist100k', 960, '/home/ubuntu/project/vsag-lite-datasets/gist/prepared-10k-100k/scale-100000'),
        ('cohere100k', 768, '/home/ubuntu/project/vsag-lite-cohere-normalized-20261006/prepared/scale-100000')]:
        root = Path(root)
        snapshot = scratch / (label + '.snapshot')
        env = dict(os.environ, OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1',
                   MKL_NUM_THREADS='1', LD_LIBRARY_PATH=str(BUILD),
                   VSAG_GRAPH_STORAGE='rabitq8', VSAG_GRAPH_DEGREE='16',
                   VSAG_GRAPH_EF='128', VSAG_GRAPH_QUERY_EF='512')
        for key in ['VSAG_GRAPH_REPLACEMENTS', 'VSAG_GRAPH_CRUD_MODE',
                    'VSAG_LOAD_QUERY_PATH', 'VSAG_LOAD_QUALITY_TRUTH']:
            env.pop(key, None)
        identity['inputs'][label] = {name: dict(path=str(root / name), sha256=sha(root / name))
            for name in ['base.fvecs', 'queries.fvecs', 'groundtruth.ivecs']}
        run(label + '-prepare', ['taskset', '-c', '0', BUILD / 'lite_graph_crud_quality',
            root, snapshot, '0', '1', OUT / (label + '-prepare.queries.csv')], env)
        digest = sha(snapshot)
        identity['snapshots'][label] = dict(bytes=snapshot.stat().st_size, sha256=digest)
        (OUT / 'identity.json').write_text(json.dumps(identity, indent=2) + '\n')
        print(label + ' prepared', flush=True)
        for trial in range(identity['trials']):
            order = [('control', CONTROL), ('candidate', BUILD)]
            if trial % 2:
                order.reverse()
            for name, library in order:
                selected = dict(env, LD_LIBRARY_PATH=str(library))
                for operation in ['load', 'save']:
                    tag = f'{label}-{trial}-{name}-{operation}'
                    target = scratch / (tag + '.snapshot')
                    command = ([BUILD / 'lite_load_memory', snapshot, str(dim), '100000']
                               if operation == 'load' else [probe, snapshot, target])
                    output = run(tag, ['taskset', '-c', '0'] + command, selected)
                    metrics = next(csv.DictReader(io.StringIO(output)))
                    if operation == 'save':
                        assert sha(target) == digest
                        target.unlink()
                    rows.append(dict(dataset=label, trial=trial, variant=name,
                                     operation=operation, metrics=metrics))
                    (OUT / 'rows.json').write_text(json.dumps(rows, indent=2) + '\n')
        print(label + ' five pairs complete', flush=True)
summary = {}
for label in ['gist100k', 'cohere100k']:
    summary[label] = {}
    for operation, metric in [('load', 'load_ms'), ('load', 'loaded_rss_kib'),
                              ('load', 'process_peak_rss_kib'), ('save', 'save_ms'),
                              ('save', 'before_rss_kib'), ('save', 'after_hwm_kib')]:
        medians = {name: statistics.median(float(row['metrics'][metric]) for row in rows
            if row['dataset'] == label and row['operation'] == operation
            and row['variant'] == name) for name in ['control', 'candidate']}
        summary[label][operation + ':' + metric] = dict(medians,
            change_percent=100 * (medians['candidate'] / medians['control'] - 1))
(OUT / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
print(json.dumps(summary, indent=2), flush=True)
