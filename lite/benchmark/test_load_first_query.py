# Copyright 2024-present the vsag project
# SPDX-License-Identifier: Apache-2.0
"""Validate optional loaded-only query without altering default loader schema."""
import csv
import io
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile

builder,loader=[str(Path(p).resolve()) for p in sys.argv[1:]]
with tempfile.TemporaryDirectory() as temporary:
    directory=Path(temporary)
    records=b"".join(struct.pack("<i17f",17,*[float(i==j) for j in range(17)]) for i in range(8))
    (directory/"base.fvecs").write_bytes(records)
    (directory/"queries.fvecs").write_bytes(records)
    (directory/"groundtruth.ivecs").write_bytes(b"".join(struct.pack("<ii",1,i) for i in range(8)))
    for storage in ["fp32","fp16","rabitq8"]:
        snapshot=directory/(storage+".snapshot")
        environment=os.environ.copy();environment["VSAG_GRAPH_STORAGE"]=storage
        result=subprocess.run([builder,str(directory),str(snapshot),"0","1"],env=environment,capture_output=True,text=True)
        assert result.returncode==0,result.stderr
        plain=subprocess.run([loader,str(snapshot),"17","8"],capture_output=True,text=True)
        assert plain.returncode==0,plain.stderr
        row=list(csv.DictReader(io.StringIO(plain.stdout)))[0]
        assert "first_query_us" not in row
        output=directory/(storage+".first.csv")
        environment.update(VSAG_LOAD_QUERY=str(directory/"queries.fvecs"),VSAG_LOAD_QUERY_RESULTS=str(output))
        result=subprocess.run([loader,str(snapshot),"17","8"],env=environment,capture_output=True,text=True)
        assert result.returncode==0,result.stderr
        row=list(csv.DictReader(io.StringIO(result.stdout)))[0]
        assert int(row["first_query_count"])==8 and float(row["first_query_us"])>=0
        values=list(csv.DictReader(io.StringIO(output.read_text())))
        assert [int(v["rank"]) for v in values]==list(range(8))
        assert len({int(v["id"]) for v in values})==8 and int(values[0]["id"])==0
        assert subprocess.run([loader,str(snapshot),"17","8"],env=environment,capture_output=True).returncode!=0
        environment.pop("VSAG_LOAD_QUERY_RESULTS")
        environment.update(VSAG_LOAD_QUALITY_TRUTH=str(directory/"groundtruth.ivecs"),VSAG_LOAD_QUALITY_EF="2")
        quality=subprocess.run([loader,str(snapshot),"17","8"],env=environment,capture_output=True,text=True)
        assert quality.returncode==0,quality.stderr
        row=list(csv.DictReader(io.StringIO(quality.stdout)))[0]
        assert int(row["quality_queries"])==8 and int(row["quality_ef"])==2
        assert float(row["recall_at_k"])==1
        environment.pop("VSAG_LOAD_QUALITY_TRUTH")
        environment.pop("VSAG_LOAD_QUALITY_EF")
        bad=directory/"bad.fvecs";bad.write_bytes(struct.pack("<i",16))
        environment["VSAG_LOAD_QUERY"]=str(bad);environment.pop("VSAG_LOAD_QUERY_RESULTS",None)
        assert subprocess.run([loader,str(snapshot),"17","8"],env=environment,capture_output=True).returncode!=0
print("PASS: all storage first-query/rank checks, legacy schema, invalid query and overwrite rejection")
