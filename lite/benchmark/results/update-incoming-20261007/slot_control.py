from pathlib import Path
import struct,json,hashlib,subprocess,csv,io
root=Path(__file__).resolve().parent
source=root/'after-crud-r0.snapshot';target=root/'after-crud-restored-slot-order.snapshot'
assert not target.exists()
blob=source.read_bytes();magic=blob[:8];version,dim,count,payload,kind=struct.unpack_from('<5Q',blob,8)
assert magic==b'VSAGLT01' and version==2 and kind==2 and payload+48==len(blob)
assert count==10000 and dim==768
ids=list(struct.unpack_from('<'+str(count)+'q',blob,64));assert len(set(ids))==count
offset=64+count*8;vectors=blob[offset:offset+count*dim*4];offset+=count*dim*4
links=[]
for slot in range(count):
 degree=struct.unpack_from('<Q',blob,offset)[0];offset+=8
 neighbors=list(struct.unpack_from('<'+str(degree)+'Q',blob,offset));offset+=degree*8
 assert all(x<count and x!=slot for x in neighbors) and len(neighbors)==len(set(neighbors));links.append(neighbors)
assert offset==len(blob)
order=sorted(range(count),key=lambda x:ids[x]);remap={old:new for new,old in enumerate(order)}
parts=[blob[:64],struct.pack('<'+str(count)+'q',*[ids[i] for i in order]),b''.join(vectors[i*dim*4:(i+1)*dim*4] for i in order)]
for i in order:parts.extend([struct.pack('<Q',len(links[i])),struct.pack('<'+str(len(links[i]))+'Q',*[remap[x] for x in links[i]])])
rebuilt=b''.join(parts);assert len(rebuilt)==len(blob);target.write_bytes(rebuilt)
# Independently compare all external-ID edges and vector bytes under the mapping.
new_ids=[ids[i] for i in order];new_vectors=parts[2]
assert all(new_vectors[j*dim*4:(j+1)*dim*4]==vectors[i*dim*4:(i+1)*dim*4] for j,i in enumerate(order))
assert all([new_ids[remap[x]] for x in links[i]]==[ids[x] for x in links[i]] for i in order)
cmd=['taskset','-c','0','build-lite-fragment-release/lite_graph_route_probe',str(target),str(root.with_name('vsag-lite-cohere-normalized-20261006')/'prepared/scale-10000'),str(root/'slot-control.csv'),'128','uniform','preserve','1']
result=subprocess.run(cmd,capture_output=True,text=True);(root/'slot-control.stdout.log').write_text(result.stdout);(root/'slot-control.stderr.log').write_text(result.stderr);assert result.returncode==0,result.stderr
row=next(csv.DictReader(io.StringIO(result.stdout)));native=next(csv.DictReader((root/'slot-control.csv.api.csv').open()))
(root/'slot-control.json').write_text(json.dumps({'command':cmd,'exit':result.returncode,'source_sha256':hashlib.sha256(blob).hexdigest(),'reordered_sha256':hashlib.sha256(rebuilt).hexdigest(),'all_vector_bytes_equal_by_id':True,'all_ordered_edges_equal_by_id':True,'slots_reordered':sum(i!=j for j,i in enumerate(order)),'scalar':row,'native':native,'scope':'Combined physical-slot ring/entry/tie-order control, not isolated ring effect; no new policy adoption or budget tuning'},indent=2)+'\n')
print(row);print(native)
