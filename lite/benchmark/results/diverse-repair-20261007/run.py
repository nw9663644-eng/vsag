from pathlib import Path
import csv, hashlib, json, os, statistics, subprocess
root=Path(__file__).resolve().parent
repo=Path('/home/ubuntu/project/vsag-lite-baseline-v01')
dataset=Path('/home/ubuntu/project/vsag-lite-cohere-normalized-20261006/prepared/scale-10000')
binary=repo/'build-lite-fragment-release/lite_graph_crud_quality'
libraries={'baseline':root/'before','candidate':repo/'build-lite-diverse-repair-release'}
def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
identity={'parent':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'files':{str(p):sha(p) for p in [binary,repo/'src/lite/graph_backend.cpp',repo/'src/lite/graph_backend_test.cpp',dataset/'base.fvecs',dataset/'queries.fvecs',dataset/'groundtruth.ivecs']},'library_sha256':{key:sha(path/'libvsag-lite.so') for key,path in libraries.items()}}
(root/'identity.json').write_text(json.dumps(identity,indent=2)+'\n')
for variant,directory in libraries.items():
 env=dict(os.environ,LD_LIBRARY_PATH=str(directory));(root/f'{variant}-ldd.log').write_text(subprocess.check_output(['ldd',str(binary)],env=env,text=True))
rows=[]
for repeat in range(3):
 for flow in (['build','crud'] if repeat%2==0 else ['crud','build']):
  for variant in (['baseline','candidate'] if repeat%2==0 else ['candidate','baseline']):
   stem=f'{variant}-{flow}-r{repeat}';snapshot=root/f'{stem}.snapshot';hits=root/f'{stem}.hits.csv'
   cmd=['/usr/bin/time','-f','%U,%S','-o',str(root/f'{stem}.time.csv'),'taskset','-c','0',str(binary),str(dataset),str(snapshot),'0' if flow=='build' else '1','10000',str(hits)]
   env=dict(os.environ,LD_LIBRARY_PATH=str(libraries[variant]))
   with (root/f'{stem}.stdout.csv').open('wb') as out,(root/f'{stem}.stderr.log').open('wb') as err:result=subprocess.run(cmd,cwd=repo,env=env,stdout=out,stderr=err)
   row=dict(variant=variant,flow=flow,repeat=repeat,command=cmd,library_path=str(libraries[variant]),exit=result.returncode)
   assert result.returncode==0,(row,(root/f'{stem}.stderr.log').read_text())
   row['metrics']=next(csv.DictReader((root/f'{stem}.stdout.csv').open()))
   user,system=map(float,(root/f'{stem}.time.csv').read_text().strip().split(','));row['whole_cpu_s']=user+system
   row['snapshot_sha256']=sha(snapshot);row['hits_sha256']=sha(hits)
   rows.append(row);(root/'runs.json').write_text(json.dumps(rows,indent=2)+'\n')
   print(stem,row['metrics']['recall_at_k'],row['whole_cpu_s'],flush=True)
summary=[]
for flow in ['build','crud']:
 for variant in libraries:
  selected=[r for r in rows if r['flow']==flow and r['variant']==variant]
  assert len(selected)==3
  summary.append(dict(flow=flow,variant=variant,recalls=[float(r['metrics']['recall_at_k']) for r in selected],median_whole_cpu_s=statistics.median(r['whole_cpu_s'] for r in selected)))
(root/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(summary,flush=True)
