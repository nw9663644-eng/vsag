from pathlib import Path
import hashlib,json,shutil,tarfile
HOST=Path(__file__).resolve().parent; REPO=Path('/home/ubuntu/project/vsag-lite-baseline-v01'); OUT=REPO/'lite/benchmark/results/diverse-old-gate-pilot-20261008'
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
OUT.mkdir(parents=True,exist_ok=False); items={}
def add(p,n=None): p=Path(p);n=n or p.name;assert p.is_file() and n not in items;items[n]=p
for n in ['analysis.json','previous-evidence.json','build-receipts.json','graph_backend.cpp','fixture.cpp','candidate.patch','format.log','tidy.log']:
 add(HOST/n)
for v in ['release','asan']:
 for n in ['build.log','fixture.log','baseline-fixture.log','existing-tests.log']:add(HOST/v/n,v+'-'+n)
for stem in ['diverse-coordinate-gist','diverse-coordinate-gist-r2']:
 for suffix in ['.csv','.csv.neighbors.csv','.csv.updates.csv','.log']:add(HOST/(stem+suffix))
members={n:sha(p) for n,p in sorted(items.items())}
with tarfile.open(OUT/'raw.tar.gz','w:gz',compresslevel=9) as t:
 for n,p in sorted(items.items()):t.add(p,arcname=n)
(OUT/'members.json').write_text(json.dumps(members,indent=2)+'\n')
for s,d in [('README.md','README.md'),('verify.py','verify.py'),('package.py','package-host.py'),('candidate.patch','candidate.patch')]:shutil.copyfile(HOST/s,OUT/d)
print(OUT)
