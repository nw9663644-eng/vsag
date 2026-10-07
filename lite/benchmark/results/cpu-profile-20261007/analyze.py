import json,re,collections,csv,statistics,sys
from pathlib import Path
root=Path(sys.argv[1]) if len(sys.argv)==2 else Path(__file__).resolve().parent
records=[]
for path in sorted(root.glob('*.stacks.txt')):
 groups=collections.defaultdict(collections.Counter)
 samples=0
 for block in re.split(r'\n\s*\n',path.read_text().strip()):
  lines=block.splitlines();assert 'cpu-clock:u:' in lines[0],lines[0]
  frames=[]
  for line in lines[1:]:
   match=re.match(r'\s*[0-9a-f]+\s+(.+)',line)
   if match:
    symbol=match[1].rsplit(' (',1)[0]
    symbol=re.sub(r'\+0x[0-9a-f]+$', '', symbol)
    frames.append(symbol)
  assert frames
  joined='\n'.join(frames)
  if 'Index::BuildGraph' in joined: phase='BuildGraph'
  elif 'GraphBackend::Update' in joined or 'Index::Update' in joined: phase='Update'
  elif 'GraphBackend::Remove' in joined or 'Index::Remove' in joined: phase='Remove'
  elif 'GraphBackend::Add' in joined: phase='GraphAdd'
  elif 'BruteForceBackend::Add' in joined: phase='FlatStaging'
  elif 'Index::Search' in joined: phase='Query'
  else:phase='Other'
  groups[phase][frames[0]]+=1;samples+=1
 report=(root/path.name.replace('.stacks.txt','.self.txt')).read_text()
 match=re.search(r'\((\d+) samples\)', (root/path.name.replace('.stacks.txt','.stderr.log')).read_text())
 assert match and samples==int(match[1].replace(',','')),(samples,path)
 assert 'Total Lost Samples: 0' in report
 stdout=(root/path.name.replace('.stacks.txt','.stdout.log')).read_text()
 header=next(line for line in stdout.splitlines() if 'recall_at_k' in line)
 data=stdout.splitlines()[stdout.splitlines().index(header)+1]
 quality=next(csv.DictReader([header,data]))
 records.append({'name':path.name.replace('.stacks.txt',''),'samples':samples,'quality':quality,'phases':{p:{'samples':sum(counter.values()),'fraction':sum(counter.values())/samples,'hot_self':counter.most_common(12),'distance_self_fraction':sum(n for name,n in counter.items() if 'distance' in name.lower())/sum(counter.values())} for p,counter in groups.items()}})
(root/'stack-summary.json').write_text(json.dumps(records,indent=2)+'\n')
for record in records:
 print(record['name'],record['samples'],{p:(x['samples'],round(x['distance_self_fraction']*100,2)) for p,x in record['phases'].items()})
 for p in ['BuildGraph','Update','GraphAdd']:
  if p in record['phases']:print(p,record['phases'][p]['hot_self'][:3])
