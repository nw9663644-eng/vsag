#!/usr/bin/env python3
# Copyright 2024-present the vsag project
# SPDX-License-Identifier: Apache-2.0
"""Archive completed real100k evidence; never rerun timing in collection."""
import difflib
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile
import time

repo=Path(__file__).resolve().parents[2]
out=repo/"lite/benchmark/results/rabitq-owned-real100k-20261011"
while not (out/"source-identity.json").exists() or not (out/"summary.json").exists():
    time.sleep(2)
assert len(json.loads((out/"rows.json").read_text()))==12
meta=json.loads((out/"source-identity.json").read_text())
commands=json.loads((out/"setup-commands.json").read_text())
assert all(r["exit"]==0 for r in commands)
control=Path(
    next(r["command"] for r in commands if r["tag"]=="link-control")[
        next(r["command"] for r in commands if r["tag"]=="link-control").index("-o")+1])
if control.exists():
    with (out/"driver-fixture.log").open("w") as log:
        r=subprocess.run(["python3","lite/benchmark/test_aligned_comparison.py",
            "build-lite-fp16-simd-release",str(control)],cwd=repo,stdout=log,stderr=log)
    assert r.returncode==0
else:
    # A completed archive can be collected offline after RAM control expires.
    with tarfile.open(out/"raw.tar.gz") as saved:
        log=saved.extractfile("driver-fixture.log").read()
    assert b"storage, per-query budget, unchanged construction, paired snapshots and output guards passed" in log
    (out/"driver-fixture.log").write_bytes(log)
for name in ["run_owned_real_acceptance.py","verify_owned_real_acceptance.py",
             "collect_owned_real_acceptance.py"]:
    compile((repo/"lite/benchmark"/name).read_text(),name,"exec")
data=json.loads((out/"summary.json").read_text())
report="""# RaBitQ ownership: real100k acceptance slice (2026-10-11)

Frozen production candidate4f73870 versus parent0444bf9. Both are Lite, NOT Full VSAG.
Both public NONE/reverse=false; no CACHED/safe-link adapter enabled.
This extends the synthetic ownership diagnostic to real high-dimensional inputs.
No production edits or degree/budget/model/seed tuning during this study.

GIST960 and normalized Cohere768,100k base/100 observed query vectors,k10,
degree16/build128/query512,CPU0 and BLAS/OMP/MKL1. Three alternating paired trials per
dataset;12 complete builders and36 fresh-process loaders. No concurrent build/test timing.
Base/query/GT identities and original preparation manifests preserved. Truth is existing
subset-specific squared-L2 GT; Cohere stores FP32 normalized rows with original cosine
rounding audit. This collection verifies raw GT intersections, not recomputation of GT.

## Resource/cost and quality

|Dataset|Whole-process peak old/new KiB|Change|Build old/new ms|Change|Recall old/new|
|---|---:|---:|---:|---:|---:|
"""
comparisons={}
for dataset in ["gist100k","cohere100k"]:
    pair={r["name"]:r for r in data if r["dataset"]==dataset}
    old,new=pair["control"],pair["lite"]
    comp={key:100*(new[key]/old[key]-1) for key in [
        "external_peak_rss_kib","build_ms","load_ms","save_ms","search_p50_us","search_p99_us"]}
    comparisons[dataset]=comp
    report+=f'|{dataset}|{old["external_peak_rss_kib"]:.0f}/{new["external_peak_rss_kib"]:.0f}|{comp["external_peak_rss_kib"]:+.2f}%|{old["build_ms"]:.3f}/{new["build_ms"]:.3f}|{comp["build_ms"]:+.2f}%|{old["recall_at_k"]:.6f}/{new["recall_at_k"]:.6f}|\n'
report+="\\n|Dataset|Save old/new ms|Change|\\n|---|---:|---:|\\n"
for dataset in ["gist100k","cohere100k"]:
    pair={r["name"]:r for r in data if r["dataset"]==dataset}
    old,new=pair["control"],pair["lite"]
    report+=f'|{dataset}|{old["save_ms"]:.3f}/{new["save_ms"]:.3f}|{comparisons[dataset]["save_ms"]:+.2f}%|\\n'
report+="\\nBoth query P50 medians increase; Save median regresses substantially. Do not claim overall speed acceptance. Reasons are not established by this study. Source still compacts full adjacency in save_mutable_snapshot via GetGraph; ownership handoff can also change row allocation locality. These are follow-up hypotheses requiring phase/cache profiling, not proven causes.\\n"
report+="\n|Dataset|P50 old/new us|P99 old/new us|Fresh warm load old/new ms|Snapshot bytes|Loaded total RSS old/new KiB|\n|---|---:|---:|---:|---:|---:|\n"
for dataset in ["gist100k","cohere100k"]:
    pair={r["name"]:r for r in data if r["dataset"]==dataset}
    old,new=pair["control"],pair["lite"]
    assert old["snapshot_bytes"]==new["snapshot_bytes"]
    report+=f'|{dataset}|{old["search_p50_us"]:.3f}/{new["search_p50_us"]:.3f}|{old["search_p99_us"]:.3f}/{new["search_p99_us"]:.3f}|{old["load_ms"]:.3f}/{new["load_ms"]:.3f}|{new["snapshot_bytes"]:.0f}|{old["loaded_rss_kib"]:.0f}/{new["loaded_rss_kib"]:.0f}|\n'
