from pathlib import Path
import json,os,subprocess
root=Path(__file__).resolve().parent;repo=Path.cwd();rows=[]
cases=[('cohere-initial','baseline-build-r0',root/'validation/scale-10000','baseline'),('cohere-baseline','baseline-crud-r0',root/'validation/scale-10000','baseline'),('cohere-candidate','candidate-crud-r0',root/'validation/scale-10000','candidate')]
for dataset in ['sift','gist']:
    for variant in ['baseline','candidate']:
        cases.append((dataset+'-'+variant,dataset+'-'+variant+'-crud',Path('/home/ubuntu/project/vsag-lite-datasets')/dataset/'prepared-10k-100k/scale-10000',variant))
for name,stem,data,variant in cases:
    snap=root/(stem+'.snapshot');output=root/(name+'.native.csv')
    cmd=['taskset','-c','0',str(repo/'build-lite-fragment-release/lite_graph_slot_probe'),str(snap),str(snap),str(data),str(output)]
    lib=root/'before' if variant=='baseline' else repo/'build-lite-diverse-repair-release'
    result=subprocess.run(cmd,env=dict(os.environ,LD_LIBRARY_PATH=str(lib)),capture_output=True)
    (root/(name+'.native.stderr.log')).write_bytes(result.stderr)
    rows.append(dict(name=name,stem=stem,dataset=str(data),command=cmd,library=str(lib),exit=result.returncode))
    (root/'native-commands.json').write_text(json.dumps(rows,indent=2)+'\n')
    assert result.returncode==0,(name,result.stderr)
    print(name,'native ID sets verified',flush=True)
