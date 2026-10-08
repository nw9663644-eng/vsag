from pathlib import Path
import json,os,subprocess,hashlib,shutil,csv
root=Path(__file__).resolve().parent;repo=Path.cwd();previous=Path('/home/ubuntu/project/vsag-lite-update-trace-20261008')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
info=json.loads((previous/'prepared.json').read_text());(root/'prepared.json').write_text(json.dumps(info,indent=2)+'\n')
shutil.copyfile(previous/'queries.fvecs',root/'dataset/queries.fvecs');shutil.copyfile(previous/'changed-groundtruth.ivecs',root/'dataset/groundtruth.ivecs')
files=[repo/'lite/benchmark/edge_restoration_probe.py',repo/'lite/benchmark/test_edge_restoration_probe.py',repo/'lite/benchmark/graph_slot_probe.cpp',repo/'lite/benchmark/graph_route_probe.cpp',repo/'build-lite-fragment-release/lite_graph_slot_probe',repo/'build-lite-fragment-release/libvsag-lite.so']
(root/'identity.json').write_text(json.dumps({'parent':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'files':{str(p):sha(p) for p in files}},indent=2)+'\n')
env=dict(os.environ,LD_LIBRARY_PATH=str(repo/'build-lite-fragment-release'))
(root/'ldd.log').write_bytes(subprocess.check_output(['ldd',str(repo/'build-lite-fragment-release/lite_graph_slot_probe')],env=env))
runs=[]
for variant in ['baseline','candidate']:
 edges=previous/(variant+'.csv.final-edges.csv.u32')
 for mask in range(4):
  name=variant+'-'+str(mask);output=root/(name+'.csv')
  command=['taskset','-c','0','python3',str(repo/'lite/benchmark/edge_restoration_probe.py'),info['snapshot'],str(edges),str(root/'dataset'),str(output),'10000',str(mask),str(repo/'build-lite-fragment-release/lite_graph_slot_probe')]
  with (root/(name+'.log')).open('wb') as f:done=subprocess.run(command,env=env,stdout=f,stderr=subprocess.STDOUT)
  record=dict(variant=variant,mask=mask,command=command,exit=done.returncode);runs.append(record);(root/'runs.json').write_text(json.dumps(runs,indent=2)+'\n')
  assert done.returncode==0,(name,(root/(name+'.log')).read_text())
  rows=[r for r in csv.DictReader(output.open()) if r['mask']=='0']
  print(name,'recall',sum(int(r['hits']) for r in rows)/1000,'visited',sum(int(r['visited_nodes']) for r in rows)/100,flush=True)
