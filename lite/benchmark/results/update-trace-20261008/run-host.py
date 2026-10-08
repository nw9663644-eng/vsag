from pathlib import Path
import json,subprocess,os,hashlib,csv
root=Path(__file__).resolve().parent;repo=Path.cwd()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
record=next(r for r in json.loads(Path('/home/ubuntu/project/vsag-lite-persistent-20261007/prepared.json').read_text()) if r['dataset']=='gist')
(root/'prepared.json').write_text(json.dumps(record,indent=2)+'\n')
files=[repo/'lite/benchmark/graph_route_probe.cpp',repo/'lite/benchmark/test_persistent_update_probe.py',repo/'build-lite-fragment-release/lite_graph_route_probe']
for variant,dirname in [('baseline','build-lite-fragment-release'),('candidate','build-lite-diverse-repair-release')]:
 files.append(repo/dirname/'libvsag-lite.so')
(root/'identity.json').write_text(json.dumps({'parent':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'files':{str(p):sha(p) for p in files}},indent=2)+'\n')
runs=[]
for variant,dirname in [('baseline','build-lite-fragment-release'),('candidate','build-lite-diverse-repair-release')]:
 output=root/(variant+'.csv');env=dict(os.environ,LD_LIBRARY_PATH=str(repo/dirname))
 command=['taskset','-c','0',str(repo/'build-lite-fragment-release/lite_graph_route_probe'),'--persistent-update',record['snapshot'],'/home/ubuntu/project/vsag-lite-persistent-20261007/gist',str(output),'10000','trace']
 (root/(variant+'.ldd.log')).write_bytes(subprocess.check_output(['ldd',command[3]],env=env))
 with (root/(variant+'.log')).open('wb') as f:result=subprocess.run(command,env=env,stdout=f,stderr=subprocess.STDOUT)
 run={'variant':variant,'command':command,'exit':result.returncode};runs.append(run)
 (root/'runs.json').write_text(json.dumps(runs,indent=2)+'\n');assert result.returncode==0,(variant,(root/(variant+'.log')).read_text())
 run['summary']=next(csv.DictReader(output.open()));(root/'runs.json').write_text(json.dumps(runs,indent=2)+'\n');print(variant,run['summary'],flush=True)
