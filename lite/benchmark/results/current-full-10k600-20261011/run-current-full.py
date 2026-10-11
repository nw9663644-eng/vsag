# Copyright 2024-present the vsag project
# SPDX-License-Identifier: Apache-2.0
"""Current Lite / pinned native Full, reusing recorded observed query cohorts."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

repo = Path('/home/ubuntu/project/vsag-lite-baseline-v01')
out = repo / 'lite/benchmark/results/current-full-10k600-20261011'
assert not out.exists()
prior = repo / 'lite/benchmark/results/acceptance-full-expanded-r1-20261009'
inputs = repo / 'lite/benchmark/results/acceptance-expanded-inputs-20261009'
full = Path('/home/ubuntu/project/vsag-full-known-install-20261006')
env = {key: value for key, value in os.environ.items() if not key.startswith('VSAG_')}
env.update(OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1', MKL_NUM_THREADS='1',
    PYTHONPATH='/home/ubuntu/project/vsag-lite-datasets/sift/python-deps')

def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1048576), b''):
            digest.update(block)
    return digest.hexdigest()

assert sha(full / 'lib/libvsag.so') == '9aeaa550703f116bef2959769d4f2f03da254b07c906ba941d8186224cc70c72'
provenance = json.loads((prior / 'provenance.json').read_text())
for name, digest in provenance['full_headers_sha256'].items():
    assert sha(full / 'include' / name) == digest
provenance.update(lite_source_head=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo, text=True).strip(),
    cpp_tests='inherited production a492b6f Release6/SAN8/Cov-build6; not rerun here',
    new_tests='raw verifier to be run after measurement',
    query_split='source queries[400,1000), observed cohort, not blind',
    scope='initial10k, rounds0; no mutation throughput or latest fresh Full claim')
provenance['full_runner_sha256'] = {name: sha(repo / 'build-full-known-runner' / name)
    for name in ['full_rabitq_dataset_benchmark', 'full_load_memory']}
with tempfile.TemporaryDirectory(prefix='vsag-current-full-', dir='/dev/shm') as scratch:
    root = Path(scratch)
    for label, base in [
        ('gist', '/home/ubuntu/project/vsag-lite-datasets/gist/prepared-10k-100k/scale-10000/base.fvecs'),
        ('cohere', '/home/ubuntu/project/vsag-lite-cohere-normalized-20261006/prepared/scale-10000/base.fvecs')]:
        data = root / label
        data.mkdir()
        shutil.copyfile(base, data / 'base.fvecs')
        for name in ['queries.fvecs', 'groundtruth.ivecs']:
            shutil.copyfile(inputs / (label + '-' + name), data / name)
        historical = json.loads((prior / (label + '10k600.dataset.json')).read_text())
        for name, info in historical.items():
            assert sha(data / name) == info['sha256'], (label, name)
    command = ['python3', 'lite/benchmark/prepare_sift.py',
        '/home/ubuntu/project/vsag-lite-datasets/sift/sift-128-euclidean.hdf5', root / 'sift',
        '--counts', '10000', '--queries', '600', '--query-offset', '400']
    subprocess.run(list(map(str, command)), cwd=repo, env=env, check=True)
    command = ['python3', 'lite/benchmark/run_aligned_comparison.py',
        '--lite-build', 'build-lite-fp16-simd-release', '--full-library', full / 'lib/libvsag.so',
        '--full-builder', repo / 'build-full-known-runner/full_rabitq_dataset_benchmark',
        '--full-loader', repo / 'build-full-known-runner/full_load_memory',
        '--dataset', 'sift10k600=' + str(root / 'sift/scale-10000'),
        '--dataset', 'gist10k600=' + str(root / 'gist'),
        '--dataset', 'cohere10k600=' + str(root / 'cohere'),
        '--storage', 'fp32', 'fp16', 'rabitq8', '--output', out,
        '--scratch', root, '--trials', '3', '--loads', '3', '--ef', '512', '--full-ef', '128', '--cpu', '0']
    subprocess.run(list(map(str, command)), cwd=repo, env=env, check=True)
    for label, data in [('sift', root / 'sift/scale-10000'), ('gist', root / 'gist'), ('cohere', root / 'cohere')]:
        for name in ['queries.fvecs', 'groundtruth.ivecs']:
            shutil.copyfile(data / name, out / (label + '10k600.' + name))
    (out / 'provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')
    shutil.copyfile(__file__, out / 'run-current-full.py')
print('complete54builders162loaders', flush=True)
