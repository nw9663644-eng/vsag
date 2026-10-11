# Copyright 2024-present the vsag project
# SPDX-License-Identifier: Apache-2.0
"""Initial GIST100k diagnostic; do not report its instrumented timing as performance."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

repo = Path('/home/ubuntu/project/vsag-lite-baseline-v01')
out = repo / 'lite/benchmark/results/gist-route-quality-20261011'
root = Path('/home/ubuntu/project/vsag-lite-datasets/gist/prepared-10k-100k/scale-100000')
build = repo / 'build-lite-fp16-simd-release'
probe = Path('/home/ubuntu/project/vsag-gist-route-probe-20261011')
assert not (out / 'identity.json').exists()

def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            digest.update(block)
    return digest.hexdigest()

env = {key: value for key, value in os.environ.items() if not key.startswith('VSAG_')}
env.update(OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1',
           VSAG_GRAPH_STORAGE='rabitq8', VSAG_GRAPH_DEGREE='16', VSAG_GRAPH_EF='128',
           VSAG_GRAPH_QUERY_EF='512', LD_LIBRARY_PATH=str(build))
identity = dict(head=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo).decode().strip(),
    library_sha256=sha(build / 'libvsag-lite.so'), static_sha256=sha(build / 'libvsag-lite.a'),
    probe_sha256=sha(probe), inputs={name: sha(root / name)
        for name in ['base.fvecs', 'queries.fvecs', 'groundtruth.ivecs']},
    sources={name: sha(repo / name) for name in ['src/lite/rabitq_graph_state.h',
        'src/lite/rabitq_snapshot.h', 'lite/benchmark/rabitq_route_quality_probe.cpp']},
    configuration=dict(cpu=0, threads=1, count=100000, queries=100, degree=16,
        build_ef=128, query_ef=512, k=10, rounds=0, scope='initial graph diagnostic, not timed speed evidence'),
    commands=[])
for name in identity['sources']:
    shutil.copyfile(repo / name, out / ('source-' + Path(name).name))
for name in ['queries.fvecs', 'groundtruth.ivecs']:
    shutil.copyfile(root / name, out / name)
with tempfile.TemporaryDirectory(prefix='vsag-gist-diagnostic-', dir='/dev/shm') as directory:
    snapshot = Path(directory) / 'initial.snapshot'
    for tag, command in [('prepare', [build / 'lite_graph_crud_quality', root, snapshot, '0', '1',
                                     out / 'prepare.queries.csv']),
                         ('diagnostic', [probe, snapshot, root / 'queries.fvecs',
                                         root / 'groundtruth.ivecs', out / 'trace'])]:
        selected = ['taskset', '-c', '0', *map(str, command)]
        with (out / (tag + '.stdout')).open('w') as stdout, (out / (tag + '.stderr')).open('w') as stderr:
            result = subprocess.run(selected, cwd=repo, env=env, stdout=stdout, stderr=stderr)
        identity['commands'].append(dict(argv=selected, exit=result.returncode))
        if tag == 'prepare' and result.returncode == 0:
            identity['snapshot_sha256'] = sha(snapshot)
            identity['snapshot_bytes'] = snapshot.stat().st_size
        (out / 'identity.json').write_text(json.dumps(identity, indent=2) + '\n')
        assert result.returncode == 0, tag
        print(tag + ' passed', flush=True)
