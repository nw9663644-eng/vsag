#!/usr/bin/env python3
# Copyright 2024-present the vsag project
# SPDX-License-Identifier: Apache-2.0
"""Collect isolated row-capacity tradeoff; no production adoption."""
import difflib
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile
import time

repo=Path(__file__).resolve().parents[2]
out=repo/"lite/benchmark/results/rabitq-row-capacity-20261011"
while not (out/"source-identity.json").exists() or not (out/"summary.json").exists():time.sleep(2)
rows=json.loads((out/"rows.json").read_text());assert len(rows)==12
meta=json.loads((out/"source-identity.json").read_text())
commands=json.loads((out/"setup-commands.json").read_text());assert all(r["exit"]==0 for r in commands)
source=(repo/"src/lite/rabitq_backend.cpp").read_text()
start=source.index("            // Construction reserves a spare edge per row;")
end=source.index("            rabitq::MutableGraphState state(",start)
assert (source[:start]+source[end:]).encode()==(out/"candidate-backend.cpp").read_bytes()
assert meta["parent"]=="bf50173f02e972a30a0f10a77530f31a356e046a"
data=json.loads((out/"summary.json").read_text())
comparison={}
report="""# Isolated build-row capacity candidate (2026-10-11)

Source evidence: make_rabitq_graph_backend shrinks every build adjacency row before
moving ownership. Existing GraphBackend::TakeBuildLinks already transfers owned rows.
Hypothesis: retaining build capacity avoids many reallocations and could change query
locality, at a permanent capacity cost. This was NOT an established regression cause.

Control bf50173 and candidate share every production header/object and streamed Save.
Only isolated candidate adapter removes the six-line build-row shrink loop.
No production source changes or public option. API/model/degree/ef/edges/order/format/
public NONE/reverse=false unchanged. Candidate backend SHA and exact source diff verified.
Old Lite/control is NOT Full. Current headers retain recently implemented streamed Save.

GIST960/normalized Cohere768 each100k/100 observed queries,k10,degree16/build128/query512,
CPU0/OMP-BLAS-MKL1;three alternating pairs/dataset,12 complete builders/36 fresh loaders.
No concurrent compile/test while timed. Rounds0,NOT changed-value durable CRUD acceptance.
No parameter/seed/budget tuning after results. Inputs hashes and manifests archived.
All six pairs have native snapshot SHA and ordered neighbor equality; each builder also
natively verifies Save/Load100 ordered results. Loaded state drops build slack when CSR
is expanded, so loaded RSS is not built-state retained capacity.

|Dataset|Build old/new ms|Change|Query P50 old/new us|Change|Whole-process peak old/new KiB|Change|
|---|---:|---:|---:|---:|---:|---:|
"""
for label in ["gist100k","cohere100k"]:
    pair={r["name"]:r for r in data if r["dataset"]==label}
    old,new=pair["control"],pair["lite"]
    comp={key:100*(new[key]/old[key]-1) for key in
        ["build_ms","search_p50_us","search_p99_us","save_ms","load_ms","external_peak_rss_kib"]}
    comparison[label]=comp
    report+=f'|{label}|{old["build_ms"]:.3f}/{new["build_ms"]:.3f}|{comp["build_ms"]:+.2f}%|{old["search_p50_us"]:.3f}/{new["search_p50_us"]:.3f}|{comp["search_p50_us"]:+.2f}%|{old["external_peak_rss_kib"]:.0f}/{new["external_peak_rss_kib"]:.0f}|{comp["external_peak_rss_kib"]:+.2f}%|\n'
report+="\n|Dataset|P99 old/new us|Save old/new ms|Warm load old/new ms|Recall both|Snapshot bytes|\n|---|---:|---:|---:|---:|---:|\n"
for label in ["gist100k","cohere100k"]:
    pair={r["name"]:r for r in data if r["dataset"]==label}
    old,new=pair["control"],pair["lite"]
    assert old["recall_at_k"]==new["recall_at_k"] and old["snapshot_bytes"]==new["snapshot_bytes"]
    report+=f'|{label}|{old["search_p99_us"]:.3f}/{new["search_p99_us"]:.3f}|{old["save_ms"]:.3f}/{new["save_ms"]:.3f}|{old["load_ms"]:.3f}/{new["load_ms"]:.3f}|{new["recall_at_k"]:.6f}|{new["snapshot_bytes"]:.0f}|\n'
