import pathlib,subprocess,json
root=pathlib.Path('/home/ubuntu/project/vsag-lite-full-sift-20261006')
data='/home/ubuntu/project/vsag-lite-sift-matched-20261006/final/scale-100000'
(root/'warm-protocol.json').write_text(json.dumps({'query_ef':128,'warmup_rounds':1,'timed_rounds':1,'replicates':3,'cpu':0,'quality_floor':.95,'query_rows':[400,700],'queries_previously_observed':True,'maintenance_not_measured':True},indent=2)+'\n')
commands=[]
for r in [1,2,3]:
 cmd=['env','OMP_NUM_THREADS=1','OPENBLAS_NUM_THREADS=1','MKL_NUM_THREADS=1','taskset','-c','0','build-full-comparison-runner/full_rabitq_dataset_benchmark',data,str(root/f'warm-r{r}.snapshot'),'fp32','128','1']
 commands.append(cmd)
 with (root/f'warm-r{r}.log').open('w') as f:subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,check=True)
 print('complete Full warm run',r,flush=True)
(root/'warm-commands.json').write_text(json.dumps(commands,indent=2)+'\n')
