# Copyright 2024-present the vsag project
# SPDX-License-Identifier: Apache-2.0
"""Isolated no-filter routing specialization; no production-source modification."""
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
build = repo / 'build-lite-fp16-simd-release'
out = repo / 'lite/benchmark/results/rabitq-no-filter-20261011'
out.mkdir(exist_ok=False)

def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            digest.update(block)
    return digest.hexdigest()

commands = []
def run(tag, argv, env):
    result = subprocess.run(list(map(str, argv)), cwd=repo, env=env, text=True, capture_output=True)
    commands.append(dict(tag=tag, argv=list(map(str, argv)), exit=result.returncode))
    (out / (tag + '.stdout')).write_text(result.stdout)
    (out / (tag + '.stderr')).write_text(result.stderr)
    (out / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
    result.check_returncode()

env = {key: value for key, value in os.environ.items() if not key.startswith('VSAG_')}
env.update(LD_LIBRARY_PATH=str(build), OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1',
    VSAG_GRAPH_STORAGE='rabitq8', VSAG_GRAPH_DEGREE='16', VSAG_GRAPH_EF='128', VSAG_GRAPH_QUERY_EF='512')
identity = dict(head=subprocess.check_output(['git','rev-parse','HEAD'], cwd=repo, text=True).strip(),
    library_sha256=sha(build / 'libvsag-lite.so'), archive_sha256=sha(build / 'libvsag-lite.a'),
    sources={}, inputs={}, snapshots={}, executables={}, trials=7,
    scope='internal SearchWithOptions; initial snapshot; 100 historical queries; CPU0; one warmup; not Full/CRUD/final P99 acceptance')
rows = []
with tempfile.TemporaryDirectory(prefix='vsag-no-filter-', dir='/dev/shm') as directory:
    scratch = Path(directory)
    overlay = scratch / 'overlay'
    (overlay / 'lite').mkdir(parents=True)
    original = (repo / 'src/lite/rabitq_graph_state.h').read_text()
    begin = original.index('inline GraphSearchResult\ngraph_search_impl(')
    end = original.index('inline GraphSearchResult\ngraph_search(', begin)
    body = original[begin:end]
    assert body.count('if (filter and filter(') == 1 and body.count('if (filter) {') == 1
    body = body.replace('if (filter and filter(', 'if (evaluate_filter and filter and filter(')
    body = body.replace('if (filter) {', 'if (evaluate_filter and filter) {')
    prefix = original[:begin]
    marker = '          bool packed_visited = false>'
    assert prefix.count(marker) == 1
    prefix = prefix.replace(marker, '          bool packed_visited = false,\n          bool evaluate_filter = true>')
    candidate = prefix + body + original[end:]
    marker = '    // Select once per query: small graphs retain byte checks without per-slot policy branches.'
    assert candidate.count(marker) == 1
    candidate = candidate.replace(marker, '''    if (not filter) {
        if (codes.Size() >= 65536) {
            return graph_search_impl<decltype(range), true, true, true, true, false>(
                query, query_norm, codes, range, k, ef_search, external_ids, filter);
        }
        return graph_search_impl<decltype(range), true, true, true, false, false>(
            query, query_norm, codes, range, k, ef_search, external_ids, filter);
    }
''' + marker)
    (overlay / 'lite/rabitq_graph_state.h').write_text(candidate)
    (out / 'control-rabitq_graph_state.h').write_text(original)
    (out / 'candidate-rabitq_graph_state.h').write_text(candidate)
    run('format-overlay', ['clang-format-15', '-style=file:' + str(repo / '.clang-format'), '--dry-run', '--Werror', overlay / 'lite/rabitq_graph_state.h'], env)
    source = repo / 'lite/benchmark/rabitq_full_route_probe.cpp'
    for name in ['src/lite/rabitq_graph_state.h','src/lite/query_heap.h','src/lite/rabitq_snapshot.h',
                 'lite/benchmark/rabitq_full_route_probe.cpp','lite/benchmark/run_rabitq_no_filter.py',
                 'src/impl/searcher/basic_searcher.cpp','src/simd/kernels/rabitq_compute.h']:
        identity['sources'][name] = sha(repo / name)
        shutil.copyfile(repo / name, out / ('source-' + Path(name).name))
    for variant in ['control','candidate']:
        argv = ['c++','-O3','-DNDEBUG','-std=c++17','-DVSAG_LITE_RABITQ_X86_SIMD']
        if variant == 'candidate':
            argv += ['-I' + str(overlay)]
        argv += ['-Isrc','-Iinclude',source,build / 'libvsag-lite.a','-o',scratch / variant]
        run('compile-' + variant, argv, env)
        identity['executables'][variant] = sha(scratch / variant)
    for label, count, location in [
        ('gist100k',100000,'/home/ubuntu/project/vsag-lite-datasets/gist/prepared-10k-100k/scale-100000'),
        ('sift10k',10000,'/home/ubuntu/project/vsag-lite-datasets/sift/prepared-10k-100k/scale-10000'),
        ('gist10k',10000,'/home/ubuntu/project/vsag-lite-datasets/gist/prepared-10k-100k/scale-10000'),
        ('cohere10k',10000,'/home/ubuntu/project/vsag-lite-cohere-normalized-20261006/prepared/scale-10000')]:
        data = Path(location)
        identity['inputs'][label] = dict(count=count, hashes={name: sha(data / name) for name in ['base.fvecs','queries.fvecs','groundtruth.ivecs']})
        for name in ['queries.fvecs','groundtruth.ivecs']:
            shutil.copyfile(data / name, out / (label + '.' + name))
        snapshot = scratch / (label + '.snapshot')
        run(label + '-prepare', ['taskset','-c','0',build / 'lite_graph_crud_quality',data,snapshot,'0','1',out / (label + '-prepare.csv')], env)
        identity['snapshots'][label] = dict(sha256=sha(snapshot), bytes=snapshot.stat().st_size)
        run(label + '-native-parity', ['taskset','-c','0',scratch / 'control',snapshot,data / 'queries.fvecs',data / 'groundtruth.ivecs',out / (label + '-native-parity'),'1'], env)
        reference = (out / (label + '-native-parity.neighbors.csv')).read_bytes()
        for trial in range(7):
            for variant in (['control','candidate'] if trial % 2 == 0 else ['candidate','control']):
                tag = f'{label}-{trial}-{variant}'
                run(tag, ['taskset','-c','0',scratch / variant,snapshot,data / 'queries.fvecs',data / 'groundtruth.ivecs',out / tag,'0'], env)
                assert (out / (tag + '.neighbors.csv')).read_bytes() == reference
                with (out / (tag + '.queries.csv')).open() as stream:
                    queries = list(csv.DictReader(stream))
                assert len(queries) == 100
                latency = sorted(float(q['latency_us']) for q in queries)
                rows.append(dict(dataset=label,trial=trial,variant=variant,recall=sum(int(q['hits']) for q in queries) / 1000,
                    p50_us=latency[49],p99_us=latency[98],average_visited=sum(int(q['visited']) for q in queries) / 100))
                (out / 'rows.json').write_text(json.dumps(rows, indent=2) + '\n')
        (out / 'identity.json').write_text(json.dumps(identity, indent=2) + '\n')
        print(label, {v: {key: statistics.median(row[key] for row in rows if row['dataset']==label and row['variant']==v)
            for key in ['p50_us','p99_us','recall']} for v in ['control','candidate']}, flush=True)
print('complete56runs5600queries', flush=True)
