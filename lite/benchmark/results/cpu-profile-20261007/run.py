import json,subprocess,hashlib
from pathlib import Path
root=Path(__file__).resolve().parent
base=Path('/home/ubuntu/project/vsag-lite-cohere-normalized-20261006/prepared/scale-10000')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
binaries={'default':'build-lite-fragment-release/lite_graph_crud_quality','diverse':'build-lite-online-diverse-release/lite_graph_crud_quality'}
protocol={'source_parent':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'dataset':str(base),'dataset_sha256':{p.name:sha(p) for p in base.iterdir() if p.is_file()},'binaries':{m:{'path':b,'sha256':sha(b)} for m,b in binaries.items()},'cpu':0,'sampling':'cpu-clock:u 199Hz, DWARF8192, root perf; target CPU0','repeats':2,'flows':{'build':{'rounds':0,'ops':1},'crud':{'rounds':1,'ops':10000}},'scope':'Whole process including data IO, initial flat staging, graph build, same-vector Update/Remove/Add, query and snapshot. Stack attribution separates identifiable API paths, not isolated phase timing.'}
(root/'protocol.json').write_text(json.dumps(protocol,indent=2)+'\n')
commands=[]
for repeat in range(2):
 for mode in (['default','diverse'] if repeat==0 else ['diverse','default']):
  for flow in (['build','crud'] if repeat==0 else ['crud','build']):
   name=f'{mode}-{flow}-r{repeat}';rounds=0 if flow=='build' else 1
   target=['taskset','-c','0',binaries[mode],str(base),str(root/(name+'.snapshot')),str(rounds),'10000' if rounds else '1']
   cmd=['sudo','-n','perf','record','-e','cpu-clock:u','-F','199','--call-graph','dwarf,8192','-o',str(root/(name+'.data')),'--']+target
   result=subprocess.run(cmd,capture_output=True,text=True)
   (root/(name+'.stdout.log')).write_text(result.stdout);(root/(name+'.stderr.log')).write_text(result.stderr)
   commands.append({'name':name,'command':cmd,'exit':result.returncode});(root/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
   assert result.returncode==0,(name,result.stderr)
   for args,suffix in [(['report','--stdio','--no-children','--sort','symbol','--percent-limit','0.5'],'.self.txt'),(['script','--ns'],'.stacks.txt')]:
    result=subprocess.run(['sudo','-n','perf']+args+['-i',str(root/(name+'.data'))],capture_output=True,text=True,check=True)
    (root/(name+suffix)).write_text(result.stdout);(root/(name+suffix+'.stderr.log')).write_text(result.stderr)
   print(name,'done',flush=True)
