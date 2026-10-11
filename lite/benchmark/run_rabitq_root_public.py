# Copyright 2024-present the vsag project
# SPDX-License-Identifier: Apache-2.0
"""Compare actual shared-library small-graph best-heap replacement."""
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
control = Path('/home/ubuntu/project/vsag-root-control-c55466b')
out = repo / 'lite/benchmark/results/rabitq-root-public-20261011'
out.mkdir(exist_ok=False)

def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576),b''):
            digest.update(block)
    return digest.hexdigest()

commands = []
def run(tag,argv,env):
    result = subprocess.run(list(map(str,argv)),cwd=repo,env=env,text=True,capture_output=True)
    commands.append(dict(tag=tag,argv=list(map(str,argv)),exit=result.returncode,
        ld_library_path=env['LD_LIBRARY_PATH']))
    (out / (tag+'.stdout')).write_text(result.stdout)
    (out / (tag+'.stderr')).write_text(result.stderr)
    (out / 'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
    result.check_returncode()

env = {k:v for k,v in os.environ.items() if not k.startswith('VSAG_')}
env.update(LD_LIBRARY_PATH=str(build),OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',
    VSAG_GRAPH_DEGREE='16',VSAG_GRAPH_EF='128',VSAG_GRAPH_QUERY_EF='512')
identity = dict(head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip(),
    libraries={v:dict(path=str(p),sha256=sha(p / 'libvsag-lite.so')) for v,p in [('control',control),('candidate',build)]},
    sources={},inputs={},snapshots={},trials=7,scope='public SearchWithOptions; CPU0; initial snapshots; 100 historical queries and one warmup; allocation runs separate from timing')
rows = []
allocations = []
with tempfile.TemporaryDirectory(prefix='vsag-visited-bitmap-',dir='/dev/shm') as directory:
    scratch = Path(directory)
    for name in ['src/lite/query_visited.h','src/lite/query_heap.h','src/lite/graph_backend.cpp','src/lite/rabitq_graph_state.h',
        'src/lite/graph_backend_test.cpp','lite/benchmark/query_heap_reserve_probe.cpp',
        'lite/benchmark/query_allocation_probe.cpp','lite/benchmark/run_rabitq_root_public.py','src/impl/heap/standard_heap.cpp']:
        identity['sources'][name]=sha(repo / name)
        shutil.copyfile(repo / name,out / ('source-'+Path(name).name))
    for tag,source in [('timing','query_heap_reserve_probe.cpp'),('allocation','query_allocation_probe.cpp')]:
        run('compile-'+tag,['c++','-O3','-DNDEBUG','-std=c++17','-Wl,--export-dynamic','-Iinclude',
            repo / 'lite/benchmark' / source,'-L'+str(build),'-lvsag-lite','-o',scratch / tag],env)
    for label,count,location in [
        ('sift10k',10000,'/home/ubuntu/project/vsag-lite-datasets/sift/prepared-10k-100k/scale-10000'),
        ('gist10k',10000,'/home/ubuntu/project/vsag-lite-datasets/gist/prepared-10k-100k/scale-10000'),
        ('cohere10k',10000,'/home/ubuntu/project/vsag-lite-cohere-normalized-20261006/prepared/scale-10000'),
        ('gist100k',100000,'/home/ubuntu/project/vsag-lite-datasets/gist/prepared-10k-100k/scale-100000')]:
        data=Path(location)
        identity['inputs'][label]=dict(count=count,hashes={n:sha(data / n) for n in ['base.fvecs','queries.fvecs','groundtruth.ivecs']})
        for name in ['queries.fvecs','groundtruth.ivecs']:
            shutil.copyfile(data / name,out / (label+'.'+name))
        for storage in ['rabitq8']:
            cell=label+'-'+storage
            snapshot=scratch / (cell+'.snapshot')
            current=dict(env,VSAG_GRAPH_STORAGE=storage)
            run(cell+'-prepare',['taskset','-c','0',build / 'lite_graph_crud_quality',data,snapshot,'0','1',out / (cell+'-native.csv')],current)
            identity['snapshots'][cell]=dict(sha256=sha(snapshot),bytes=snapshot.stat().st_size)
            reference=(out / (cell+'-native.csv.neighbors.csv')).read_bytes()
            for variant,path in [('control',control),('candidate',build)]:
                tag=cell+'-'+variant+'-allocation'
                run(tag,['taskset','-c','0',scratch / 'allocation',snapshot,data / 'queries.fvecs',
                    out / (tag+'.csv'),out / (tag+'.neighbors.csv')],dict(current,LD_LIBRARY_PATH=str(path)))
                assert (out / (tag+'.neighbors.csv')).read_bytes()==reference
                with (out / (tag+'.csv')).open() as stream:
                    counts=list(csv.DictReader(stream))
                allocations.append(dict(dataset=label,storage=storage,variant=variant,
                    median_requests=statistics.median(int(q['ordinary_new_requests']) for q in counts),
                    median_bytes=statistics.median(int(q['ordinary_new_bytes']) for q in counts)))
            for trial in range(7):
                for variant in (['control','candidate'] if trial%2==0 else ['candidate','control']):
                    tag=f'{cell}-{trial}-{variant}'
                    path=control if variant=='control' else build
                    run(tag,['taskset','-c','0',scratch / 'timing',snapshot,data / 'queries.fvecs',
                        out / (tag+'.queries.csv'),out / (tag+'.neighbors.csv')],dict(current,LD_LIBRARY_PATH=str(path)))
                    assert (out / (tag+'.neighbors.csv')).read_bytes()==reference
                    with (out / (tag+'.queries.csv')).open() as stream:
                        times=sorted(float(q['latency_us']) for q in csv.DictReader(stream))
                    assert len(times)==100
                    rows.append(dict(dataset=label,storage=storage,trial=trial,variant=variant,p50_us=times[49],p99_us=times[98]))
            (out / 'identity.json').write_text(json.dumps(identity,indent=2)+'\n')
            (out / 'rows.json').write_text(json.dumps(rows,indent=2)+'\n')
            (out / 'allocations.json').write_text(json.dumps(allocations,indent=2)+'\n')
            print(cell,{v:statistics.median(r['p50_us'] for r in rows if r['dataset']==label and r['storage']==storage and r['variant']==v) for v in ['control','candidate']},allocations[-2:],flush=True)
print('complete4cells56timedruns',flush=True)
