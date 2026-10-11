# Copyright 2024-present the vsag project
# SPDX-License-Identifier: Apache-2.0
"""Independently check bitmap allocation savings and public-query parity."""
import csv
import hashlib
import json
import math
from pathlib import Path
import statistics
import struct
import sys

out=Path(sys.argv[1])
identity=json.loads((out / 'identity.json').read_text())
rows=json.loads((out / 'rows.json').read_text())
allocations=json.loads((out / 'allocations.json').read_text())
commands=json.loads((out / 'commands.json').read_text())
assert len(rows)==168 and len(allocations)==24 and len(commands)==206
assert all(c['exit']==0 for c in commands)
for name,digest in identity['sources'].items():
    assert hashlib.sha256((out / ('source-'+Path(name).name)).read_bytes()).hexdigest()==digest

def read_csv(path):
    with path.open() as stream:
        return list(csv.DictReader(stream))

summary={}
for label,receipt in identity['inputs'].items():
    for name in ['queries.fvecs','groundtruth.ivecs']:
        assert hashlib.sha256((out / (label+'.'+name)).read_bytes()).hexdigest()==receipt['hashes'][name]
    count=receipt['count']
    payload=(count//64+int(count%64!=0))*8
    raw_truth=(out / (label+'.groundtruth.ivecs')).read_bytes()
    assert len(raw_truth)==4400
    truth=[]
    for offset in range(0,len(raw_truth),44):
        record=struct.unpack_from('<11i',raw_truth,offset)
        assert record[0]==10 and len(set(record[1:]))==10
        truth.append(set(record[1:]))
    for storage in ['fp32','fp16','rabitq8']:
        cell=label+'-'+storage
        reference=(out / (cell+'-native.csv.neighbors.csv')).read_bytes()
        neighbors=read_csv(out / (cell+'-native.csv.neighbors.csv'))
        assert len(neighbors)==1000
        hits=0
        for q in range(100):
            ids=[]
            for rank,item in enumerate(neighbors[q*10:(q+1)*10]):
                assert int(item['query'])==q and int(item['rank'])==rank
                assert math.isfinite(float.fromhex(item['distance']))
                ids.append(int(item['id']))
            assert len(set(ids))==10 and all(0<=id<count for id in ids)
            hits+=len(truth[q].intersection(ids))
        raw_alloc={}
        for variant in ['control','candidate']:
            tag=cell+'-'+variant+'-allocation'
            assert (out / (tag+'.neighbors.csv')).read_bytes()==reference
            counts=read_csv(out / (tag+'.csv'))
            assert len(counts)==100 and [int(q['query']) for q in counts]==list(range(100))
            raw_alloc[variant]=counts
            recorded=[a for a in allocations if a['dataset']==label and a['storage']==storage and a['variant']==variant]
            assert len(recorded)==1
            for field,key in [('ordinary_new_requests','median_requests'),('ordinary_new_bytes','median_bytes')]:
                assert statistics.median(int(q[field]) for q in counts)==recorded[0][key]
        for old,new in zip(raw_alloc['control'],raw_alloc['candidate']):
            assert int(old['ordinary_new_requests'])==int(new['ordinary_new_requests'])
            assert int(old['ordinary_new_bytes'])-int(new['ordinary_new_bytes'])==count-payload
            assert int(old['count_sized_requests'])==1 and int(new['count_sized_requests'])==0
        summary[cell]=dict(recall=hits/1000,visited_old_bytes=count,visited_new_bytes=payload,
            query_requested_bytes={v:statistics.median(int(q['ordinary_new_bytes']) for q in raw_alloc[v]) for v in raw_alloc})
        for variant in ['control','candidate']:
            values=[r for r in rows if r['dataset']==label and r['storage']==storage and r['variant']==variant]
            assert sorted(r['trial'] for r in values)==list(range(7))
            for row in values:
                tag=f"{cell}-{row['trial']}-{variant}"
                assert (out / (tag+'.neighbors.csv')).read_bytes()==reference
                queries=read_csv(out / (tag+'.queries.csv'))
                assert len(queries)==100 and [int(q['query']) for q in queries]==list(range(100))
                times=sorted(float(q['latency_us']) for q in queries)
                assert all(math.isfinite(t) and t>0 for t in times)
                assert times[49]==row['p50_us'] and times[98]==row['p99_us']
            summary[cell][variant]={k:statistics.median(r[k] for r in values) for k in ['p50_us','p99_us']}
        for key in ['p50_us','p99_us']:
            paired=[]
            for trial in range(7):
                pair={r['variant']:r[key] for r in rows if r['dataset']==label and r['storage']==storage and r['trial']==trial}
                paired.append(100*(pair['candidate']/pair['control']-1))
            summary[cell][key+'_paired_changes_percent']=paired
            summary[cell][key+'_pair_wins']=sum(value<0 for value in paired)
            summary[cell][key+'_median_change_percent']=100*(summary[cell]['candidate'][key]/summary[cell]['control'][key]-1)
    print(label,'verified',flush=True)
(out / 'audit.json').write_text(json.dumps(dict(status='PASS',timed_runs=168,timed_queries=16800,
    allocation_runs=24,allocation_queries=2400,commands=206,summary=summary),indent=2)+'\n')
for cell,value in summary.items():
    print(cell,value['p50_us_median_change_percent'],value['p50_us_pair_wins'],value['query_requested_bytes'])
print('PASS exact public ordered IDs/hex distances; per-query allocation reduction exact bitmap payload difference')
