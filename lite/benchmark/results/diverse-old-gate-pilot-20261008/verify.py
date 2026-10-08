"""Verify the strict directional old-neighbor gate pilot."""
import csv,hashlib,io,json,struct,tarfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent; REPORTS=ROOT.parent
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def unpack(data):
 out={}
 with tarfile.open(fileobj=io.BytesIO(data),mode='r:gz') as t:
  for m in t.getmembers():
   assert m.isfile() and Path(m.name).name==m.name and m.name not in out
   out[m.name]=t.extractfile(m).read()
 return out
def rows(data): return list(csv.DictReader(io.StringIO(data.decode())))
def truths(data):
 out=[];o=0
 while o<len(data):
  n=struct.unpack_from('<i',data,o)[0];o+=4;assert n==10;out.append(set(struct.unpack_from('<10i',data,o)));o+=40
 assert o==len(data);return out
def main():
 manifest=json.loads((ROOT/'manifest.json').read_text())
 for n,h in manifest.items(): assert Path(n).name==n and sha(ROOT/n)==h
 raw=unpack((ROOT/'raw.tar.gz').read_bytes()); members=json.loads((ROOT/'members.json').read_text()); assert raw.keys()==members.keys()
 for n,h in members.items(): assert hashlib.sha256(raw[n]).hexdigest()==h
 evidence=json.loads(raw['previous-evidence.json'])['scored-old-candidates-20261008']; prev=REPORTS/'scored-old-candidates-20261008'
 for n,h in evidence.items(): assert sha(prev/n)==h
 scored=unpack((prev/'raw.tar.gz').read_bytes())
 builds=json.loads(raw['build-receipts.json']); source_hash=hashlib.sha256(raw['graph_backend.cpp']).hexdigest()
 assert {x['variant'] for x in builds}=={'release','asan'}
 for x in builds:
  assert x['source_sha256']==source_hash and '-DVSAG_LITE_EXPERIMENT_DIVERSE_OLD_UPDATE' in x['compile']
  assert raw[x['variant']+'-fixture.log'].decode().strip()=='Diverse-old gate fixtures passed'
  assert raw[x['variant']+'-baseline-fixture.log'].decode().strip()=='Diverse-old gate fixtures passed'
  assert 'All tests passed (545120 assertions in 14 test cases)' in raw[x['variant']+'-existing-tests.log'].decode()
 assert raw['format.log']==b'' and raw['tidy.log']==b''
 patch=raw['candidate.patch'].decode(); assert 'VSAG_LITE_EXPERIMENT_DIVERSE_OLD_UPDATE' in patch and 'distance(qualified[i].slot, ranked[j].slot)' in patch
 assert raw['diverse-coordinate-gist.csv.neighbors.csv']==raw['diverse-coordinate-gist-r2.csv.neighbors.csv']
 for stem in ['diverse-coordinate-gist','diverse-coordinate-gist-r2']:
  summary=rows(raw[stem+'.csv']); assert len(summary)==1 and summary[0]['cycles']=='10000' and summary[0]['query_count']=='300' and summary[0]['k']=='10' and summary[0]['changed_recall']=='0.680000' and summary[0]['roundtrip']=='1'
  assert len(rows(raw[stem+'.csv.updates.csv']))==10000 and len(rows(raw[stem+'.csv.neighbors.csv']))==6000
 truth=truths(scored['input-coordinate-gist-changed-groundtruth.ivecs']); assert len(truth)==300
 streams={'baseline':rows(scored['coordinate-gist-baseline-0.csv.neighbors.csv']),'scored':rows(scored['coordinate-gist-candidate-0.csv.neighbors.csv']),'diverse':rows(raw['diverse-coordinate-gist-r2.csv.neighbors.csv'])}
 ordered={};hits={}
 for name,rs in streams.items():
  ordered[name]=[(r['phase'],int(r['query']),int(r['rank']),int(r['id'])) for r in rs]; got=[set() for _ in truth]
  for r in rs:
   if r['phase']=='changed': got[int(r['query'])].add(int(r['id']))
  assert all(len(x)==10 for x in got); hits[name]=[len(a&b) for a,b in zip(got,truth)]
 def delta(a,b):
  ds=[x-y for x,y in zip(hits[a],hits[b])]
  return {'net_hits':sum(ds),'wins':sum(x>0 for x in ds),'losses':sum(x<0 for x in ds),'ties':sum(x==0 for x in ds),'different_ordered_rows':sum(x!=y for x,y in zip(ordered[a],ordered[b]))}
 analysis={'query_count':300,'k':10,'baseline_hits':sum(hits['baseline']),'scored_hits':sum(hits['scored']),'diverse_hits':sum(hits['diverse']),'diverse_vs_baseline':delta('diverse','baseline'),'diverse_vs_scored':delta('diverse','scored'),'repeat_neighbors_exact':True,'decision':'reject this strict all-ANN directional gate; it redistributes errors without recovering net recall'}
 assert analysis==json.loads(raw['analysis.json'])
 print(json.dumps({'pass_checks':True,'analysis':analysis},indent=2))
if __name__=='__main__': main()
