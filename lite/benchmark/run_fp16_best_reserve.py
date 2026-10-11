# Copyright 2024-present the vsag project
# SPDX-License-Identifier: Apache-2.0
"""Isolate FP16 best-heap reserve by replacing a scratch static-archive member."""
import csv
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import statistics
import subprocess
import tempfile

repo = Path('/home/ubuntu/project/vsag-lite-baseline-v01')
build = repo / 'build-lite-fp16-simd-release'
out = repo / 'lite/benchmark/results/fp16-best-reserve-20261011'
out.mkdir(exist_ok=False)

def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            digest.update(block)
    return digest.hexdigest()

commands = []
def run(tag, argv, env, cwd=repo):
    result = subprocess.run(list(map(str, argv)), cwd=cwd, env=env, text=True, capture_output=True)
    commands.append(dict(tag=tag,argv=list(map(str, argv)),cwd=str(cwd),exit=result.returncode))
    (out / (tag + '.stdout')).write_text(result.stdout)
    (out / (tag + '.stderr')).write_text(result.stderr)
    (out / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
    result.check_returncode()

env = {key: value for key, value in os.environ.items() if not key.startswith('VSAG_')}
env.update(LD_LIBRARY_PATH=str(build),OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',
    VSAG_GRAPH_STORAGE='fp16',VSAG_GRAPH_DEGREE='16',VSAG_GRAPH_EF='128',VSAG_GRAPH_QUERY_EF='512')
identity = dict(head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip(),
    library_sha256=sha(build / 'libvsag-lite.so'),archive_sha256=sha(build / 'libvsag-lite.a'),
    sources={},inputs={},snapshots={},executables={},trials=7,
    scope='public SearchWithOptions; initial snapshot; 100 historical queries; CPU0; one warmup; not Full/CRUD/final P99 acceptance')
rows = []
with tempfile.TemporaryDirectory(prefix='vsag-fp16-best-reserve-',dir='/dev/shm') as directory:
    scratch = Path(directory)
    original = (repo / 'src/lite/graph_backend.cpp').read_text()
    marker = '            QueryHeap<Candidate, Closer> best;'
    assert original.count(marker) == 1
    replacement = ('            std::vector<Candidate> best_storage;\n'
        '            best_storage.reserve(ef + static_cast<uint64_t>(ef < Size()));\n'
        '            QueryHeap<Candidate, Closer> best(Closer{}, std::move(best_storage));')
    candidate = original.replace(marker,replacement)
    candidate_source = scratch / 'graph_backend.cpp'
    candidate_source.write_text(candidate)
    (out / 'control-graph_backend.cpp').write_text(original)
    (out / 'candidate-graph_backend.cpp').write_text(candidate)
    source = repo / 'lite/benchmark/query_heap_reserve_probe.cpp'
    run('format',['clang-format-15','-i',source],env)
    for name in ['src/lite/graph_backend.cpp','src/lite/query_heap.h','lite/benchmark/query_heap_reserve_probe.cpp',
                 'lite/benchmark/run_fp16_best_reserve.py']:
        identity['sources'][name] = sha(repo / name)
        shutil.copyfile(repo / name,out / ('source-' + Path(name).name))
    compile_db = json.loads((build / 'compile_commands.json').read_text())
    entry = [row for row in compile_db if row['file'] == str(repo / 'src/lite/graph_backend.cpp')]
    assert len(entry) == 1
    entry = entry[0]
    (out / 'compile-entry.json').write_text(json.dumps(entry,indent=2) + '\n')
    argv = shlex.split(entry['command'])
    argv[argv.index('-o')+1] = str(scratch / 'graph_backend.cpp.o')
    argv[argv.index('-c')+1] = str(candidate_source)
    run('compile-object',argv,env,Path(entry['directory']))
    candidate_archive = scratch / 'libcandidate.a'
    shutil.copyfile(build / 'libvsag-lite.a',candidate_archive)
    run('replace-member',['ar','r',candidate_archive,scratch / 'graph_backend.cpp.o'],env)
    run('archive-members',['ar','t',candidate_archive],env)
    assert (out / 'archive-members.stdout').read_text().splitlines().count('graph_backend.cpp.o') == 1
    identity['candidate_archive_sha256'] = sha(candidate_archive)
    for variant in ['control','candidate']:
        archive = build / 'libvsag-lite.a' if variant == 'control' else candidate_archive
        run('compile-' + variant,['c++','-O3','-DNDEBUG','-std=c++17','-Iinclude',source,archive,'-o',scratch / variant],env)
        identity['executables'][variant] = sha(scratch / variant)
    for label,count,location in [
        ('sift10k',10000,'/home/ubuntu/project/vsag-lite-datasets/sift/prepared-10k-100k/scale-10000'),
        ('gist10k',10000,'/home/ubuntu/project/vsag-lite-datasets/gist/prepared-10k-100k/scale-10000'),
        ('cohere10k',10000,'/home/ubuntu/project/vsag-lite-cohere-normalized-20261006/prepared/scale-10000'),
        ('gist100k',100000,'/home/ubuntu/project/vsag-lite-datasets/gist/prepared-10k-100k/scale-100000')]:
        data = Path(location)
        identity['inputs'][label] = dict(count=count,hashes={name:sha(data / name) for name in ['base.fvecs','queries.fvecs','groundtruth.ivecs']})
        for name in ['queries.fvecs','groundtruth.ivecs']:
            shutil.copyfile(data / name,out / (label + '.' + name))
        snapshot = scratch / (label + '.snapshot')
        run(label + '-prepare',['taskset','-c','0',build / 'lite_graph_crud_quality',data,snapshot,'0','1',out / (label + '-prepare.csv')],env)
        identity['snapshots'][label] = dict(sha256=sha(snapshot),bytes=snapshot.stat().st_size)
        reference = (out / (label + '-prepare.csv.neighbors.csv')).read_bytes()
        for trial in range(7):
            for variant in (['control','candidate'] if trial%2 == 0 else ['candidate','control']):
                tag = f'{label}-{trial}-{variant}'
                run(tag,['taskset','-c','0',scratch / variant,snapshot,data / 'queries.fvecs',out / (tag + '.queries.csv'),out / (tag + '.neighbors.csv')],env)
                assert (out / (tag + '.neighbors.csv')).read_bytes() == reference
                with (out / (tag + '.queries.csv')).open() as stream:
                    queries = list(csv.DictReader(stream))
                assert len(queries) == 100
                times = sorted(float(q['latency_us']) for q in queries)
                rows.append(dict(dataset=label,trial=trial,variant=variant,p50_us=times[49],p99_us=times[98]))
                (out / 'rows.json').write_text(json.dumps(rows,indent=2) + '\n')
        (out / 'identity.json').write_text(json.dumps(identity,indent=2) + '\n')
        print(label,{v:{key:statistics.median(r[key] for r in rows if r['dataset']==label and r['variant']==v)
            for key in ['p50_us','p99_us']} for v in ['control','candidate']},flush=True)
    assert sha(build / 'libvsag-lite.a') == identity['archive_sha256']
print('complete56runs5600queries',flush=True)
