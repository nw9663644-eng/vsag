from pathlib import Path
import json,shlex,subprocess,hashlib,os
root=Path(__file__).resolve().parent;repo=Path.cwd();receipts=[]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
for variant,dirname in [('release','build-lite-fragment-release'),('asan','build-lite-baseline-asan')]:
 build=repo/dirname;out=root/variant
 command=shlex.split(next(r['command'] for r in json.loads((build/'compile_commands.json').read_text()) if r['file'].endswith('/src/lite/graph_backend.cpp')))
 command[command.index('-o')+1]=str(out/'graph_backend.o');command[-1]=str(root/'graph_backend.cpp');command.insert(1,'-DVSAG_LITE_EXPERIMENT_SCORED_OLD_UPDATE')
 receipt={'variant':variant,'compile':command,'source_sha256':sha(root/'graph_backend.cpp'),'parent_source_sha256':sha(repo/'src/lite/graph_backend.cpp')}
 with (out/'build.log').open('wb') as f:
  subprocess.run(command,cwd=build,stdout=f,stderr=subprocess.STDOUT,check=True)
  line=subprocess.check_output(['ninja','-C',str(build),'-t','commands','vsag_lite'],text=True).splitlines()[-1]
  link=shlex.split(line)[2:-2];link[link.index('-o')+1]=str(out/'libvsag-lite.so')
  objects={}
  for i,a in enumerate(link):
   if a.endswith('/src/lite/graph_backend.cpp.o'):link[i]=str(out/'graph_backend.o')
   elif a.endswith('.o'):
    link[i]=str(build/a);objects[link[i]]=sha(link[i])
  subprocess.run(link,cwd=build,stdout=f,stderr=subprocess.STDOUT,check=True);receipt.update(link=link,reused_object_sha256=objects)
  fixture=shlex.split(next(r['command'] for r in json.loads((build/'compile_commands.json').read_text()) if r['file'].endswith('/src/lite/graph_backend_test.cpp')))
  fixture[fixture.index('-o')+1]=str(out/'fixture.o');fixture[-1]=str(root/'fixture.cpp')
  subprocess.run(fixture,cwd=build,stdout=f,stderr=subprocess.STDOUT,check=True)
  flags=['-fsanitize=address,undefined','-fno-omit-frame-pointer'] if variant=='asan' else []
  fixture_link=['/usr/bin/c++']+flags+[str(out/'fixture.o'),'-L'+str(out),'-Wl,-rpath,'+str(out),'-lvsag-lite','-o',str(out/'fixture')]
  subprocess.run(fixture_link,stdout=f,stderr=subprocess.STDOUT,check=True)
  receipt.update(fixture_compile=fixture,fixture_link=fixture_link,library_sha256=sha(out/'libvsag-lite.so'))
 receipts.append(receipt);(root/'build-receipts.json').write_text(json.dumps(receipts,indent=2)+'\n')
 env=dict(os.environ,LD_LIBRARY_PATH=str(out),ASAN_OPTIONS='detect_leaks=1:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')
 with (out/'fixture.log').open('wb') as f:subprocess.run([str(out/'fixture'),'on'],env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
 with (out/'existing-tests.log').open('wb') as f:subprocess.run([str(build/'lite_graph_tests')],env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
 env['LD_LIBRARY_PATH']=str(build)
 with (out/'baseline-fixture.log').open('wb') as f:subprocess.run([str(out/'fixture'),'off'],env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
 print(variant,'build/fixture/existing-tests passed',flush=True)
