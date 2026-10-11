# Copyright 2024-present the vsag project
# SPDX-License-Identifier: Apache-2.0
"""Byte-preserving old/current Lite FP16 Save comparison; no Full claim."""
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import statistics
import subprocess
import tempfile

repo = Path('/home/ubuntu/project/vsag-lite-baseline-v01')
out = repo / 'lite/benchmark/results/fp16-direct-save-20261011'
out.mkdir(exist_ok=False)
build = repo / 'build-lite-fp16-simd-release'
control = Path('/home/ubuntu/project/vsag-fp16-save-control-20261011/libvsag-lite.so')

def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1048576), b''):
            digest.update(block)
    return digest.hexdigest()

env = {key: value for key, value in os.environ.items() if not key.startswith('VSAG_')}
env.update(OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1', MKL_NUM_THREADS='1',
    VSAG_GRAPH_STORAGE='fp16', VSAG_GRAPH_DEGREE='16', VSAG_GRAPH_EF='128', VSAG_GRAPH_QUERY_EF='512')
identity = dict(head=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo, text=True).strip(),
    control_sha256=sha(control), candidate_sha256=sha(build / 'libvsag-lite.so'),
    diff=subprocess.check_output(['git', 'diff'], cwd=repo, text=True), inputs={}, snapshots={})
commands = []

def run(tag, command, environment):
    result = subprocess.run(list(map(str, command)), cwd=repo, env=environment, text=True, capture_output=True)
    (out / (tag + '.stdout')).write_text(result.stdout)
    (out / (tag + '.stderr')).write_text(result.stderr)
    commands.append(dict(tag=tag, command=list(map(str, command)), exit=result.returncode))
    (out / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
    result.check_returncode()
    return result.stdout

roots = dict(sift='/home/ubuntu/project/vsag-lite-datasets/sift/prepared-10k-100k',
    gist='/home/ubuntu/project/vsag-lite-datasets/gist/prepared-10k-100k',
    cohere='/home/ubuntu/project/vsag-lite-cohere-normalized-20261006/prepared')
with tempfile.TemporaryDirectory(prefix='vsag-fp16-direct-', dir='/dev/shm') as directory:
    scratch = Path(directory)
    run('compile-save-probe', ['c++', '-O3', '-std=c++17', '-Iinclude',
        'lite/benchmark/rabitq_save_probe.cpp', '-L' + str(build), '-lvsag-lite',
        '-o', scratch / 'save-probe'], env)
    for label, location in roots.items():
        data = scratch / label
        data.mkdir()
        shutil.copyfile(Path(location) / 'scale-10000/base.fvecs', data / 'base.fvecs')
        prior = repo / 'lite/benchmark/results/current-full-10k600-20261011'
        for name in ['queries.fvecs', 'groundtruth.ivecs']:
            shutil.copyfile(prior / (label + '10k600.' + name), data / name)
        command = ['python3', 'lite/benchmark/run_aligned_comparison.py',
            '--lite-build', build, '--control-library', control,
            '--dataset', label + '10k600=' + str(data), '--storage', 'fp16',
            '--output', out / (label + '-10k'), '--scratch', scratch,
            '--trials', '3', '--loads', '1', '--ef', '512', '--cpu', '0']
        run(label + '-10k-pairs', command, env)
        print(label, '10k three byte-exact pairs complete', flush=True)
    rows = []
    for label, location in roots.items():
        data = Path(location) / 'scale-100000'
        identity['inputs'][label] = {name: sha(data / name) for name in ['base.fvecs', 'queries.fvecs', 'groundtruth.ivecs']}
        snapshot = scratch / (label + '.snapshot')
        current = dict(env, LD_LIBRARY_PATH=str(build))
        run(label + '-100k-prepare', ['taskset', '-c', '0', build / 'lite_graph_crud_quality',
            data, snapshot, '0', '1', out / (label + '-100k-prepare.csv')], current)
        expected_sha = sha(snapshot)
        identity['snapshots'][label] = dict(sha256=expected_sha, bytes=snapshot.stat().st_size)
        for trial in range(7):
            order = ['control', 'candidate'] if trial % 2 == 0 else ['candidate', 'control']
            for variant in order:
                output = scratch / f'{label}-{trial}-{variant}.snapshot'
                tag = f'{label}-100k-{trial}-{variant}'
                environment = dict(env, LD_LIBRARY_PATH=str(control.parent if variant == 'control' else build))
                text = run(tag, ['taskset', '-c', '0', scratch / 'save-probe', snapshot, output], environment)
                record = list(csv.DictReader(io.StringIO(text)))[0]
                assert sha(output) == expected_sha
                rows.append(dict(dataset=label, trial=trial, variant=variant, metrics=record, saved_sha256=expected_sha))
                (out / 'save-rows.json').write_text(json.dumps(rows, indent=2) + '\n')
                output.unlink()  # Only this newly created and SHA-verified temporary output.
        print(label, {variant: statistics.median(float(row['metrics']['save_ms']) for row in rows
            if row['dataset'] == label and row['variant'] == variant) for variant in ['control', 'candidate']}, flush=True)
    (out / 'identity.json').write_text(json.dumps(identity, indent=2) + '\n')
shutil.copyfile(__file__, out / 'run.py')
print('complete18builders42freshloaded-state-saves', flush=True)