report+="""
Peak is /usr/bin/time whole builder high-water RSS INCLUDING input rows, source index,
graph construction, querying and native Save/Load validation with two index states.
It is NOT an isolated build-stage peak. Synthetic dim17's25.30% peak saving does not
transfer as-is to high-dimensional data: fixed source/input and encoded-state memory
dominate. Cumulative allocation traffic was not instrumented in this real study.
Medians mix trials; raw paired rows are preserved. Host is not exclusive and timing
differences are not statistical/general guarantees. No query/load speed win is attributed
to this ownership-only change. Loading still uses CSR, with unchanged persisted layout.
All six native snapshots and ordered query files match exactly;12 builders additionally
check native Save/Load ordered result equality. Query return quality is unchanged.
Recall at fixed512 may still miss study quality goals; no threshold/budget adjustment.
100 previously observed queries give exploratory P99, not a robust tail or blind cohort.

## Requirements and limits

This supplies fresh P6/P7/P8 evidence for two real100k datasets and validates a structure
change's resource/correctness effect. It is not P9's native Full comparison or P10's
long-changed-data quality gate. Rounds=0: no CRUD throughput or enduring Update/Remove/Add
claim. No FP32/FP16 fresh comparison, complete package closure or cold-cache claim.
Fresh Release6 and driver fixture passed. ASan/UBSan5,OFF4 and scoped Lite95.41195%
coverage are inherited from unchanged4f73870 code, NOT rerun or new whole Full evidence.
Remaining: interleaved/long true changed-value CRUD and quality, larger query cohorts,
fresh native Full config/SIMD/quality-aligned comparison, final deployment package metrics.

## Reproduction

Production checkout4f73870 is required by run_owned_real_acceptance.py; the helper is
committed later as evidence. Copy the recorded helper into the matching checkout without
changing production, confirm source/library hashes and existing host dataset paths, then
use a fresh results directory. Current helper fixed-output guard rejects overwriting this
study. Preserve original helper before adapting only its fresh destination for another run.
Control header/backend and exact compiler/link/dependency commands are archived; same
shared Release objects are bound by SHA. Libraries reside on RAM for comparison.
run_aligned_comparison.py executes native Save/Load correctness checks and paired SHA/
ordered-neighbor checks before its temporary snapshot directories are removed.
Only newly generated RAM snapshots are removed; original source/data/results retained.
A later collection-only fixture replay failed before benchmarking because the RAM control\nlibrary was no longer present; failure logs are retained. The original successful fixture\nlog is restored from the already-hashed archive, NOT a successful later replay.\nRaw stdout/stderr/commands/latencies/neighbors/GT/manifests are in raw.tar.gz; members and
canonical SHA manifests bind them. verify_owned_real_acceptance.py rederives evidence
without rerunning performance. Paths and query history are recorded, not portable downloads.
"""
def edit(p,text):
    old=p.read_text() if p.exists() else ""
    name=str(p.relative_to(repo))
    patch="".join(difflib.unified_diff(old.splitlines(True),text.splitlines(True),
        fromfile="a/"+name if p.exists() else "/dev/null",tofile="b/"+name))
    subprocess.run(["git","apply","-"],cwd=repo,input=patch,text=True,check=True)
edit(out/"README.md",report)
(out/"comparison.json").write_text(json.dumps(comparisons,indent=2)+"\n")
raw={p.name:p.read_bytes() for p in out.iterdir() if p.is_file() and p.name not in ["raw.tar.gz","members.json","SHA256SUMS"]}
originals={
 "gist100k":Path("/home/ubuntu/project/vsag-lite-datasets/gist/prepared-10k-100k/scale-100000"),
 "cohere100k":Path("/home/ubuntu/project/vsag-lite-cohere-normalized-20261006/prepared/scale-100000")}
for label,root in originals.items():
    for name in ["queries.fvecs","groundtruth.ivecs","manifest.json"]:
        raw["inputs/"+label+"/"+name]=(root/name).read_bytes()
for name in ["run_owned_real_acceptance.py","verify_owned_real_acceptance.py",
             "collect_owned_real_acceptance.py","test_aligned_comparison.py"]:
    raw["helper-"+name]=(repo/"lite/benchmark"/name).read_bytes()
with tarfile.open(out/"raw.tar.gz","w:gz") as tar:
    for name,blob in sorted(raw.items()):
        entry=tarfile.TarInfo(name);entry.size=len(blob);tar.addfile(entry,io.BytesIO(blob))
(out/"members.json").write_text(json.dumps({n:hashlib.sha256(b).hexdigest()
    for n,b in sorted(raw.items())},indent=2,sort_keys=True)+"\n")
canonical=["README.md","identity.json","source-identity.json","rows.json","summary.json",
           "comparison.json","raw.tar.gz","members.json"]
(out/"SHA256SUMS").write_text("".join(hashlib.sha256((out/name).read_bytes()).hexdigest()+
    "  "+name+"\n" for name in sorted(canonical)))
subprocess.run(["python3","lite/benchmark/verify_owned_real_acceptance.py"],cwd=repo,check=True)
print("Archived and verified real100k acceptance slice",flush=True)
