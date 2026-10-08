from pathlib import Path
import hashlib,json,shutil,struct
import numpy as np
root=Path(__file__).resolve().parent;old=Path('/home/ubuntu/project/vsag-lite-persistent-20261007');prior=Path('/home/ubuntu/project/vsag-lite-restoration-validation-20261008')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();records=[]
for dataset in ['sift','cohere','gist']:
 info=next(r for r in json.loads((old/'prepared.json').read_text()) if r['dataset']==dataset);count=info['count'];dim=info['dim'];cycles=1000
 source=Path(info['snapshot']);assert sha(source)==info['snapshot_sha256'];out=root/dataset;out.mkdir(exist_ok=False)
 query_source=(prior/'gist-supplement/queries.fvecs' if dataset=='gist' else old/dataset/'queries.fvecs')
 initial_truth=(Path('/home/ubuntu/project/vsag-lite-gist-holdout-20261006/scale-100000/groundtruth.ivecs') if dataset=='gist' else old/dataset/'groundtruth.ivecs')
 shutil.copyfile(query_source,out/'queries.fvecs');shutil.copyfile(initial_truth,out/'groundtruth.ivecs')
 vectors=np.memmap(source,mode='r',dtype='<f4',offset=64+8*count,shape=(count,dim))
 targets=np.arange(cycles,dtype=np.int64)*8191%count;donors=(np.arange(cycles,dtype=np.int64)+cycles)*8191%count
 assert len(set(targets))==len(set(donors))==cycles and not set(targets)&set(donors)
 replacement=((vectors[targets].copy()+vectors[donors].copy())*np.float32(.5)).astype('<f4')
 if dataset=='cohere':
  norm=np.sqrt(np.sum(replacement.astype(np.float64)**2,axis=1));assert np.all(norm>0)
  replacement=(replacement.astype(np.float64)/norm[:,None]).astype('<f4')
 assert np.all(np.isfinite(replacement)) and np.all(np.any(replacement!=vectors[targets],axis=1))
 with (out/'replacement.fvecs').open('wb') as f:
  for r in replacement:f.write(struct.pack('<I',dim)+r.tobytes())
 with (out/'replacement-map.csv').open('w') as f:
  f.write('cycle,id,donor_id,squared_displacement\n')
  for cycle,(a,b) in enumerate(zip(targets,donors)):
   diff=replacement[cycle].astype(np.float64)-vectors[a].astype(np.float64);f.write(f'{cycle},{a},{b},{float(np.dot(diff,diff)):.17g}\n')
 queries=np.fromfile(out/'queries.fvecs',dtype='<i4').reshape(-1,dim+1);assert np.all(queries[:,0]==dim);queries=queries[:,1:].copy().view('<f4');nq=len(queries);assert nq==({'sift':100,'cohere':100,'gist':300}[dataset])
 changed=np.array(vectors,dtype='<f4');changed[targets]=replacement;ids=np.arange(count,dtype=np.int64);truth=[]
 for i,q in enumerate(queries):
  distances=np.empty(count,dtype=np.float64)
  for start in range(0,count,4096):
   stop=min(start+4096,count);diff=changed[start:stop].astype(np.float64)-q.astype(np.float64);distances[start:stop]=np.einsum('ij,ij->i',diff,diff)
  truth.append(np.lexsort((ids,distances))[:10].astype('<i4'))
  if (i+1)%25==0:print(dataset,'changed truth',i+1,flush=True)
 with (out/'changed-groundtruth.ivecs').open('wb') as f:
  for r in truth:f.write(struct.pack('<I',10)+r.tobytes())
 info.update(cycles=cycles,query_count=nq,query_rows=([100,400] if dataset=='gist' else [0,100]),normalized_replacement=dataset=='cohere')
 info['files']={p.name:sha(p) for p in out.iterdir()};records.append(info);(root/'prepared.json').write_text(json.dumps(records,indent=2)+'\n')
 del changed
 print(dataset,'prepared',flush=True)
