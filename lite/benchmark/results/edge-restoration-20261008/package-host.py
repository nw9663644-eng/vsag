from pathlib import Path
import json,hashlib,tarfile,shutil
host=Path(__file__).resolve().parent;out=Path('lite/benchmark/results/edge-restoration-20261008');previous=Path('lite/benchmark/results/update-trace-20261008')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for p in Path('/tmp').glob('edge-restoration-*.log'):shutil.copyfile(p,host/p.name)
for name in ['queries.fvecs','groundtruth.ivecs']:shutil.copyfile(host/'dataset'/name,host/name)
(host/'previous-evidence.json').write_text(json.dumps({n:sha(previous/n) for n in ['raw.tar.gz','members.json','manifest.json']},indent=2)+'\n')
for name in ['run.py','package.py']:shutil.copyfile(host/name,out/name.replace('.py','-host.py'))
files={p.name:p for p in host.iterdir() if p.is_file() and p.suffix!='.py'}
with tarfile.open(out/'raw.tar.gz','w:gz') as archive:
 for name,p in sorted(files.items()):archive.add(p,arcname=name)
(out/'members.json').write_text(json.dumps({n:sha(p) for n,p in files.items()},indent=2)+'\n')
(out/'manifest.json').write_text(json.dumps({p.name:sha(p) for p in out.iterdir() if p.is_file() and p.name!='manifest.json'},indent=2)+'\n')
