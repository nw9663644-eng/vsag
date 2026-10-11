# Copyright 2024-present the vsag project
# SPDX-License-Identifier: Apache-2.0
"""Isolated full-code routing candidate; never overwrite production sources."""
import csv
import hashlib
import io
import json
import math
import os
from pathlib import Path
import shutil
import statistics
import subprocess
import tempfile

repo = Path('/home/ubuntu/project/vsag-lite-baseline-v01')
build = repo / 'build-lite-fp16-simd-release'
out = repo / 'lite/benchmark/results/rabitq-full-route-retry-20261011'
out.mkdir(exist_ok=False)

def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1048576), b''):
            digest.update(block)
    return digest.hexdigest()

commands = []
def run(tag, command, env=None):
    result = subprocess.run(list(map(str, command)), cwd=repo, env=env, capture_output=True, text=True)
    (out / (tag + '.stdout')).write_text(result.stdout)
    (out / (tag + '.stderr')).write_text(result.stderr)
    commands.append(dict(tag=tag, argv=list(map(str, command)), exit=result.returncode))
    (out / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
    assert result.returncode == 0, tag

env = {key: value for key, value in os.environ.items() if not key.startswith('VSAG_')}
env.update(OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1',
           LD_LIBRARY_PATH=str(build), VSAG_GRAPH_STORAGE='rabitq8',
           VSAG_GRAPH_DEGREE='16', VSAG_GRAPH_EF='128', VSAG_GRAPH_QUERY_EF='512')
identity = dict(head=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo).decode().strip(),
    library_sha256=sha(build / 'libvsag-lite.so'), archive_sha256=sha(build / 'libvsag-lite.a'),
    inputs={}, snapshots={}, executable_sha256={}, trials=5, sources={},
    scope='initial100k internal SearchWithOptions, one warmup pass, CPU0/thread1/degree16/build128/query512')
rows = []
with tempfile.TemporaryDirectory(prefix='vsag-full-route-', dir='/dev/shm') as directory:
    scratch = Path(directory)
    overlay = scratch / 'candidate-headers'
    (overlay / 'lite').mkdir(parents=True)
    path = repo / 'src/lite/rabitq_graph_state.h'
    original = path.read_text()
    begin = original.index('inline GraphSearchResult\ngraph_search_impl(')
    end = original.index('inline GraphSearchResult\ngraph_search(', begin)
    body = original[begin:end]
    marker = 'const Candidate next{slot, estimate.distance, estimate.centered_ip};'
    assert body.count(marker) == 1
    body = body.replace(marker, 'const Candidate next{slot, full_distance(query, query_norm, code, estimate.centered_ip, query_sum), estimate.centered_ip};')
    candidate = original[:begin] + body + original[end:]
    (overlay / 'lite/rabitq_graph_state.h').write_text(candidate)
    (out / 'control-rabitq_graph_state.h').write_text(original)
    (out / 'candidate-rabitq_graph_state.h').write_text(candidate)
    source = repo / 'lite/benchmark/rabitq_full_route_probe.cpp'
    run('format', ['clang-format-15', '-i', source])
    for name in ['src/lite/rabitq_graph_state.h', 'src/lite/rabitq_snapshot.h',
                 'lite/benchmark/rabitq_full_route_probe.cpp', 'lite/benchmark/run_rabitq_full_route.py']:
        identity['sources'][name] = sha(repo / name)
        shutil.copyfile(repo / name, out / ('source-' + Path(name).name))
    for variant in ['control', 'candidate']:
        command = ['c++', '-O3', '-DNDEBUG', '-std=c++17', '-DVSAG_LITE_RABITQ_X86_SIMD']
        if variant == 'candidate':
            command += ['-DVSAG_LITE_EXPERIMENT_FULL_ROUTE', '-I' + str(overlay)]
        command += ['-Isrc', '-Iinclude', str(source), str(build / 'libvsag-lite.a'),
                    '-o', str(scratch / variant)]
        run('compile-' + variant, command)
        identity['executable_sha256'][variant] = sha(scratch / variant)
    for label, root in [
        ('sift100k', '/home/ubuntu/project/vsag-lite-datasets/sift/prepared-10k-100k/scale-100000'),
        ('gist100k', '/home/ubuntu/project/vsag-lite-datasets/gist/prepared-10k-100k/scale-100000'),
        ('cohere100k', '/home/ubuntu/project/vsag-lite-cohere-normalized-20261006/prepared/scale-100000')]:
        root = Path(root)
        identity['inputs'][label] = {name: sha(root / name) for name in ['base.fvecs', 'queries.fvecs', 'groundtruth.ivecs']}
        for name in ['queries.fvecs', 'groundtruth.ivecs']:
            shutil.copyfile(root / name, out / (label + '.' + name))
        snapshot = scratch / (label + '.snapshot')
        run(label + '-prepare', ['taskset', '-c', '0', build / 'lite_graph_crud_quality',
            root, snapshot, '0', '1', out / (label + '-prepare.queries.csv')], env)
        identity['snapshots'][label] = dict(sha256=sha(snapshot), bytes=snapshot.stat().st_size)
        run(label + '-native-parity', ['taskset', '-c', '0', scratch / 'control', snapshot,
            root / 'queries.fvecs', root / 'groundtruth.ivecs', out / (label + '-native-parity'), '1'], env)
        for trial in range(5):
            order = ['control', 'candidate'] if trial % 2 == 0 else ['candidate', 'control']
            for variant in order:
                tag = f'{label}-{trial}-{variant}'
                run(tag, ['taskset', '-c', '0', scratch / variant, snapshot,
                    root / 'queries.fvecs', root / 'groundtruth.ivecs', out / tag, '0'], env)
                with (out / (tag + '.queries.csv')).open() as source_csv:
                    values = list(csv.DictReader(source_csv))
                assert len(values) == 100
                latencies = sorted(float(row['latency_us']) for row in values)
                rows.append(dict(dataset=label, trial=trial, variant=variant,
                    recall=sum(int(row['hits']) for row in values) / 1000,
                    p50_us=latencies[49], p99_us=latencies[98],
                    average_visited=sum(int(row['visited']) for row in values) / 100))
                (out / 'rows.json').write_text(json.dumps(rows, indent=2) + '\n')
        (out / 'identity.json').write_text(json.dumps(identity, indent=2) + '\n')
        print(label, {name: dict(recall=statistics.median(row['recall'] for row in rows if row['dataset'] == label and row['variant'] == name),
            p50_us=statistics.median(row['p50_us'] for row in rows if row['dataset'] == label and row['variant'] == name))
            for name in ['control', 'candidate']}, flush=True)
print('all three datasets complete', flush=True)
