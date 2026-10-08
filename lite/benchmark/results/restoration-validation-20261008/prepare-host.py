from pathlib import Path
import hashlib,json,struct,shutil
import numpy as np
root=Path(__file__).resolve().parent;out=root/'gist-supplement';old=Path('/home/ubuntu/project/vsag-lite-persistent-20261007')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
info=next(r for r in json.loads((old/'prepared.json').read_text()) if r['dataset']=='gist')
snapshot=Path(info['snapshot']);query_source=Path('/home/ubuntu/project/vsag-lite-datasets/gist/hf-100k/queries.fbin')
assert sha(snapshot)==info['snapshot_sha256']
with query_source.open('rb') as f:
 count,dim=struct.unpack('<2I',f.read(8));assert(count,dim)==(1000,960)
 f.seek(8+100*dim*4);queries=np.frombuffer(f.read(300*dim*4),dtype='<f4').reshape(300,dim).copy()
assert np.all(np.isfinite(queries))
original=np.fromfile('/home/ubuntu/project/vsag-lite-gist-holdout-20261006/scale-100000/queries.fvecs',dtype='<i4').reshape(300,961)
assert np.all(original[:,0]==dim) and np.array_equal(original[:,1:].view('<f4'),queries)
with (out/'queries.fvecs').open('wb') as f:
 for q in queries:f.write(struct.pack('<i',dim)+q.tobytes())
vectors=np.memmap(snapshot,mode='r',dtype='<f4',offset=64+8*100000,shape=(100000,dim))
slots=(np.arange(10000,dtype=np.int64)*8191)%100000;first=vectors[:,0].copy();first[slots]=(first[slots]+np.float32(.125)).astype('<f4')
assert np.all(first[slots]!=vectors[slots,0])
ids=np.arange(100000,dtype=np.int64);truth=[]
for i,q in enumerate(queries):
 distances=np.empty(100000,dtype=np.float64)
 for start in range(0,100000,4096):
  stop=min(100000,start+4096);diff=vectors[start:stop].astype(np.float64)-q.astype(np.float64)
  diff[:,0]=first[start:stop].astype(np.float64)-float(q[0])
  distances[start:stop]=np.einsum('ij,ij->i',diff,diff)
 truth.append(np.lexsort((ids,distances))[:10].astype('<i4'))
 if (i+1)%25==0:print('gist changed truth',i+1,flush=True)
with (out/'groundtruth.ivecs').open('wb') as f:
 for r in truth:f.write(struct.pack('<i',10)+r.tobytes())
info.update(dataset='gist-supplement',query_count=300,query_rows=[100,400],query_source=str(query_source),query_source_sha256=sha(query_source),query_history='previously observed in historical holdout; not used for restoration selection')
info['files']={p.name:sha(p) for p in out.iterdir()}
(root/'gist-prepared.json').write_text(json.dumps(info,indent=2)+'\n')
shutil.copyfile('/home/ubuntu/project/vsag-lite-gist-holdout-20261006/holdout-manifest.json',root/'historical-gist-holdout.json')
shutil.copyfile('/home/ubuntu/project/vsag-lite-gist-final-20261006/holdout-manifest.json',root/'historical-gist-final.json')
print('prepared300',flush=True)
