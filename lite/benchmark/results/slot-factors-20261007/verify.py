#!/usr/bin/env python3
"""Audit archived slot-factor outputs without the large host snapshots."""
import collections,csv,gzip,hashlib,json,pathlib,struct
root=pathlib.Path(__file__).resolve().parent
for name,digest in json.loads((root/'manifest.json').read_text()).items():
    assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest,name
raw=(root/'groundtruth.ivecs').read_bytes(); truth=[]; offset=0
while offset<len(raw):
    count=struct.unpack_from('<i',raw,offset)[0]; offset+=4
    truth.append(set(struct.unpack_from('<'+'i'*count,raw,offset))); offset+=4*count
assert len(truth)==100

def rows(name):
    with gzip.open(root/(name+'.gz'),'rt',newline='') as stream: return list(csv.DictReader(stream))
def neighbors(case):
    result=collections.defaultdict(list)
    for r in rows(case+'.csv.neighbors.csv'):
        key=(int(r['query']),int(r['mask'])); assert int(r['rank'])==len(result[key])
        result[key].append(int(r['id']))
    return result
cases=['initial','full-churn','cycle-1099','cycle-3000','cycle-7112']
for case in cases:
    original=neighbors(case); ordered=neighbors(case+'-ordered')
    for name,ids in [(case,original),(case+'-ordered',ordered)]:
        traces=rows(name+'.csv'); assert len(traces)==800
        assert len({(r['query'],r['mask']) for r in traces})==800
        for r in traces:
            q,m=int(r['query']),int(r['mask']); returned=ids[q,m]
            assert int(r['eligible'])==1 and len(returned)==10 and len(set(returned))==10
            assert int(r['hits'])==len(set(returned)&truth[q])
            assert int(r['baseline_native_ids_equal'])==int(m==0)
    assert all(original[q,7]==ordered[q,0] for q in range(100))
    baseline={r['query']:r for r in rows(case+'.csv') if r['mask']=='0'}
    legacy=rows(case+'.legacy.csv')
    for r in legacy:
        for metric in ['hits','truth_visited','visited_nodes','expanded_nodes','distance_evaluations']:
            assert r[metric]==baseline[r['query']][metric]
assert all(r['exit']==0 for r in json.loads((root/'commands.json').read_text()))
print('PASS: manifest; 8,000 traces; truth hits; 1,000 native baseline receipts; 500 ordered controls; legacy metrics')
