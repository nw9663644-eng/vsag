from pathlib import Path
import json,subprocess,hashlib,csv,io
root=Path('/home/ubuntu/project/vsag-lite-full-cohere-20261006')
data=Path('/home/ubuntu/project/vsag-lite-cohere-matched-20261006/final/scale-100000')
lib=Path('/home/ubuntu/project/vsag-full-known-install-20261006/lib/libvsag.so.0.0.0')
assert lib.exists()
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
protocol={'source_commit':revision,'full_library_sha256':sha(lib),'full_binary_sha256':sha(Path('build-full-known-runner/full_rabitq_dataset_benchmark')),'dataset_manifest_sha256':sha(data/'manifest.json'),'query_rows':[400,1000],'query_status':'already observed in Lite; descriptive Full reference, not fresh blind evaluation','cpu':0,'mode':'fp32','degree':16,'construction_ef':128,'query_ef':128,'warmup_rounds':1,'replicates':3,'full_graph_storage':'compressed','store_raw_vector':True,'limits':'no matched Lite RSS yet, no Full mixed CRUD, no equal-quality budget tuning'}
(root/'protocol.json').write_text(json.dumps(protocol,indent=2)+'\n')
commands=[];rows=[]
for repeat in range(3):
 snap=root/f'full-rep{repeat}.snapshot'
 cmd=['taskset','-c','0','build-full-known-runner/full_rabitq_dataset_benchmark',str(data),str(snap),'fp32','128','1']
 commands.append(cmd);(root/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
 if not snap.exists():
  with (root/f'full-rep{repeat}.csv').open('w') as f, (root/f'full-rep{repeat}.log').open('w') as log:subprocess.run(cmd,stdout=f,stderr=log,check=True)
 raw=(root/f'full-rep{repeat}.csv').read_text()
 start=raw.index('mode,base_count,query_count,')
 if start>0:(root/f'full-rep{repeat}.stdout.log').write_text(raw)
 clean=raw[start:]
 row=next(csv.DictReader(io.StringIO(clean)))
 (root/f'full-rep{repeat}.csv').write_text(clean)
 rows.append(row);(root/'summary.json').write_text(json.dumps(rows,indent=2)+'\n')
 print(repeat,row['recall_at_k'],row['build_ms'],row['search_p50_us'],row['final_steady_rss_kib'],flush=True)
(root/'snapshot-sha256.json').write_text(json.dumps({p.name:sha(p) for p in root.glob('*.snapshot')},indent=2)+'\n')
