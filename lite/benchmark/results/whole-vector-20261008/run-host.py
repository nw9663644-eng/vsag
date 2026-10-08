from pathlib import Path
import json,hashlib,subprocess,os,struct,csv,shutil
root=Path(__file__).resolve().parent;repo=Path.cwd();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();infos=json.loads((root/'prepared.json').read_text());assert len(infos)==3
libs={'baseline':repo/'build-lite-fragment-release','candidate':repo/'build-lite-diverse-repair-release'}
files=[repo/'lite/benchmark/graph_route_probe.cpp',repo/'lite/benchmark/edge_restoration_probe.py',repo/'lite/benchmark/test_replacement_update_probe.py',repo/'build-lite-fragment-release/lite_graph_route_probe',repo/'build-lite-fragment-release/lite_graph_slot_probe']+[p/'libvsag-lite.so' for p in libs.values()]
(root/'identity.json').write_text(json.dumps({'parent':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'files':{str(p):sha(p) for p in files},'plan_sha256':sha(root/'plan.json')},indent=2)+'\n');traces=[];runs=[]
for info in infos:
 d=info['dataset'];controls=root/(d+'-control');controls.mkdir(exist_ok=False)
 shutil.copyfile(root/d/'queries.fvecs',controls/'queries.fvecs');shutil.copyfile(root/d/'changed-groundtruth.ivecs',controls/'groundtruth.ivecs')
 for variant,lib in libs.items():
  name=d+'-'+variant;out=root/(name+'.trace.csv');cmd=['taskset','-c','0',str(repo/'build-lite-fragment-release/lite_graph_route_probe'),'--replacement-update',info['snapshot'],str(root/d),str(out),'1000','trace'];env=dict(os.environ,LD_LIBRARY_PATH=str(lib))
  (root/(name+'.trace.ldd.log')).write_bytes(subprocess.check_output(['ldd',cmd[3]],env=env))
  with (root/(name+'.trace.log')).open('wb') as f:done=subprocess.run(cmd,env=env,stdout=f,stderr=subprocess.STDOUT)
  traces.append(dict(dataset=d,variant=variant,command=cmd,exit=done.returncode));(root/'traces.json').write_text(json.dumps(traces,indent=2)+'\n');assert done.returncode==0,(name,(root/(name+'.trace.log')).read_text())
  links=[[] for _ in range(100000)]
  for row in csv.DictReader(Path(str(out)+'.final-edges.csv').open()):
   a,rank,b=int(row['source']),int(row['rank']),int(row['target']);assert rank==len(links[a]);links[a].append(b)
  edges=root/(name+'.u32')
  with edges.open('wb') as f:
   for row in links:f.write(struct.pack('<'+'I'*(len(row)+1),len(row),*row))
  print(name,'native',next(csv.DictReader(out.open()))['changed_recall'],flush=True)
  for mask in [0,1]:
   label=name+'-'+str(mask);output=root/(label+'.csv');cmd=['taskset','-c','0','python3',str(repo/'lite/benchmark/edge_restoration_probe.py'),info['snapshot'],str(edges),str(controls),str(output),'1000',str(mask),str(repo/'build-lite-fragment-release/lite_graph_slot_probe'),'--replacement-vectors',str(root/d/'replacement.fvecs')];env=dict(os.environ,LD_LIBRARY_PATH=str(libs['baseline']))
   with (root/(label+'.log')).open('wb') as f:done=subprocess.run(cmd,env=env,stdout=f,stderr=subprocess.STDOUT)
   runs.append(dict(dataset=d,variant=variant,mask=mask,command=cmd,exit=done.returncode));(root/'runs.json').write_text(json.dumps(runs,indent=2)+'\n');assert done.returncode==0,(label,(root/(label+'.log')).read_text())
   states=[r for r in csv.DictReader(output.open()) if r['mask']=='0'];print(label,sum(int(r['hits']) for r in states)/(info['query_count']*10),flush=True)
