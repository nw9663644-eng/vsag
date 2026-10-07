from pathlib import Path
import subprocess,json,csv,hashlib,io
root=Path(__file__).resolve().parent/'quality';root.mkdir(exist_ok=False)
prior=root.parent.with_name('vsag-lite-comparator-final-20261007')
base=root.parent.with_name('vsag-lite-cohere-normalized-20261006')/'prepared/scale-10000'
binary=Path('build-lite-fragment-release/lite_graph_route_probe')
commands=[];rows=[]
for mode in ['default','diverse']:
 for phase in ['build','crud']:
  name=f'{mode}-{phase}';snap=prior/(name+'-new-r0.snapshot');prefix=root/name
  cmd=['taskset','-c','0',str(binary),str(snap),str(base),str(prefix)+'.csv','128','uniform','preserve','1']
  result=subprocess.run(cmd,capture_output=True,text=True);(root/(name+'.stdout.log')).write_text(result.stdout);(root/(name+'.stderr.log')).write_text(result.stderr)
  commands.append({'name':name,'command':cmd,'exit':result.returncode,'snapshot_sha256':hashlib.sha256(snap.read_bytes()).hexdigest()});assert result.returncode==0,result.stderr
  row=next(csv.DictReader(io.StringIO(result.stdout)));row.update(name=name)
  native=next(csv.DictReader(Path(str(prefix)+'.csv.api.csv').open()));row['native']=native
  traces=list(csv.DictReader(Path(str(prefix)+'.csv').open()))
  previous=list(csv.DictReader((prior/(name+'-new-r0.queries.csv')).open()))
  assert len(traces)==len(previous)==100
  row['native_prior_hits_match']=all(int(x['hits'])==int(y['hits']) for x,y in zip(traces,previous))
  row['truth_not_visited_total']=sum(int(x['truth_not_visited']) for x in traces)
  row['visited_not_returned_total']=sum(int(x['visited_not_returned']) for x in traces)
  rows.append(row)
(root/'commands.json').write_text(json.dumps(commands,indent=2)+'\n');(root/'summary.json').write_text(json.dumps(rows,indent=2)+'\n')
(root/'provenance.json').write_text(json.dumps({'source_parent':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'probe_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'library_sha256':hashlib.sha256(Path('build-lite-fragment-release/libvsag-lite.so').read_bytes()).hexdigest(),'dataset':str(base),'query_count':100,'budget':128,'notes':'Known observed queries; native API and scalar trace at same budget; edge reachability excludes implicit slot ring; no policy/budget change'},indent=2)+'\n')
for x in rows:print(x)
