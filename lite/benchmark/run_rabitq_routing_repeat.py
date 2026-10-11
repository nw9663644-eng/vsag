# Copyright 2024-present the vsag project
# SPDX-License-Identifier: Apache-2.0
"""Longer GIST100k windows:100 historical queries repeated ten times, not1000 unique queries."""
import csv
import hashlib
import json
import os
from pathlib import Path
import shutil
import statistics
import subprocess
import tempfile

repo=Path('/home/ubuntu/project/vsag-lite-baseline-v01')
build=repo / 'build-lite-fp16-simd-release'
out=repo / 'lite/benchmark/results/rabitq-routing-repeat-20261011'
out.mkdir(exist_ok=False)
data=Path('/home/ubuntu/project/vsag-lite-datasets/gist/prepared-10k-100k/scale-100000')
libraries=dict(control=Path('/home/ubuntu/project/vsag-nofilter-control-9c44640'),candidate=build,
               reference=Path('/home/ubuntu/project/vsag-root-control-c55466b'))
def sha(path):
    digest=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1048576),b''):
            digest.update(block)
    return digest.hexdigest()
env={k:v for k,v in os.environ.items() if not k.startswith('VSAG_')}
env.update(LD_LIBRARY_PATH=str(build),OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',
           VSAG_GRAPH_STORAGE='rabitq8',VSAG_GRAPH_DEGREE='16',VSAG_GRAPH_EF='128',VSAG_GRAPH_QUERY_EF='512')
identity=dict(head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip(),
    libraries={v:dict(path=str(p),sha256=sha(p / 'libvsag-lite.so')) for v,p in libraries.items()},
    sources={},inputs={name:sha(data / name) for name in ['base.fvecs','queries.fvecs','groundtruth.ivecs']},
    scope='public API; CPU0; 7 rotating-order triples; 100 historical queries repeated ten times; not1000 unique queries')
commands=[]
rows=[]
def run(tag,argv,current):
    result=subprocess.run(list(map(str,argv)),cwd=repo,env=current,capture_output=True,text=True)
    commands.append(dict(tag=tag,argv=list(map(str,argv)),exit=result.returncode,ld_library_path=current['LD_LIBRARY_PATH']))
    (out / (tag+'.stdout')).write_text(result.stdout)
    (out / (tag+'.stderr')).write_text(result.stderr)
    (out / 'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
    result.check_returncode()
for name in ['src/lite/rabitq_graph_state.h','src/lite/query_heap.h','src/lite/query_visited.h',
             'lite/benchmark/query_repeat_window_probe.cpp','lite/benchmark/run_rabitq_routing_repeat.py']:
    identity['sources'][name]=sha(repo / name)
    shutil.copyfile(repo / name,out / ('source-'+Path(name).name))
for name in ['queries.fvecs','groundtruth.ivecs']:
    shutil.copyfile(data / name,out / name)
with tempfile.TemporaryDirectory(prefix='vsag-route-repeat-',dir='/dev/shm') as directory:
    scratch=Path(directory)
    run('compile',['c++','-O3','-DNDEBUG','-std=c++17','-Iinclude','lite/benchmark/query_repeat_window_probe.cpp',
         '-L'+str(build),'-lvsag-lite','-o',scratch / 'probe'],env)
    snapshot=scratch / 'snapshot'
    run('prepare',['taskset','-c','0',build / 'lite_graph_crud_quality',data,snapshot,'0','1',out / 'native.csv'],env)
    identity['snapshot']=dict(sha256=sha(snapshot),bytes=snapshot.stat().st_size)
    reference=(out / 'native.csv.neighbors.csv').read_bytes().splitlines()[1:]
    for trial in range(7):
        order=['control','candidate','reference']
        order=order[trial%3:]+order[:trial%3]
        if trial%2:
            order.reverse()
        for variant in order:
            tag=f'{trial}-{variant}'
            run(tag,['taskset','-c','0',scratch / 'probe',snapshot,data / 'queries.fvecs',
                out / (tag+'.queries.csv'),out / (tag+'.neighbors.csv')],dict(env,LD_LIBRARY_PATH=str(libraries[variant])))
            with (out / (tag+'.queries.csv')).open() as stream:
                times=[float(row['latency_us']) for row in csv.DictReader(stream)]
            with (out / (tag+'.neighbors.csv')).open() as stream:
                neighbors=list(csv.DictReader(stream))
            assert len(times)==1000 and len(neighbors)==10000
            for index,item in enumerate(neighbors):
                expected=reference[index%1000].decode().split(',')
                assert int(item['query'])==index//10 and int(item['rank'])==index%10
                assert [item['id'],item['distance']]==expected[2:]
            ordered=sorted(times)
            rows.append(dict(trial=trial,variant=variant,mean_us=statistics.mean(times),
                p50_us=ordered[499],p99_us=ordered[989]))
            (out / 'rows.json').write_text(json.dumps(rows,indent=2)+'\n')
    (out / 'identity.json').write_text(json.dumps(identity,indent=2)+'\n')
print({v:{key:statistics.median(r[key] for r in rows if r['variant']==v) for key in ['mean_us','p50_us','p99_us']} for v in libraries},flush=True)
