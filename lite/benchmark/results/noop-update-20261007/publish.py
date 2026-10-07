from pathlib import Path
import json,hashlib,statistics,gzip,shutil
root=Path(__file__).resolve().parent;out=Path('lite/benchmark/results/noop-update-20261007');out.mkdir(parents=True,exist_ok=False)
raw={}
for p in root.rglob('*'):
 if not p.is_file() or 'before' in p.relative_to(root).parts:continue
 if p.suffix not in ['.json','.csv','.txt','.log','.py','.gz']:continue
 relative=p.relative_to(root);target=out/relative;target.parent.mkdir(parents=True,exist_ok=True);data=p.read_bytes();raw[str(relative)]=hashlib.sha256(data).hexdigest()
 if p.suffix in ['.log','.txt']:
  # Catch2's initial string comparison dumped non-UTF8 snapshot bytes. Keep exact raw copy.
  if b'\x00' in data or p.name=='test-before.log':
   (out/(str(relative)+'.raw.gz')).write_bytes(gzip.compress(data,mtime=0))
   text=data.decode('utf-8',errors='backslashreplace')
   text=''.join(c if c in '\n\t' or 32<=ord(c)<127 else c.encode('unicode_escape').decode('ascii') for c in text)
  else:text=data.decode('utf-8')
  data=('\n'.join(x.rstrip() for x in text.splitlines()).rstrip()+'\n').encode()
 target.write_bytes(data)
rows=json.loads((out/'summary.json').read_text());assert len(rows)==12
metrics=[]
for flow in ['build','crud']:
 for variant in ['before','after']:
  selected=[x for x in rows if x['flow']==flow and x['variant']==variant];assert len(selected)==3
  assert len({x['snapshot_sha256'] for x in selected})==len({x['recall_at_k'] for x in selected})==1
  metrics.append({'flow':flow,'variant':variant,'cpu_seconds_median':statistics.median(x['cpu_seconds'] for x in selected),'recall':selected[0]['recall_at_k']})
assert len({x['snapshot_sha256'] for x in rows if x['flow']=='build'})==1
changed=json.loads((out/'changed/summary.json').read_text());assert len(changed)==6
control={v:{'mutation_cpu_ms_median':statistics.median(float(x['after']['crud_loop_cpu_ms']) for x in changed if x['variant']==v),'recall_values':sorted({x['after']['recall_at_k'] for x in changed if x['variant']==v})} for v in ['before','after']}
(out/'audit.json').write_text(json.dumps({'same_value':metrics,'changed_control':control},indent=2)+'\n');(out/'raw-sha256.json').write_text(json.dumps(raw,indent=2)+'\n')
print(metrics);print(control)
