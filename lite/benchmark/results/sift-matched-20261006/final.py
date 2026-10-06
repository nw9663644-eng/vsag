import pathlib,json,subprocess
root=pathlib.Path('/home/ubuntu/project/vsag-lite-sift-matched-20261006')
inputs=pathlib.Path('/home/ubuntu/project/vsag-lite-sift-online-20261006')
frozen=json.loads((root/'frozen.json').read_text());commands=[]
for repeat in range(3):
 for every in [1,10]:
  for mode in (['default','diverse'] if repeat%2==0 else ['diverse','default']):
   build='build-lite-fragment-release' if mode=='default' else 'build-lite-online-diverse-release'
   name=f'final-{mode}-every{every}-r{repeat+1}'
   cmd=['taskset','-c','0',build+'/lite_graph_route_probe',str(inputs/(mode+'.snapshot')),str(root/'final/scale-100000'),str(root/(name+'.csv')),str(frozen[mode]),'uniform','preserve','1','2000',str(every)]
   commands.append(cmd)
   (root/'commands-final.json').write_text(json.dumps(commands,indent=2)+'\n')
   with (root/(name+'.log')).open('w') as f: subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,check=True)
   print('complete '+name,flush=True)
