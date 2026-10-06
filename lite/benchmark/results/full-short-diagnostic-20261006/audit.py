import csv,hashlib,json,subprocess
from pathlib import Path
root=Path(__file__).resolve().parent
assert (root/'final-exit.txt').read_text().strip()=='diagnostic exit=0'
rows=list(csv.DictReader((root/'final-diagnostic.snapshot.diagnostic.csv').open()))
assert len(rows)==6
for cycle,row,id_value in [(711,110,15610),(889,288,73608)]:
 group=[r for r in rows if int(r['cycle'])==cycle]
 assert [int(r['ef_search']) for r in group]==[128,512,100000]
 assert all(int(r['query'])==row and int(r['returned_count'])==1 and int(r['hits'])==0
            and int(r['first_id'])==id_value for r in group)
 assert (cycle-1)*8191%100000==id_value
controls=json.loads((root/'controls.json').read_text())
assert len(controls)==12
for mode in ['remove','update-remove','last-remove','restored']:
 group=[r for r in controls if r['mode']==mode]
 assert len(group)==3 and all(r['returncode']==(-11 if 'remove'==mode or mode=='update-remove' else 0) for r in group)
text=(root/'minimal-gdb.log').read_text()
assert 'SIGSEGV' in text and 'codes3=0x0' in text and '{1, 3, 7, 6, 2, 5}' in text
paths=['lite/benchmark/full_rabitq_dataset_main.cpp','build-full-known-runner/full_rabitq_dataset_benchmark',str(root/'delete_reproducer.cpp'),str(root/'delete_reproducer'),'/home/ubuntu/project/vsag-full-known-install-20261006/lib/libvsag.so']
manifest={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in paths}
(root/'provenance.json').write_text(json.dumps({'parent':'765fc550db5979fe3b39fee41a97998de2f6e4ea','sha256':manifest,'dataset_provenance':'../full-mixed-20261006/provenance-sha256.json','scope':'known incremental d18c82a library, not latest upstream'},indent=2)+'\n')
print('Six retries, two identity matches, twelve controls and GDB stale-slot evidence verified')
