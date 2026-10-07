from pathlib import Path
import hashlib,json,struct,shutil
import numpy as np
root=Path(__file__).resolve().parent
old=Path('/home/ubuntu/project/vsag-lite-crud-raw-20261007')
runs=json.loads((old/'runs.json').read_text())
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda:f.read(1048576),b''):h.update(block)
    return h.hexdigest()
records=[]
for dataset in ['sift','gist','cohere']:
    run=next(r for r in runs if r['dataset']==dataset)
    snap=Path(run['command'][9]);source=Path(run['command'][10]);out=root/dataset;out.mkdir(exist_ok=False)
    with snap.open('rb') as f:header=f.read(64)
    version,dim,count,payload,kind,degree,ef=struct.unpack('<7Q',header[8:])
    assert version==kind==2 and count==100000 and ef==128 and degree==16
    ids=np.memmap(snap,mode='r',dtype='<i8',offset=64,shape=(count,))
    assert np.array_equal(ids,np.arange(count))
    vectors=np.memmap(snap,mode='r',dtype='<f4',offset=64+8*count,shape=(count,dim))
    raw=np.fromfile(source/'queries.fvecs',dtype='<i4').reshape(-1,dim+1)
    assert len(raw)==100 and np.all(raw[:,0]==dim)
    queries=raw[:,1:].copy().view('<f4')
    slots=(np.arange(10000,dtype=np.int64)*8191)%count
    assert len(np.unique(slots))==10000
    first=vectors[slots,0].copy();changed=(first+np.float32(0.125)).astype(np.float32)
    assert np.all(np.isfinite(changed)) and np.all(first!=changed)
    mask=np.zeros(count,dtype=bool);mask[slots]=True
    first_changed=vectors[:,0].copy();first_changed[slots]=changed
    truths=[[],[]]
    for q,query in enumerate(queries):
        distances=[np.empty(count,dtype=np.float64),np.empty(count,dtype=np.float64)]
        for start in range(0,count,4096):
            stop=min(start+4096,count)
            diff=vectors[start:stop].astype(np.float64)-query.astype(np.float64)
            distances[0][start:stop]=np.einsum('ij,ij->i',diff,diff)
            diff[:,0]=first_changed[start:stop].astype(np.float64)-float(query[0])
            distances[1][start:stop]=np.einsum('ij,ij->i',diff,diff)
        for i in range(2):truths[i].append(np.lexsort((ids,distances[i]))[:10].astype('<i4'))
        if (q+1)%25==0:print(dataset,'truth',q+1,flush=True)
    for name,truth in zip(['groundtruth.ivecs','changed-groundtruth.ivecs'],truths):
        with (out/name).open('wb') as f:
            for row in truth:f.write(struct.pack('<i',10)+row.tobytes())
    original=np.fromfile(source/'groundtruth.ivecs',dtype='<i4').reshape(100,11)[:,1:]
    matches=sum(set(a)==set(b) for a,b in zip(original,truths[0]))
    assert matches==100,(dataset,matches)
    shutil.copyfile(source/'queries.fvecs',out/'queries.fvecs')
    moved=sum(set(a)!=set(b) for a,b in zip(truths[0],truths[1]))
    record=dict(dataset=dataset,snapshot=str(snap),snapshot_sha256=sha(snap),dim=int(dim),count=int(count),cycles=10000,initial_truth_matches_original=matches,changed_truth_queries=moved,files={p.name:sha(p) for p in out.iterdir()})
    records.append(record);(root/'prepared.json').write_text(json.dumps(records,indent=2)+'\n')
    print(dataset,'prepared',moved,'changed truth queries',flush=True)
