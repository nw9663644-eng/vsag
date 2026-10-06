import pathlib,json,hashlib,csv,statistics,math
import numpy as np
root=pathlib.Path('/home/ubuntu/project/vsag-lite-sift-matched-20261006')
def vec(path):
 x=np.fromfile(path,dtype='<f4').reshape(-1,129)
 return x[:,1:]
old=vec(pathlib.Path('/home/ubuntu/project/vsag-lite-datasets/sift/prepared-10k-100k/scale-100000/queries.fvecs'))
validation=vec(root/'validation/scale-100000/queries.fvecs');final=vec(root/'final/scale-100000/queries.fvecs')
seen={q.tobytes() for q in np.vstack([old,validation])}
assert not any(q.tobytes() in seen for q in final)
base=vec(root/'final/scale-100000/base.fvecs').astype(np.float64)
truth=np.fromfile(root/'final/scale-100000/groundtruth.ivecs',dtype='<i4').reshape(-1,11)[:,1:]
ids=np.arange(len(base));checked=[0,42,85,128,170,213,256,299]
for i in checked:
 d=((base-final[i].astype(np.float64))**2).sum(axis=1)
 assert np.array_equal(np.lexsort((ids,d))[:10],truth[i])
(root/'input-audit.json').write_text(json.dumps({'final_queries':len(final),'byte_overlap_with_first_400':0,'float64_exact_truth_rows_checked':checked,'all_checks_passed':True},indent=2)+'\n')
summary=[]
for every in [1,10]:
 for mode in ['default','diverse']:
  rows=[]
  for repeat in [1,2,3]:
   path=root/f'final-{mode}-every{every}-r{repeat}.csv.api.csv.crud.csv'
   with path.open() as f:r=next(csv.DictReader(f))
   with pathlib.Path(str(path)+'.mixed.csv').open() as f:events=list(csv.DictReader(f))
   with pathlib.Path(str(path)+'.samples.csv').open() as f:samples=list(csv.DictReader(f))
   assert len(samples)==2000 and len(events)==2000//every==int(r['mixed_queries'])
   values=sorted(float(e['latency_us']) for e in events)
   for fraction,key in [(.5,'mixed_search_p50_us'),(.99,'mixed_search_p99_us')]: assert abs(values[math.ceil(fraction*len(values))-1]-float(r[key]))<.000002
   assert float(r['recall_at_k'])>=.95
   rows.append(r)
  s={'mode':mode,'query_every':every,'replicates':3}
  for key in ['recall_at_k','mixed_recall_at_k','crud_loop_cpu_ms','mixed_query_cpu_ms','mixed_loop_cpu_ms','mixed_search_p50_us','mixed_search_p99_us']:
   vals=[float(r[key]) for r in rows];s[key]={'median':statistics.median(vals),'min':min(vals),'max':max(vals)}
  summary.append(s)
(root/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print('12 runs audited; final queries do not overlap old/validation; 8 exact FP64 truth checks passed')
