from pathlib import Path
import json,hashlib,subprocess,os,struct,csv
root=Path(__file__).resolve().parent;repo=Path.cwd();old=Path('/home/ubuntu/project/vsag-lite-persistent-20261007');gist=Path('/home/ubuntu/project/vsag-lite-update-trace-20261008')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert (root/'gist-prepared.json').is_file()
records=[dict(r,query_count=100) for r in json.loads((old/'prepared.json').read_text()) if r['dataset'] in ['sift','cohere']]+[json.loads((root/'gist-prepared.json').read_text())]
(root/'prepared.json').write_text(json.dumps(records,indent=2)+'\n')
libs={'baseline':repo/'build-lite-fragment-release','candidate':repo/'build-lite-diverse-repair-release'}
files=[repo/'lite/benchmark/edge_restoration_probe.py',repo/'lite/benchmark/graph_route_probe.cpp',repo/'lite/benchmark/graph_slot_probe.cpp',repo/'build-lite-fragment-release/lite_graph_route_probe',repo/'build-lite-fragment-release/lite_graph_slot_probe']+[p/'libvsag-lite.so' for p in libs.values()]
(root/'identity.json').write_text(json.dumps({'parent':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'files':{str(p):sha(p) for p in files},'plan_sha256':sha(root/'plan.json')},indent=2)+'\n')
traces=json.loads((root/'traces.json').read_text()) if (root/'traces.json').exists() else []
runs=json.loads((root/'runs.json').read_text()) if (root/'runs.json').exists() else []
for info in records:
 dataset=info['dataset']
 for variant,lib in libs.items():
  if dataset!='gist-supplement':
   name=dataset+'-'+variant;output=root/(name+'.trace.csv')
   if not any(r['dataset']==dataset and r['variant']==variant and r['exit']==0 for r in traces):
    cmd=['taskset','-c','0',str(repo/'build-lite-fragment-release/lite_graph_route_probe'),'--persistent-update',info['snapshot'],str(old/dataset),str(output),'10000','trace']
    env=dict(os.environ,LD_LIBRARY_PATH=str(lib))
    (root/(name+'.trace.ldd.log')).write_bytes(subprocess.check_output(['ldd',cmd[3]],env=env))
    with (root/(name+'.trace.log')).open('wb') as f:done=subprocess.run(cmd,env=env,stdout=f,stderr=subprocess.STDOUT)
    traces.append(dict(dataset=dataset,variant=variant,command=cmd,exit=done.returncode));(root/'traces.json').write_text(json.dumps(traces,indent=2)+'\n');assert done.returncode==0,name
   edges=root/(name+'.u32')
   links=[[] for _ in range(100000)]
   for row in csv.DictReader(Path(str(output)+'.final-edges.csv').open()):
    a,rank,b=int(row['source']),int(row['rank']),int(row['target']);assert rank==len(links[a]);links[a].append(b)
   with edges.open('wb') as f:
    for row in links:f.write(struct.pack('<'+'I'*(len(row)+1),len(row),*row))
   print('trace',name,'done',flush=True)
  else:edges=gist/(variant+'.csv.final-edges.csv.u32')
  data=(old/dataset if dataset!='gist-supplement' else root/dataset)
  if dataset!='gist-supplement':
   data=root/dataset;data.mkdir(exist_ok=True)
   import shutil
   for source,target in [(old/dataset/'queries.fvecs',data/'queries.fvecs'),(old/dataset/'changed-groundtruth.ivecs',data/'groundtruth.ivecs')]:
    if target.exists():assert sha(source)==sha(target)
    else:shutil.copyfile(source,target)
  for mask in [0,1]:
   name=dataset+'-'+variant+'-'+str(mask);output=root/(name+'.csv')
   if any(r['dataset']==dataset and r['variant']==variant and r['mask']==mask and r['exit']==0 for r in runs):
    assert Path(str(output)+'.receipt.json').is_file();print('reuse',name,flush=True);continue
   cmd=['taskset','-c','0','python3',str(repo/'lite/benchmark/edge_restoration_probe.py'),info['snapshot'],str(edges),str(data),str(output),'10000',str(mask),str(repo/'build-lite-fragment-release/lite_graph_slot_probe')]
   env=dict(os.environ,LD_LIBRARY_PATH=str(libs['baseline']))
   with (root/(name+'.log')).open('wb') as f:done=subprocess.run(cmd,env=env,stdout=f,stderr=subprocess.STDOUT)
   runs.append(dict(dataset=dataset,variant=variant,mask=mask,command=cmd,exit=done.returncode));(root/'runs.json').write_text(json.dumps(runs,indent=2)+'\n');assert done.returncode==0,name
   rows=[r for r in csv.DictReader(output.open()) if r['mask']=='0'];print(name,sum(int(r['hits']) for r in rows)/(info['query_count']*10),flush=True)
