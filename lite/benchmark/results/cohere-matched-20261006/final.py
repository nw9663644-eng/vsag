import pathlib,json,subprocess,csv,os,hashlib
root=pathlib.Path('/home/ubuntu/project/vsag-lite-cohere-matched-20261006')
frozen=json.loads((root/'frozen.json').read_text()); frozen_sha=hashlib.sha256((root/'frozen.json').read_bytes()).hexdigest()
(root/'before-final.json').write_text(json.dumps({'frozen_sha256':frozen_sha,'final_not_yet_prepared':not (root/'final').exists()},indent=2)+'\n')
assert not (root/'final').exists()
env=dict(os.environ,PYTHONPATH='/home/ubuntu/project/vsag-lite-datasets/cohere/python-deps:/home/ubuntu/project/vsag-lite-datasets/sift/python-deps',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
prepare=['python3','lite/benchmark/prepare_cohere.py','/home/ubuntu/project/vsag-lite-datasets/cohere/cohere-small-100k',str(root/'final'),'--counts','100000','--queries','600','--query-offset','400']
with (root/'prepare-final.log').open('w') as f:subprocess.run(prepare,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
print('Final truth prepared with frozen budgets',frozen['budgets'],flush=True)
commands=[prepare]; results=[]
pilot=root.with_name('vsag-lite-cohere-normalized-20261006')
for every in [1,10]:
 for repeat in range(3):
  for mode in (['default','diverse'] if repeat%2==0 else ['diverse','default']):
   build='build-lite-fragment-release' if mode=='default' else 'build-lite-online-diverse-release'
   output=root/f'final-every{every}-rep{repeat}-{mode}.csv'
   cmd=['taskset','-c','0',build+'/lite_graph_route_probe',str(pilot/f'cohere-100000-{mode}.snapshot'),str(root/'final/scale-100000'),str(output),str(frozen['budgets'][mode]),'uniform','preserve','1','1000',str(every)]
   commands.append(cmd);(root/'final-commands.json').write_text(json.dumps(commands,indent=2)+'\n')
   with output.with_suffix('.log').open('w') as f:subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,check=True)
   with pathlib.Path(str(output)+'.api.csv').open() as f:initial=next(csv.DictReader(f))
   with pathlib.Path(str(output)+'.api.csv.crud.csv').open() as f:after=next(csv.DictReader(f))
   row={'mode':mode,'repeat':repeat,'query_every':every,'initial':initial,'after':after,'quality_pass':min(float(initial['recall_at_k']),float(after['recall_at_k']))>=frozen['final_floor']}
   results.append(row);(root/'final-summary.json').write_text(json.dumps(results,indent=2)+'\n')
   print(mode,every,repeat,initial['recall_at_k'],after['recall_at_k'],after['mixed_loop_cpu_ms'],'pass',row['quality_pass'],flush=True)
assert hashlib.sha256((root/'frozen.json').read_bytes()).hexdigest()==frozen_sha
print('Final completed. No retuning. Quality passes:',sum(r['quality_pass'] for r in results),'/',len(results),flush=True)
