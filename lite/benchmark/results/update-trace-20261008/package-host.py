from pathlib import Path
import hashlib,json,tarfile,shutil,struct
host=Path(__file__).resolve().parent;repo=Path.cwd();out=repo/'lite/benchmark/results/update-trace-20261008'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
info=json.loads((host/'prepared.json').read_text())
with Path(info['snapshot']).open('rb') as f,(host/'initial-edges.csv').open('w') as output:
 f.seek(64+8*info['count']+4*info['count']*info['dim']);output.write('source,rank,target\n')
 for source in range(info['count']):
  n=struct.unpack('<Q',f.read(8))[0]
  for rank,target in enumerate(struct.unpack('<'+'Q'*n,f.read(8*n))):output.write(f'{source},{rank},{target}\n')
for name in ['queries.fvecs','groundtruth.ivecs','changed-groundtruth.ivecs']:
 shutil.copyfile(Path('/home/ubuntu/project/vsag-lite-persistent-20261007/gist')/name,host/name)
previous={}
for report,label in [('persistent-update-20261007','update'),('storage-control-20261007','control')]:
 prior=repo/'lite/benchmark/results'/report
 previous[report]={n:sha(prior/n) for n in ['raw.tar.gz','members.json','manifest.json']}
 hashes=json.loads((prior/'members.json').read_text())
 with tarfile.open(prior/'raw.tar.gz','r:gz') as archive:
  for variant in ['baseline','candidate']:
   name='gist-'+variant+'.csv.neighbors.csv';data=archive.extractfile(name).read()
   assert hashlib.sha256(data).hexdigest()==hashes[name]
   (host/(label+'-'+variant+'.neighbors.csv')).write_bytes(data)
(host/'previous-evidence.json').write_text(json.dumps(previous,indent=2)+'\n')
for p in Path('/tmp').glob('update-trace-*.log'):shutil.copyfile(p,host/p.name)
for name in ['run.py','package.py']:shutil.copyfile(host/name,out/name.replace('.py','-host.py'))
# Preserve adjacency order in a compact uint32 stream: degree then targets per source.
import csv
conversion={}
for name in ['initial-edges.csv','baseline.csv.final-edges.csv','candidate.csv.final-edges.csv']:
 source=host/name;target=host/(name+'.u32');links=[[] for _ in range(info['count'])]
 with source.open() as f:
  for row in csv.DictReader(f):
   a,rank,b=int(row['source']),int(row['rank']),int(row['target'])
   assert rank==len(links[a]) and 0<=b<info['count'] and rank<16
   links[a].append(b)
 with target.open('wb') as f:
  for row in links:f.write(struct.pack('<'+'I'*(len(row)+1),len(row),*row))
 conversion[name]={'csv_sha256':sha(source),'packed_name':target.name,'packed_sha256':sha(target)}
(host/'edge-conversion.json').write_text(json.dumps(conversion,indent=2)+'\n')
files={p.name:p for p in host.iterdir() if p.is_file() and p.suffix!='.py' and p.name not in conversion}
with tarfile.open(out/'raw.tar.gz','w:gz') as archive:
 for name,p in sorted(files.items()):archive.add(p,arcname=name)
(out/'members.json').write_text(json.dumps({n:sha(p) for n,p in files.items()},indent=2)+'\n')
(out/'manifest.json').write_text(json.dumps({p.name:sha(p) for p in out.iterdir() if p.is_file() and p.name!='manifest.json'},indent=2)+'\n')
