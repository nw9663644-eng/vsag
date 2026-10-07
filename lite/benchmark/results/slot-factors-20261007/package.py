import csv,json,pathlib,shutil,gzip,hashlib,collections
root=pathlib.Path('/home/ubuntu/project/vsag-lite-slot-factors-20261007'); repo=pathlib.Path.cwd(); out=repo/'lite/benchmark/results/slot-factors-20261007'; out.mkdir(exist_ok=False)
cases=['initial','full-churn','cycle-1099','cycle-3000','cycle-7112']; summary=[]
for case in cases:
    rows=list(csv.DictReader((root/'final'/f'{case}.csv').open())); ordered=list(csv.DictReader((root/'final'/f'{case}-ordered.csv').open()))
    assert len(rows)==len(ordered)==800 and all(int(r['eligible'])==1 for r in rows)
    baseline={int(r['query']):int(r['hits']) for r in rows if r['mask']=='0'}
    masks=[]
    for mask in range(8):
        current=[r for r in rows if int(r['mask'])==mask]; assert len(current)==100
        assert all(int(r['baseline_native_ids_equal'])==int(mask==0) for r in current)
        delta=[int(r['hits'])-baseline[int(r['query'])] for r in current]
        masks.append(dict(mask=mask,recall=sum(int(r['hits']) for r in current)/1000,wins=sum(d>0 for d in delta),losses=sum(d<0 for d in delta),ties=sum(int(r['tie_comparisons']) for r in current)))
    def ids(name,mask):
        result=collections.defaultdict(list)
        for r in csv.DictReader((root/'final'/f'{name}.csv.neighbors.csv').open()):
            if int(r['mask'])==mask: result[int(r['query'])].append(int(r['id']))
        return dict(result)
    assert ids(case,7)==ids(case+'-ordered',0)
    summary.append(dict(case=case,masks=masks,all_restored_ordered_ids_equal=True))
(out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
for p in (root/'final').iterdir():
    if p.is_file():
        if p.suffix=='.csv':
            with p.open('rb') as source,gzip.open(out/(p.name+'.gz'),'wb') as dest: shutil.copyfileobj(source,dest)
        else: shutil.copy2(p,out/p.name)
for name in ['checks.json','ordered-receipts.json','run_final.py','package.py']:
    shutil.copy2(root/name,out/name)
for p in root.glob('*.log'): shutil.copy2(p,out/p.name)
manifest={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.iterdir()) if p.is_file()}
(out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(summary,indent=2))
