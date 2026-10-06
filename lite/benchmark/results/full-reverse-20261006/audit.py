import csv,json,math,statistics
from pathlib import Path
root=Path(__file__).resolve().parent
protocol=json.loads((root/'protocol.json').read_text())
assert protocol['use_reverse_edges'] is True
controls=json.loads((root/'controls.json').read_text())
assert len(controls)==12 and all(r['returncode']==0 for r in controls)
commands=json.loads((root/'commands.json').read_text())
assert len(commands)==6 and all(row['exit']==0 for row in commands)
rows=[]
for record in commands:
 prefix=Path(record['command'][5])
 summary=next(csv.DictReader(Path(str(prefix)+'.crud.csv').open()))
 samples=list(csv.DictReader(Path(str(prefix)+'.crud.samples.csv').open()))
 queries=list(csv.DictReader(Path(str(prefix)+'.mixed.csv').open()))
 log=Path(str(prefix)+'.stdout.log').read_text()
 initial=next(csv.DictReader(log[log.index('mode,base_count,'):].splitlines()))
 every=int(summary['query_every'])
 assert len(samples)==1000 and len(queries)==1000//every
 assert [int(r['cycle']) for r in samples]==list(range(1000))
 assert [int(r['query']) for r in queries]==[i%600 for i in range(len(queries))]
 assert all(0<=int(r['hits'])<=int(r['returned_count'])<=10 for r in queries)
 recall=sum(int(r['hits']) for r in queries)/(len(queries)*10)
 assert abs(recall-float(summary['mixed_recall_at_k']))<=1e-6
 latencies=sorted(float(r['latency_us']) for r in queries)
 for field,fraction in [('mixed_p50_us',.5),('mixed_p99_us',.99)]:
  assert abs(float(summary[field])-latencies[math.ceil(len(latencies)*fraction)-1])<1e-6
 assert int(initial['base_count'])==100000 and int(initial['query_count'])==600
 assert int(initial['query_ef_search'])==128
 row={'name':prefix.name,'initial':initial,'after':summary,
      'short_query_events':sum(int(r['returned_count'])<10 for r in queries),
      'quality_pass':float(summary['end_recall_at_k'])>=.95,
      'mutation_p50_us':{key:statistics.median(float(r[key]) for r in samples)
                         for key in ['update_us','restore_us','remove_us','readd_us']}}
 rows.append(row)
(root/'summary.json').write_text(json.dumps(rows,indent=2)+'\n')
medians=[]
for every in [1,10]:
 group=[r for r in rows if int(r['after']['query_every'])==every]
 medians.append({'query_every':every,'quality_passes':sum(r['quality_pass'] for r in group),
 'short_query_events':sum(r['short_query_events'] for r in group),
 'initial_recall':statistics.median(float(r['initial']['recall_at_k']) for r in group),
 **{key:statistics.median(float(r['after'][key]) for r in group) for key in
 ['end_recall_at_k','mixed_recall_at_k','mutation_cpu_ms','query_cpu_ms','mixed_loop_cpu_ms','mixed_p50_us','mixed_p99_us']}})
(root/'medians.json').write_text(json.dumps(medians,indent=2)+'\n')
print(json.dumps(medians,indent=2))
print('AUDIT: 6000 four-operation cycles; 3300 mixed queries; six Save/Load roundtrip checks passed')
