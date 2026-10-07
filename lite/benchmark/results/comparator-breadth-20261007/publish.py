from pathlib import Path
import json,hashlib,statistics,subprocess
root=Path(__file__).resolve().parent
out=Path('lite/benchmark/results/comparator-breadth-20261007');out.mkdir(parents=True,exist_ok=False)
raw={}
for p in root.iterdir():
 if p.is_file() and p.suffix in ['.csv','.json','.txt','.log','.py']:
  data=p.read_bytes();raw[p.name]=hashlib.sha256(data).hexdigest()
  if p.suffix in ['.txt','.log']:data=(p.read_text().rstrip()+'\n').encode()
  (out/p.name).write_bytes(data)
rows=json.loads((out/'summary.json').read_text());pairs=json.loads((out/'pairs.json').read_text());assert len(rows)==24 and len(pairs)==12
metrics=[]
for case in ['sift100k','gist10k']:
 for flow in ['build','crud']:
  selected=[x for x in rows if x['case']==case and x['flow']==flow]
  assert len(selected)==6
  for key in ['snapshot_sha256','neighbors_sha256','hits_sha256','recall_at_k']:assert len({x[key] for x in selected})==1,(case,flow,key)
  values={v:statistics.median(x['cpu_seconds'] for x in selected if x['variant']==v) for v in ['old','new']}
  metrics.append({'case':case,'flow':flow,'cpu_seconds':values,'change_percent':100*(values['new']/values['old']-1),'recall':selected[0]['recall_at_k']})
(out/'audit.json').write_text(json.dumps(metrics,indent=2)+'\n');(out/'raw-sha256.json').write_text(json.dumps(raw,indent=2)+'\n')
(out/'environment.txt').write_text((subprocess.check_output(['uname','-a'],text=True)+subprocess.check_output(['lscpu'],text=True)).rstrip()+'\n')
text='''# Comparator breadth verification, 2026-10-07

Source parent d806f14825eb35942655d1732c0f6cf5969302b2. No new C++ or algorithm change.
Default policy OFF only. Extend previous Cohere10k comparison to SIFT100k/128dim
and GIST10k/960dim, each with existing100 observed prefix queries, L2 Top10,
degree16/construction/query128. Fixed settings, no recall retuning or new holdout.
Build-only vs build plus1000 distinct-ID same-vector Update/Remove/Add cycles:
1% of SIFT100k and10% of GIST10k. Not full-ID churn or the four-call changed/restore
mixed protocol. All operation/live-count/query/roundtrip checks run in the probe.

## Protocol and results

CPU0, three fresh processes per case/flow/variant,24 runs. Variant/case/flow order
reverses on odd repeat. Same current diagnostic runner, old/new libraries explicitly
selected through LD_LIBRARY_PATH, ldd and hashes. Libraries/runner match the previous
comparator study exactly; no intervening build/test/profiler workload.
/usr/bin/time user+system covers WHOLE process (IO/staging/build/optional CRUD/query/
SaveLoad/output),0.01s resolution; this is not isolated mutation/search timing.
Three repeats give descriptive medians, not statistical significance/global optimum.

| Case | Flow | Old median CPU s | New median CPU s | Change | Recall@10 |
|---|---|---:|---:|---:|---:|
'''
for m in metrics:text+=f"| {m['case']} | {m['flow']} | {m['cpu_seconds']['old']:.2f} | {m['cpu_seconds']['new']:.2f} | {m['change_percent']:+.2f}% | {m['recall']} |\n"
text+='''
All12 pairs passed actual streaming byte comparison of old/new snapshots, SHA256
comparison, identical query-hit CSV and identical1000 ordered ID/hexfloat-distance
rows. Snapshot/hash/recall invariants also hold across all three repeats per case/flow.
The current runner internally compares every query's ID/distance after SaveLoad.
This strengthens evidence for the semantics-preserving dispatch change on an additional
scale/distributions; it is not exhaustive equivalence for all inputs/platforms.

## Boundaries and evidence

Recall here is at fixed128, not the selected matched-quality budgets in earlier final
studies. Approximate recall is not expected to be1. Equivalence does not itself prove
quality acceptance. Small-fraction churn here cannot erase the earlier Cohere10k
full-ID default degradation0.960 to0.933. Diversity, FP16 and other scales are not
newly timed here; their prior unit/regression evidence remains at its measured commit.
No new library tests/sanitizer/coverage claims, since no implementation changed.

Original disk free space was3.5GiB. Each NEW temporary pair retains at most two
snapshots until byte comparison succeeds, records hashes, then deletes only that
pair's generated files with resolved path checks. Existing inputs/history/old libraries
are untouched. Big snapshots are not retained/published; audit checks recorded hashes
and comparison receipts, not independent re-comparison of absent bytes.
Raw logs remain on host, normalized publication logs have separate hashes. Protocol,
commands, input/library/runner SHA, ldd, CPU CSV, exact outputs and comparison receipts
are included. run.py encodes original host paths; use a NEW output root/prefix and
recorded binaries to reproduce, never overwrite original records.

Only personal experiment/lite-rabitq-next-20260926 is pushed; PRs remain frozen.
Next diagnose full-ID quality using existing before/after snapshots and route traces;
no blind budget tuning or additional default feature adoption follows from this report.
'''
(out/'README.md').write_text(text)
print(text[text.index('| Case'):text.index('All12')])
