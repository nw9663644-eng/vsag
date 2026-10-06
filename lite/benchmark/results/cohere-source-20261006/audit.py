import pathlib,json,hashlib
import numpy as np
import pyarrow.parquet as pq
root=pathlib.Path('/home/ubuntu/project/vsag-lite-datasets/cohere/cohere-small-100k')
result={'official_definition':'https://github.com/zilliztech/VectorDBBench/blob/main/vectordb_bench/backend/dataset.py','mirror_configuration':'https://github.com/zilliztech/VectorDBBench/blob/main/vectordb_bench/__init__.py','source_metric':'cosine','download_mirror':'https://assets.zilliz.com.cn/benchmark/cohere_small_100k/','status':'raw files validated; no ANN recall or performance measurement; normalized squared-L2 preparation pending','original_s3_attempt':'timed out at 300s; incomplete train.parquet.part retained; not used'}
for name,expected in [('train.parquet',100000),('test.parquet',1000)]:
 p=root/name;table=pq.read_table(p,columns=['id','emb']);ids=table['id'].combine_chunks().to_numpy();emb=table['emb'].combine_chunks()
 lengths=np.diff(emb.offsets.to_numpy());assert np.all(lengths==768)
 vectors=emb.values.to_numpy().reshape(-1,768);assert len(vectors)==expected and len(np.unique(ids))==expected
 assert np.all(np.isfinite(vectors))
 norms=[]
 for start in range(0,len(vectors),4096):
  values=vectors[start:start+4096].astype(np.float64)
  norms.extend(np.sqrt(np.einsum('ij,ij->i',values,values)).tolist())
 assert min(norms)>0
 result[name]={'rows':len(vectors),'dim':768,'unique_ids':len(np.unique(ids)),'source_ids_contiguous_in_row_order':bool(np.array_equal(ids,np.arange(expected))),'all_finite':True,'zero_norm_count':0,'norm_min':min(norms),'norm_max':max(norms),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
path=pathlib.Path('/home/ubuntu/project/vsag-lite-cohere-source-20261006/audit.json');path.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
