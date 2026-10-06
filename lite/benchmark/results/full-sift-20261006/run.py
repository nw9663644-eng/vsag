import subprocess,pathlib,json,hashlib
root=pathlib.Path('/home/ubuntu/project/vsag-lite-full-sift-20261006')
data='/home/ubuntu/project/vsag-lite-sift-matched-20261006/final/scale-100000'
protocol={'source':'f3a3bcdc55964fbe16b056e77d4c0dbb2f48ad34','dataset':data,'mode':'Full HGraph FP32','degree':16,'construction_ef':128,'query_ef':128,'cpu':0,'replicates':3,'query_rows':[400,700],'queries_previously_observed':True,'limitation':'existing runner has one timed pass with no warmup; no mixed CRUD or per-phase CPU; Full graph differs from Lite; common final quality floor .95 descriptive comparison only'}
(root/'protocol.json').write_text(json.dumps(protocol,indent=2)+'\n')
commands=[]
for r in range(1,4):
 cmd=['env','OMP_NUM_THREADS=1','OPENBLAS_NUM_THREADS=1','MKL_NUM_THREADS=1','taskset','-c','0','build-full-comparison-runner/full_rabitq_dataset_benchmark',data,str(root/f'full-r{r}.snapshot'),'fp32']
 commands.append(cmd)
 with (root/f'full-r{r}.log').open('w') as f: subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,check=True)
 print('complete Full run',r,flush=True)
(root/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
