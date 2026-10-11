#!/usr/bin/env python3
"""Recompute paired summaries, raw outputs and fresh scoped coverage."""
import csv
import gzip
import hashlib
import io
import json
from pathlib import Path
import statistics
import tarfile

out=Path(__file__).resolve().parent
repo=out.parents[3]
sha=lambda b:hashlib.sha256(b).hexdigest()
for line in (out/"SHA256SUMS").read_text().splitlines():
    digest,name=line.split("  ",1)
    assert sha((out/name).read_bytes())==digest,name
rows=json.loads((out/"rows.json").read_text())
assert len(rows)==12
identity=json.loads((out/"identity.json").read_text())
for name,digest in identity["source_sha256"].items():
    assert sha((repo/name).read_bytes())==digest,name
summary={}
for count in [10000,100000]:
    summary[str(count)]={}
    for trial in range(3):
        pair=[r for r in rows if r["count"]==count and r["trial"]==trial]
        assert len(pair)==2 and {r["variant"] for r in pair}=={"control","candidate"}
        assert pair[0]["snapshot_sha256"]==pair[1]["snapshot_sha256"]
        assert pair[0]["snapshot_bytes"]==pair[1]["snapshot_bytes"]
        assert pair[0]["ordered_query_sha256"]==pair[1]["ordered_query_sha256"]
        for r in pair:
            lines=(out/f'n{count}-t{trial}-{r["variant"]}.stdout').read_text().splitlines()
            parsed=list(csv.DictReader(io.StringIO("\n".join(lines[:2]))))[0]
            actual={k:float(v) if k=="build_ms" else int(v) for k,v in parsed.items()}
            assert actual==r["metrics"]
            assert len(lines[2:])==80
            assert sha("\n".join(lines[2:]).encode())==r["ordered_query_sha256"]
    for metric in ["build_ms","hwm_kib","ordinary_new_requests","ordinary_new_bytes"]:
        med={name:statistics.median([r["metrics"][metric] for r in rows
             if r["count"]==count and r["variant"]==name]) for name in ["control","candidate"]}
        summary[str(count)][metric]=dict(med,change_percent=100*(med["candidate"]/med["control"]-1))
assert summary==json.loads((out/"summary.json").read_text())
for name in ["commands.json","validation-commands.json"]:
    commands=json.loads((out/name).read_text());assert commands and all(x["exit"]==0 for x in commands)
for name,n in [("vsag-owned-topology-release-20261011.log",6),
               ("vsag-owned-topology-santest-20261011.log",5),
               ("coverage-test.log",5),("disabled-test.log",4)]:
    assert f"0 tests failed out of {n}" in (out/name).read_text()
lines={}
with tarfile.open(out/"coverage-raw.tar.gz") as tar:
    members=[m for m in tar if m.isfile()];assert len(members)==19
    for member in members:
        for f in json.loads(gzip.decompress(tar.extractfile(member).read()))["files"]:
            for line in f["lines"]:
                key=(f["file"],line["line_number"])
                lines[key]=lines.get(key,False) or line["count"]>0
for scope,expected in json.loads((out/"coverage.json").read_text())["scopes"].items():
    selected=[]
    for (name,_),covered in lines.items():
        lite=("/src/lite/" in name or "/include/vsag/lite/" in name) and not name.endswith("_test.cpp")
        simd="/src/simd/" in name and not name.endswith("_test.cpp")
        if (scope=="lite" and lite) or (scope=="shared_simd" and simd) or (scope=="combined" and (lite or simd)):
            selected.append(covered)
    assert expected==dict(covered=sum(selected),total=len(selected),percent=100*sum(selected)/len(selected))
    assert expected["percent"]>=90
print("Verified 12 builders, six byte-identical snapshot/query pairs, raw summaries, validation and 19 fresh coverage counters.")
