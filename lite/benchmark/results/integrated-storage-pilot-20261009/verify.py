# Copyright 2024-present the vsag project
# SPDX-License-Identifier: Apache-2.0
"""Audit recorded pilot rows and truth intersections; never extract or rerun."""
import csv
import hashlib
import io
import json
import math
from pathlib import Path, PurePosixPath
import re
import statistics
import struct
import tarfile

report=Path(__file__).resolve().parent
for line in (report/"SHA256SUMS").read_text().splitlines():
    digest,name=line.split(maxsplit=1)
    path=(report/name).resolve()
    assert report in path.parents
    assert hashlib.sha256(path.read_bytes()).hexdigest()==digest,name
identity=json.loads((report/"identity.json").read_text())
rows=json.loads((report/"rows.json").read_text())
summary=json.loads((report/"summary.json").read_text())
assert len(rows)==30
with tarfile.open(report/"raw.tar.gz") as archive:
    members={m.name:m for m in archive.getmembers()}
    assert len(members)==len(archive.getmembers())
    assert all(m.isfile() and not PurePosixPath(m.name).is_absolute() and ".." not in PurePosixPath(m.name).parts for m in members.values())
    def read(name):return archive.extractfile(members[name]).read()
    truths={}
    for dataset,dim in [("sift",128),("gist",960),("cohere",768)]:
        truth=read(f"inputs/{dataset}/groundtruth.ivecs")
        query=read(f"inputs/{dataset}/queries.fvecs")
        assert hashlib.sha256(truth).hexdigest()==identity["inputs"][dataset]["groundtruth.ivecs"]["sha256"]
        assert hashlib.sha256(query).hexdigest()==identity["inputs"][dataset]["queries.fvecs"]["sha256"]
        assert len(truth)==100*44 and len(query)==100*(4+4*dim)
        selected=[]
        for i in range(100):
            value=struct.unpack_from("<11i",truth,i*44)
            assert value[0]==10 and len(set(value[1:]))==10
            assert all(0<=x<10000 for x in value[1:])
            selected.append(set(value[1:]))
            assert struct.unpack_from("<i",query,i*(4+4*dim))[0]==dim
        truths[dataset]=selected
    peaks={}
    for row in rows:
        stem=f"{row['dataset']}-{row['storage']}-r{row['repeat']}-rounds{row['rounds']}"
        raw=list(csv.DictReader(io.StringIO(read(stem+".stdout.csv").decode())))
        assert len(raw)==1 and all(row[key]==value for key,value in raw[0].items())
        assert int(row["base_count"])==10000 and int(row["query_count"])==100 and int(row["k"])==10
        assert int(row["max_degree"])==16 and int(row["ef_search"])==128
        command=json.loads(read(stem+".command.json"))
        assert command["exit_code"]==0 and "taskset" in command["command"]
        neighbors=list(csv.DictReader(io.StringIO(read(stem+".queries.csv.neighbors.csv").decode())))
        hits=list(csv.DictReader(io.StringIO(read(stem+".queries.csv").decode())))
        assert len(neighbors)==1000 and len(hits)==100
        total=0
        for query in range(100):
            selected=neighbors[query*10:(query+1)*10]
            assert [int(x["query"]) for x in selected]==[query]*10
            assert [int(x["rank"]) for x in selected]==list(range(10))
            ids=[int(x["id"]) for x in selected]
            distances=[float.fromhex(x["distance"]) for x in selected]
            assert len(set(ids))==10 and all(0<=x<10000 for x in ids)
            assert all(math.isfinite(x) for x in distances)
            assert list(zip(distances,ids))==sorted(zip(distances,ids))
            count=len(set(ids)&truths[row["dataset"]][query])
            assert int(hits[query]["query"])==query and int(hits[query]["hits"])==count
            total+=count
        assert abs(total/1000-float(row["recall_at_k"]))<1e-9
        stderr=read(stem+".stderr.txt").decode()
        match=re.search(r"Maximum resident set size \(kbytes\):\s*(\d+)",stderr)
        assert match
        peaks[stem]=int(match[1])
    for entry in summary["initial_medians"]:
        group=[r for r in rows if r["dataset"]==entry["dataset"] and r["storage"]==entry["storage"] and int(r["rounds"])==0]
        assert len(group)==3 and {int(r["repeat"]) for r in group}=={0,1,2}
        for key in ["recall_at_k","build_ms","search_p50_us","search_p99_us","save_ms","load_ms","snapshot_bytes"]:
            assert statistics.median(float(r[key]) for r in group)==entry[key]
        peak=statistics.median(peaks[f"{r['dataset']}-{r['storage']}-r{r['repeat']}-rounds0"] for r in group)
        assert peak==entry["whole_process_peak_rss_kib"]
    assert len(summary["short_crud"])==3
print("PASS:30 runs,30000 returned rows, truth intersections/options/medians/peak scope; no new benchmark or exhaustive-GT audit")
