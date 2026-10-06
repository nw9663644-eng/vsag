from pathlib import Path
import json,csv,math,statistics,shutil,hashlib,subprocess
root=Path('/home/ubuntu/project/vsag-lite-full-cohere-20261006');out=Path('lite/benchmark/results/full-cohere-20261006');out.mkdir(parents=True,exist_ok=True)
rows=json.loads((root/'summary.json').read_text());assert len(rows)==3
for repeat,row in enumerate(rows):
 with (root/f'full-rep{repeat}.snapshot.latencies.csv').open() as f:raw=list(csv.DictReader(f))
 assert len(raw)==600
 values=sorted(float(r['latency_us']) for r in raw)
 for fraction,key in [(.5,'search_p50_us'),(.99,'search_p99_us')]:assert abs(values[math.ceil(600*fraction)-1]-float(row[key]))<1e-5
 assert float(row['recall_at_k'])>=.95 and int(row['query_ef_search'])==128 and int(row['warmup_rounds'])==1
for p in root.iterdir():
 if p.is_file() and p.suffix!='.snapshot':shutil.copy2(p,out/p.name)
fields=['recall_at_k','build_ms','search_p50_us','search_p99_us','query_loop_cpu_ms','save_ms','load_ms','snapshot_bytes','build_steady_rss_kib','final_steady_rss_kib','process_peak_rss_kib']
audit={k:{'median':statistics.median(float(r[k]) for r in rows),'min':min(float(r[k]) for r in rows),'max':max(float(r[k]) for r in rows)} for k in fields}
(out/'audit.json').write_text(json.dumps({'raw_queries':1800,'processes':3,'quality_passes':3,'metrics':audit},indent=2)+'\n')
(out/'linked-libraries.txt').write_text(subprocess.check_output(['ldd','build-full-known-runner/full_rabitq_dataset_benchmark'],text=True))
cache=Path('build-full-comparison-library/CMakeCache.txt').read_text()
(out/'build-configuration.txt').write_text('\n'.join(line for line in cache.splitlines() if line.startswith(('ENABLE_','CMAKE_BUILD_TYPE:','CMAKE_CXX_COMPILER:','CMAKE_CXX_FLAGS','CMAKE_HOME_DIRECTORY:','CMAKE_GENERATOR:')))+'\n')
(out/'version-header.txt').write_text(Path('src/version.h').read_text())
(out/'environment.txt').write_text(subprocess.check_output(['uname','-a'],text=True)+subprocess.check_output(['lscpu'],text=True))
text='''# Known-source Full Cohere FP32 reference (2026-10-06)

Rebuilt the existing Full shared-library target incrementally from clean tracked
source d18c82a1f1f23ff84362516e86af5f3cb2e34475, then installed into a separate
vsag-full-known-install-20261006 prefix and built a new benchmark runner.
Version header/build log, flags, ldd and library/binary SHA bind this measurement
to that source. This is not a fresh all-object rebuild or latest upstream claim;
unchanged cached objects/dependencies were reused. Only shared target was rebuilt;
installed static archive was not used and has no matching-version certification.

Official APIs used by the existing full_rabitq_dataset_main.cpp benchmark:
Factory::CreateIndex("hgraph"), Build, KnnSearch, Serialize and Deserialize.
FP32 squared-L2, degree16, construction/query ef128, compressed graph storage and
store_raw_vector=true. CPU affinity0; one warmup pass, one timed pass, three fresh
processes. Cohere prepared base100k/dim768, normalized FP32 with FP64 truth;
600 query rows[400,1000) were already observed in Lite and are not new blind data.
The same input manifest is recorded in protocol.json. No index code was changed.

## Results

| Metric | Median | Min | Max |
|---|---:|---:|---:|
'''
for k,v in audit.items():text+=f"| {k} | {v['median']:.6f} | {v['min']:.6f} | {v['max']:.6f} |\n"
text+='''
All three pass Recall@10>=.95. Save/Load verifies IDs exactly and distances within
1e-5 relative scale for all 600 queries per run. Raw 1800 timed-query counts and
nearest-rank P50/P99 were independently recomputed. RSS is whole process:
build_steady drops base input and trims allocator; final_steady is after reload and
result checks; peak includes preparation/build temporaries. File Load is warm
filesystem-cache measurement, not strict cold start. CPU loop includes vector
copy/search/scoring/bookkeeping and excludes warmup. P50/P99 time search+result copy.

## Interpretation

See cohere-matched-20261006 for prior Lite default768/candidate256 results. These
were measured in earlier processes, not interleaved with Full. Different quality
and index topology/storage mean timing ratios are descriptive reference points,
not exact equal-quality optimization or an adoption decision. No matching Lite RSS
measurement or Full mixed CRUD is included; Full/Lite memory or end-to-end CPU
benefit cannot yet be claimed. Snapshot sizes can be compared for these formats,
but a shared-library size alone is not a deployment-package size.

On the first run, Full logs preceded the CSV header on stdout. The collector's
CSV parser failed after the benchmark succeeded; parsing now preserves raw stdout
and extracts from the explicit header. Run0 was recovered, not remeasured/discarded.
No C++ source edits, new sanitizer/coverage results or concurrent CRUD claims.

## Reproduction and next work

commands.json and run.py contain actual host paths and parameters; use a fresh
output directory to remeasure. Large snapshots/binaries/datasets are excluded from
Git; snapshot hashes and linked-library/source provenance are retained. Build,
install and runner logs are included. Next: equivalent Lite memory lifecycle and
Full mixed CRUD, then a unified SIFT/GIST/Cohere report and policy decision.
'''
(out/'README.md').write_text(text)
checks={str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.is_file() and p.name!='sha256.json'}
(out/'sha256.json').write_text(json.dumps(checks,indent=2)+'\n')
print(json.dumps(audit,indent=2),flush=True)
