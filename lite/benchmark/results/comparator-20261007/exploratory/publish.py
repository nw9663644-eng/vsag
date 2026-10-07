from pathlib import Path
import json,hashlib,statistics,gzip,shutil,subprocess
raw=Path(__file__).resolve().parent
final=raw.with_name('vsag-lite-comparator-final-20261007')
out=Path('lite/benchmark/results/comparator-20261007');out.mkdir(parents=True,exist_ok=False)
rawhashes={}
for source,label in [(raw,'exploratory'),(final,'final')]:
 target=out/label;target.mkdir()
 for p in source.iterdir():
  if p.is_file() and p.suffix in ['.csv','.json','.txt','.log','.py']:
   data=p.read_bytes();rawhashes[label+'/'+p.name]=hashlib.sha256(data).hexdigest()
   if p.suffix in ['.txt','.log']:
    data=('\n'.join(x.rstrip() for x in p.read_text().splitlines())+'\n').encode()
   (target/p.name).write_bytes(data)
 if label=='exploratory':
  shutil.copytree(source/'gcov',target/'gcov')
metrics=[]
for label in ['exploratory','final']:
 source=raw if label=='exploratory' else final
 rows=json.loads((out/label/'summary.json').read_text());assert len(rows)==24
 commands=json.loads((out/label/'commands.json').read_text());assert len(commands)==24 and all(x['exit']==0 for x in commands)
 for row in rows:
  prefix=source/row['name']
  for suffix,key in [('.snapshot','snapshot_sha256'),('.queries.csv.neighbors.csv','neighbors_sha256'),('.queries.csv','hits_sha256')]:
   assert hashlib.sha256(Path(str(prefix)+suffix).read_bytes()).hexdigest()==row[key]
 for mode in ['default','diverse']:
  for flow in ['build','crud']:
   subset=[x for x in rows if x['mode']==mode and x['flow']==flow]
   for key in ['snapshot_sha256','neighbors_sha256','hits_sha256','recall_at_k']:assert len({x[key] for x in subset})==1,(label,mode,flow,key)
   values={v:statistics.median(x['cpu_seconds'] for x in subset if x['variant']==v) for v in ['old','new']}
   metrics.append({'label':label,'mode':mode,'flow':flow,'cpu_seconds':values,'change_percent':100*(values['new']/values['old']-1),'recall':subset[0]['recall_at_k']})
(out/'audit.json').write_text(json.dumps(metrics,indent=2)+'\n');(out/'raw-sha256.json').write_text(json.dumps(rawhashes,indent=2)+'\n')
text='''# Typed comparator optimization, 2026-10-07

Source parent549a44d plus this recorded change. Following official StandardHeap's
concrete CompareMax/CompareMin pattern, Lite priority queues and sorts now use
Closer/Farther objects. Operators call the original distance/slot comparison;
queue direction, tie order, distances, budgets, graph policy and snapshot format
remain unchanged. No Full, third-party, public API or concurrency change.
Prior CPU profiles identified distance, visit and heap/comparator hotspots.

The existing optional query-hit output now also emits .neighbors.csv containing
ordered ID and hexfloat distance for exact differential checks. Original hit CSV
schema remains unchanged, no sidecar without query-output argument, existing
sidecars are rejected before the workload. Small fixture verifies output and
non-overwrite behavior.

## Fixed comparison

CPU0, normalized Cohere10k/768dim, existing100 observed queries, L2 Top10,
degree16/construction/query128. Two library modes: default OFF/diversity ON.
Build-only vs10000 distinct-ID same-vector Update/Remove/Add cycles, with staging,
build, quality queries and snapshot roundtrip in both. Three processes per
mode/flow/variant =24 final runs, reversed variant/mode/flow order on odd repeats.
Each variant uses the SAME new diagnostic runner, explicitly bound by
LD_LIBRARY_PATH to saved old or rebuilt new libvsag-lite.so. ldd/hash evidence
confirms binding; do not describe this as two unrelated build/compiler settings.

A separate24 exploratory runs overlapped verification builds. Preserve them for
correctness but exclude their timings from the final performance conclusion.
Final runs began after build/test/tidy jobs completed; unrelated system services
still run. No profiler instrumentation in final runs. /usr/bin/time user+system
CPU includes the whole process, not isolated maintenance;0.01s rounding and
normal frequency/cache variability apply. It is not a statistical confidence bound.

| Library mode | Flow | Old median CPU s | New median CPU s | Change | Recall@10 |
|---|---|---:|---:|---:|---:|
'''
for m in metrics:
 if m['label']=='final':text+=f"| {m['mode']} | {m['flow']} | {m['cpu_seconds']['old']:.2f} | {m['cpu_seconds']['new']:.2f} | {m['change_percent']:+.2f}% | {m['recall']} |\n"
text+='''
All48 runs: old/new snapshots byte-identical,100-query hit CSVs byte-identical,
1000 ordered ID/hexfloat-distance rows byte-identical for each mode/flow across
all repeats. API/count/roundtrip checks pass. Published neighbor files and hashes
are independently auditable; large snapshots/binaries remain on the server.
Fixed query workloads do not measure general query latency gains; do not extend
these whole-process CPU ratios to other datasets/scales, cold start or concurrency.

Default after full-ID churn remains0.933 (initial0.960); diversity remains0.960
(initial0.982). The default quality limitation is NOT fixed by dispatch optimization.
Candidate stays OFF by default. Timing gains do not establish quality acceptance
or whole-project completion. Next diagnose full-ID quality degradation separately,
and confirm performance/semantic equivalence at100k and another distribution.

## Verification

Default Release4/4; diversity Release3/3; default ASan+UBSan6/6 pass.
Fresh unit-only gcov run after resetting generated counters:957/1060 emitted
Lite source/internal-header lines =90.28%. File counts are in coverage.json and
raw gcov JSON is retained; this is not Full/extern/benchmark or branch coverage.
Source graph/backend and diagnostic probe pass clang-format15/clang-tidy15.
Non-user header warnings are suppressed, not a whole-repository lint claim.
New sidecar fixture checks8x16 one-hot outputs, unchanged hit schema and overwrite
rejection. Existing unit tests cover filter traversal, FP16, ties, invalid inputs,
randomized CRUD and persistence. No new algorithm correctness promise.

verify.py checks manifest/raw neighbor hashes, protocol/binding, CPU derivation,
48-run equivalence, medians/changes and coverage >=90%. Test logs retain scope.
Reproduction scripts encode original host paths; use NEW output roots/prefixes
and recorded library binaries, do not overwrite old evidence. Snapshots and old
libraries in /home/ubuntu/project/vsag-lite-comparator-20261007 and final inputs
in sibling vsag-lite-comparator-final-20261007 remain available on the host.
Only personal experiment/lite-rabitq-next-20260926 is pushed; PRs remain frozen.
'''
(out/'README.md').write_text(text)
print(text[text.index('| Library mode'):text.index('All48')])
