"""Cross-distribution audit; historical GIST queries are never relabeled blind."""
import csv
import hashlib
import io
import json
import math
import random
from pathlib import Path
import struct
import tarfile

ROOT = Path(__file__).resolve().parent

def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1048576),b''):h.update(block)
    return h.hexdigest()

def archive(path):
    result={}
    with tarfile.open(path,'r:gz') as tar:
        for m in tar.getmembers():
            assert m.isfile() and Path(m.name).name==m.name and m.name not in result
            result[m.name]=tar.extractfile(m).read()
    return result

def main():
    for name,value in json.loads((ROOT/'manifest.json').read_text()).items():
        assert Path(name).name==name and digest(ROOT/name)==value
    raw=archive(ROOT/'raw.tar.gz');members=json.loads((ROOT/'members.json').read_text());assert raw.keys()==members.keys()
    for name,value in members.items():assert hashlib.sha256(raw[name]).hexdigest()==value
    references={}
    for report,hashes in json.loads(raw['previous-evidence.json']).items():
        folder=ROOT.parent/report
        for name,value in hashes.items():assert digest(folder/name)==value
        references[report]=archive(folder/'raw.tar.gz')
    plan=json.loads(raw['plan.json']);assert plan['masks']==[0,1] and (plan['degree'],plan['ef'],plan['cycles'])==(16,128,10000) and plan['no_policy_or_budget_retuning']
    identity=json.loads(raw['identity.json']);assert identity['plan_sha256']==hashlib.sha256(raw['plan.json']).hexdigest()
    sources=all(Path(p).is_file() for p in identity['files'])
    if sources:
        for p,value in identity['files'].items():assert digest(p)==value,p
    infos={r['dataset']:r for r in json.loads(raw['prepared.json'])};assert set(infos)=={'sift','cohere','gist-supplement'}
    assert json.loads(raw['historical-gist-holdout.json'])['selected_rows_half_open']==[100,400]
    assert json.loads(raw['historical-gist-final.json'])['selected_rows_half_open']==[400,1000]
    rows=lambda data:list(csv.DictReader(io.StringIO(data.decode())))
    def read_row(data,offset,a):
        n=struct.unpack_from('<I',data,offset)[0];offset+=4;assert n<=16
        targets=struct.unpack_from('<'+'I'*n,data,offset);offset+=4*n
        assert len(set(targets))==n and all(0<=b<100000 and b!=a for b in targets)
        return targets,offset
    def single(data):
        links=[];offset=0
        for a in range(100000):r,offset=read_row(data,offset,a);links.append(r)
        assert offset==len(data);return links
    traces=json.loads(raw['traces.json']);assert len(traces)==4 and all(t['exit']==0 for t in traces)
    runs=json.loads(raw['runs.json']);assert len(runs)==12 and all(r['exit']==0 for r in runs)
    assert {(r['dataset'],r['variant'],r['mask']) for r in runs}=={(d,v,m) for d in infos for v in ['baseline','candidate'] for m in [0,1]}
    updated={c*8191%100000 for c in range(10000)};summaries=[];host_checks=0;distance_checks=0;state_count=0
    for dataset,info in infos.items():
        count,dim,qcount=info['count'],info['dim'],info['query_count'];assert count==100000 and info['cycles']==10000 and dim=={'sift':128,'cohere':768,'gist-supplement':960}[dataset]
        assert qcount==plan['datasets'][dataset]['queries']
        if dataset=='gist-supplement':
            prior=references['update-trace-20261008'];initial=single(prior['initial-edges.csv.u32']);maintained={v:single(prior[v+'.csv.final-edges.csv.u32']) for v in ['baseline','candidate']}
            assert info['query_rows']==[100,400] and info['query_count']==300
        else:
            data=raw[dataset+'-topologies.u32'];offset=0;groups=[[],[],[]]
            for a in range(count):
                for group in groups:r,offset=read_row(data,offset,a);group.append(r)
            assert offset==len(data);initial=groups[0];maintained={'baseline':groups[1],'candidate':groups[2]}
        queries_data=raw[dataset+'-queries.fvecs'];truth_data=raw[dataset+'-groundtruth.ivecs'];assert len(queries_data)==qcount*(4+4*dim) and len(truth_data)==qcount*44
        assert hashlib.sha256(queries_data).hexdigest()==info['files']['queries.fvecs']
        assert hashlib.sha256(truth_data).hexdigest()==info['files']['groundtruth.ivecs' if dataset=='gist-supplement' else 'changed-groundtruth.ivecs']
        queries=[];truths=[]
        for q in range(qcount):
            assert struct.unpack_from('<I',queries_data,q*(4+4*dim))[0]==dim and struct.unpack_from('<I',truth_data,q*44)[0]==10
            query=struct.unpack_from('<'+'f'*dim,queries_data,q*(4+4*dim)+4);truth=set(struct.unpack_from('<10i',truth_data,q*44+4))
            assert all(math.isfinite(x) for x in query) and len(truth)==10 and all(0<=i<count for i in truth);queries.append(query);truths.append(truth)
        snapshot=Path(info['snapshot']);host=snapshot.is_file()
        if host:
            assert digest(snapshot)==info['snapshot_sha256'];host_checks+=1
            with snapshot.open('rb') as f:
                f.seek(64+8*count+4*dim*count)
                for expected in initial:
                    n=struct.unpack('<Q',f.read(8))[0];assert tuple(struct.unpack('<'+'Q'*n,f.read(8*n)))==expected
                assert not f.read(1)
            if dataset=='gist-supplement':
                source=Path(info['query_source']);assert digest(source)==info['query_source_sha256']
                with source.open('rb') as f:
                    assert struct.unpack('<2I',f.read(8))==(1000,dim);f.seek(8+100*dim*4)
                    for q in queries:assert struct.unpack('<'+'f'*dim,f.read(4*dim))==q
        variant_hits={};variant_ids={}
        for variant in ['baseline','candidate']:
            packed=b''.join(struct.pack('<'+'I'*(len(r)+1),len(r),*r) for r in maintained[variant])
            adjacency_sha=hashlib.sha256(packed).hexdigest()
            if dataset!='gist-supplement':
                bindings=json.loads(raw['topology-inputs.json'])[dataset]
                assert adjacency_sha==bindings[dataset+'-'+variant+'.u32']
                text='source,rank,target\n'+''.join(f'{a},{rank},{b}\n' for a,r in enumerate(maintained[variant]) for rank,b in enumerate(r))
                assert hashlib.sha256(text.encode()).hexdigest()==bindings[dataset+'-'+variant+'.trace.csv.final-edges.csv']
                assert rows(raw[dataset+'-'+variant+'.trace.csv.neighbors.csv'])==rows(references['persistent-update-20261007'][dataset+'-'+variant+'.csv.neighbors.csv'])
            for mask in [0,1]:
                name=dataset+'-'+variant+'-'+str(mask)+'.csv';receipt=json.loads(raw[name+'.receipt.json'])
                assert (receipt['mask'],receipt['cycles'],receipt['count'],receipt['dim'],receipt['max_degree'],receipt['ef_search'],receipt['exit'])==(mask,10000,count,dim,16,128,0)
                assert receipt['input_snapshot_sha256']==info['snapshot_sha256'] and receipt['adjacency_sha256']==adjacency_sha
                assert receipt['binary_sha256']==identity['files'][next(p for p in identity['files'] if p.endswith('/lite_graph_slot_probe'))]
                assert receipt['restored_rows']==mask*10000
                chosen=[initial[a] if mask==1 and a in updated else maintained[variant][a] for a in range(count)];edges=sum(map(len,chosen));assert receipt['explicit_edges']==edges
                if host:
                    h=hashlib.sha256()
                    with snapshot.open('rb') as f:
                        magic=f.read(8);fields=list(struct.unpack('<7Q',f.read(56)));assert magic==b'VSAGLT01' and (fields[0],fields[1],fields[2],fields[4],fields[5],fields[6])==(2,dim,count,2,16,128)
                        fields[3]=16+16*count+4*count*dim+8*edges;h.update(magic+struct.pack('<7Q',*fields));h.update(f.read(8*count))
                        for first in range(0,count,256):
                            n=min(256,count-first);data=bytearray(f.read(n*dim*4));assert len(data)==n*dim*4
                            for a in range(first,first+n):
                                if a in updated:
                                    at=(a-first)*dim*4;value=struct.unpack_from('<f',data,at)[0];struct.pack_into('<f',data,at,value+.125)
                            h.update(data)
                        for r in chosen:h.update(struct.pack('<Q',len(r))+struct.pack('<'+'Q'*len(r),*r))
                    assert h.hexdigest()==receipt['control_sha256'],name
                states=rows(raw[name]);neighbors=rows(raw[name+'.neighbors.csv']);assert len(states)==qcount*8 and len(neighbors)==qcount*80
                hits=[];idsets=[];vectors={};f=snapshot.open('rb') if host else None
                for q in range(qcount):
                    keys0=[]
                    for slot_mask in range(8):
                        state=states[q*8+slot_mask];assert (int(state['query']),int(state['mask']),state['eligible'],state['k'])==(q,slot_mask,'1','10')
                        assert state['baseline_native_ids_equal']==('1' if slot_mask==0 else '0');keys=[]
                        for rank,r in enumerate(neighbors[(q*8+slot_mask)*10:(q*8+slot_mask+1)*10]):
                            assert (int(r['query']),int(r['mask']),int(r['rank']))==(q,slot_mask,rank)
                            i,dist=int(r['id']),float.fromhex(r['distance']);assert 0<=i<count and math.isfinite(dist) and dist>=0;keys.append((dist,i))
                            if f and slot_mask==0:
                                if i not in vectors:
                                    f.seek(64+8*count+4*dim*i);v=list(struct.unpack('<'+'f'*dim,f.read(4*dim)))
                                    if i in updated:v[0]=struct.unpack('<f',struct.pack('<f',v[0]+.125))[0]
                                    vectors[i]=v
                                exact=sum((float(a)-float(b))**2 for a,b in zip(queries[q],vectors[i]));assert math.isclose(dist,exact,rel_tol=3e-6,abs_tol=1e-6);distance_checks+=1
                        assert keys==sorted(keys) and len({i for _,i in keys})==10
                        hit=len({i for _,i in keys}&truths[q]);assert int(state['hits'])==hit and hit<=int(state['truth_visited'])<=10
                        if slot_mask==0:keys0=keys;hits.append(hit);idsets.append({i for _,i in keys})
                        else:
                            assert keys==keys0
                            assert all(state[k]==states[q*8][k] for k in ['hits','truth_visited','visited_nodes','expanded_nodes','distance_evaluations','tie_comparisons'])
                        assert 0<int(state['expanded_nodes'])<=int(state['visited_nodes'])<=count
                    if mask==0 and dataset!='gist-supplement':
                        ref=rows(raw[dataset+'-'+variant+'.trace.csv.trace-neighbors.csv'])[q*10:(q+1)*10]
                        assert keys0==[(float.fromhex(r['distance']),int(r['id'])) for r in ref]
                if f:f.close()
                variant_hits[variant,mask]=hits;variant_ids[variant,mask]=idsets;state_count+=qcount
                summaries.append(dict(dataset=dataset,variant=variant,mask=mask,query_count=qcount,recall=sum(hits)/(qcount*10),explicit_edges=edges,
                                      mean_visited_nodes=sum(int(states[q*8]['visited_nodes']) for q in range(qcount))/qcount,
                                      visited_not_returned=sum(int(states[q*8]['truth_visited'])-hits[q] for q in range(qcount))))
        for result in [r for r in summaries if r['dataset']==dataset and r['mask']==1]:
            v=result['variant'];delta=[b-a for a,b in zip(variant_hits[v,0],variant_hits[v,1])]
            rng=random.Random(20261008)
            bootstrap=sorted(sum(rng.choices(delta,k=qcount))/(qcount*10) for _ in range(10000))
            wins=sum(d>0 for d in delta);losses=sum(d<0 for d in delta);nonzero=wins+losses
            sign_p=min(1.0,2*sum(math.comb(nonzero,i) for i in range(min(wins,losses)+1))/(2**nonzero)) if nonzero else 1.0
            result['exploratory_paired_bootstrap_95']=[bootstrap[249],bootstrap[9749]]
            result['two_sided_sign_p']=sign_p
            result.update(net_hits=sum(delta),wins=sum(d>0 for d in delta),losses=sum(d<0 for d in delta),ties=sum(d==0 for d in delta),
                          gained_truth=sum(len((variant_ids[v,1][q]-variant_ids[v,0][q])&truths[q]) for q in range(qcount)),
                          lost_truth=sum(len((variant_ids[v,0][q]-variant_ids[v,1][q])&truths[q]) for q in range(qcount)))
    assert state_count==2000
    print(json.dumps(dict(pass_checks=True,host_snapshots_verified=host_checks,host_sources_verified=sources,
                          factor_query_states=state_count,native_calibrations=state_count,slot_query_states=state_count*8,
                          distance_checks=distance_checks,gist_history='historically observed; not selection queries; not blind',results=summaries),indent=2))

if __name__=='__main__':main()
