import hashlib, json, subprocess
from pathlib import Path
root=Path(__file__).parent
repo=Path('/home/ubuntu/project/vsag-lite-baseline-v01')
snapshot=Path('/home/ubuntu/project/vsag-lite-noop-update-20261007/before-build-r0.snapshot')
dataset=Path('/home/ubuntu/project/vsag-lite-cohere-normalized-20261006/prepared/scale-10000')
binary=repo/'build-lite-fragment-release/lite_graph_mutation_trace'
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''): h.update(b)
    return h.hexdigest()
provenance={'parent':subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip(),'files':{str(p):sha(p) for p in [snapshot,binary,repo/'build-lite-fragment-release/libvsag-lite.so',repo/'lite/benchmark/graph_mutation_trace.cpp',dataset/'queries.fvecs',dataset/'groundtruth.ivecs']},'runs':[]}
for r in range(2,4):
    cmd=['taskset','-c','0',str(binary),str(snapshot),str(dataset),str(root/f'events-r{r}.csv')]
    with (root/f'checkpoints-r{r}.csv').open('wb') as out,(root/f'trace-r{r}.stderr.log').open('wb') as err:
        result=subprocess.run(cmd,stdout=out,stderr=err)
    provenance['runs'].append({'command':cmd,'exit':result.returncode})
    (root/'protocol-final.json').write_text(json.dumps(provenance,indent=2)+'\n')
    print('run',r,'exit',result.returncode,flush=True)
    assert result.returncode==0
assert (root/'events-r2.csv').read_bytes()==(root/'events-r3.csv').read_bytes()
assert (root/'checkpoints-r2.csv').read_bytes()==(root/'checkpoints-r3.csv').read_bytes()
print('two deterministic traces identical',flush=True)
