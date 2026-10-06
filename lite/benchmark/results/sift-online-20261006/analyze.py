import pathlib,csv,json,statistics,hashlib,shutil,subprocess
root=pathlib.Path('/home/ubuntu/project/vsag-lite-sift-online-20261006')
out=pathlib.Path('lite/benchmark/results/sift-online-20261006')
out.mkdir(parents=True,exist_ok=False)
def row(path): return next(csv.DictReader(path.open()))
summary=[]
for every in [1,10]:
 for mode in ['default','diverse']:
  rows=[]
  for repeat in range(1,4):
   stem=root/f'{mode}-every{every}-r{repeat}.csv.api.csv.crud.csv'
   r=row(stem); events=list(csv.DictReader(pathlib.Path(str(stem)+'.mixed.csv').open()))
   samples=list(csv.DictReader(pathlib.Path(str(stem)+'.samples.csv').open()))
   assert len(events)==2000//every and len(samples)==2000
   assert int(r['mixed_queries'])==len(events) and int(r['cycles'])==2000
   assert float(r['mixed_loop_cpu_ms'])>=float(r['crud_loop_cpu_ms'])+float(r['mixed_query_cpu_ms'])
   assert float(r['recall_at_k'])>=.95
   rows.append(r)
  s={'mode':mode,'query_every':every,'read_to_mutation_calls':f'1:{4*every}','replicates':3}
  for key in ['recall_at_k','mixed_recall_at_k','crud_loop_cpu_ms','mixed_query_cpu_ms','mixed_loop_cpu_ms','mixed_search_p50_us','mixed_search_p99_us']:
   vals=[float(r[key]) for r in rows]
   s[key]={'median':statistics.median(vals),'min':min(vals),'max':max(vals)}
  summary.append(s)
(root/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
env=subprocess.check_output(['bash','-c','hostname; uname -a; lscpu; sha256sum build-lite-{fragment,online-diverse}-release/lite_graph_route_probe build-lite-{fragment,online-diverse}-release/libvsag-lite.so'],text=True)
(root/'environment.txt').write_text(env)
for p in root.iterdir():
 if p.is_file() and p.suffix!='.snapshot': shutil.copy2(p,out/p.name)
manifest={}
for p in root.glob('*.snapshot'): manifest[p.name]=hashlib.sha256(p.read_bytes()).hexdigest()
for p in pathlib.Path('/home/ubuntu/project/vsag-lite-datasets/sift/prepared-10k-100k/scale-100000').iterdir(): manifest[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
(out/'input-sha256.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(summary,indent=2))
