import hashlib,json,shutil
from pathlib import Path
root=Path(__file__).resolve().parent
out=Path('/home/ubuntu/project/vsag-lite-baseline-v01/lite/benchmark/results/full-mixed-20261006')
out.mkdir(parents=True,exist_ok=True)
raw={}
for p in sorted(root.rglob('*')):
 if not p.is_file() or p.name.endswith('.snapshot'):continue
 relative=p.relative_to(root)
 raw[str(relative)]=hashlib.sha256(p.read_bytes()).hexdigest()
 target=out/relative;target.parent.mkdir(parents=True,exist_ok=True)
 if p.suffix in ['.log','.txt']:
  target.write_text('\n'.join(line.rstrip() for line in p.read_text().splitlines())+'\n')
 else:shutil.copyfile(p,target)
(out/'original-evidence-sha256.json').write_text(json.dumps(raw,indent=2)+'\n')
published={str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest() for p in out.rglob('*') if p.is_file() and p.name!='sha256.json'}
(out/'sha256.json').write_text(json.dumps(published,indent=2)+'\n')
