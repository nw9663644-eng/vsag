set -eu
cd /home/ubuntu/project/vsag-lite-baseline-v01
python3 - <<'PY'
import json,os,subprocess
from pathlib import Path
out=Path('lite/benchmark/results/rabitq-load-id-map-20261011')
logs=Path('/home/ubuntu/project/vsag-load-id-map-20261011')
logs.mkdir(exist_ok=True)
records=[]
env=dict(os.environ,TMPDIR='/dev/shm',ASAN_OPTIONS='detect_leaks=1:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
def run(tag,command):
 with (logs/(tag+'.log')).open('w') as log:r=subprocess.run(command,env=env,stdout=log,stderr=log)
 records.append({'tag':tag,'command':command,'exit':r.returncode,'expected_exit':0})
 (out/'validation-commands.json').write_text(json.dumps(records,indent=2)+'\n')
 assert r.returncode==0,tag
run('release-build',['cmake','--build','build-lite-fp16-simd-release','-j1'])
run('release-test',['ctest','--test-dir','build-lite-fp16-simd-release','-V'])
for tag,build in [('sanitize-final','/home/ubuntu/project/vsag-opt-sanitize-20261009'),('coverage','/home/ubuntu/project/vsag-opt-coverage-20261009'),('disabled','/home/ubuntu/project/vsag-opt-default-20261009')]:
 run(tag+'-build',['cmake','--build',build,'-j1'])
 if tag=='coverage':
  base=Path(build).resolve();files=list(base.rglob('*.gcda'));assert len(files)==19
  for p in files:
   assert p.resolve().is_relative_to(base) and p.is_file()
   p.unlink()
  print('Reset19 verified generated counters',flush=True)
 run(tag+'-test',['ctest','--test-dir',build,'-V'])
run('format-final',['clang-format-15','--dry-run','--Werror','src/lite/rabitq_snapshot.h','src/lite/rabitq_backend_test.cpp'])
run('tidy-final',['clang-tidy-15','-p','build-lite-fp16-simd-release','-header-filter=.*/src/lite/.*','-warnings-as-errors=*','src/lite/rabitq_backend.cpp','src/lite/rabitq_backend_test.cpp'])
print('Ten final validation commands passed',flush=True)
PY
