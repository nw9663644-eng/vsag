from pathlib import Path
import subprocess,os,json,csv,hashlib,struct
root=Path(__file__).resolve().parent/'changed';root.mkdir(exist_ok=False)
parent=root.parent;repo=Path.cwd()
base=repo.parent/'vsag-lite-cohere-normalized-20261006/prepared/scale-10000'
snapshot=parent/'before-build-r0.snapshot';binary=repo/'build-lite-fragment-release/lite_graph_route_probe'
# Every changed coordinate differs at FP32 storage precision; restores also differ.
blob=(base/'base.fvecs').read_bytes();stride=4+768*4
for cycle in range(1000):
 slot=cycle*8191%10000;original=blob[slot*stride+4:slot*stride+8]
 value=struct.unpack('<f',original)[0];changed=struct.pack('<f',value+0.125);assert changed!=original
commands=[];rows=[]
for repeat in range(3):
 for variant in (['before','after'] if repeat%2==0 else ['after','before']):
  name=f'{variant}-r{repeat}';prefix=root/name
  library=parent/'before' if variant=='before' else repo/'build-lite-fragment-release';env=dict(os.environ,LD_LIBRARY_PATH=str(library))
  cmd=['taskset','-c','0',str(binary),str(snapshot),str(base),str(prefix)+'.csv','128','uniform','preserve','1','1000','10']
  result=subprocess.run(cmd,capture_output=True,text=True,env=env);(root/(name+'.stdout.log')).write_text(result.stdout);(root/(name+'.stderr.log')).write_text(result.stderr)
  commands.append({'name':name,'command':cmd,'LD_LIBRARY_PATH':str(library),'exit':result.returncode});(root/'commands.json').write_text(json.dumps(commands,indent=2)+'\n');assert result.returncode==0,result.stderr
  initial=next(csv.DictReader(Path(str(prefix)+'.csv.api.csv').open()));after=next(csv.DictReader(Path(str(prefix)+'.csv.api.csv.crud.csv').open()));rows.append({'name':name,'variant':variant,'repeat':repeat,'initial':initial,'after':after});(root/'summary.json').write_text(json.dumps(rows,indent=2)+'\n')
  print(name,after['recall_at_k'],after['crud_loop_cpu_ms'],flush=True)
(root/'protocol.json').write_text(json.dumps({'source_parent':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'cpu':0,'cycles':1000,'repeats':3,'query_every':10,'construction_maintenance_query':128,'changed_vectors':'+.125 first coordinate then restore; every coordinate change differs as FP32; no-op not applicable','snapshot':str(snapshot),'snapshot_sha256':hashlib.sha256(snapshot.read_bytes()).hexdigest(),'probe_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'native_probes':'existing binary, current/old library explicit; own SaveLoad exact checks; cross-variant exact neighbors not exported'},indent=2)+'\n')
