# Copyright 2024-present the vsag project
# SPDX-License-Identifier: Apache-2.0
"""Frozen 10k integrated storage pilot; outputs must be new (use RAM filesystem)."""
import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import shutil
import tarfile


def digest(path):
    result=hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda:stream.read(1048576),b""):result.update(chunk)
    return result.hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("build",type=Path)
    parser.add_argument("output",type=Path)
    parser.add_argument("--archive",type=Path,required=True,help="New durable small-evidence directory")
    parser.add_argument("--sift",type=Path,required=True)
    parser.add_argument("--gist",type=Path,required=True)
    parser.add_argument("--cohere",type=Path,required=True)
    args=parser.parse_args()
    build=args.build.resolve()
    root=Path(__file__).resolve().parents[2]
    binary=build/"lite_graph_crud_quality"
    datasets={name:getattr(args,name).resolve() for name in ["sift","gist","cohere"]}
    if args.archive.exists():parser.error("Archive must be new")
    args.output.mkdir(parents=True,exist_ok=False)
    identity=dict(revision=subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],text=True).strip(),
                  benchmark_source_sha256=digest(root/"lite/benchmark/graph_crud_quality.cpp"),
                  binary_sha256=digest(binary),library_sha256=digest(build/"libvsag-lite.so"),
                  inputs={name:{file:dict(path=str(path/file),sha256=digest(path/file)) for file in ["base.fvecs","queries.fvecs","groundtruth.ivecs"]} for name,path in datasets.items()},
                  plan=dict(cpu=0,degree=16,ef=128,repeats=3,scale=10000,short_crud_cycles=100),
                  query_history="Existing observed dataset queries; not blind validation")
    (args.output/"identity.json").write_text(json.dumps(identity,indent=2)+"\n")
    rows=[]
    def run(name,storage,repeat,rounds):
        stem=f"{name}-{storage}-r{repeat}-rounds{rounds}"
        environment=os.environ.copy()
        environment.update(LD_LIBRARY_PATH=str(build),VSAG_GRAPH_STORAGE=storage,VSAG_GRAPH_DEGREE="16",VSAG_GRAPH_EF="128")
        command=["/usr/bin/time","-v","taskset","-c","0",str(binary),str(datasets[name]),str(args.output/(stem+".snapshot")),str(rounds),"100",str(args.output/(stem+".queries.csv"))]
        result=subprocess.run(command,env=environment,capture_output=True,text=True)
        (args.output/(stem+".stdout.csv")).write_text(result.stdout)
        (args.output/(stem+".stderr.txt")).write_text(result.stderr)
        (args.output/(stem+".command.json")).write_text(json.dumps(dict(command=command,exit_code=result.returncode),indent=2)+"\n")
        if result.returncode:raise RuntimeError(result.stderr)
        row=list(csv.DictReader(io.StringIO(result.stdout)))[0]
        assert row["storage"]==storage and int(row["base_count"])==10000
        row.update(dataset=name,repeat=repeat,snapshot_sha256=digest(args.output/(stem+".snapshot")))
        rows.append(row)
        (args.output/"rows.json").write_text(json.dumps(rows,indent=2)+"\n")
        print(json.dumps({k:row[k] for k in ["dataset","storage","repeat","rounds","recall_at_k","build_ms","search_p50_us"]}),flush=True)
    for name in datasets:
        for repeat in range(3):
            modes=["fp32","fp16","rabitq8"]
            modes=modes[repeat:]+modes[:repeat]
            for storage in modes:run(name,storage,repeat,0)
    for name in datasets:run(name,"rabitq8",0,1)
    args.archive.mkdir(parents=True,exist_ok=False)
    for name in ["identity.json","rows.json"]:
        shutil.copy2(args.output/name,args.archive/name)
    with tarfile.open(args.archive/"raw.tar.gz","w:gz") as archive:
        for path in sorted(args.output.iterdir()):
            if path.is_file() and path.suffix!=".snapshot":archive.add(path,arcname=path.name)
        for name,path in datasets.items():
            for filename in ["queries.fvecs","groundtruth.ivecs"]:
                archive.add(path/filename,arcname=f"inputs/{name}/{filename}")
    (args.archive/"availability.json").write_text(json.dumps(dict(snapshots="RAM-only, ephemeral after session; hashes recorded; not archived",base_vectors="Cached host datasets, hashes and paths recorded",raw_queries_truth="Included in raw.tar.gz",scope="Same-process RAM-filesystem save/load; not cold I/O or isolated RSS"),indent=2)+"\n")
    print("ARCHIVED "+str(args.archive),flush=True)


if __name__=="__main__":
    main()
