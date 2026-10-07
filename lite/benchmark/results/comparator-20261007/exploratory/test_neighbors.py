import subprocess,csv,tempfile
from pathlib import Path
binary='build-lite-fragment-release/lite_graph_crud_quality'
base='/home/ubuntu/project/vsag-lite-load-memory-20261006/fixture'
with tempfile.TemporaryDirectory() as temp:
 root=Path(temp);snap=root/'ok.snapshot';query=root/'queries.csv'
 result=subprocess.run([binary,base,str(snap),'0','1',str(query)],capture_output=True,text=True)
 assert result.returncode==0,result.stderr
 hits=list(csv.DictReader(query.open()));neighbors=list(csv.DictReader(Path(str(query)+'.neighbors.csv').open()))
 assert len(hits)==len(neighbors)==8
 assert list(hits[0])==['query','hits','k','recall_at_k']
 for row in neighbors:
  assert row['query']==row['id'] and row['rank']=='0' and float.fromhex(row['distance'])==0
 protected=root/'protected.csv';sidecar=Path(str(protected)+'.neighbors.csv');sidecar.write_text('preserve\n')
 result=subprocess.run([binary,base,str(root/'bad.snapshot'),'0','1',str(protected)],capture_output=True,text=True)
 assert result.returncode!=0 and 'neighbor results path already exists' in result.stderr
 assert sidecar.read_text()=='preserve\n' and not protected.exists()
print('Exact hex neighbor sidecar, original hits schema, and overwrite rejection passed.')
