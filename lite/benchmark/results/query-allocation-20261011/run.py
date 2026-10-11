# Copyright 2024-present the vsag project
# SPDX-License-Identifier: Apache-2.0
"""Count ordinary-new requests in public queries; not a latency benchmark."""
import csv
import hashlib
import json
import os
from pathlib import Path
import shutil
import statistics
import subprocess
import tempfile

repo = Path('/home/ubuntu/project/vsag-lite-baseline-v01')
out = repo / 'lite/benchmark/results/query-allocation-20261011'
out.mkdir(exist_ok=False)
build = repo / 'build-lite-fp16-simd-release'
env = {key: value for key, value in os.environ.items() if not key.startswith('VSAG_')}
env.update(LD_LIBRARY_PATH=str(build), OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1', MKL_NUM_THREADS='1',
    VSAG_GRAPH_DEGREE='16', VSAG_GRAPH_EF='128', VSAG_GRAPH_QUERY_EF='512')
commands = []

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def run(tag, argv, environment):
    result = subprocess.run(list(map(str, argv)), cwd=repo, env=environment, text=True, capture_output=True)
    commands.append(dict(tag=tag, argv=list(map(str, argv)), exit=result.returncode))
    (out / (tag + '.stdout')).write_text(result.stdout)
    (out / (tag + '.stderr')).write_text(result.stderr)
    (out / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
    result.check_returncode()

identity = dict(head=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo, text=True).strip(),
    library_sha256=sha(build / 'libvsag-lite.so'), sources={}, inputs={}, snapshots={})
summary = []
with tempfile.TemporaryDirectory(prefix='vsag-query-alloc-', dir='/dev/shm') as directory:
    scratch = Path(directory)
    source = repo / 'lite/benchmark/query_allocation_probe.cpp'
    run('format', ['clang-format-15', '-i', source], env)
    run('compile', ['c++', '-O3', '-std=c++17', '-Wl,--export-dynamic', '-Iinclude', source,
        '-L' + str(build), '-lvsag-lite', '-o', scratch / 'probe'], env)
    identity['sources'][str(source.relative_to(repo))] = sha(source)
    for label, count, location in [
        ('sift10k',10000,'/home/ubuntu/project/vsag-lite-datasets/sift/prepared-10k-100k/scale-10000'),
        ('gist10k',10000,'/home/ubuntu/project/vsag-lite-datasets/gist/prepared-10k-100k/scale-10000'),
        ('cohere10k',10000,'/home/ubuntu/project/vsag-lite-cohere-normalized-20261006/prepared/scale-10000'),
        ('gist100k',100000,'/home/ubuntu/project/vsag-lite-datasets/gist/prepared-10k-100k/scale-100000')]:
        data = Path(location)
        identity['inputs'][label] = {name: sha(data / name) for name in ['base.fvecs','queries.fvecs','groundtruth.ivecs']}
        for storage in ['fp16','rabitq8']:
            tag = label + '-' + storage
            snapshot = scratch / (tag + '.snapshot')
            current = dict(env, VSAG_GRAPH_STORAGE=storage)
            run(tag + '-prepare', ['taskset','-c','0',build / 'lite_graph_crud_quality',data,
                snapshot,'0','1',out / (tag + '-native.csv')], current)
            identity['snapshots'][tag] = dict(sha256=sha(snapshot), bytes=snapshot.stat().st_size)
            run(tag + '-probe', ['taskset','-c','0',scratch / 'probe',snapshot,data / 'queries.fvecs',
                out / (tag + '.allocations.csv'),out / (tag + '.neighbors.csv')], current)
            assert (out / (tag + '.neighbors.csv')).read_bytes() == (out / (tag + '-native.csv.neighbors.csv')).read_bytes()
            with (out / (tag + '.allocations.csv')).open() as stream:
                rows = list(csv.DictReader(stream))
            assert len(rows) == 100
            summary.append(dict(dataset=label,storage=storage,count=count,queries=len(rows),
                median_requests=statistics.median(int(row['ordinary_new_requests']) for row in rows),
                median_bytes=statistics.median(int(row['ordinary_new_bytes']) for row in rows),
                count_sized_requests=sorted({int(row['count_sized_requests']) for row in rows})))
            (out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
            print(summary[-1], flush=True)
    (out / 'identity.json').write_text(json.dumps(identity, indent=2) + '\n')
shutil.copyfile(__file__, out / 'run.py')
print('complete8cells800queries', flush=True)
