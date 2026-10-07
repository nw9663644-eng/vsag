#!/usr/bin/env python3
"""Recompute archived truth hits, native checks and artifact hashes."""
from pathlib import Path
import collections,csv,gzip,hashlib,json,math,statistics,struct,random
root=Path(__file__).resolve().parent
for name,digest in json.loads((root/'manifest.json').read_text()).items():
    assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest,name

def rows(name):
    with gzip.open(root/(name+'.gz'),'rt',newline='') as f:return list(csv.DictReader(f))
def truth(name):
    data=(root/(name+'-groundtruth.ivecs')).read_bytes();offset=0;result=[]
    while offset<len(data):
        k=struct.unpack_from('<i',data,offset)[0];offset+=4
        result.append(set(struct.unpack_from('<'+'i'*k,data,offset)));offset+=4*k
    return result

def neighbors(name,mask=False):
    result=collections.defaultdict(list)
    for r in rows(name):
        q=int(r['query']);key=(q,int(r['mask'])) if mask else q
        assert int(r['rank'])==len(result[key]);assert math.isfinite(float.fromhex(r['distance']))
        result[key].append(int(r['id']))
    for ids in result.values():assert len(ids)==len(set(ids))==10
    return result
runs=json.loads((root/'runs.json').read_text());assert len(runs)==12
for r in runs:
    assert r['exit']==0
    stem=f"{r['variant']}-{r['flow']}-r{r['repeat']}";expected=truth('cohere')
    ids=neighbors(stem+'.hits.csv.neighbors.csv')
    hits=rows(stem+'.hits.csv');assert len(hits)==len(expected)==100
    for h in hits:assert int(h['hits'])==len(set(ids[int(h['query'])])&expected[int(h['query'])])
    assert abs(sum(int(h['hits']) for h in hits)/1000-float(r['metrics']['recall_at_k']))<1e-6
    with gzip.open(root/(stem+'.time.csv.gz'),'rt') as f:cpu=sum(map(float,f.read().strip().split(',')))
    assert abs(cpu-r['whole_cpu_s'])<1e-8
assert len({r['snapshot_sha256'] for r in runs if r['flow']=='build'})==1
for r in json.loads((root/'summary.json').read_text()):
    selected=[x for x in runs if x['variant']==r['variant'] and x['flow']==r['flow']]
    assert statistics.median(x['whole_cpu_s'] for x in selected)==r['median_whole_cpu_s']
commands=json.loads((root/'validation-commands.json').read_text());assert len(commands)==11 and all(r['exit']==0 for r in commands)
for c in json.loads((root/'native-commands.json').read_text()):
    assert c['exit']==0
    expected=truth('validation' if c['name'].startswith('cohere') else c['name'].split('-')[0])
    ids=neighbors(c['name']+'.native.csv.neighbors.csv',True)
    traces=rows(c['name']+'.native.csv');assert len(traces)==8*len(expected)
    for r in traces:
        q,m=int(r['query']),int(r['mask']);assert r['eligible']=='1'
        assert int(r['baseline_native_ids_equal'])==int(m==0)
        assert int(r['hits'])==len(set(ids[q,m])&expected[q]);assert ids[q,m]==ids[q,0]
for c in commands[3:]:
    expected=truth(c['name'].split('-')[0]);ids=neighbors(c['name']+'.hits.csv.neighbors.csv')
    hits=rows(c['name']+'.hits.csv');assert len(hits)==100
    for r in hits:assert int(r['hits'])==len(set(ids[int(r['query'])])&expected[int(r['query'])])
    assert abs(sum(int(r['hits']) for r in hits)/1000-float(c['metrics']['recall_at_k']))<1e-6
for r in json.loads((root/'paired-summary.json').read_text()):
    d=r['dataset']
    if d=='cohere':a,b='baseline-crud-r0.hits.csv','candidate-crud-r0.hits.csv'
    elif d=='validation':a,b='cohere-validation-baseline.csv','cohere-validation-candidate.csv'
    else:a,b=d+'-baseline-crud.hits.csv',d+'-candidate-crud.hits.csv'
    left,right=rows(a),rows(b);delta=[int(y['hits'])-int(x['hits']) for x,y in zip(left,right)]
    assert len(delta)==r['queries'];assert sum(x>0 for x in delta)==r['wins'];assert sum(x<0 for x in delta)==r['losses']
    assert all(x['query']==y['query'] for x,y in zip(left,right))
    rng=random.Random(20261007);boot=sorted(sum(rng.choices(delta,k=len(delta)))/(10*len(delta)) for _ in range(5000))
    assert [boot[125],boot[4874]]==r['bootstrap_mean_delta_95']
    n=r['wins']+r['losses'];pv=min(1,2*sum(math.comb(n,i) for i in range(min(r['wins'],r['losses'])+1))/2**n) if n else 1
    assert pv==r['sign_p']
    assert sum(int(x['hits']) for x in left)/(10*len(left))==r['baseline']
    assert sum(int(x['hits']) for x in right)/(10*len(right))==r['candidate']
def source_ids(name):
    data=(root/(name+'-source-query-ids.i64')).read_bytes();return set(struct.unpack('<'+'q'*(len(data)//8),data))
assert source_ids('cohere').isdisjoint(source_ids('validation'))
assert json.loads((root/'validation-manifest.json').read_text())['query_rows']==[100,400]
assert json.loads((root/'restoration.json').read_text())['src_include_unchanged']
ident=json.loads((root/'identity.json').read_text())
assert hashlib.sha256((root/'candidate_graph_backend.cpp.txt').read_bytes()).hexdigest()==ident['files'][next(x for x in ident['files'] if x.endswith('/src/lite/graph_backend.cpp'))]
host=[]
for r in runs:
    path=Path(r['command'][r['command'].index('10000')-2]);assert path.suffix=='.snapshot'
    available=path.exists()
    if available:assert hashlib.sha256(path.read_bytes()).hexdigest()==r['snapshot_sha256']
    host.append(available)
print(json.dumps({'archive':'PASS','primary_runs':12,'cross_data_runs':8,'independent_queries':300,'native_id_set_checks':1300,'host_primary_snapshots_available':all(host)},indent=2))
