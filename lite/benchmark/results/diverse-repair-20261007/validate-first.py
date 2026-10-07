from pathlib import Path
import csv,json,os,subprocess,hashlib
root=Path(__file__).resolve().parent;repo=Path.cwd();records=[]
def run(name,command,library):
    env=dict(os.environ,LD_LIBRARY_PATH=str(library))
    with (root/(name+'.stdout.log')).open('wb') as out,(root/(name+'.stderr.log')).open('wb') as err:
        result=subprocess.run(command,env=env,stdout=out,stderr=err)
    row=dict(name=name,command=command,library=str(library),exit=result.returncode);records.append(row)
    (root/'validation-commands.json').write_text(json.dumps(records,indent=2)+'\n')
    assert result.returncode==0,(row,(root/(name+'.stderr.log')).read_text())
    return row
libs={'baseline':root/'before','candidate':repo/'build-lite-diverse-repair-release'}
for label,stem in [('initial','baseline-build-r0'),('baseline','baseline-crud-r0'),('candidate','candidate-crud-r0')]:
    name='cohere-validation-'+label
    cmd=['taskset','-c','0',str(repo/'build-lite-fragment-release/lite_graph_route_probe'),str(root/(stem+'.snapshot')),str(root/'validation/scale-10000'),str(root/(name+'.csv')),'128','uniform','preserve','1']
    run(name,cmd,libs['candidate' if label=='candidate' else 'baseline'])
    rows=list(csv.DictReader((root/(name+'.csv')).open()));eligible=[r for r in rows if r['eligible']=='1']
    print(name,sum(int(r['hits']) for r in eligible)/(10*len(eligible)),len(eligible),flush=True)
for dataset in ['sift','gist']:
    data=Path('/home/ubuntu/project/vsag-lite-datasets')/dataset/'prepared-10k-100k/scale-10000'
    for flow in ['build','crud']:
        for variant in libs:
            name=dataset+'-'+variant+'-'+flow
            cmd=['/usr/bin/time','-f','%U,%S','-o',str(root/(name+'.time.csv')),'taskset','-c','0',str(repo/'build-lite-fragment-release/lite_graph_crud_quality'),str(data),str(root/(name+'.snapshot')),'0' if flow=='build' else '1','10000',str(root/(name+'.hits.csv'))]
            row=run(name,cmd,libs[variant]);metric=next(csv.DictReader((root/(name+'.stdout.log')).open()))
            row['metrics']=metric;row['whole_cpu_s']=sum(map(float,(root/(name+'.time.csv')).read_text().strip().split(',')))
            row['snapshot_sha256']=hashlib.sha256((root/(name+'.snapshot')).read_bytes()).hexdigest()
            (root/'validation-commands.json').write_text(json.dumps(records,indent=2)+'\n')
            print(name,metric['recall_at_k'],row['whole_cpu_s'],flush=True)
