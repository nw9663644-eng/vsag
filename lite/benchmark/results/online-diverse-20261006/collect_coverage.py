from pathlib import Path
import subprocess,gzip,json
build=Path('/home/ubuntu/project/vsag-lite-baseline-v01/build-lite-online-diverse-release')
out=Path(__file__).resolve().parent
merged={}
for file in build.rglob('*.gcno'):
    subprocess.run(['gcov','-j','-b',str(file)],cwd=out,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True)
for file in out.glob('*.gcov.json.gz'):
    for record in json.loads(gzip.decompress(file.read_bytes()))['files']:
        name=record['file']
        if '/src/lite/' not in name and '/include/vsag/lite/' not in name:
            continue
        lines=merged.setdefault(name,{})
        for line in record['lines']:
            lines[line['line_number']]=lines.get(line['line_number'],0)+line['count']
result={}
for scope,files in [('all',merged),('cpp_and_public_headers',{k:v for k,v in merged.items() if k.endswith('.cpp') or '/include/vsag/lite/' in k})]:
    total=sum(len(x) for x in files.values())
    covered=sum(sum(v>0 for v in x.values()) for x in files.values())
    result[scope]={'covered':covered,'total':total,'percentage':100*covered/total}
result['files']={k:{'covered':sum(v>0 for v in x.values()),'total':len(x)} for k,x in merged.items()}
(out/'lite-line-coverage.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
