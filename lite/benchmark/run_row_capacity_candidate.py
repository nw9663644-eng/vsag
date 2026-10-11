#!/usr/bin/env python3
# Copyright 2024-present the vsag project
# SPDX-License-Identifier: Apache-2.0
"""Frozen real100k RaBitQ ownership comparison; old Lite is NOT Full."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

repo=Path(__file__).resolve().parents[2]
build=repo/"build-lite-fp16-simd-release"
out=repo/"lite/benchmark/results/rabitq-row-capacity-20261011"
assert not out.exists(), "Requires a fresh output directory"
scratch=Path(tempfile.mkdtemp(prefix="vsag-row-capacity-",dir="/dev/shm"))
control=scratch/"control"
(control/"lite").mkdir(parents=True)
parent="bf50173f02e972a30a0f10a77530f31a356e046a"
head=subprocess.check_output(["git","rev-parse","HEAD"],cwd=repo,text=True).strip()
assert head=="bf50173f02e972a30a0f10a77530f31a356e046a"
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
records=[]
def run(tag,cmd,cwd=repo):
    with (scratch/(tag+".log")).open("w") as log:
        result=subprocess.run(cmd,cwd=cwd,env=dict(os.environ,TMPDIR="/dev/shm"),stdout=log,stderr=log)
    records.append(dict(tag=tag,command=cmd,cwd=str(cwd),exit=result.returncode))
    assert result.returncode==0,tag
for name,target in [("src/lite/rabitq_graph_state.h",control/"lite/rabitq_graph_state.h"),
                    ("src/lite/rabitq_backend.cpp",control/"adapter.cpp")]:
    target.write_bytes(subprocess.check_output(["git","show",parent+":"+name],cwd=repo))
prior=json.loads((repo/"lite/benchmark/results/rabitq-safe-link-20261011/identity.json").read_text())
variant=prior["variants"]["control"]
compile_cmd=[("-I"+str(control)) if x.startswith("-I/dev/shm/") else x for x in variant["compile"]]
compile_cmd[compile_cmd.index("-o")+1]=str(control/"adapter.o")
compile_cmd[-1]=str(control/"adapter.cpp")
run("compile-control",compile_cmd)
run("deps-control",compile_cmd[:compile_cmd.index("-o")]+["-MM",str(control/"adapter.cpp")])
assert str(control/"lite/rabitq_graph_state.h") in (scratch/"deps-control.log").read_text()
link_cmd=variant["link"][:]
link_cmd[link_cmd.index("-o")+1]=str(control/"libvsag-lite.so")
link_cmd=[str(control/"adapter.o") if x.endswith("/adapter.o") else x for x in link_cmd]
run("link-control",link_cmd,build)
run("release-tests",["ctest","--test-dir",str(build),"--output-on-failure"])
meta=dict(parent=parent,candidate=head,
    policy="Both public NONE/reverse=false; no incoming-safe experimental adapter",
    libraries=dict(control=sha(control/"libvsag-lite.so"),candidate=sha(build/"libvsag-lite.so")),
    source_sha256={n:sha(repo/n) for n in [
        "src/lite/rabitq_graph_state.h","src/lite/rabitq_backend.cpp",
        "src/lite/rabitq_backend_test.cpp","lite/benchmark/graph_crud_quality.cpp",
        "lite/benchmark/load_memory.cpp","lite/benchmark/run_aligned_comparison.py",
        "lite/benchmark/run_row_capacity_candidate.py"]},
    shared_object_sha256={n:sha(build/n) for n in link_cmd if n.endswith(".o") and not n.endswith("/adapter.o")},
    config=dict(degree=16,construction_ef=128,query_ef=512,cpu=0,trials=3,loads_per_builder=3,
        count=100000,queries=100,rounds=0),
    limits=["Observed100 queries, exploratory P99", "Warm/uncontrolled cache",
            "Not Full", "No real changed-value long CRUD measured",
            "External builder peak includes input data and native reload state"])
candidate=scratch/"candidate"
candidate.mkdir()
source=(repo/"src/lite/rabitq_backend.cpp").read_text()
start=source.index("            // Construction reserves a spare edge per row;")
end=source.index("            rabitq::MutableGraphState state(",start)
source=source[:start]+source[end:]
(candidate/"adapter.cpp").write_text(source)
cmd2=compile_cmd[:]
cmd2=[x for x in cmd2 if x!="-I"+str(control)]
cmd2[cmd2.index("-o")+1]=str(candidate/"adapter.o")
cmd2[-1]=str(candidate/"adapter.cpp")
run("compile-candidate",cmd2)
link2=link_cmd[:]
link2[link2.index("-o")+1]=str(candidate/"libvsag-lite.so")
link2=[str(candidate/"adapter.o") if x==str(control/"adapter.o") else x for x in link2]
run("link-candidate",link2,build)
meta["libraries"]["candidate"]=sha(candidate/"libvsag-lite.so")
meta["candidate_only_change"]="Remove build-row shrink loop; keep build capacity, same edges/order/defaults"
meta["overlay_backend_sha256"]=sha(candidate/"adapter.cpp")
runner=scratch/"candidate-build"
runner.mkdir()
for n in ["lite_graph_crud_quality","lite_load_memory"]:
    (runner/n).symlink_to(build/n)
(runner/"libvsag-lite.so").symlink_to(candidate/"libvsag-lite.so")
cmd=["python3",str(repo/"lite/benchmark/run_aligned_comparison.py"),
    "--lite-build",str(runner),"--control-library",str(control/"libvsag-lite.so"),
    "--dataset","gist100k=/home/ubuntu/project/vsag-lite-datasets/gist/prepared-10k-100k/scale-100000",
    "--dataset","cohere100k=/home/ubuntu/project/vsag-lite-cohere-normalized-20261006/prepared/scale-100000",
    "--storage","rabitq8","--output",str(out),"--scratch","/dev/shm",
    "--trials","3","--loads","3","--ef","512","--cpu","0"]
print("START isolated no-shrink candidate real100k comparison",flush=True)
result=subprocess.run(cmd,cwd=repo,env=dict(os.environ,TMPDIR="/dev/shm",
    OPENBLAS_NUM_THREADS="1",OMP_NUM_THREADS="1",MKL_NUM_THREADS="1"))
records.append(dict(tag="measure",command=cmd,cwd=str(repo),exit=result.returncode))
if out.exists():
    (out/"candidate-backend.cpp").write_bytes((candidate/"adapter.cpp").read_bytes())
    (out/"source-identity.json").write_text(json.dumps(meta,indent=2)+"\n")
    (out/"setup-commands.json").write_text(json.dumps(records,indent=2)+"\n")
    for name,target in [("control-state.h",control/"lite/rabitq_graph_state.h"),
                        ("control-backend.cpp",control/"adapter.cpp")]:
        (out/name).write_bytes(target.read_bytes())
    for n in meta["source_sha256"]:
        (out/("source-"+Path(n).name)).write_bytes((repo/n).read_bytes())
    for p in scratch.glob("*.log"):
        (out/p.name).write_bytes(p.read_bytes())
assert result.returncode==0, "Raw failures retained"
assert len(json.loads((out/"rows.json").read_text()))==12
print("COMPLETE12 builders36 fresh loaders; not Full or long CRUD",flush=True)
