#!/usr/bin/env python3
# Copyright 2024-present the vsag project
# SPDX-License-Identifier: Apache-2.0
"""Fresh loaded-state save pairs; do not confuse with build-then-save timings."""
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import statistics
import subprocess
import tempfile

repo=Path(__file__).resolve().parents[2]
out=repo/"lite/benchmark/results/rabitq-stream-save-20261011"
out.mkdir(exist_ok=False)
scratch=Path(tempfile.mkdtemp(prefix="vsag-stream-save-",dir="/dev/shm"))
build=repo/"build-lite-fp16-simd-release"
parent="b09631c876bf9d35326d65f32d304838a8f4427b"
control=scratch/"control"
(control/"lite").mkdir(parents=True)
records=[]
def sha(p):
    h=hashlib.sha256()
    with p.open("rb") as stream:
        for block in iter(lambda:stream.read(1048576),b""):h.update(block)
    return h.hexdigest()
def run(tag,cmd,cwd=repo,env=None):
    r=subprocess.run(cmd,cwd=cwd,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    (out/(tag+".stdout")).write_text(r.stdout)
    (out/(tag+".stderr")).write_text(r.stderr)
    records.append(dict(tag=tag,command=list(map(str,cmd)),cwd=str(cwd),exit=r.returncode))
    (out/"commands.json").write_text(json.dumps(records,indent=2)+"\n")
    assert r.returncode==0,tag
    return r.stdout
for n in ["rabitq_graph_state.h","rabitq_snapshot.h"]:
    payload=subprocess.check_output(["git","show",parent+":src/lite/"+n],cwd=repo)
    (control/"lite"/n).write_bytes(payload);(out/("control-"+n)).write_bytes(payload)
payload=subprocess.check_output(["git","show",parent+":src/lite/rabitq_backend.cpp"],cwd=repo)
(control/"adapter.cpp").write_bytes(payload);(out/"control-backend.cpp").write_bytes(payload)
prior=json.loads((repo/"lite/benchmark/results/rabitq-safe-link-20261011/identity.json").read_text())["variants"]["control"]
cmd=[("-I"+str(control)) if x.startswith("-I/dev/shm/") else x for x in prior["compile"]]
cmd[cmd.index("-o")+1]=str(control/"adapter.o");cmd[-1]=str(control/"adapter.cpp")
run("compile-control",cmd)
deps=run("deps-control",cmd[:cmd.index("-o")]+["-MM",str(control/"adapter.cpp")])
assert str(control/"lite/rabitq_snapshot.h") in deps and str(control/"lite/rabitq_graph_state.h") in deps
link=prior["link"][:];link[link.index("-o")+1]=str(control/"libvsag-lite.so")
link=[str(control/"adapter.o") if x.endswith("/adapter.o") else x for x in link]
run("link-control",link,build)
probe=scratch/"save-probe"
run("compile-probe",["/usr/bin/c++","-O3","-DNDEBUG","-std=c++17","-I"+str(repo/"include"),
    str(repo/"lite/benchmark/rabitq_save_probe.cpp"),"-L"+str(build),
    "-Wl,-rpath,"+str(build),"-lvsag-lite","-o",str(probe)])
variants={"control":control,"candidate":build}
sources=["src/lite/rabitq_graph_state.h","src/lite/rabitq_snapshot.h","src/lite/rabitq_backend.cpp",
         "src/lite/rabitq_backend_test.cpp","lite/benchmark/rabitq_save_probe.cpp",
         "lite/benchmark/run_stream_save.py","lite/benchmark/graph_crud_quality.cpp"]
identity=dict(parent=parent,source_sha256={n:sha(repo/n) for n in sources},
    libraries={n:sha(p/"libvsag-lite.so") for n,p in variants.items()},
    shared_object_sha256={n:sha(build/n) for n in link if n.endswith(".o") and not n.endswith("/adapter.o")},
    scope="Fresh loaded-state Save/close, not original build-then-save cost or cold I/O",
    trials=7,cpu=0,policy="Both public NONE/reverse=false",inputs={},snapshots={})
for n in sources:(out/("source-"+Path(n).name)).write_bytes((repo/n).read_bytes())
(out/"candidate.patch").write_bytes(subprocess.check_output(["git","diff","--",
    "src/lite/rabitq_graph_state.h","src/lite/rabitq_snapshot.h","src/lite/rabitq_backend_test.cpp"],cwd=repo))
previous=json.loads((repo/"lite/benchmark/results/rabitq-owned-real100k-20261011/rows.json").read_text())
rows=[]
for label,path in [
    ("gist100k","/home/ubuntu/project/vsag-lite-datasets/gist/prepared-10k-100k/scale-100000"),
    ("cohere100k","/home/ubuntu/project/vsag-lite-cohere-normalized-20261006/prepared/scale-100000")]:
    root=Path(path);snapshot=scratch/(label+".snapshot")
    env=dict(os.environ,LD_LIBRARY_PATH=str(build),VSAG_GRAPH_STORAGE="rabitq8",
        VSAG_GRAPH_DEGREE="16",VSAG_GRAPH_EF="128",VSAG_GRAPH_QUERY_EF="512",
        OMP_NUM_THREADS="1",OPENBLAS_NUM_THREADS="1",MKL_NUM_THREADS="1")
    identity["inputs"][label]={n:dict(path=str(root/n),bytes=(root/n).stat().st_size,sha256=sha(root/n))
        for n in ["base.fvecs","queries.fvecs","groundtruth.ivecs"]}
    run(label+"-prepare",["taskset","-c","0",str(build/"lite_graph_crud_quality"),
        str(root),str(snapshot),"0","1",str(out/(label+"-prepare.queries.csv"))],env=env)
    digest=sha(snapshot);assert all(r["snapshot_sha256"]==digest for r in previous if r["dataset"]==label)
    identity["snapshots"][label]=dict(sha256=digest,bytes=snapshot.stat().st_size)
    print(label,"prepared unchanged100k snapshot",flush=True)
    for trial in range(7):
        names=["control","candidate"] if trial%2==0 else ["candidate","control"]
        for name in names:
            tag=f"{label}-t{trial}-{name}";target=scratch/(tag+".snapshot")
            e=dict(env,LD_LIBRARY_PATH=str(variants[name]))
            text=run(tag,["taskset","-c","0",str(probe),str(snapshot),str(target)],env=e)
            values=next(csv.DictReader(io.StringIO(text)))
            assert int(values["count"])==100000
            assert sha(target)==digest
            rows.append(dict(dataset=label,trial=trial,variant=name,metrics=values,
                snapshot_sha256=digest))
            (out/"rows.json").write_text(json.dumps(rows,indent=2)+"\n")
            assert target.resolve().parent==scratch.resolve() and target.is_file();target.unlink()
    assert snapshot.resolve().parent==scratch.resolve() and snapshot.is_file();snapshot.unlink()
    print(label,"seven save pairs complete",flush=True)
(out/"identity.json").write_text(json.dumps(identity,indent=2)+"\n")
summary={}
for label in ["gist100k","cohere100k"]:
    summary[label]={}
    for metric in ["save_ms","before_rss_kib","before_hwm_kib","after_rss_kib","after_hwm_kib","bytes"]:
        med={name:statistics.median(float(r["metrics"][metric]) for r in rows
             if r["dataset"]==label and r["variant"]==name) for name in variants}
        summary[label][metric]=dict(med,change_percent=100*(med["candidate"]/med["control"]-1))
(out/"summary.json").write_text(json.dumps(summary,indent=2)+"\n")
print(json.dumps(summary,indent=2),flush=True)
