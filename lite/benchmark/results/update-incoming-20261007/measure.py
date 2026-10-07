from pathlib import Path
import subprocess,json,csv,io,hashlib,os
root=Path(__file__).resolve().parent;repo=Path.cwd()
base=repo.parent/'vsag-lite-cohere-normalized-20261006/prepared/scale-10000'
binary=repo/'build-lite-fragment-release/lite_graph_crud_quality'
libraries={'before':root/'before','after':repo/'build-lite-fragment-release'}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
protocol={'source_parent':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'source_sha256':{p:sha(p) for p in ['src/lite/graph_backend.cpp','src/lite/graph_backend_test.cpp']},'dataset':str(base),'input_sha256':{p.name:sha(p) for p in base.iterdir() if p.is_file()},'libraries':{v:{'path':str(p),'sha256':sha(p/'libvsag-lite.so')} for v,p in libraries.items()},'runner_sha256':sha(binary),'cpu':0,'repeats':3,'operations':'same-vector Update/Remove/Add,10000 distinct original IDs; build-only vs build+CRUD; fixed16/128','timing':'whole-process CPU; no concurrent build/test/profiler; not isolated mutation','retention':'keep first-replicate snapshots only; later generated snapshots hashed/checked then removed'}
(root/'protocol.json').write_text(json.dumps(protocol,indent=2)+'\n')
rows=[];commands=[]
for repeat in range(3):
 for flow in (['build','crud'] if repeat%2==0 else ['crud','build']):
  for variant in (['before','after'] if repeat%2==0 else ['after','before']):
   name=f'{variant}-{flow}-r{repeat}';prefix=root/name;snapshot=Path(str(prefix)+'.snapshot');env=dict(os.environ,LD_LIBRARY_PATH=str(libraries[variant]))
   if repeat==0 and flow=='build':(root/(variant+'-ldd.txt')).write_text(subprocess.check_output(['ldd',str(binary)],env=env,text=True))
   cmd=['/usr/bin/time','-f','%U,%S,%e','-o',str(prefix)+'.cpu.csv','taskset','-c','0',str(binary),str(base),str(snapshot),'0' if flow=='build' else '1','1' if flow=='build' else '10000',str(prefix)+'.queries.csv']
   result=subprocess.run(cmd,capture_output=True,text=True,env=env);(root/(name+'.stdout.log')).write_text(result.stdout);(root/(name+'.stderr.log')).write_text(result.stderr)
   commands.append({'name':name,'command':cmd,'LD_LIBRARY_PATH':str(libraries[variant]),'exit':result.returncode});(root/'commands.json').write_text(json.dumps(commands,indent=2)+'\n');assert result.returncode==0,result.stderr
   row=next(csv.DictReader(io.StringIO(result.stdout)));user,system,wall=map(float,Path(str(prefix)+'.cpu.csv').read_text().split(','));row.update(name=name,variant=variant,flow=flow,repeat=repeat,cpu_seconds=user+system,wall_seconds=wall,snapshot_sha256=sha(snapshot),neighbors_sha256=sha(str(prefix)+'.queries.csv.neighbors.csv'));rows.append(row);(root/'summary.json').write_text(json.dumps(rows,indent=2)+'\n')
   print(name,row['recall_at_k'],user+system,flush=True)
   if repeat>0:assert snapshot.resolve().parent==root.resolve();snapshot.unlink()
print('Completed12 measurements',flush=True)
