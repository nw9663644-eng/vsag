# Copyright 2024-present the vsag project
# SPDX-License-Identifier: Apache-2.0
"""Frozen per-call ef grid on existing snapshots; observed-query selection study."""
import argparse
import csv
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
from run_integrated_pilot import digest

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument("build",type=Path)
parser.add_argument("snapshots",type=Path)
parser.add_argument("--identity",type=Path,required=True)
parser.add_argument("--archive",type=Path,required=True)
args=parser.parse_args()
args.archive.mkdir(parents=True,exist_ok=False)
identity=json.loads(args.identity.read_text())
build=args.build.resolve();loader=build/"lite_load_memory"
plan=dict(budgets=[128,512,2048,8192],cpu=0,repeats=1,
          floors=dict(sift=0.95,gist=0.90,cohere=0.95),
          query_history="Observed historical100-query cohort; not blind final acceptance",identity=identity,
          loader_sha256=digest(loader),library_sha256=digest(build/"libvsag-lite.so"))
(args.archive/"plan.json").write_text(json.dumps(plan,indent=2)+"\n")
rows=[]
for dataset,dim in [("sift",128),("gist",960),("cohere",768)]:
    query=Path(identity["inputs"][dataset]["queries.fvecs"]["path"])
    truth=Path(identity["inputs"][dataset]["groundtruth.ivecs"]["path"])
    for storage in ["fp32","fp16","rabitq8"]:
        stem=dataset+"-"+storage;snapshot=args.snapshots/(stem+".snapshot")
        assert digest(snapshot)==identity["snapshots"][stem]["sha256"]
        for budget in plan["budgets"]:
            name=f"{stem}-ef{budget}"
            env=os.environ.copy();env.update(LD_LIBRARY_PATH=str(build),VSAG_LOAD_QUERY=str(query),VSAG_LOAD_QUALITY_TRUTH=str(truth),VSAG_LOAD_QUALITY_EF=str(budget))
            command=["taskset","-c","0",str(loader),str(snapshot),str(dim),"100000"]
            result=subprocess.run(command,env=env,capture_output=True,text=True)
            (args.archive/(name+".stdout.csv")).write_text(result.stdout)
            (args.archive/(name+".stderr.txt")).write_text(result.stderr)
            assert result.returncode==0 and not result.stderr,result.stderr
            row=list(csv.DictReader(io.StringIO(result.stdout)))[0]
            assert int(row["quality_queries"])==100 and int(row["quality_ef"])==budget
            row.update(dataset=dataset,storage=storage);rows.append(row)
            (args.archive/"rows.json").write_text(json.dumps(rows,indent=2)+"\n")
            print(json.dumps({key:row[key] for key in ["dataset","storage","quality_ef","recall_at_k","search_p50_us"]}),flush=True)
print("DONE36 budget cells",flush=True)
