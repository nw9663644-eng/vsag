#!/usr/bin/env python3
# Copyright 2024-present the vsag project
# SPDX-License-Identifier: Apache-2.0
"""Offline verification; never rerun timing."""
import csv
import gzip
import hashlib
import io
import json
from pathlib import Path
import statistics
import tarfile

out=Path(__file__).resolve().parents[2]/"lite/benchmark/results/rabitq-stream-save-20261011"
sha=lambda b:hashlib.sha256(b).hexdigest()
for line in (out/"SHA256SUMS").read_text().splitlines():
    digest,name=line.split("  ",1);assert sha((out/name).read_bytes())==digest,name
with tarfile.open(out/"raw.tar.gz") as tar:
    raw={m.name:tar.extractfile(m).read() for m in tar if m.isfile()}
assert {n:sha(b) for n,b in sorted(raw.items())}==json.loads((out/"members.json").read_text())
meta=json.loads((out/"identity.json").read_text())
for n,digest in meta["source_sha256"].items():assert sha(raw["source-"+Path(n).name])==digest,n
assert all(x["exit"]==0 for x in json.loads((out/"commands.json").read_text()))
validation=json.loads((out/"validation-commands.json").read_text())
assert len(validation)==11 and all(x["exit"]==0 for x in validation)
for tag,n in [("release",6),("san",5),("cov",5),("off",4)]:
    assert f"0 tests failed out of {n}" in raw[f"vsag-stream-save-final-{tag}-test-20261011.log"].decode()
rows=json.loads((out/"rows.json").read_text());assert len(rows)==28
summary={}
for label in ["gist100k","cohere100k"]:
    for name in ["queries.fvecs","groundtruth.ivecs"]:
        assert sha(raw["inputs/"+label+"/"+name])==meta["inputs"][label][name]["sha256"]
    for trial in range(7):
        pair=[r for r in rows if r["dataset"]==label and r["trial"]==trial]
        assert len(pair)==2 and {r["variant"] for r in pair}=={"control","candidate"}
        for r in pair:
            tag=f'{label}-t{trial}-{r["variant"]}'
            actual=next(csv.DictReader(io.StringIO(raw[tag+".stdout"].decode())))
            assert r["metrics"]==actual and int(actual["count"])==100000
            assert r["snapshot_sha256"]==meta["snapshots"][label]["sha256"]
            assert int(actual["bytes"])==meta["snapshots"][label]["bytes"]
    summary[label]={}
    for metric in ["save_ms","before_rss_kib","before_hwm_kib","after_rss_kib","after_hwm_kib","bytes"]:
        med={name:statistics.median(float(r["metrics"][metric]) for r in rows
             if r["dataset"]==label and r["variant"]==name) for name in ["control","candidate"]}
        summary[label][metric]=dict(med,change_percent=100*(med["candidate"]/med["control"]-1))
assert summary==json.loads((out/"summary.json").read_text())
lines={}
with tarfile.open(out/"coverage-raw.tar.gz") as tar:
    members=[m for m in tar if m.isfile()];assert len(members)==19
    for m in members:
        for f in json.loads(gzip.decompress(tar.extractfile(m).read()))["files"]:
            for line in f["lines"]:
                k=(f["file"],line["line_number"])
                lines[k]=lines.get(k,False) or line["count"]>0
for scope,expected in json.loads((out/"coverage.json").read_text())["scopes"].items():
    selected=[]
    for (n,_),covered in lines.items():
        lite=("/src/lite/" in n or "/include/vsag/lite/" in n) and not n.endswith("_test.cpp")
        simd="/src/simd/" in n and not n.endswith("_test.cpp")
        if (scope=="lite" and lite) or (scope=="shared_simd" and simd) or (scope=="combined" and (lite or simd)):
            selected.append(covered)
    assert expected==dict(covered=sum(selected),total=len(selected),percent=100*sum(selected)/len(selected))
    assert expected["percent"]>=90
print("Verified28 saves/14 fresh pairs,snapshot hashes,raw medians,sources,11 validation exits and19 fresh coverage unions.")
