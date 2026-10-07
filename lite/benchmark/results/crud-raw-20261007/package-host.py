from pathlib import Path
import hashlib,json,tarfile,shutil,subprocess,os
host=Path(__file__).resolve().parent;out=Path('lite/benchmark/results/crud-raw-20261007')
runs=json.loads((host/'runs.json').read_text());assert len(runs)==6
for dataset in ['sift','gist','cohere']:
    run=next(r for r in runs if r['dataset']==dataset)
    shutil.copyfile(Path(run['command'][10])/'groundtruth.ivecs',host/(dataset+'-groundtruth.ivecs'))
for name in ['lite-crud-evidence-build.log','lite-crud-evidence-test.log','lite-crud-slot-test.log','lite-crud-tidy.log','lite-crud-asan-build.log','lite-crud-asan-test.log']:
    shutil.copyfile(Path('/tmp')/name,host/name)
for variant,build in [('baseline','build-lite-fragment-release'),('candidate','build-lite-diverse-repair-release')]:
    env=os.environ.copy();env['LD_LIBRARY_PATH']=str(Path(build).resolve())
    (host/(variant+'-ldd.log')).write_bytes(subprocess.check_output(['ldd','build-lite-fragment-release/lite_graph_route_probe'],env=env))
    with (host/(variant+'-persistent.log')).open('wb') as f:
        subprocess.run(['build-lite-fragment-release/lite_graph_route_probe','--self-test'],env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
identity=json.loads((host/'identity.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for name in ['lite/benchmark/test_graph_route_probe.py','build-lite-baseline-asan/lite_graph_route_probe','build-lite-baseline-asan/libvsag-lite.so']:
    path=Path(name).resolve();identity['files'][str(path)]=sha(path)
for variant,build in [('baseline','build-lite-fragment-release'),('candidate','build-lite-diverse-repair-release')]:
    path=Path(build+'/libvsag-lite.so').resolve();assert sha(path)==identity['libraries'][variant];identity['files'][str(path)]=sha(path)
(host/'identity.json').write_text(json.dumps(identity,indent=2)+'\n')
for name in ['run.py','package.py']:
    shutil.copyfile(host/name,out/(name.replace('.py','-host.py')))
files=sorted(p for p in host.iterdir() if p.is_file() and p.name not in ['run.py','package.py'])
with tarfile.open(out/'raw.tar.gz','w:gz') as archive:
    for p in files:archive.add(p,arcname=p.name)
(out/'members.json').write_text(json.dumps({p.name:sha(p) for p in files},indent=2)+'\n')
(out/'manifest.json').write_text(json.dumps({p.name:sha(p) for p in out.iterdir() if p.name!='manifest.json'},indent=2)+'\n')
