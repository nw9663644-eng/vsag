from pathlib import Path
import csv,json,struct
root=Path(__file__).resolve().parent
def read(path):
 data=path.read_bytes();assert data[:8]==b'VSAGLT01'
 version,dim,count,payload,kind=struct.unpack_from('<5Q',data,8)
 assert version==2 and kind==2 and payload+48==len(data)
 ids=struct.unpack_from('<'+str(count)+'q',data,64);assert len(set(ids))==count
 start=64+count*8;vec=data[start:start+count*dim*4];offset=start+count*dim*4;edges={};vectors={}
 for slot,id in enumerate(ids):
  length=struct.unpack_from('<Q',data,offset)[0];offset+=8;neighbors=struct.unpack_from('<'+str(length)+'Q',data,offset);offset+=length*8
  assert all(x<count and x!=slot for x in neighbors) and len(set(neighbors))==length
  edges[id]=set(ids[x] for x in neighbors);vectors[id]=vec[slot*dim*4:(slot+1)*dim*4]
 assert offset==len(data);return edges,vectors
old,v=read(root/'before-build-r0.snapshot');new,w=read(root/'after-crud-r0.snapshot');assert v==w
control,cv=read(root/'after-crud-restored-slot-order.snapshot');assert new==control and w==cv
common=sum(len(old[id]&new[id]) for id in old);original=sum(len(x) for x in old.values());final=sum(len(x) for x in new.values())
a=list(csv.DictReader((root/'after-crud-r0.queries.csv').open()));b=list(csv.DictReader((root/'slot-control.csv').open()));assert len(a)==len(b)==100
result={'all_vector_bytes_equal_by_id':True,'original_edges':original,'post_edges':final,'common_external_id_edges':common,'original_edge_retention':common/original,'slot_control_query_wins':sum(int(y['hits'])>int(x['hits']) for x,y in zip(a,b)),'slot_control_query_losses':sum(int(y['hits'])<int(x['hits']) for x,y in zip(a,b)),'slot_control_query_ties':sum(x['hits']==y['hits'] for x,y in zip(a,b))}
(root/'edge-retention.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
