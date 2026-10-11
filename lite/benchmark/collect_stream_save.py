#!/usr/bin/env python3
# Copyright 2024-present the vsag project
# SPDX-License-Identifier: Apache-2.0
"""Archive completed Save measurements and fresh scoped validation."""
import difflib
import gzip
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile
import time

repo=Path(__file__).resolve().parents[2]
out=repo/"lite/benchmark/results/rabitq-stream-save-20261011"
while not (out/"summary.json").exists():time.sleep(2)
assert len(json.loads((out/"rows.json").read_text()))==28
base=Path("/home/ubuntu/project/vsag-opt-coverage-20261009")
counters=list(base.rglob("*.gcda"));assert len(counters)==19
ram=Path(tempfile.mkdtemp(prefix="vsag-stream-save-gcov-",dir="/dev/shm"))
with (out/"gcov.log").open("w") as log:
    for p in counters:
        subprocess.run(["gcov","--json-format",str(p)],cwd=ram,stdout=log,stderr=log,check=True)
files=list(ram.glob("*.gcov.json.gz"));assert len(files)==19
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
    note="Scoped Lite/shared SIMD, not whole Full VSAG"),indent=2)+"\n")
with tarfile.open(out/"coverage-raw.tar.gz","w:gz") as tar:
    for p in files:tar.add(p,arcname=p.name)
commands=json.loads(Path("/home/ubuntu/project/vsag-stream-save-validation-20261011.json").read_text())
assert len(commands)==11 and all(r["exit"]==0 for r in commands)
(out/"validation-commands.json").write_text(json.dumps(commands,indent=2)+"\n")
summary=json.loads((out/"summary.json").read_text())
report="""# RaBitQ streamed adjacency Save (2026-10-11)

Source: save_mutable_snapshot called GetGraph/compact_graph, materializing all offsets
and edges before writing. Existing native src/storage/stream_writer.h::WriteVector and
Lite write_integer_array use contiguous block I/O. Stream the same CSR wire order from
read-only row adjacency in an at-most8192uint64/64KiB buffer, reused for offsets and edges.
Check sum/count overflow and retain scalar little-endian fallback and stream errors.
No public API/model/encoding/topology/degree/budget/default/format change.
GetAdjacency is internal read-only; original GetGraph remains for callers/tests/load.
Validate remains before writing. Save can still allocate validation scratch in cached/
reverse modes;64KiB refers only to this adjacency staging buffer, not all Save memory.

## Frozen fresh loaded-state Save comparison

Parentb09631c versus candidate, both public NONE/reverse=false. Real GIST960 and
normalized Cohere768,100k. Prepare one unchanged snapshot/dataset using degree16/
build128/query512; its SHA matches all six previous real100k snapshots/dataset.
CPU0 and OMP/BLAS/MKL1;seven alternating paired fresh processes/dataset,28 saves.
No tests/builds overlapped timed runs. Probe loads input before checkpoint, then times
ofstream open + Index::Save + close. Native roundtrip output SHA must equal input.
RAM/pagecache uncontrolled, not cold I/O or fdatasync durability.
VmRSS/VmHWM checkpoints bracket Save; loader allocation/launcher can hide Save-only
peaks. This is NOT the preceding build-then-Save timing, whose allocation layout differs.

|Dataset|Save old/new median ms|Change|Before HWM old/new KiB|After HWM old/new KiB|
|---|---:|---:|---:|---:|
"""
for label,s in summary.items():
    t=s["save_ms"];b=s["before_hwm_kib"];h=s["after_hwm_kib"]
    report+=f'|{label}|{t["control"]:.3f}/{t["candidate"]:.3f}|{t["change_percent"]:+.2f}%|{b["control"]:.0f}/{b["candidate"]:.0f}|{h["control"]:.0f}/{h["candidate"]:.0f}|\n'
