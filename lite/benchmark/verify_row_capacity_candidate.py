#!/usr/bin/env python3
# Copyright 2024-present the vsag project
# SPDX-License-Identifier: Apache-2.0
"""Read-only rederivation of real100k paired ownership evidence."""
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import statistics
import struct
import tarfile

out=Path(__file__).resolve().parents[2]/"lite/benchmark/results/rabitq-row-capacity-20261011"
sha=lambda b:hashlib.sha256(b).hexdigest()
for line in (out/"SHA256SUMS").read_text().splitlines():
    digest,name=line.split("  ",1)
    assert sha((out/name).read_bytes())==digest,name
with tarfile.open(out/"raw.tar.gz") as tar:
    raw={m.name:tar.extractfile(m).read() for m in tar if m.isfile()}
assert {name:sha(blob) for name,blob in sorted(raw.items())}==json.loads((out/"members.json").read_text())
rows=json.loads((out/"rows.json").read_text())
meta=json.loads((out/"source-identity.json").read_text())
assert len(rows)==12 and meta["config"]["rounds"]==0
assert all(r["exit"]==0 for r in json.loads(raw["setup-commands.json"]))
assert sha(raw["candidate-backend.cpp"])==meta["overlay_backend_sha256"]
for name,digest in meta["source_sha256"].items():
    assert sha(raw["source-"+Path(name).name])==digest,name
summary=[]
for dataset in ["cohere100k","gist100k"]:
    info=json.loads(raw[dataset+".dataset.json"])
    for filename in ["queries.fvecs","groundtruth.ivecs"]:
        assert sha(raw["inputs/"+dataset+"/"+filename])==info[filename]["sha256"]
    truth=raw["inputs/"+dataset+"/groundtruth.ivecs"]
    assert len(truth)==100*44
    truth_ids=[]
    for q in range(100):
        k,*ids=struct.unpack_from("<11i",truth,q*44)
        assert k==10 and len(set(ids))==10 and all(0<=x<100000 for x in ids)
        truth_ids.append(set(ids))
    for trial in range(3):
        pair=[r for r in rows if r["dataset"]==dataset and r["trial"]==trial]
        assert len(pair)==2 and {r["name"] for r in pair}=={"control","lite"}
        assert pair[0]["snapshot_sha256"]==pair[1]["snapshot_sha256"]
        buffers=[]
        for r in pair:
            tag=f'{dataset}-rabitq8-{trial}-{r["name"]}'
            lines=raw[tag+".stdout"].decode().splitlines()
            i=next(i for i,x in enumerate(lines) if x.startswith("base_count,query_count,"))
            b=next(csv.DictReader(io.StringIO("\n".join(lines[i:i+2]))))
            for key,val in b.items():
                assert r["build"][key]==val
            assert int(b["base_count"])==100000 and int(b["query_count"])==100
            assert b["storage"]=="rabitq8" and int(b["rounds"])==0 and int(b["max_degree"])==16
            assert int(b["ef_search"])==128 and int(b["query_ef_search"])==512
            neighbors=raw[tag+".queries.csv.neighbors.csv"]
            buffers.append(neighbors)
            ordered=list(csv.DictReader(io.StringIO(neighbors.decode())))
            assert len(ordered)==1000
            hits=0
            for q in range(100):
                part=ordered[q*10:(q+1)*10]
                assert [(int(x["query"]),int(x["rank"])) for x in part]==[(q,k) for k in range(10)]
                ids=[int(x["id"]) for x in part]
                assert len(set(ids))==10 and all(math.isfinite(float.fromhex(x["distance"])) for x in part)
                hits+=len(set(ids)&truth_ids[q])
            assert hits/1000==float(b["recall_at_k"])
            lat=list(csv.DictReader(io.StringIO(raw[tag+".queries.csv.latencies.csv"].decode())))
            values=sorted(float(x["latency_us"]) for x in lat)
            assert len(values)==100
            for fraction,key in [(0.50,"search_p50_us"),(0.99,"search_p99_us")]:
                assert abs(values[math.ceil(fraction*100)-1]-float(b[key]))<0.0000011
            assert int(raw[tag+".peak_kib"])==r["build"]["external_peak_rss_kib"]
            assert len(r["loads"])==3
            for sample,s in enumerate(r["loads"]):
                text=raw[tag+f"-load-{sample}.stdout"].decode().splitlines()
                i=next(i for i,x in enumerate(text) if x.startswith("dim,count,"))
                actual=next(csv.DictReader(io.StringIO("\n".join(text[i:i+2]))))
                assert all(s[k]==v for k,v in actual.items())
                assert int(actual["count"])==100000
                assert int(raw[tag+f"-load-{sample}.peak_kib"])==s["external_peak_rss_kib"]
        assert buffers[0]==buffers[1]
    for name in ["control","lite"]:
        selected=[r for r in rows if r["dataset"]==dataset and r["name"]==name]
        entry=dict(dataset=dataset,storage="rabitq8",name=name)
        for key in ["recall_at_k","build_ms","search_p50_us","search_p99_us","save_ms",
                    "snapshot_bytes","external_peak_rss_kib"]:
            entry[key]=statistics.median(float(r["build"][key]) for r in selected)
        for key in ["load_ms","loaded_rss_kib","process_peak_rss_kib",
                    "before_create_rss_kib","before_load_rss_kib"]:
            entry[key]=statistics.median(float(s[key]) for r in selected for s in r["loads"])
        summary.append(entry)
assert summary==json.loads((out/"summary.json").read_text())
assert "0 tests failed out of 6" in raw["release-tests.log"].decode()
print("Verified12 builders,36 fresh loaders,six identical snapshots/ordered-query pairs,12000 GT intersections,raw quantiles,source hashes and median summaries.")
