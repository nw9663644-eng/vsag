from pathlib import Path
import subprocess,json,csv,gzip
root=Path(__file__).resolve().parent;commands=[];summary=[]
for path in sorted(root.glob('*.snapshot')):
 cycle=int(path.name.split('-')[1]);query={1099:99,3000:0,7112:12}[cycle]
 output=root/(path.stem+'.nodes.csv');cmd=['taskset','-c','0',str(root/'inspect'),str(path),str(root/f'query-{query}'),str(output)]
 result=subprocess.run(cmd,capture_output=True);(root/(path.stem+'.inspect.log')).write_bytes(result.stderr);commands.append(dict(command=cmd,exit=result.returncode));assert result.returncode==0,result.stderr
 rows=list(csv.DictReader(output.open()));hits=sum(int(r['truth'])*int(r['native_returned']) for r in rows);visited=sum(int(r['truth'])*int(r['visited']) for r in rows)
 summary.append(dict(snapshot=path.name,cycle=cycle,query=query,count=len(rows),hits=hits,truth_visited=visited,visited=sum(int(r['visited']) for r in rows),missed_truth_ids=[int(r['id']) for r in rows if r['truth']=='1' and r['visited']=='0']))
 with gzip.open(str(output)+'.gz','wb') as f:f.write(output.read_bytes())
 print(path.stem,hits,summary[-1]['missed_truth_ids'],flush=True)
(root/'inspect-commands.json').write_text(json.dumps(commands,indent=2)+'\n');(root/'inspect-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