report+="""
28 output snapshot hashes equal input. File sizes and semantics remain unchanged.
This measures loaded-state Save only, NOT query/CRUD/build/Full advantage or resolution
of prior query P50 regressions. Two prepare builders natively verify100 ordered queries
after Save/Load, but not a new query benchmark/quality claim. No retuning after results.
The full graph transient is removed by construction; checkpoint differences are not
a universal peak-saving guarantee. See raw rows for per-pair variation and RSS.
Previous build-then-Save regression is not automatically proven resolved by this protocol.

## Verification and limits

Release6,ASan/UBSan5,freshCov5,RaBitQ-OFF4,format15/tidy15 and probe-tidy passed.
Initial uppercase local constant failed identifier-naming lint, corrected before timing;
original failure log retained. No product test failure.
CSR bytes match for0/1/8191/8192/8193/9000 rows,variable degree including empty rows,
bulk/scalar endian and limited-output short writes. Existing lifecycle/allocation faults
and snapshot roundtrips retained. Coverage is scoped Lite/shared SIMD, not whole Full.
Original19fresh counters are archived; verification recomputes their union.

run_stream_save.py uses recorded host paths, matching Release objects and new output.
Replay at parent business checkout plus archived candidate source/patch, rebuilding
Release first; restore measured candidate headers and verify their SHA before running.
Current fixed output guard prevents overwriting evidence; adapt only fresh destination.
Exact old headers/backend, compiler/link/dependency commands and object hashes retained.
New RAM snapshots are SHA-verified then exact-path unlinked; no old source/data/results
or libraries removed. Base data stays cached; snapshot bodies not archived but SHA/size
and input identities retained. Small stdout/raw scripts/source/query/GT are archived.
Long changed-value/interleaved CRUD,latest aligned native Full,larger query cohorts and
deployment package final acceptance remain open. No complete-project claim.
"""
def edit(p,text):
    name=str(p.relative_to(repo));old=p.read_text() if p.exists() else ""
    subprocess.run(["git","apply","-"],cwd=repo,input="".join(difflib.unified_diff(
        old.splitlines(True),text.splitlines(True),fromfile="a/"+name if p.exists() else "/dev/null",
        tofile="b/"+name)),text=True,check=True)
edit(out/"README.md",report)
raw={p.name:p.read_bytes() for p in out.iterdir() if p.is_file() and p.name not in
     ["raw.tar.gz","members.json","SHA256SUMS"]}
for p in Path("/home/ubuntu/project").glob("vsag-stream-save-*20261011.log"):
    raw[p.name]=p.read_bytes()
for label,entries in json.loads((out/"identity.json").read_text())["inputs"].items():
    for name in ["queries.fvecs","groundtruth.ivecs"]:
        raw["inputs/"+label+"/"+name]=Path(entries[name]["path"]).read_bytes()
for name in ["collect_stream_save.py","run_stream_save.py","verify_stream_save.py"]:
    raw["helper-"+name]=(repo/"lite/benchmark"/name).read_bytes()
with tarfile.open(out/"raw.tar.gz","w:gz") as tar:
    for name,blob in sorted(raw.items()):
        entry=tarfile.TarInfo(name);entry.size=len(blob);tar.addfile(entry,io.BytesIO(blob))
(out/"members.json").write_text(json.dumps({n:hashlib.sha256(b).hexdigest()
    for n,b in sorted(raw.items())},indent=2,sort_keys=True)+"\n")
names=["README.md","identity.json","commands.json","rows.json","summary.json","coverage.json",
       "coverage-raw.tar.gz","validation-commands.json","raw.tar.gz","members.json"]
(out/"SHA256SUMS").write_text("".join(hashlib.sha256((out/n).read_bytes()).hexdigest()+
    "  "+n+"\n" for n in sorted(names)))
subprocess.run(["python3","lite/benchmark/verify_stream_save.py"],cwd=repo,check=True)
print(json.dumps(scopes,indent=2),flush=True)
