from pathlib import Path
import json,hashlib,tarfile,shutil
host=Path(__file__).resolve().parent;out=Path('lite/benchmark/results/storage-control-20261007');previous=Path('lite/benchmark/results/persistent-update-20261007')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for p in Path('/tmp').glob('lite-storage-*.log'):shutil.copyfile(p,host/p.name)
identity=json.loads((host/'identity.json').read_text())
for name in ['build-lite-fragment-release/libvsag-lite.so','build-lite-diverse-repair-release/libvsag-lite.so','build-lite-baseline-asan/lite_graph_route_probe','build-lite-baseline-asan/libvsag-lite.so']:
    p=Path(name).resolve();identity['files'][str(p)]=sha(p)
(host/'identity.json').write_text(json.dumps(identity,indent=2)+'\n')
old_members=json.loads((previous/'members.json').read_text())
with tarfile.open(previous/'raw.tar.gz','r:gz') as archive:
    for member in archive.getmembers():
        if member.name in ['prepared.json','identity.json'] or any(member.name.startswith(d+'-'+v+'.csv') for d in ['sift','gist','cohere'] for v in ['baseline','candidate']) or member.name.endswith(('.fvecs','.ivecs')):
            data=archive.extractfile(member).read();assert hashlib.sha256(data).hexdigest()==old_members[member.name]
            target=member.name if member.name=='prepared.json' or member.name.endswith(('.fvecs','.ivecs')) else 'update-'+member.name
            (host/target).write_bytes(data)
receipt={'previous_report_revision':'24601b707ddd2834850e900470077539555553e7','sha256':{p.name:sha(p) for p in [previous/'raw.tar.gz',previous/'members.json',previous/'manifest.json']}}
(host/'previous-evidence.json').write_text(json.dumps(receipt,indent=2)+'\n')
for name in ['run.py','package.py']:shutil.copyfile(host/name,out/(name.replace('.py','-host.py')))
files={p.name:p for p in host.iterdir() if p.is_file() and p.suffix!='.py'}
with tarfile.open(out/'raw.tar.gz','w:gz') as archive:
    for name,p in sorted(files.items()):archive.add(p,arcname=name)
(out/'members.json').write_text(json.dumps({n:sha(p) for n,p in files.items()},indent=2)+'\n')
(out/'manifest.json').write_text(json.dumps({p.name:sha(p) for p in out.iterdir() if p.is_file() and p.name!='manifest.json'},indent=2)+'\n')
