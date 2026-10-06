from pathlib import Path
import json,statistics,hashlib,shutil,subprocess
root=Path('/home/ubuntu/project/vsag-lite-load-memory-20261006');out=Path('lite/benchmark/results/load-memory-20261006');out.mkdir(parents=True,exist_ok=True)
rows=json.loads((root/'summary.json').read_text());assert len(rows)==21
metrics={}
for mode in ['full','default','diverse']:
 r=[x for x in rows if x['mode']==mode];assert len(r)==7 and {x['repeat'] for x in r}==set(range(7))
 assert all(int(x['count'])==100000 and int(x['dim'])==768 for x in r)
 metrics[mode]={k:{'median':statistics.median(float(x[k]) for x in r),'min':min(float(x[k]) for x in r),'max':max(float(x[k]) for x in r)} for k in ['load_ms','before_create_rss_kib','before_load_rss_kib','loaded_rss_kib','process_peak_rss_kib','snapshot_bytes']}
rawlogs={}
for p in root.iterdir():
 if p.is_file() and p.suffix != ".snapshot":
  shutil.copy2(p,out/p.name)
  if p.suffix=='.log':
   rawlogs[p.name]=hashlib.sha256(p.read_bytes()).hexdigest()
   (out/p.name).write_text('\n'.join(line.rstrip() for line in p.read_text().splitlines())+ '\n')
(out/'raw-logs-sha256.json').write_text(json.dumps(rawlogs,indent=2)+'\n')
(out/'audit.json').write_text(json.dumps(metrics,indent=2)+'\n')
text='''# Common load-only Full/Lite memory probe (2026-10-06)

## Source and lifecycle

New Linux C++17 benchmark load_memory.cpp uses existing Lite Index::Load or Full
Factory::CreateIndex/Deserialize APIs. The same /proc/self/status VmRSS,
getrusage process peak and malloc_trim(0) measurement code is compiled for both.
Public index code, storage policy and snapshot formats are unchanged. Source parent
101e3f6 and working helper/binary hashes are in protocol.json; Full shared library
is the known-source d18c82a rebuild. Full and Lite remain different index designs.

Fresh processes, taskset CPU0, seven runs per configuration; cyclic order rotates
Full/default/diverse. Snapshot files are read once beforehand (warm attempt, no
cache eviction controls). No source base vectors, queries, searches, construction,
save or result arrays are retained. Record before-create RSS, after-empty-create
RSS, load time, then close the input stream and malloc_trim while keeping the index
alive before recording loaded RSS and process peak. Lite static Load creates the
index inside timed Load; Full empty Factory creation is outside the timer.
Full public API checks loaded count, with caller-supplied dimension; Lite also
checks restored dimension. This probe does not independently check Full restored
dimension or rerun retrieval quality. Existing snapshot validation supplies quality.

## Results

Medians across seven runs; raw samples and min/max are in audit.json and CSV files.
RSS and peak are whole-process values in KiB, not allocation counters or index-only
memory. MiB = KiB/1024. Peak here covers only startup and load, not build.

| Mode | Load ms | Loaded RSS KiB | Loaded RSS MiB | Peak KiB | Snapshot bytes |
|---|---:|---:|---:|---:|---:|
'''
for mode,m in metrics.items():text+=f"| {mode} | {m['load_ms']['median']:.3f} | {m['loaded_rss_kib']['median']:.0f} | {m['loaded_rss_kib']['median']/1024:.2f} | {m['process_peak_rss_kib']['median']:.0f} | {m['snapshot_bytes']['median']:.0f} |\n"
for mode in ['default','diverse']:
 m=metrics[mode];f=metrics['full']
 text+=f"\nLite {mode}: loaded RSS {100*(m['loaded_rss_kib']['median']/f['loaded_rss_kib']['median']-1):+.2f}%, load-stage peak {100*(m['process_peak_rss_kib']['median']/f['process_peak_rss_kib']['median']-1):+.2f}%, load wall time {100*(m['load_ms']['median']/f['load_ms']['median']-1):+.2f}% relative to this Full configuration.\n"
text+='''
## Interpretation and verification

These numbers establish lower whole-process load-only memory for these specific
snapshots/libraries, and faster warm file loads. They do not prove strict cold
start, index-only memory, deployment footprint, other workloads or all architectures.
Snapshot recall differs: Full .952, default .958, diverse .961333, all common .95
floor; quality provenance is in full-cohere/cohere-matched reports, not measured
again by this loader. Full has compressed graph storage and raw-vector retention;
Lite snapshot formats differ. This is not an exact equal-quality/equal-feature
comparison or justification for replacing Full based on memory alone. Full remains
faster on previous retrieval measurements. Historical build-inclusive Full peak
958556 KiB must not be compared to this load-only Lite peak.

New CLI fixtures cover both adapters on 8x16 one-hot snapshots, invalid numeric
arguments, size mismatch, missing and corrupt files. Release and Lite ASan/UBSan
fixtures, clang-format15, clang-tidy15 in both adapters and existing default/diverse
CTest pass; no new library coverage claim. Full ASan was not run. Fixture snapshots
are produced with existing graph_crud_quality/full_rabitq_dataset tools, k1 truth;
test_load_memory.py accepts Full binary, Lite binary and fixture directory.

Published logs remove trailing whitespace; raw-log SHA and host originals preserve
byte provenance. Binary and snapshot hashes are in protocol.json. The new Full
Makefile target initially required explicit reconfiguration, after which it built.
Large fixture/real snapshots and binaries are not committed. Next: actual Full mixed
CRUD under the same restored-data protocol and a unified three-dataset report.
'''
(out/'README.md').write_text(text)
(out/'environment.txt').write_text(subprocess.check_output(['uname','-a'],text=True)+subprocess.check_output(['lscpu'],text=True))
checks={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.is_file() and p.name!='sha256.json'}
(out/'sha256.json').write_text(json.dumps(checks,indent=2)+'\n')
print(text[text.index('## Results'):text.index('## Interpretation')],flush=True)
