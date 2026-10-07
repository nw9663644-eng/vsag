import csv,io,json,subprocess,hashlib,os,statistics,filecmp
from pathlib import Path
root=Path(__file__).resolve().parent
repo=Path.cwd()
cases={'sift100k':repo.parent/'vsag-lite-datasets/sift/prepared-10k-100k/scale-100000','gist10k':repo.parent/'vsag-lite-datasets/gist/prepared-10k-100k/scale-10000'}
binary=repo/'build-lite-fragment-release/lite_graph_crud_quality'
libraries={'old':repo.parent/'vsag-lite-comparator-20261007/old-default','new':repo/'build-lite-fragment-release'}
def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
previous=json.loads((repo/'lite/benchmark/results/comparator-20261007/final/protocol.json').read_text())
assert sha(libraries['old']/'libvsag-lite.so')==previous['old_library']['default']
assert sha(libraries['new']/'libvsag-lite.so')==previous['new_library']['default']
assert sha(binary)==previous['runner']['default']
protocol={'source_parent':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'cpu':0,'replicates':3,'policy':'default OFF only','graph_degree':16,'construction_query_budget':128,'flows':{'build':{'rounds':0,'ops':1},'crud':{'rounds':1,'ops':1000}},'cases':{k:{'directory':str(d),'input_sha256':{p.name:sha(p) for p in d.iterdir() if p.is_file()}} for k,d in cases.items()},'binary_sha256':sha(binary),'library_sha256':{v:sha(p/'libvsag-lite.so') for v,p in libraries.items()},'snapshot_retention':'new per-pair temporary snapshots streamed byte-compared and hashed, then removed after success only; existing inputs/history untouched','timing':'whole process /usr/bin/time user+system, no profiler, builds/tests not running; not isolated CRUD','quality':'same observed diagnostic queries, fixed128, exact equivalence only; no new recall acceptance gate or retuning'}
(root/'protocol.json').write_text(json.dumps(protocol,indent=2)+'\n')
for variant,path in libraries.items():
 env=dict(os.environ,LD_LIBRARY_PATH=str(path))
 (root/(variant+'-ldd.txt')).write_text(subprocess.check_output(['ldd',str(binary)],env=env,text=True))
rows=[];commands=[];pairs=[]
for repeat in range(3):
 for case in (list(cases) if repeat%2==0 else list(reversed(cases))):
  for flow in (['build','crud'] if repeat%2==0 else ['crud','build']):
   pairroot=root/f'{case}-{flow}-r{repeat}-temporary';pairroot.mkdir(exist_ok=False)
   current=[]
   for variant in (['old','new'] if repeat%2==0 else ['new','old']):
    name=f'{case}-{flow}-{variant}-r{repeat}';prefix=root/name
    snapshot=pairroot/(variant+'.snapshot');env=dict(os.environ,LD_LIBRARY_PATH=str(libraries[variant]))
    cmd=['/usr/bin/time','-f','%U,%S,%e','-o',str(prefix)+'.cpu.csv','taskset','-c','0',str(binary),str(cases[case]),str(snapshot),'0' if flow=='build' else '1','1' if flow=='build' else '1000',str(prefix)+'.queries.csv']
    result=subprocess.run(cmd,env=env,capture_output=True,text=True)
    (root/(name+'.stdout.log')).write_text(result.stdout);(root/(name+'.stderr.log')).write_text(result.stderr)
    commands.append({'name':name,'command':cmd,'LD_LIBRARY_PATH':str(libraries[variant]),'exit':result.returncode});(root/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
    assert result.returncode==0,(name,result.stderr)
    row=next(csv.DictReader(io.StringIO(result.stdout)));u,s,w=map(float,Path(str(prefix)+'.cpu.csv').read_text().split(','))
    row.update(name=name,case=case,flow=flow,variant=variant,repeat=repeat,cpu_seconds=u+s,wall_seconds=w,snapshot_sha256=sha(snapshot),neighbors_sha256=sha(str(prefix)+'.queries.csv.neighbors.csv'),hits_sha256=sha(str(prefix)+'.queries.csv'));rows.append(row);current.append(row)
    (root/'summary.json').write_text(json.dumps(rows,indent=2)+'\n')
    print(name,u+s,row['recall_at_k'],flush=True)
   assert filecmp.cmp(pairroot/'old.snapshot',pairroot/'new.snapshot',shallow=False)
   for key in ['snapshot_sha256','neighbors_sha256','hits_sha256','recall_at_k']:assert current[0][key]==current[1][key],(case,flow,key)
   pairs.append({'case':case,'flow':flow,'repeat':repeat,'stream_byte_equal':True,'snapshot_sha256':current[0]['snapshot_sha256'],'neighbors_sha256':current[0]['neighbors_sha256']});(root/'pairs.json').write_text(json.dumps(pairs,indent=2)+'\n')
   for variant in ['old','new']:
    p=pairroot/(variant+'.snapshot');assert p.resolve().parent==pairroot.resolve() and root in p.resolve().parents;p.unlink()
   pairroot.rmdir()
print('Completed24 runs/12 exact pairs',flush=True)
