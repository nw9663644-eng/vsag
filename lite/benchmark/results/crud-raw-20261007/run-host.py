from pathlib import Path
import hashlib,json,os,subprocess,csv,statistics
root=Path(__file__).resolve().parent;repo=Path.cwd();old=repo/'lite/benchmark/results/diverse-repair-20261007'
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda:f.read(1048576),b''):h.update(chunk)
    return h.hexdigest()
libraries={'baseline':repo/'build-lite-fragment-release','candidate':repo/'build-lite-diverse-repair-release'}
previous=json.loads((old/'identity.json').read_text())['library_sha256']
assert all(sha(p/'libvsag-lite.so')==previous[v] for v,p in libraries.items())
common=Path('/home/ubuntu/project/vsag-lite-independent-crud-quality-20261005')
cases={'sift':(common/'sift-100k-initial.snapshot',Path('/home/ubuntu/project/vsag-lite-datasets/sift/prepared-10k-100k/scale-100000')),'gist':(common/'gist-100k-initial.snapshot',Path('/home/ubuntu/project/vsag-lite-datasets/gist/prepared-10k-100k/scale-100000')),'cohere':(Path('/home/ubuntu/project/vsag-lite-cohere-normalized-20261006/cohere-100000-default.snapshot'),Path('/home/ubuntu/project/vsag-lite-cohere-normalized-20261006/prepared/scale-100000'))}
identity={'parent':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'files':{},'libraries':{v:sha(p/'libvsag-lite.so') for v,p in libraries.items()}}
for snap,data in cases.values():
    for p in [snap,data/'base.fvecs',data/'queries.fvecs',data/'groundtruth.ivecs']:identity['files'][str(p)]=sha(p)
for name in ['AGENTS.md','docs/agents/coding-standards.md','docs/agents/build-and-test.md','docs/agents/contribution-workflow.md','lite/benchmark/graph_route_probe.cpp','build-lite-fragment-release/lite_graph_route_probe']:
    p=repo/name;identity['files'][str(p)]=sha(p)
(root/'identity.json').write_text(json.dumps(identity,indent=2)+'\n')
protocol={'scale':100000,'cycles':10000,'mutation_calls_per_cycle':4,'query_every':[10],'repeats':{'10':1},'cpu':0,'query_ef':128,'entry':'uniform','neighbor_order':'preserve','candidate':'unchanged bounded direction refill patch from684564a','same_initial':True,'queries':'existing observed100; no new holdout','scope':'raw neighbor correctness audit only; evidence allocations alter loop timing; not new performance comparison'}
(root/'protocol.json').write_text(json.dumps(protocol,indent=2)+'\n')
records=[]
for freq,repeats in [(10,1)]:
    for repeat in range(repeats):
        for dataset in (list(cases) if repeat%2==0 else list(reversed(cases))):
            snap,data=cases[dataset]
            for variant in (list(libraries) if repeat%2==0 else list(reversed(libraries))):
                name=f'{dataset}-{variant}-q{freq}-r{repeat}';output=root/(name+'.csv')
                command=['/usr/bin/time','-f','%U,%S,%M','-o',str(root/(name+'.time.csv')),'taskset','-c','0',str(repo/'build-lite-fragment-release/lite_graph_route_probe'),str(snap),str(data),str(output),'128','uniform','preserve','1','10000',str(freq)]
                env=dict(os.environ,LD_LIBRARY_PATH=str(libraries[variant]))
                with (root/(name+'.stdout.log')).open('wb') as out,(root/(name+'.stderr.log')).open('wb') as err:
                    result=subprocess.run(command,env=env,stdout=out,stderr=err)
                row={'name':name,'dataset':dataset,'variant':variant,'query_every':freq,'repeat':repeat,'command':command,'library_path':str(libraries[variant]),'exit':result.returncode};records.append(row)
                (root/'runs.json').write_text(json.dumps(records,indent=2)+'\n')
                assert result.returncode==0,(name,(root/(name+'.stderr.log')).read_text())
                row['metrics']=next(csv.DictReader(Path(str(output)+'.api.csv.crud.csv').open()))
                (root/'runs.json').write_text(json.dumps(records,indent=2)+'\n')
                print(name,'recall',row['metrics']['recall_at_k'],'mixed',row['metrics']['mixed_recall_at_k'],'mutationCPU',row['metrics']['crud_loop_cpu_ms'],'loopCPU',row['metrics']['mixed_loop_cpu_ms'],flush=True)
summary=[]
for freq in [10]:
    for dataset in cases:
        for variant in libraries:
            selected=[r for r in records if (r['dataset'],r['variant'],r['query_every'])==(dataset,variant,freq)]
            metrics={key:statistics.median(float(r['metrics'][key]) for r in selected) for key in ['recall_at_k','mixed_recall_at_k','crud_loop_cpu_ms','mixed_query_cpu_ms','mixed_loop_cpu_ms','update_changed_p50_us','restore_p50_us','remove_p50_us','readd_p50_us','mixed_search_p50_us','mixed_search_p99_us']}
            summary.append(dict(dataset=dataset,variant=variant,query_every=freq,runs=len(selected),median=metrics))
(root/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
