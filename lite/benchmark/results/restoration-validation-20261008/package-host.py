from pathlib import Path
import hashlib,json,tarfile,shutil,struct
host=Path(__file__).resolve().parent;out=Path('lite/benchmark/results/restoration-validation-20261008');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
infos=json.loads((host/'prepared.json').read_text());conversion={}
for info in infos:
 d=info['dataset']
 for name in ['queries.fvecs','groundtruth.ivecs']:shutil.copyfile(host/d/name,host/(d+'-'+name))
 if d=='gist-supplement':continue
 sources=[host/(d+'-'+v+'.u32') for v in ['baseline','candidate']]
 with Path(info['snapshot']).open('rb') as original,sources[0].open('rb') as baseline,sources[1].open('rb') as candidate,(host/(d+'-topologies.u32')).open('wb') as dest:
  original.seek(64+8*100000+4*100000*info['dim'])
  for a in range(100000):
   for f,code in [(original,'Q'),(baseline,'I'),(candidate,'I')]:
    n=struct.unpack('<'+code,f.read(struct.calcsize(code)))[0];assert n<=16
    targets=struct.unpack('<'+code*n,f.read(struct.calcsize(code)*n))
    dest.write(struct.pack('<'+'I'*(n+1),n,*targets))
  assert not original.read(1) and not baseline.read(1) and not candidate.read(1)
 conversion[d]={p.name:sha(p) for p in sources}
 for v in ['baseline','candidate']:
  p=host/(d+'-'+v+'.trace.csv.final-edges.csv');conversion[d][p.name]=sha(p)
(host/'topology-inputs.json').write_text(json.dumps(conversion,indent=2)+'\n')
reports=['persistent-update-20261007','update-trace-20261008','edge-restoration-20261008']
(host/'previous-evidence.json').write_text(json.dumps({r:{n:sha(Path('lite/benchmark/results')/r/n) for n in ['raw.tar.gz','members.json','manifest.json']} for r in reports},indent=2)+'\n')
for name in ['prepare.py','run.py','package.py']:shutil.copyfile(host/name,out/name.replace('.py','-host.py'))
files={p.name:p for p in host.iterdir() if p.is_file() and p.suffix!='.py' and not p.name.endswith(('.trace.csv.final-edges.csv','.trace.csv.edges.csv')) and p.name not in {d+'-'+v+'.u32' for d in ['sift','cohere'] for v in ['baseline','candidate']}}
with tarfile.open(out/'raw.tar.gz','w:gz') as archive:
 for name,p in sorted(files.items()):archive.add(p,arcname=name)
(out/'members.json').write_text(json.dumps({n:sha(p) for n,p in files.items()},indent=2)+'\n')
(out/'manifest.json').write_text(json.dumps({p.name:sha(p) for p in out.iterdir() if p.is_file() and p.name!='manifest.json'},indent=2)+'\n')
