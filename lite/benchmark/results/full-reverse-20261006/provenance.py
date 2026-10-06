import hashlib,json,subprocess
from pathlib import Path
root=Path(__file__).resolve().parent
paths=['lite/benchmark/full_rabitq_dataset_main.cpp','lite/benchmark/full_delete_regression.cpp','build-full-known-runner/full_rabitq_dataset_benchmark','build-full-known-runner/full_delete_regression','/home/ubuntu/project/vsag-full-known-install-20261006/lib/libvsag.so','/home/ubuntu/project/vsag-lite-cohere-matched-20261006/final/scale-100000/base.fvecs','/home/ubuntu/project/vsag-lite-cohere-matched-20261006/final/scale-100000/queries.fvecs','/home/ubuntu/project/vsag-lite-cohere-matched-20261006/final/scale-100000/groundtruth.ivecs']
values={}
for p in paths:
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
 values[p]=h.hexdigest()
(root/'provenance.json').write_text(json.dumps({'parent':'f1733b203fafa663be94909f2bbfe3018d1bbb70','sha256':values,'library_origin':'d18c82a cached incremental shared build; not latest upstream'},indent=2)+'\n')
with (root/'environment.txt').open('w') as output:
 for cmd in [['uname','-a'],['lscpu'],['ldd','build-full-known-runner/full_rabitq_dataset_benchmark']]:
  output.write(str(cmd)+'\n');subprocess.run(cmd,stdout=output,stderr=subprocess.STDOUT)
