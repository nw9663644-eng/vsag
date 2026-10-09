# Copyright 2024-present the vsag project
# SPDX-License-Identifier: Apache-2.0
"""Generate RAM snapshots, measure fresh loaded-only processes and archive before logout."""
import argparse
import csv
import io
import json
import os
from pathlib import Path
import shutil
import statistics
import subprocess
import tarfile
from run_integrated_pilot import digest


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("build",type=Path)
    parser.add_argument("output",type=Path)
    parser.add_argument("--archive",type=Path,required=True)
    parser.add_argument("--inputs",type=Path,required=True,help="Prior pilot identity.json")
    args=parser.parse_args()
    if args.archive.exists():parser.error("Archive must be new")
    args.output.mkdir(parents=True,exist_ok=False)
    root=Path(__file__).resolve().parents[2]
    build=args.build.resolve();builder=build/"lite_graph_crud_quality";loader=build/"lite_load_memory"
    prior=json.loads(args.inputs.read_text())
    identity=dict(revision=subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],text=True).strip(),
                  builder_sha256=digest(builder),loader_sha256=digest(loader),library_sha256=digest(build/"libvsag-lite.so"),
                  loader_source_sha256=digest(root/"lite/benchmark/load_memory.cpp"),inputs=prior["inputs"],
                  scope="10k loaded-only RSS before query; fresh processes; RAM page cache uncontrolled",
                  plan=dict(cpu=0,degree=16,ef=128,repeats=7,count=10000),snapshots={})
    for dataset,files in prior["inputs"].items():
        for filename,record in files.items():
            assert digest(Path(record["path"]))==record["sha256"], (dataset,filename)
    environment=os.environ.copy();environment["LD_LIBRARY_PATH"]=str(build)
    rows=[]
    for dataset,dim in [("sift",128),("gist",960),("cohere",768)]:
        directory=Path(prior["inputs"][dataset]["base.fvecs"]["path"]).parent
        for storage in ["fp32","fp16","rabitq8"]:
            stem=dataset+"-"+storage
            env=environment.copy();env.update(VSAG_GRAPH_STORAGE=storage,VSAG_GRAPH_DEGREE="16",VSAG_GRAPH_EF="128")
            command=["taskset","-c","0",str(builder),str(directory),str(args.output/(stem+".snapshot")),"0","1",str(args.output/(stem+".builder.queries.csv"))]
            result=subprocess.run(command,env=env,capture_output=True,text=True)
            (args.output/(stem+".builder.stdout.csv")).write_text(result.stdout)
            (args.output/(stem+".builder.stderr.txt")).write_text(result.stderr)
            assert result.returncode==0,result.stderr
            identity["snapshots"][stem]=dict(sha256=digest(args.output/(stem+".snapshot")),bytes=(args.output/(stem+".snapshot")).stat().st_size)
        for repeat in range(7):
            modes=["fp32","fp16","rabitq8"];offset=repeat%3;modes=modes[offset:]+modes[:offset]
            for storage in modes:
                stem=dataset+"-"+storage;name=f"{stem}-r{repeat}"
                env=environment.copy();env.update(VSAG_LOAD_QUERY=str(directory/"queries.fvecs"),VSAG_LOAD_QUERY_RESULTS=str(args.output/(name+".first.csv")))
                command=["taskset","-c","0",str(loader),str(args.output/(stem+".snapshot")),str(dim),"10000"]
                result=subprocess.run(command,env=env,capture_output=True,text=True)
                (args.output/(name+".stdout.csv")).write_text(result.stdout)
                (args.output/(name+".stderr.txt")).write_text(result.stderr)
                (args.output/(name+".command.json")).write_text(json.dumps(dict(command=command,exit_code=result.returncode),indent=2)+"\n")
                assert result.returncode==0 and not result.stderr,result.stderr
                row=list(csv.DictReader(io.StringIO(result.stdout)))[0]
                assert int(row["count"])==10000 and int(row["dim"])==dim
                assert int(row["first_query_count"])==10
                expected=list(csv.DictReader(io.StringIO((args.output/(stem+".builder.queries.csv.neighbors.csv")).read_text())))[:10]
                actual=list(csv.DictReader(io.StringIO((args.output/(name+".first.csv")).read_text())))
                assert [(int(x["id"]),float.fromhex(x["distance"])) for x in actual]==[(int(x["id"]),float.fromhex(x["distance"])) for x in expected]
                row.update(dataset=dataset,storage=storage,repeat=repeat);rows.append(row)
        print("DONE "+dataset,flush=True)
    summary=[]
    for dataset in ["sift","gist","cohere"]:
        for storage in ["fp32","fp16","rabitq8"]:
            group=[r for r in rows if r["dataset"]==dataset and r["storage"]==storage]
            entry=dict(dataset=dataset,storage=storage,repeats=7)
            for key in ["load_ms","loaded_rss_kib","process_peak_rss_kib","first_query_us","snapshot_bytes","before_load_rss_kib","load_vm_hwm_kib"]:
                entry[key]=statistics.median(float(r[key]) for r in group)
            summary.append(entry);print(json.dumps(entry),flush=True)
    args.archive.mkdir(parents=True,exist_ok=False)
    for name,value in [("identity.json",identity),("rows.json",rows),("summary.json",summary)]:
        (args.archive/name).write_text(json.dumps(value,indent=2)+"\n")
    with tarfile.open(args.archive/"raw.tar.gz","w:gz") as archive:
        for path in sorted(args.output.iterdir()):
            if path.is_file() and path.suffix!=".snapshot":archive.add(path,arcname=path.name)
    print("ARCHIVED "+str(args.archive),flush=True)


if __name__=="__main__":
    main()
