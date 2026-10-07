# Copyright 2024-present the vsag project
# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import csv,hashlib,json,tarfile,shutil,subprocess,os,struct
root=Path(__file__).resolve().parent;repo=Path.cwd();out=repo/'lite/benchmark/results/diverse-repair-scale-20261007';out.mkdir(exist_ok=False)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for phase,host in [('pilot',root),('extended',root/'extended')]:
    dest=out/phase;dest.mkdir();index={}
    with tarfile.open(out/(phase+'-raw.tar.gz'),'w:gz') as archive:
        for p in sorted(host.iterdir()):
            if p.is_file() and p.suffix in ['.csv','.log']:
                archive.add(p,arcname=p.name);index[p.name]=sha(p)
    (dest/'raw-index.json').write_text(json.dumps(index,indent=2)+'\n')
    for name in ['identity.json','protocol.json','runs.json','summary.json']:
        shutil.copy2(host/name,dest/name)
for name in ['run.py','run_extended.py','package.py']:shutil.copy2(root/name,out/name)
options=[]
for p in [Path(x) for x in json.loads((root/'identity.json').read_text())['files'] if x.endswith('.snapshot')]:
    with p.open('rb') as f:header=f.read(64)
    values=struct.unpack('<7Q',header[8:]);assert header[:8]==b'VSAGLT01'
    assert values[2]==100000 and values[5]==16 and values[6]==128
    options.append(dict(path=str(p),version=values[0],dim=values[1],count=values[2],kind=values[4],degree=values[5],ef=values[6]))
(out/'initial-options.json').write_text(json.dumps(options,indent=2)+'\n')
for variant,build in [('baseline','build-lite-fragment-release'),('candidate','build-lite-diverse-repair-release')]:
    env=dict(os.environ,LD_LIBRARY_PATH=str(repo/build))
    (out/(variant+'-ldd.txt')).write_text(subprocess.check_output(['ldd',str(repo/'build-lite-fragment-release/lite_graph_route_probe')],text=True,env=env))
shutil.copy2(repo/'lite/benchmark/graph_route_probe.cpp',out/'measured_graph_route_probe.cpp.txt')
shutil.copy2(repo/'lite/benchmark/results/diverse-repair-20261007/candidate.patch',out/'candidate.patch')
(out/'environment.txt').write_text(subprocess.check_output(['uname','-a'],text=True)+subprocess.check_output(['lscpu'],text=True))
comparison=[]
for phase in ['pilot','extended']:
    rows=json.loads((out/phase/'summary.json').read_text())
    for dataset in ['sift','gist','cohere']:
        for freq in sorted({r['query_every'] for r in rows}):
            base=next(r for r in rows if (r['dataset'],r['variant'],r['query_every'])==(dataset,'baseline',freq))
            candidate=next(r for r in rows if (r['dataset'],r['variant'],r['query_every'])==(dataset,'candidate',freq))
            comparison.append(dict(phase=phase,dataset=dataset,query_every=freq,baseline=base['median'],candidate=candidate['median'],mutation_cpu_change_percent=100*(candidate['median']['crud_loop_cpu_ms']/base['median']['crud_loop_cpu_ms']-1)))
(out/'comparison.json').write_text(json.dumps(comparison,indent=2)+'\n')
print(json.dumps([{'dataset':r['dataset'],'recall':[r['baseline']['recall_at_k'],r['candidate']['recall_at_k']],'mixed_recall':[r['baseline']['mixed_recall_at_k'],r['candidate']['mixed_recall_at_k']],'mutation_ms':[r['baseline']['crud_loop_cpu_ms'],r['candidate']['crud_loop_cpu_ms']],'mutation_change_percent':r['mutation_cpu_change_percent']} for r in comparison if r['phase']=='extended'],indent=2))
