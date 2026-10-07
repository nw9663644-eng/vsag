from pathlib import Path
import csv,json,hashlib,gzip,shutil,subprocess,struct,statistics,random,math
root=Path(__file__).resolve().parent;repo=Path.cwd();out=repo/'lite/benchmark/results/diverse-repair-20261007';out.mkdir(exist_ok=False)
for p in root.iterdir():
    if p.is_file() and p.suffix in ['.csv','.log','.json','.py','.patch','.txt']:
        if p.suffix in ['.csv','.log']:
            with gzip.open(out/(p.name+'.gz'),'wb') as f:f.write(p.read_bytes())
        else:shutil.copy2(p,out/p.name)
data={'cohere':Path('/home/ubuntu/project/vsag-lite-cohere-normalized-20261006/prepared/scale-10000'),'validation':root/'validation/scale-10000','sift':Path('/home/ubuntu/project/vsag-lite-datasets/sift/prepared-10k-100k/scale-10000'),'gist':Path('/home/ubuntu/project/vsag-lite-datasets/gist/prepared-10k-100k/scale-10000')}
input_hashes={}
for name,p in data.items():
    shutil.copy2(p/'groundtruth.ivecs',out/(name+'-groundtruth.ivecs'))
    for f in ['base.fvecs','queries.fvecs','groundtruth.ivecs']:
        input_hashes[str(p/f)]=hashlib.sha256((p/f).read_bytes()).hexdigest()
    if (p/'manifest.json').exists():shutil.copy2(p/'manifest.json',out/(name+'-manifest.json'))
for name in ['cohere','validation']:
    shutil.copy2(data[name]/'source-query-ids.i64',out/(name+'-source-query-ids.i64'))
assert input_hashes[str(data['cohere']/'base.fvecs')]==input_hashes[str(data['validation']/'base.fvecs')]
shutil.copy2('/home/ubuntu/project/vsag-lite-cohere-normalized-20261006/protocol.json',out/'prior-query-split.json')
(out/'input-hashes.json').write_text(json.dumps(input_hashes,indent=2)+'\n')
paired=[]
for dataset in ['cohere','sift','gist','validation']:
    if dataset=='cohere':a=root/'baseline-crud-r0.hits.csv';b=root/'candidate-crud-r0.hits.csv'
    elif dataset=='validation':a=root/'cohere-validation-baseline.csv';b=root/'cohere-validation-candidate.csv'
    else:a=root/(dataset+'-baseline-crud.hits.csv');b=root/(dataset+'-candidate-crud.hits.csv')
    left=list(csv.DictReader(a.open()));right=list(csv.DictReader(b.open()));assert len(left)==len(right)
    deltas=[int(y['hits'])-int(x['hits']) for x,y in zip(left,right)]
    rng=random.Random(20261007);boot=sorted(sum(rng.choices(deltas,k=len(deltas)))/(10*len(deltas)) for _ in range(5000))
    wins=sum(x>0 for x in deltas);losses=sum(x<0 for x in deltas);n=wins+losses
    p=min(1,2*sum(math.comb(n,i) for i in range(min(wins,losses)+1))/2**n) if n else 1
    paired.append(dict(dataset=dataset,queries=len(deltas),baseline=sum(int(x['hits']) for x in left)/(10*len(left)),candidate=sum(int(x['hits']) for x in right)/(10*len(right)),wins=wins,losses=losses,ties=len(deltas)-n,bootstrap_mean_delta_95=[boot[125],boot[4874]],sign_p=p))
(out/'paired-summary.json').write_text(json.dumps(paired,indent=2)+'\n');print(json.dumps(paired,indent=2))
(root/'restoration.json').write_text(json.dumps({'head':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'src_include_unchanged':not bool(subprocess.check_output(['git','diff','--name-only','--','src','include'],text=True))},indent=2)+'\n')
shutil.copy2(root/'restoration.json',out/'restoration.json')
(out/'environment.txt').write_text(subprocess.check_output(['uname','-a'],text=True)+subprocess.check_output(['lscpu'],text=True))
