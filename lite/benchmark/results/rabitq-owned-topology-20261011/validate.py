#!/usr/bin/env python3
import gzip
import json
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
import time

repo=Path(__file__).resolve().parents[4]
out=Path(__file__).resolve().parent
while not (out/"summary.json").exists():
    time.sleep(2)
assert len(json.loads((out/"rows.json").read_text()))==12
env=dict(os.environ,TMPDIR="/dev/shm",ASAN_OPTIONS="detect_leaks=1:halt_on_error=1",
         UBSAN_OPTIONS="halt_on_error=1:print_stacktrace=1")
commands=[]
def run(tag,cmd):
    with (out/(tag+".log")).open("w") as log:
        r=subprocess.run(cmd,cwd=repo,env=env,stdout=log,stderr=log)
    commands.append(dict(tag=tag,command=cmd,exit=r.returncode))
    (out/"validation-commands.json").write_text(json.dumps(commands,indent=2)+"\n")
    assert r.returncode==0,tag
for tag,build in [("coverage",Path("/home/ubuntu/project/vsag-opt-coverage-20261009")),
                  ("disabled",Path("/home/ubuntu/project/vsag-opt-default-20261009"))]:
    run(tag+"-build",["cmake","--build",str(build),"-j1"])
    if tag=="coverage":
        files=list(build.rglob("*.gcda"));assert len(files)==19
        for p in files:
            assert p.resolve().is_relative_to(build.resolve()) and p.is_file()
            p.unlink()
    run(tag+"-test",["ctest","--test-dir",str(build),"--output-on-failure"])
sources=["src/lite/rabitq_graph_state.h","src/lite/rabitq_backend.cpp",
         "src/lite/rabitq_backend_test.cpp",str((out/"probe.cpp").relative_to(repo))]
run("format",["clang-format-15","--dry-run","--Werror"]+sources)
run("tidy",["clang-tidy-15","-p","build-lite-fp16-simd-release",
    "-header-filter=.*/src/lite/.*","-warnings-as-errors=*",
    "src/lite/rabitq_backend.cpp","src/lite/rabitq_backend_test.cpp"])
ram=Path(tempfile.mkdtemp(prefix="vsag-owned-gcov-",dir="/dev/shm"))
with (out/"gcov.log").open("w") as log:
    for p in Path("/home/ubuntu/project/vsag-opt-coverage-20261009").rglob("*.gcda"):
        subprocess.run(["gcov","--json-format",str(p)],cwd=ram,stdout=log,stderr=log,check=True)
files=sorted(ram.glob("*.gcov.json.gz"));assert len(files)==19
lines={}
for p in files:
    for f in json.loads(gzip.decompress(p.read_bytes()))["files"]:
        for line in f["lines"]:
            key=(f["file"],line["line_number"])
            lines[key]=lines.get(key,False) or line["count"]>0
scopes={}
for scope in ["lite","shared_simd","combined"]:
    selected=[]
    for (name,_),covered in lines.items():
        lite=("/src/lite/" in name or "/include/vsag/lite/" in name) and not name.endswith("_test.cpp")
        simd="/src/simd/" in name and not name.endswith("_test.cpp")
        if (scope=="lite" and lite) or (scope=="shared_simd" and simd) or (scope=="combined" and (lite or simd)):
            selected.append(covered)
    scopes[scope]=dict(covered=sum(selected),total=len(selected),percent=100*sum(selected)/len(selected))
    assert scopes[scope]["percent"]>=90
(out/"coverage.json").write_text(json.dumps(dict(scopes=scopes,fresh_counters=19,
    note="Scoped Lite and shared SIMD, not whole Full VSAG"),indent=2)+"\n")
with tarfile.open(out/"coverage-raw.tar.gz","w:gz") as tar:
    for p in files:
        tar.add(p,arcname=p.name)
for p in Path("/home/ubuntu/project").glob("vsag-owned-topology-*20261011.log"):
    (out/p.name).write_bytes(p.read_bytes())
print(json.dumps(scopes,indent=2),flush=True)
