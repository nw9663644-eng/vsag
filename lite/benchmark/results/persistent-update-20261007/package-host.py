from pathlib import Path
import json,hashlib,tarfile,shutil
host=Path(__file__).resolve().parent;out=Path('lite/benchmark/results/persistent-update-20261007')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for p in Path('/tmp').glob('lite-persistent-*.log'):shutil.copyfile(p,host/p.name)
identity=json.loads((host/'identity.json').read_text())
for name in ['build-lite-fragment-release/libvsag-lite.so','build-lite-diverse-repair-release/libvsag-lite.so','build-lite-baseline-asan/lite_graph_route_probe','build-lite-baseline-asan/libvsag-lite.so','AGENTS.md','docs/agents/coding-standards.md']:
    p=Path(name).resolve();identity['files'][str(p)]=sha(p)
(host/'identity.json').write_text(json.dumps(identity,indent=2)+'\n')
for name in ['prepare.py','run.py','package.py']:shutil.copyfile(host/name,out/(name.replace('.py','-host.py')))
files={p.name:p for p in host.iterdir() if p.is_file() and p.suffix not in ['.py']}
for record in json.loads((host/'prepared.json').read_text()):
    dataset=record['dataset']
    for p in (host/dataset).iterdir():files[dataset+'-'+p.name]=p
with tarfile.open(out/'raw.tar.gz','w:gz') as archive:
    for name,p in sorted(files.items()):archive.add(p,arcname=name)
(out/'members.json').write_text(json.dumps({n:sha(p) for n,p in files.items()},indent=2)+'\n')
(out/'manifest.json').write_text(json.dumps({p.name:sha(p) for p in out.iterdir() if p.name!='manifest.json'},indent=2)+'\n')
