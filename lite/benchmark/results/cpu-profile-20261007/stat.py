import subprocess,json
from pathlib import Path
root=Path(__file__).resolve().parent
records=[]
for mode in ['default','diverse']:
 for flow in ['build','crud']:
  binary='build-lite-fragment-release/lite_graph_crud_quality' if mode=='default' else 'build-lite-online-diverse-release/lite_graph_crud_quality'
  name=f'{mode}-{flow}-stat'
  target=['taskset','-c','0',binary,'/home/ubuntu/project/vsag-lite-cohere-normalized-20261006/prepared/scale-10000',str(root/(name+'.snapshot')),'0' if flow=='build' else '1','1' if flow=='build' else '10000']
  cmd=['sudo','-n','perf','stat','-x',',','-e','task-clock,cycles,instructions,cache-misses,context-switches,cpu-migrations,page-faults','-o',str(root/(name+'.stat.csv')),'--']+target
  result=subprocess.run(cmd,capture_output=True,text=True)
  (root/(name+'.stdout.log')).write_text(result.stdout);(root/(name+'.stderr.log')).write_text(result.stderr)
  records.append({'name':name,'command':cmd,'exit':result.returncode});(root/'stat-commands.json').write_text(json.dumps(records,indent=2)+'\n')
  assert result.returncode==0,(name,result.stderr)
  print(name,'done',flush=True)