report+="""
## Decision and boundaries

No production adoption in this commit. One observed small-query cohort and three paired
trials cannot establish allocation/cache causality or general timing gains. The capacity
cost is not fully instrumented in this study. No hardware performance counters collected.
Retain current shrinking default pending a separately justified built-state capacity and
multi-cohort cost/quality study. Do not infer no-shrink is faster from fewer allocations.
The driver records whole-process builder peak including inputs/native reload,not isolated
adjacency memory. Fresh loader RAM cache is uncontrolled;not cold I/O.100 observed queries
give exploratory P99 only;fixed512 Recall still insufficient,unchanged by candidate.
No Full/package/CRUD advantage. This study tests row-capacity hypothesis,not ANN semantics.

Fresh unchanged production Release6 passed before timing. Prior bf50173 ASan/UBSan5,
OFF4 and scopedLite95.456% coverage are inherited,not rerun or candidate SAN evidence.
Candidate adapter compiled and completed native lifecycle/paired checks;no claim of
candidate allocation-fault/sanitizer acceptance. Private experiment does not enable a
public runtime switch or affect PR2904/2926.

## Replay and verification

Helper requires bf50173 business checkout and new output directory;archive its actual
helper before adapting only output destination. Same host cached datasets required.
Exact control/candidate adapters,compiler/link/dependency logs and shared-object hashes
retained. Native snapshots live only in newly generated RAM dirs and driver checks paired
SHA before deleting exact temp targets. No original source/data/results/library cleanup.
Raw queries,GT,manifests,neighbor/latency records,stdout,commands and source identities
archived. Existing subset GT was not recomputed;verifier recomputes raw result intersections
and quantiles only. verify_row_capacity_candidate.py does not rerun performance.
Pending project acceptance:query layout/route optimization,interleaved true changed CRUD,
latest native Full config/SIMD/quality alignment,broader query tails and package closure.
"""
def edit(p,text):
    old=p.read_text() if p.exists() else "";name=str(p.relative_to(repo))
    subprocess.run(["git","apply","-"],cwd=repo,input="".join(difflib.unified_diff(
        old.splitlines(True),text.splitlines(True),fromfile="a/"+name if p.exists() else "/dev/null",
        tofile="b/"+name)),text=True,check=True)
edit(out/"README.md",report)
(out/"comparison.json").write_text(json.dumps(comparison,indent=2)+"\n")
raw={p.name:p.read_bytes() for p in out.iterdir() if p.is_file() and p.name not in
     ["raw.tar.gz","members.json","SHA256SUMS"]}
for label,path in [
 ("gist100k","/home/ubuntu/project/vsag-lite-datasets/gist/prepared-10k-100k/scale-100000"),
 ("cohere100k","/home/ubuntu/project/vsag-lite-cohere-normalized-20261006/prepared/scale-100000")]:
    for name in ["queries.fvecs","groundtruth.ivecs","manifest.json"]:
        raw["inputs/"+label+"/"+name]=(Path(path)/name).read_bytes()
for name in ["run_row_capacity_candidate.py","collect_row_capacity_candidate.py","verify_row_capacity_candidate.py"]:
    raw["helper-"+name]=(repo/"lite/benchmark"/name).read_bytes()
with tarfile.open(out/"raw.tar.gz","w:gz") as tar:
    for name,blob in sorted(raw.items()):
        entry=tarfile.TarInfo(name);entry.size=len(blob);tar.addfile(entry,io.BytesIO(blob))
(out/"members.json").write_text(json.dumps({n:hashlib.sha256(b).hexdigest()
    for n,b in sorted(raw.items())},indent=2,sort_keys=True)+"\n")
names=["README.md","identity.json","source-identity.json","rows.json","summary.json",
       "comparison.json","raw.tar.gz","members.json","setup-commands.json"]
(out/"SHA256SUMS").write_text("".join(hashlib.sha256((out/n).read_bytes()).hexdigest()+
    "  "+n+"\n" for n in sorted(names)))
subprocess.run(["python3","lite/benchmark/verify_row_capacity_candidate.py"],cwd=repo,check=True)
print(json.dumps(comparison,indent=2),flush=True)
