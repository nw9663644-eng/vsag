import pathlib,json,subprocess
root=pathlib.Path('/home/ubuntu/project/vsag-lite-cohere-normalized-20261006')
protocol={'library_source':'e547eb1cc595828a19ffc82b6bdbf8fd5a43069a','dataset':'Cohere normalized FP32 squared-L2 10k/100k','query_rows':[0,100],'reserved_validation_rows':[100,400],'reserved_final_rows':[400,1000],'degree':16,'construction_and_maintenance_ef':128,'query_ef':128,'cycles':1000,'mutation_calls_per_cycle':4,'query_every':10,'replicates':1,'cpu':0,'quality_floor':.9,'limitation':'same-budget different-quality descriptive pilot; not independent acceptance or Full comparison'}
(root/'protocol.json').write_text(json.dumps(protocol,indent=2)+'\n')
commands=[]
for count in [10000,100000]:
 for mode in ['default','diverse']:
  build='build-lite-fragment-release' if mode=='default' else 'build-lite-online-diverse-release'
  name=f'cohere-{count}-{mode}';data=str(root/'prepared'/f'scale-{count}');snap=str(root/(name+'.snapshot'))
  for stage,cmd in [('build',['taskset','-c','0',build+'/lite_graph_crud_quality',data,snap,'0','100']),('mixed',['taskset','-c','0',build+'/lite_graph_route_probe',snap,data,str(root/(name+'.csv')),'128','uniform','preserve','1','1000','10'])]:
   commands.append(cmd)
   (root/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
   with (root/(name+'-'+stage+'.log')).open('w') as f:subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,check=True)
   print('complete',name,stage,flush=True)
