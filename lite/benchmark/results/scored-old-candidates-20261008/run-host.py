from pathlib import Path
import json,hashlib,subprocess,os,shutil,csv
root=Path(__file__).resolve().parent;repo=Path.cwd();whole=Path('/home/ubuntu/project/vsag-lite-whole-vector-20261008');old=Path('/home/ubuntu/project/vsag-lite-persistent-20261007');supp=Path('/home/ubuntu/project/vsag-lite-restoration-validation-20261008');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
infos=json.loads((whole/'prepared.json').read_text());libs={'baseline':repo/'build-lite-fragment-release','candidate':root/'release'}
files=[repo/'src/lite/graph_backend.cpp',root/'graph_backend.cpp',root/'fixture.cpp',repo/'build-lite-fragment-release/lite_graph_route_probe',libs['baseline']/'libvsag-lite.so',libs['candidate']/'libvsag-lite.so']
(root/'identity.json').write_text(json.dumps({'parent':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'files':{str(p):sha(p) for p in files},'plan_sha256':sha(root/'plan.json')},indent=2)+'\n')
cohorts=[]
for info in infos:
 d=info['dataset'];data=root/('coordinate-'+d);data.mkdir(exist_ok=False)
 shutil.copyfile(whole/d/'queries.fvecs',data/'queries.fvecs');shutil.copyfile(whole/d/'groundtruth.ivecs',data/'groundtruth.ivecs')
 changed=(supp/'gist-supplement/groundtruth.ivecs' if d=='gist' else old/d/'changed-groundtruth.ivecs')
 shutil.copyfile(changed,data/'changed-groundtruth.ivecs')
 cohorts.append(dict(info,protocol='coordinate',cycles=10000,directory=str(data),files={p.name:sha(p) for p in data.iterdir()}))
 cohorts.append(dict(info,protocol='whole',directory=str(whole/d)))
(root/'cohorts.json').write_text(json.dumps(cohorts,indent=2)+'\n');runs=[]
for repeat in range(3):
 for number,cohort in enumerate(cohorts):
  d=cohort['dataset'];protocol=cohort['protocol'];order=['baseline','candidate'] if (repeat+number)%2==0 else ['candidate','baseline']
  for variant in order:
   name=protocol+'-'+d+'-'+variant+'-'+str(repeat);output=root/(name+'.csv');env=dict(os.environ,LD_LIBRARY_PATH=str(libs[variant]))
   mode='--persistent-update' if protocol=='coordinate' else '--replacement-update'
   command=['taskset','-c','0',str(repo/'build-lite-fragment-release/lite_graph_route_probe'),mode,cohort['snapshot'],cohort['directory'],str(output),str(cohort['cycles'])]
   (root/(name+'.ldd.log')).write_bytes(subprocess.check_output(['ldd',command[3]],env=env))
   with (root/(name+'.log')).open('wb') as f:done=subprocess.run(command,env=env,stdout=f,stderr=subprocess.STDOUT)
   record=dict(protocol=protocol,dataset=d,variant=variant,repeat=repeat,command=command,exit=done.returncode);runs.append(record)
   (root/'runs.json').write_text(json.dumps(runs,indent=2)+'\n');assert done.returncode==0,(name,(root/(name+'.log')).read_text())
   record['summary']=next(csv.DictReader(output.open()));(root/'runs.json').write_text(json.dumps(runs,indent=2)+'\n')
   message=name+' recall='+record['summary']['changed_recall']+' cpu_ms='+record['summary']['mutation_cpu_ms']
   print(message,flush=True)
   with (root/'run.log').open('a') as log:log.write(message+'\n')
