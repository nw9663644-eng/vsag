# Copyright 2024-present the vsag project
# SPDX-License-Identifier: Apache-2.0
"""Verify21long-window runs; repetitions are not independent query samples."""
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
commands=json.loads((out / 'commands.json').read_text())
assert len(rows)==21 and len(commands)==23 and all(c['exit']==0 for c in commands)
for name,digest in identity['sources'].items():
    assert hashlib.sha256((out / ('source-'+Path(name).name)).read_bytes()).hexdigest()==digest
for name in ['queries.fvecs','groundtruth.ivecs']:
    assert hashlib.sha256((out / name).read_bytes()).hexdigest()==identity['inputs'][name]
def read(path):
    with path.open() as stream:
        return list(csv.DictReader(stream))
native=read(out / 'native.csv.neighbors.csv')
assert len(native)==1000
raw=(out / 'groundtruth.ivecs').read_bytes()
assert len(raw)==4400
truth=[set(struct.unpack_from('<11i',raw,offset)[1:]) for offset in range(0,len(raw),44)]
summary={}
for row in rows:
    tag=f"{row['trial']}-{row['variant']}"
    times=read(out / (tag+'.queries.csv'))
    neighbors=read(out / (tag+'.neighbors.csv'))
    assert len(times)==1000 and len(neighbors)==10000
    for i,item in enumerate(neighbors):
        expected=native[i%1000]
        assert int(item['query'])==i//10 and int(item['rank'])==i%10
        assert item['id']==expected['id'] and item['distance']==expected['distance']
        assert math.isfinite(float.fromhex(item['distance']))
    hits=0
    for q in range(1000):
        assert int(times[q]['query'])==q
        ids={int(v['id']) for v in neighbors[10*q:10*(q+1)]}
        assert len(ids)==10 and all(0<=id<100000 for id in ids)
        hits+=len(ids.intersection(truth[q%100]))
    assert hits==8590
    latency=[float(r['latency_us']) for r in times]
    assert all(math.isfinite(t) and t>0 for t in latency)
    ordered=sorted(latency)
    assert row['p50_us']==ordered[499] and row['p99_us']==ordered[989]
    assert row['mean_us']==statistics.mean(latency)
for variant in ['control','candidate','reference']:
    values=[r for r in rows if r['variant']==variant]
    assert sorted(r['trial'] for r in values)==list(range(7))
    summary[variant]={key:statistics.median(r[key] for r in values) for key in ['mean_us','p50_us','p99_us']}
comparisons={}
for baseline in ['control','reference']:
    comparisons[baseline]={}
    for key in ['mean_us','p50_us','p99_us']:
        paired=[]
        for trial in range(7):
            pair={r['variant']:r[key] for r in rows if r['trial']==trial}
            paired.append(100*(pair['candidate']/pair[baseline]-1))
        comparisons[baseline][key]=dict(median_change_percent=100*(summary['candidate'][key]/summary[baseline][key]-1),
            paired_changes_percent=paired,wins=sum(p<0 for p in paired))
(out / 'audit.json').write_text(json.dumps(dict(status='PASS',runs=21,executed_queries=21000,
    distinct_queries=100,ordered_neighbors=210000,commands=23,summary=summary,comparisons=comparisons,
    scope='100 historical queries repeated10times; not1000 unique queries or final P99/quality acceptance'),indent=2)+'\n')
print(json.dumps(dict(summary=summary,comparisons=comparisons),indent=2))
print('PASS21runs21000executedqueries100distinct; native ordered results and repeated truth exact')
