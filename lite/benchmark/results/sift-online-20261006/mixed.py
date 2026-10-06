import pathlib,json,subprocess,hashlib
root=pathlib.Path('/home/ubuntu/project/vsag-lite-sift-online-20261006')
data='/home/ubuntu/project/vsag-lite-datasets/sift/prepared-10k-100k/scale-100000'
commands=json.loads((root/'commands.json').read_text())
for repeat in range(3):
    for every in [1,10]:
        modes=['default','diverse'] if repeat%2==0 else ['diverse','default']
        for mode in modes:
            build='build-lite-fragment-release' if mode=='default' else 'build-lite-online-diverse-release'
            name=f'{mode}-every{every}-r{repeat+1}'
            cmd=['taskset','-c','0',build+'/lite_graph_route_probe',str(root/(mode+'.snapshot')),data,str(root/(name+'.csv')),'128','uniform','preserve','1','2000',str(every)]
            commands.append(cmd)
            (root/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
            with (root/(name+'.log')).open('w') as f: subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,check=True)
            print('complete '+name,flush=True)
