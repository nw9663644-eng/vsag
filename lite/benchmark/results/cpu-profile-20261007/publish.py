from pathlib import Path
import json,hashlib,gzip,subprocess,csv
root=Path(__file__).resolve().parent
out=Path('lite/benchmark/results/cpu-profile-20261007');out.mkdir(parents=True,exist_ok=False)
raw={}
for p in root.iterdir():
 if p.suffix in ['.py','.json','.csv','.log','.txt']:
  data=p.read_bytes();raw[p.name]=hashlib.sha256(data).hexdigest()
  if p.name.endswith('.stacks.txt'):
   (out/(p.name+'.gz')).write_bytes(gzip.compress(data,mtime=0));continue
  if p.suffix in ['.txt','.log','.csv']:
   data=('\n'.join(x.rstrip() for x in p.read_text().splitlines())+'\n').encode()
  (out/p.name).write_bytes(data)
(out/'raw-sha256.json').write_text(json.dumps(raw,indent=2)+'\n')
rows=json.loads((out/'stack-summary.json').read_text())
assert len(rows)==8
statcommands=json.loads((out/'stat-commands.json').read_text());assert len(statcommands)==4 and all(x['exit']==0 for x in statcommands)
stats=[]
for x in statcommands:
 name=x['name'];counters={}
 for line in (out/(name+'.stat.csv')).read_text().splitlines():
  if not line or line.startswith('#'):continue
  values=next(csv.reader([line]));value,unit,event=values[:3]
  assert '<not' not in value,line
  counters[event]={'value':float(value),'unit':unit,'enabled_percent':float(values[4]),'derived':values[5:]}
 text=(out/(name+'.stdout.log')).read_text();lines=text.splitlines();header=next(x for x in lines if 'recall_at_k' in x);quality=next(csv.DictReader(lines[lines.index(header):]))
 stats.append({'name':name,'counters':counters,'quality':quality})
(out/'stat-summary.json').write_text(json.dumps(stats,indent=2)+'\n')
protocol=json.loads((out/'protocol.json').read_text())
for config in protocol['binaries'].values():assert hashlib.sha256(Path(config['path']).read_bytes()).hexdigest()==config['sha256']
sources=['src/lite/graph_backend.cpp','src/lite/distance_avx512.cpp','lite/benchmark/graph_crud_quality.cpp']
provenance={'source_parent':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'source_hashes':{p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in sources if Path(p).exists()},'libraries':{mode:{'path':str(Path(config['path']).parent/'libvsag-lite.so'),'sha256':hashlib.sha256((Path(config['path']).parent/'libvsag-lite.so').read_bytes()).hexdigest()} for mode,config in protocol['binaries'].items()},'perf_data':{p.name:subprocess.check_output(['sudo','-n','sha256sum',str(p)],text=True).split()[0] for p in root.glob('*.data')},'note':'No library change; raw perf.data and snapshots stay on server; compressed exact perf script exports published.'}
(out/'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
(out/'environment.txt').write_text(subprocess.check_output(['uname','-a'],text=True)+subprocess.check_output(['lscpu'],text=True)+subprocess.check_output(['perf','--version'],text=True))
print('Published',len(list(out.iterdir())),'files',sum(x['samples'] for x in rows),'samples')
