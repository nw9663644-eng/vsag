import json,subprocess,pathlib,hashlib
root=pathlib.Path('/home/ubuntu/project/vsag-lite-sift-online-20261006')
data='/home/ubuntu/project/vsag-lite-datasets/sift/prepared-10k-100k/scale-100000'
protocol={'source_commit':'167db90310c56eda7cd7e7f13839c6b390f2376a','dataset':data,'queries':'previously observed first 100 SIFT queries, descriptive cross-dataset validation','degree':16,'maintenance_ef':128,'pilot_query_ef':128,'cycles':2000,'query_every':[1,10],'replicates':3,'quality_floor':0.95,'timing':'queries after complete restored cycle; serialized CPU0; no concurrency'}
(root/'protocol.json').write_text(json.dumps(protocol,indent=2)+'\n')
commands=[]
def run(cmd,name):
    commands.append(cmd)
    (root/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
    with (root/(name+'.log')).open('w') as f:
        subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,check=True)
    print('complete '+name,flush=True)
for mode,build in [('default','build-lite-fragment-release'),('diverse','build-lite-online-diverse-release')]:
    snap=str(root/(mode+'.snapshot'))
    run(['taskset','-c','0',build+'/lite_graph_crud_quality',data,snap,'0','100'],mode+'-build')
    run(['taskset','-c','0',build+'/lite_graph_route_probe',snap,data,str(root/(mode+'-pilot.csv')),'128','uniform','preserve','1'],mode+'-pilot')
