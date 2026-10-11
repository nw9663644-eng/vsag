#!/usr/bin/env python3
# Copyright 2024-present the vsag project
# SPDX-License-Identifier: Apache-2.0
"""Frozen SIFT100k real changed-value CRUD matrix, not a Full comparison."""
import csv
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            digest.update(block)
    return digest.hexdigest()


def main():
    repo = Path.cwd()
    output = repo / 'lite/benchmark/results/sift-production-100k-crud-20261011'
    output.mkdir(exist_ok=False)
    build = repo / 'build-lite-fp16-simd-release'
    builder = build / 'lite_graph_crud_quality'
    env = {key: value for key, value in os.environ.items() if not key.startswith('VSAG_')}
    env.update(OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1', MKL_NUM_THREADS='1',
               LD_LIBRARY_PATH=str(build),
               PYTHONPATH='/home/ubuntu/project/vsag-lite-datasets/cohere/python-deps:'
                          '/home/ubuntu/project/vsag-lite-datasets/sift/python-deps')
    identity = dict(head=subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode().strip(),
        library_sha256=sha(build / 'libvsag-lite.so'), builder_sha256=sha(builder),
        sources={name: sha(repo / name) for name in ['src/lite/rabitq_graph_state.h',
            'src/lite/rabitq_backend.cpp', 'src/lite/rabitq_snapshot.h',
            'lite/benchmark/graph_crud_quality.cpp', 'lite/benchmark/prepare_persistent_crud_100k.py']},
        configuration=dict(count=100000, queries=100, rounds=3, replacements=30000,
            api_calls_per_mode=90000, degree=16, build_ef=128, query_ef=512,
            k=10, cpu=0, trials=1, order=['fp32', 'fp16', 'rabitq8']))
    (output / 'identity.json').write_text(json.dumps(identity, indent=2) + '\n')
    for name in identity['sources']:
        shutil.copyfile(repo / name, output / ('source-' + Path(name).name))
    rows = []
    with tempfile.TemporaryDirectory(prefix='vsag-sift-crud-', dir='/dev/shm') as temporary:
        scratch = Path(temporary)
        with (output / 'prepare.txt').open('w') as log:
            subprocess.run(['taskset', '-c', '0', 'python3',
                'lite/benchmark/prepare_persistent_crud_100k.py', str(scratch / 'inputs'),
                '--datasets', 'sift100k100'], env=env, stdout=log, stderr=log, check=True)
        inputs = scratch / 'inputs/sift100k100'
        for name in ['queries.fvecs', 'groundtruth.ivecs', 'changed-groundtruth.ivecs', 'receipt.json']:
            shutil.copyfile(inputs / name, output / name)
        for mode in identity['configuration']['order']:
            snapshot = scratch / (mode + '.snapshot')
            selected = dict(env, VSAG_GRAPH_STORAGE=mode, VSAG_GRAPH_DEGREE='16',
                VSAG_GRAPH_EF='128', VSAG_GRAPH_QUERY_EF='512', VSAG_GRAPH_CRUD_MODE='all',
                VSAG_GRAPH_REPLACEMENTS=str(inputs / 'replacement.fvecs'))
            command = ['/usr/bin/time', '-f', '%M', '-o', str(output / (mode + '.peak_kib')),
                'taskset', '-c', '0', str(builder), str(inputs), str(snapshot), '3', '10000',
                str(output / (mode + '.queries.csv'))]
            (output / (mode + '.command.json')).write_text(json.dumps(
                dict(argv=command, environment={key: value for key, value in selected.items()
                    if key.startswith('VSAG_') or key in ['LD_LIBRARY_PATH', 'OPENBLAS_NUM_THREADS',
                                                        'OMP_NUM_THREADS', 'MKL_NUM_THREADS']}), indent=2) + '\n')
            with (output / (mode + '.stdout')).open('w') as stdout, (output / (mode + '.stderr')).open('w') as stderr:
                subprocess.run(command, env=selected, stdout=stdout, stderr=stderr, check=True)
            with (output / (mode + '.stdout')).open() as source:
                metrics = list(csv.DictReader(source))
            assert len(metrics) == 1
            row = dict(storage=mode, metrics=metrics[0], snapshot_sha256=sha(snapshot),
                       peak_kib=int((output / (mode + '.peak_kib')).read_text()))
            rows.append(row)
            (output / 'rows.json').write_text(json.dumps(rows, indent=2) + '\n')
            print(mode, json.dumps(row), flush=True)


if __name__ == '__main__':
    main()
