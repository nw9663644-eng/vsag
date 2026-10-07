from pathlib import Path
import json,hashlib,statistics,shutil,subprocess
root=Path(__file__).resolve().parent;out=Path('lite/benchmark/results/update-incoming-20261007');out.mkdir(exist_ok=False,parents=True)
raw={}
for p in root.iterdir():
 if p.is_file() and p.suffix in ['.csv','.json','.log','.txt','.py','.cpp']:
  data=p.read_bytes();raw[p.name]=hashlib.sha256(data).hexdigest()
  if p.suffix in ['.txt','.log']:data=(p.read_text().rstrip()+'\n').encode()
  (out/p.name).write_bytes(data)
shutil.copytree(root/'gcov',out/'gcov')
rows=json.loads((out/'summary.json').read_text());assert len(rows)==12
metrics=[]
for flow in ['build','crud']:
 for variant in ['before','after']:
  r=[x for x in rows if x['flow']==flow and x['variant']==variant];assert len(r)==3
  assert len({x['snapshot_sha256'] for x in r})==len({x['neighbors_sha256'] for x in r})==len({x['recall_at_k'] for x in r})==1
  metrics.append({'flow':flow,'variant':variant,'cpu_seconds_median':statistics.median(x['cpu_seconds'] for x in r),'recall':r[0]['recall_at_k']})
assert len({x['snapshot_sha256'] for x in rows if x['flow']=='build'})==1
(out/'audit.json').write_text(json.dumps(metrics,indent=2)+'\n');(out/'raw-sha256.json').write_text(json.dumps(raw,indent=2)+'\n')
(out/'environment.txt').write_text((subprocess.check_output(['uname','-a'],text=True)+subprocess.check_output(['lscpu'],text=True)).rstrip()+'\n')
print(metrics)
