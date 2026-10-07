#!/usr/bin/env python3
# Copyright 2024-present the vsag project
# SPDX-License-Identifier: Apache-2.0
"""Audit raw operation/query samples and aggregate receipts; never extract tar paths."""
from pathlib import Path
import csv,hashlib,io,json,math,statistics,tarfile
root=Path(__file__).resolve().parent
for name,digest in json.loads((root/'manifest.json').read_text()).items():
    assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest,name
count=0;sample_count=0;query_events=0;host=[]
for phase,expected_runs,cycles in [('pilot',24,1000),('extended',18,10000)]:
    folder=root/phase
    with tarfile.open(root/(phase+'-raw.tar.gz'),'r:gz') as tar:
        raw={m.name:tar.extractfile(m).read() for m in tar.getmembers() if m.isfile()}
    index=json.loads((folder/'raw-index.json').read_text());assert set(raw)==set(index)
    for name,digest in index.items():assert hashlib.sha256(raw[name]).hexdigest()==digest
    def rows(name):return list(csv.DictReader(io.StringIO(raw[name].decode())))
    runs=json.loads((folder/'runs.json').read_text());assert len(runs)==expected_runs
    keys={(r['dataset'],r['variant'],r['query_every'],r['repeat']) for r in runs};assert len(keys)==expected_runs
    traces={}
    for r in runs:
        assert r['exit']==0
        name=r['name'];freq=r['query_every'];metric=rows(name+'.csv.api.csv.crud.csv')[0]
        assert metric==r['metrics'];assert int(metric['cycles'])==cycles
        assert int(metric['query_every'])==freq and int(metric['mixed_queries'])==cycles//freq
        samples=rows(name+'.csv.api.csv.crud.csv.samples.csv');assert len(samples)==cycles
        assert [int(s['cycle']) for s in samples]==list(range(cycles))
        for sample_key,metric_key in [('update_changed_us','update_changed_p50_us'),('restore_us','restore_p50_us'),('remove_us','remove_p50_us'),('readd_us','readd_p50_us')]:
            values=sorted(float(s[sample_key]) for s in samples)
            assert all(math.isfinite(v) and v>=0 for v in values)
            assert abs(values[(cycles-1)//2]-float(metric[metric_key]))<1.1e-6
        mixed=rows(name+'.csv.api.csv.crud.csv.mixed.csv');assert len(mixed)==cycles//freq
        assert [int(s['query_event']) for s in mixed]==list(range(len(mixed)))
        assert [int(s['query']) for s in mixed]==[i%100 for i in range(len(mixed))]
        latencies=sorted(float(s['latency_us']) for s in mixed)
        assert all(math.isfinite(v) and v>=0 for v in latencies)
        for fraction,key in [(.5,'mixed_search_p50_us'),(.99,'mixed_search_p99_us')]:
            assert abs(latencies[math.ceil(fraction*len(latencies))-1]-float(metric[key]))<1.1e-6
        assert 0<=float(metric['recall_at_k'])<=1 and 0<=float(metric['mixed_recall_at_k'])<=1
        assert float(metric['mixed_loop_cpu_ms'])+1e-3>=float(metric['crud_loop_cpu_ms'])+float(metric['mixed_query_cpu_ms'])
        scalar=rows(name+'.csv');initial=rows(name+'.stdout.log')[0];api=rows(name+'.csv.api.csv')[0]
        assert len(scalar)==100 and int(initial['query_count'])==100
        assert abs(sum(int(s['hits']) for s in scalar)/1000-float(initial['recall_at_k']))<1e-6
        assert abs(float(api['recall_at_k'])-float(initial['recall_at_k']))<1e-6
        digest=hashlib.sha256(raw[name+'.csv']).hexdigest()
        assert traces.setdefault(r['dataset'],digest)==digest
        if phase=='extended':
            user,system,rss=map(float,raw[name+'.time.csv'].decode().strip().split(','))
            assert user>=0 and system>=0 and rss>0
        count+=1;sample_count+=cycles;query_events+=len(mixed)
    for s in json.loads((folder/'summary.json').read_text()):
        selected=[r for r in runs if (r['dataset'],r['variant'],r['query_every'])==(s['dataset'],s['variant'],s['query_every'])]
        assert len(selected)==s['runs']
        for key,value in s['median'].items():assert statistics.median(float(r['metrics'][key]) for r in selected)==value
    identity=json.loads((folder/'identity.json').read_text())
    for r in runs:
        lib=Path(r['library_path'])/'libvsag-lite.so';available=lib.exists()
        if available:assert hashlib.sha256(lib.read_bytes()).hexdigest()==identity['libraries'][r['variant']]
        host.append(available)
    for path,digest in identity['files'].items():
        p=Path(path);available=p.exists()
        if available:assert hashlib.sha256(p.read_bytes()).hexdigest()==digest
        host.append(available)
for options in json.loads((root/'initial-options.json').read_text()):assert (options['count'],options['degree'],options['ef'])==(100000,16,128)
print(json.dumps({'archive':'PASS','successful_runs':count,'mutation_cycles':sample_count,'mutation_calls':4*sample_count,'mixed_query_events':query_events,'host_inputs_available':all(host),'recall_scope':'runner aggregates; post/mixed per-query IDs are not exported','roundtrip_scope':'successful runner exits include exact ID/distance Save-Load comparisons'},indent=2))
