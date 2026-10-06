import pathlib,json,csv,math,statistics,hashlib,shutil
root=pathlib.Path('/home/ubuntu/project/vsag-lite-cohere-matched-20261006')
out=pathlib.Path('lite/benchmark/results/cohere-matched-20261006');out.mkdir(parents=True,exist_ok=True)
def read(p):
 with p.open() as f:return list(csv.DictReader(f))
def q(v,f):return sorted(v)[math.ceil(len(v)*f)-1]
for p in root.iterdir():
 if p.is_file():
  phase='validation' if p.name.startswith('validation-') else 'final'
  destination=out/phase if p.name.startswith(('validation-','final-')) and ('.csv' in p.name or p.suffix=='.log') else out
  destination.mkdir(exist_ok=True)
  shutil.copy2(p,destination/p.name)
for phase in ['validation','final']:
 d=out/phase;d.mkdir(exist_ok=True)
 shutil.copy2(root/phase/'scale-100000/manifest.json',d/'manifest.json')
summary=json.loads((root/'final-summary.json').read_text());assert len(summary)==12
counts={'initial':0,'mixed':0,'cycles':0}
for r in summary:
 name=f"final-every{r['query_every']}-rep{r['repeat']}-{r['mode']}.csv.api.csv"
 a=r['initial'];b=r['after']
 for path,n,p50,p99 in [(root/(name+'.latencies.csv'),600,a['search_p50_us'],a['search_p99_us']),(root/(name+'.crud.csv.mixed.csv'),1000//r['query_every'],b['mixed_search_p50_us'],b['mixed_search_p99_us'])]:
  data=read(path);assert len(data)==n
  values=[float(v['latency_us']) for v in data]
  assert abs(q(values,.5)-float(p50))<1e-5 and abs(q(values,.99)-float(p99))<1e-5
 assert len(read(root/(name+'.crud.csv.samples.csv')))==1000
 counts['initial']+=600;counts['mixed']+=1000//r['query_every'];counts['cycles']+=1000
medians=[]
for every in [1,10]:
 for mode in ['default','diverse']:
  rows=[r for r in summary if r['mode']==mode and r['query_every']==every]
  row={'mode':mode,'query_every':every,'all_quality_pass':all(r['quality_pass'] for r in rows),'initial_recall':rows[0]['initial']['recall_at_k'],'post_recall':rows[0]['after']['recall_at_k']}
  for field in ['crud_loop_cpu_ms','mixed_query_cpu_ms','mixed_loop_cpu_ms','mixed_search_p50_us','mixed_search_p99_us']:
   vals=[float(r['after'][field]) for r in rows];row[field]={'median':statistics.median(vals),'min':min(vals),'max':max(vals)}
  medians.append(row)
(out/'audit.json').write_text(json.dumps({'raw_counts':counts,'quality_passes':sum(r['quality_pass'] for r in summary),'medians':medians},indent=2)+'\n')
print(json.dumps(medians,indent=2),flush=True)
