import csv,io,json,subprocess,hashlib,os
from pathlib import Path
root=Path(__file__).resolve().parent
base='/home/ubuntu/project/vsag-lite-cohere-normalized-20261006/prepared/scale-10000'
builds={'default':'build-lite-fragment-release','diverse':'build-lite-online-diverse-release'}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
protocol={'source_parent':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'dataset':base,'cpu':0,'replicates':3,'flows':['build','crud'],'crud':'10000 distinct IDs, same-vector Update/Remove/Add; no query budget changes','comparison':'same new diagnostic runner, old/new libraries selected explicitly with LD_LIBRARY_PATH','old_library':{m:sha(root.with_name('vsag-lite-comparator-20261007')/('old-'+m)/'libvsag-lite.so') for m in builds},'new_library':{m:sha(Path(b)/'libvsag-lite.so') for m,b in builds.items()},'runner':{m:sha(Path(b)/'lite_graph_crud_quality') for m,b in builds.items()},'sources':{p:sha(p) for p in ['src/lite/graph_backend.cpp','lite/benchmark/graph_crud_quality.cpp']}}
(root/'protocol.json').write_text(json.dumps(protocol,indent=2)+'\n')
rows=[];commands=[]
for repeat in range(3):
 for mode in (['default','diverse'] if repeat%2==0 else ['diverse','default']):
  for flow in (['build','crud'] if repeat%2==0 else ['crud','build']):
   for variant in (['old','new'] if repeat%2==0 else ['new','old']):
    name=f'{mode}-{flow}-{variant}-r{repeat}';prefix=root/name
    library=root.with_name('vsag-lite-comparator-20261007')/('old-'+mode) if variant=='old' else Path(builds[mode]).resolve()
    env=dict(os.environ,LD_LIBRARY_PATH=str(library))
    if repeat==0 and flow=='build':(root/(mode+'-'+variant+'-ldd.txt')).write_text(subprocess.check_output(['ldd',str(Path(builds[mode])/'lite_graph_crud_quality')],env=env,text=True))
    cmd=['/usr/bin/time','-f','%U,%S,%e','-o',str(prefix)+'.cpu.csv','taskset','-c','0',str(Path(builds[mode])/'lite_graph_crud_quality'),base,str(prefix)+'.snapshot','0' if flow=='build' else '1','1' if flow=='build' else '10000',str(prefix)+'.queries.csv']
    result=subprocess.run(cmd,env=env,capture_output=True,text=True)
    (root/(name+'.stdout.log')).write_text(result.stdout);(root/(name+'.stderr.log')).write_text(result.stderr)
    commands.append({'name':name,'command':cmd,'LD_LIBRARY_PATH':str(library),'exit':result.returncode});(root/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
    assert result.returncode==0,(name,result.stderr)
    row=next(csv.DictReader(io.StringIO(result.stdout)));u,s,w=map(float,(root/(name+'.cpu.csv')).read_text().split(','))
    row.update(name=name,mode=mode,flow=flow,variant=variant,repeat=repeat,cpu_seconds=u+s,wall_seconds=w,snapshot_sha256=sha(str(prefix)+'.snapshot'),neighbors_sha256=sha(str(prefix)+'.queries.csv.neighbors.csv'),hits_sha256=sha(str(prefix)+'.queries.csv'));rows.append(row)
    (root/'summary.json').write_text(json.dumps(rows,indent=2)+'\n')
    print(name,u+s,row['recall_at_k'],flush=True)
print('Completed',len(rows),'paired runs',flush=True)
