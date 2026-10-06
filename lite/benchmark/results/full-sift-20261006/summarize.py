import csv,json,pathlib,statistics,math,hashlib,shutil,subprocess
root=pathlib.Path('/home/ubuntu/project/vsag-lite-full-sift-20261006');out=pathlib.Path('lite/benchmark/results/full-sift-20261006');out.mkdir()
(out/'pilot-no-warmup').mkdir();(out/'warm').mkdir()
rows=[]
for repeat in [1,2,3]:
 lines=(root/f'warm-r{repeat}.log').read_text().splitlines();start=next(i for i,l in enumerate(lines) if l.startswith('mode,base_count'));row=next(csv.DictReader(lines[start:start+2]))
 assert float(row['recall_at_k'])>=.95 and int(row['warmup_rounds'])==1
 with (root/f'warm-r{repeat}.snapshot.latencies.csv').open() as f:samples=list(csv.DictReader(f))
 assert len(samples)==300 and [int(r['query']) for r in samples]==list(range(300))
 values=sorted(float(s['latency_us']) for s in samples)
 for fraction,key in [(.5,'search_p50_us'),(.99,'search_p99_us')]:assert abs(values[math.ceil(fraction*300)-1]-float(row[key]))<.000002
 rows.append(row)
summary={}
for key in ['recall_at_k','build_ms','search_p50_us','search_p99_us','save_ms','load_ms','snapshot_bytes','build_steady_rss_kib','final_steady_rss_kib','process_peak_rss_kib','query_loop_cpu_ms']:
 vals=[float(r[key]) for r in rows];summary[key]={'median':statistics.median(vals),'min':min(vals),'max':max(vals)}
(root/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
artifacts={}
for p in [pathlib.Path('build-full-comparison-runner/full_rabitq_dataset_benchmark'),pathlib.Path('/home/ubuntu/project/vsag-lite-full-comparison-install/lib/libvsag.so.0.0.0'),pathlib.Path('build-lite-fragment-release/libvsag-lite.so'),pathlib.Path('build-lite-online-diverse-release/libvsag-lite.so'),pathlib.Path('lite/benchmark/full_rabitq_dataset_main.cpp')]:
 artifacts[str(p)]={'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
(root/'artifacts.json').write_text(json.dumps(artifacts,indent=2)+'\n')
(root/'environment.txt').write_text(subprocess.check_output(['bash','-c','hostname; uname -a; c++ --version; clang-format-15 --version; clang-tidy-15 --version; ldd build-full-comparison-runner/full_rabitq_dataset_benchmark'],text=True))
for p in root.iterdir():
 if p.is_file() and p.suffix!='.snapshot' and p.name!='pyarrow-install.log':
  dest=out/'pilot-no-warmup'/p.name if p.name.startswith('full-r') else out/'warm'/p.name if p.name.startswith('warm-r') else out/p.name
  shutil.copy2(p,dest)
cohere=pathlib.Path('lite/benchmark/results/cohere-source-20261006');cohere.mkdir()
for name in ['audit.json','audit.py']:shutil.copy2(pathlib.Path('/home/ubuntu/project/vsag-lite-cohere-source-20261006')/name,cohere/name)
print(json.dumps(summary,indent=2));print(json.dumps(artifacts,indent=2))
