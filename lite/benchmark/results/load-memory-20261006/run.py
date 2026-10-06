from pathlib import Path
import json,csv,io,subprocess,hashlib,statistics
root=Path('/home/ubuntu/project/vsag-lite-load-memory-20261006')
pilot=root.with_name('vsag-lite-cohere-normalized-20261006')
configs={'full':('build-full-known-runner/full_load_memory',root.with_name('vsag-lite-full-cohere-20261006')/'full-rep0.snapshot'),'default':('build-lite-fragment-release/lite_load_memory',pilot/'cohere-100000-default.snapshot'),'diverse':('build-lite-online-diverse-release/lite_load_memory',pilot/'cohere-100000-diverse.snapshot')}
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
protocol={'source_parent':'101e3f6fb3973efda6a212f84a5c532274c9f208','new_helper_sha256':sha('lite/benchmark/load_memory.cpp'),'cpu':0,'replicates':7,'order':'cyclic rotate full/default/diverse each replicate','phase':'load only; no base/query matrices, no search/build/save, input stream closed then malloc_trim','cache':'read each input once before runs; no eviction control, warm attempted','dimension':768,'count':100000,'full_library_source':'d18c82a1f1f23ff84362516e86af5f3cb2e34475','snapshot_quality':'previous measured Full .952/Lite default .958/diverse .961333; different recall/topology','configs':{m:{'binary':b,'binary_sha256':sha(b),'snapshot':str(s),'snapshot_sha256':sha(s)} for m,(b,s) in configs.items()}}
(root/'protocol.json').write_text(json.dumps(protocol,indent=2)+'\n')
for b,s in configs.values():
 with s.open('rb') as f:
  while f.read(1048576):pass
rows=[];commands=[]
for repeat in range(7):
 order=['full','default','diverse'];order=order[repeat%3:]+order[:repeat%3]
 for mode in order:
  b,s=configs[mode];cmd=['taskset','-c','0',b,str(s),'768','100000'];commands.append(cmd)
  (root/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
  result=subprocess.run(cmd,capture_output=True,text=True,check=True)
  name=f'{mode}-rep{repeat}'
  (root/(name+'.stdout.log')).write_text(result.stdout)
  (root/(name+'.stderr.log')).write_text(result.stderr)
  clean=result.stdout[result.stdout.index('dim,count,'):]
  (root/(name+'.csv')).write_text(clean)
  row=next(csv.DictReader(io.StringIO(clean)));row.update(mode=mode,repeat=repeat);rows.append(row)
  print(mode,repeat,row['load_ms'],row['loaded_rss_kib'],row['process_peak_rss_kib'],flush=True)
(root/'summary.json').write_text(json.dumps(rows,indent=2)+'\n')
print('Completed',len(rows),'fresh-process load-only measurements',flush=True)
