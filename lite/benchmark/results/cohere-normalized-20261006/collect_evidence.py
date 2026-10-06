import pathlib, shutil, json, csv, math, hashlib, subprocess
root=pathlib.Path('/home/ubuntu/project/vsag-lite-cohere-normalized-20261006')
out=pathlib.Path('lite/benchmark/results/cohere-normalized-20261006')
for p in root.iterdir():
 if p.suffix in ['.csv','.log','.json','.py']: shutil.copy2(p,out/p.name)
for count in [10000,100000]:
 d=out/'preparation'/f'scale-{count}'; d.mkdir(parents=True,exist_ok=True)
 shutil.copy2(root/'prepared'/f'scale-{count}'/'manifest.json',d/'manifest.json')
def rows(p):
 with p.open() as f: return list(csv.DictReader(f))
def quantile(values,q): return sorted(values)[math.ceil(len(values)*q)-1]
summary=[]
for count in [10000,100000]:
 for mode in ['default','diverse']:
  name=f'cohere-{count}-{mode}.csv.api.csv'
  api=rows(out/name)[0]; crud=rows(out/(name+'.crud.csv'))[0]
  for path,expected,p50,p99 in [(out/(name+'.latencies.csv'),100,api['search_p50_us'],api['search_p99_us']),(out/(name+'.crud.csv.mixed.csv'),100,crud['mixed_search_p50_us'],crud['mixed_search_p99_us'])]:
   data=rows(path); assert len(data)==expected
   values=[float(r['latency_us']) for r in data]
   assert abs(quantile(values,.5)-float(p50))<1e-5
   assert abs(quantile(values,.99)-float(p99))<1e-5
  assert len(rows(out/(name+'.crud.csv.samples.csv')))==1000
  assert int(crud['cycles'])==1000
  summary.append({'count':count,'mode':mode,'initial':api,'after_crud':crud,'initial_quality_pass':float(api['recall_at_k'])>=.9,'after_crud_quality_pass':float(crud['recall_at_k'])>=.9})
(out/'audit-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''): h.update(b)
 return h.hexdigest()
files=list(root.glob('*.snapshot'))
for b in ['build-lite-fragment-release','build-lite-online-diverse-release']:
 for name in ['libvsag-lite.so','lite_graph_route_probe','lite_graph_crud_quality']:
  p=pathlib.Path(b)/name
  if p.exists():files.append(p)
files += [pathlib.Path('lite/benchmark/prepare_cohere.py'),pathlib.Path('lite/benchmark/test_prepare_cohere.py')]
(out/'artifacts-sha256.json').write_text(json.dumps({str(p):sha(p) for p in files},indent=2)+'\n')
(out/'environment.txt').write_text(subprocess.check_output(['uname','-a'],text=True)+subprocess.check_output(['lscpu'],text=True))
print('Verified four configurations, 400 initial and 400 mixed raw latencies, 4000 CRUD cycles.')
