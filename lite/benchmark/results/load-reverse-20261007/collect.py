from pathlib import Path
import csv,json,hashlib,statistics,subprocess
root=Path(__file__).resolve().parent
out=Path('lite/benchmark/results/load-reverse-20261007');out.mkdir(parents=True,exist_ok=False)
rows=json.loads((root/'summary.json').read_text()); commands=json.loads((root/'commands.json').read_text())
assert len(rows)==len(commands)==28
metrics={}
for mode in ['full','full_reverse','default','diverse']:
 r=[x for x in rows if x['mode']==mode];assert len(r)==7 and {x['repeat'] for x in r}==set(range(7))
 for x in r:
  raw=next(csv.DictReader((root/f"{mode}-rep{x['repeat']}.csv").open()))
  assert all(raw[k]==x[k] for k in raw)
  assert int(x['count'])==100000 and int(x['dim'])==768
  assert x['page_cache_control']=='warm_uncontrolled'
  assert int(x['process_peak_rss_kib'])>=int(x['loaded_rss_kib'])>0
 metrics[mode]={k:{'median':statistics.median(float(x[k]) for x in r),'min':min(float(x[k]) for x in r),'max':max(float(x[k]) for x in r)} for k in ['load_ms','loaded_rss_kib','process_peak_rss_kib','snapshot_bytes']}
for repeat in range(7):
 order=['full','full_reverse','default','diverse'];order=order[repeat%4:]+order[:repeat%4]
 assert [x['mode'] for x in rows[repeat*4:repeat*4+4]]==order
 for mode,cmd in zip(order,commands[repeat*4:repeat*4+4]):
  assert cmd[:3]==['taskset','-c','0']
  assert (cmd[-1]=='force-remove')==(mode=='full_reverse')
rawlogs={}
for p in root.iterdir():
 if p.suffix in ['.json','.py','.csv','.log']:
  data=p.read_bytes()
  if p.suffix=='.log':
   rawlogs[p.name]=hashlib.sha256(data).hexdigest()
   data=('\n'.join(x.rstrip() for x in p.read_text().splitlines())+'\n').encode()
  (out/p.name).write_bytes(data)
(out/'raw-log-sha256.json').write_text(json.dumps(rawlogs,indent=2)+'\n')
(out/'audit.json').write_text(json.dumps(metrics,indent=2)+'\n')
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
protocol=json.loads((root/'protocol.json').read_text())
for config in protocol['configs'].values():
 assert sha(config['binary'])==config['binary_sha256']
 assert sha(config['snapshot'])==config['snapshot_sha256']
shared=Path('/home/ubuntu/project/vsag-full-known-install-20261006/lib/libvsag.so')
if not shared.exists():
 shared=Path('/home/ubuntu/project/vsag-full-known-install-20261006/lib64/libvsag.so')
provenance={'source_parent':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'shared_library':str(shared.resolve()),'shared_sha256':sha(shared),'source_sha256':{p:sha(p) for p in ['lite/benchmark/load_memory.cpp','lite/benchmark/test_load_memory.py','src/algorithm/hgraph/hgraph_serialize.cpp','src/datacell/graph_datacell.h']},'note':'Full shared source d18c82a cached incremental build; no library rebuild; snapshots are initial pre-CRUD files'}
(out/'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
(out/'environment.txt').write_text(subprocess.check_output(['uname','-a'],text=True)+subprocess.check_output(['lscpu'],text=True)+subprocess.check_output(['ldd','build-full-known-runner/full_load_memory'],text=True))
text='# Corrected Full reverse-edge load-only comparison, 2026-10-07\n\n'
text+='Seven fresh processes per mode, CPU0, cyclic rotated order, 28 runs total. Initial pre-CRUD Cohere100k/768dim snapshots, same original normalized base. Existing measured recall: Full compressed/reverse 0.952, Lite default 0.958, diversity 0.961333; common floor0.95, not exactly equal quality. No new query or mutation measurement.\n\n'
text+='| Profile | Load ms | Loaded RSS KiB | Loaded RSS MiB | Load-stage peak KiB | Snapshot bytes |\n|---|---:|---:|---:|---:|---:|\n'
for mode,m in metrics.items():
 text+=f"| {mode} | {m['load_ms']['median']:.3f} | {m['loaded_rss_kib']['median']:.0f} | {m['loaded_rss_kib']['median']/1024:.2f} | {m['process_peak_rss_kib']['median']:.0f} | {m['snapshot_bytes']['median']:.0f} |\n"
for mode in ['default','diverse']:
 text+=f"\nLite {mode} versus Full reverse: loaded RSS {100*(metrics[mode]['loaded_rss_kib']['median']/metrics['full_reverse']['loaded_rss_kib']['median']-1):+.2f}%, load wall {100*(metrics[mode]['load_ms']['median']/metrics['full_reverse']['load_ms']['median']-1):+.2f}%, load-stage peak {100*(metrics[mode]['process_peak_rss_kib']['median']/metrics['full_reverse']['process_peak_rss_kib']['median']-1):+.2f}%.\n"
(out/'README.md').write_text(text)
print(text)
