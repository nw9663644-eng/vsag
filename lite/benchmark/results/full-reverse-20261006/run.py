import csv,json,subprocess,time
from pathlib import Path
root=Path('/home/ubuntu/project/vsag-lite-full-reverse-20261006')
repo=Path('/home/ubuntu/project/vsag-lite-baseline-v01')
data='/home/ubuntu/project/vsag-lite-cohere-matched-20261006/final/scale-100000'
protocol={'source_parent':'f1733b203fafa663be94909f2bbfe3018d1bbb70','dataset':data,'cpu':0,'cycles':1000,'cadences':[1,10],'repeats':3,'ef_query':128,'ef_construction':128,'max_degree':16,'storage':'flat','support_force_remove':True,'use_reverse_edges':True,'force_update':True,'final_recall_floor':0.95,'queries':'previously observed Cohere rows 400..999; not blind','comparison':'historical frozen Lite results, not interleaved','full_library':'d18c82a cached incremental shared build; not clean rebuild'}
(root/'protocol.json').write_text(json.dumps(protocol,indent=2)+'\n')
commands=[]
for repeat in range(3):
 for every in ([1,10] if repeat%2==0 else [10,1]):
  prefix=root/f'full-every{every}-r{repeat}.snapshot'
  cmd=['taskset','-c','0',str(repo/'build-full-known-runner/full_rabitq_dataset_benchmark'),data,str(prefix),'fp32','128','1','1000',str(every)]
  record={'command':cmd,'started':time.time()}
  with Path(str(prefix)+'.stdout.log').open('w') as output:
   result=subprocess.run(cmd,stdout=output,stderr=subprocess.STDOUT)
  record.update(exit=result.returncode,elapsed_s=time.time()-record['started'])
  commands.append(record)
  (root/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
  print(prefix.name,result.returncode,round(record['elapsed_s'],2),flush=True)
  if result.returncode: raise SystemExit('Full mixed run failed; preserve outputs')
