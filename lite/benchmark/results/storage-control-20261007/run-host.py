from pathlib import Path
import json,os,subprocess,hashlib,csv
root=Path(__file__).resolve().parent;repo=Path.cwd();previous_root=Path('/home/ubuntu/project/vsag-lite-persistent-20261007')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
libraries={'baseline':repo/'build-lite-fragment-release','candidate':repo/'build-lite-diverse-repair-release'}
previous=json.loads((repo/'lite/benchmark/results/diverse-repair-20261007/identity.json').read_text())['library_sha256']
assert all(sha(p/'libvsag-lite.so')==previous[v] for v,p in libraries.items())
identity={'parent':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'files':{},'libraries':{v:sha(p/'libvsag-lite.so') for v,p in libraries.items()}}
for name in ['lite/benchmark/graph_route_probe.cpp','lite/benchmark/test_persistent_update_probe.py','build-lite-fragment-release/lite_graph_route_probe']:
    p=repo/name;identity['files'][str(p)]=sha(p)
(root/'identity.json').write_text(json.dumps(identity,indent=2)+'\n')
runs=[]
for record in json.loads((previous_root/'prepared.json').read_text()):
    dataset=record['dataset']
    for variant,lib in libraries.items():
        name=dataset+'-'+variant;output=root/(name+'.csv')
        command=['taskset','-c','0',str(repo/'build-lite-fragment-release/lite_graph_route_probe'),'--storage-only-update',record['snapshot'],str(previous_root/dataset),str(output),'10000']
        env=dict(os.environ,LD_LIBRARY_PATH=str(lib))
        (root/(name+'.ldd.log')).write_bytes(subprocess.check_output(['ldd',str(repo/'build-lite-fragment-release/lite_graph_route_probe')],env=env))
        with (root/(name+'.log')).open('wb') as f:
            done=subprocess.run(command,env=env,stdout=f,stderr=subprocess.STDOUT)
        run=dict(dataset=dataset,variant=variant,command=command,library=str(lib),exit=done.returncode)
        runs.append(run);(root/'runs.json').write_text(json.dumps(runs,indent=2)+'\n')
        assert done.returncode==0,(name,(root/(name+'.log')).read_text())
        run['summary']=next(csv.DictReader(output.open()))
        (root/'runs.json').write_text(json.dumps(runs,indent=2)+'\n')
        print(name,run['summary'],flush=True)
