# Copyright 2024-present the vsag project
# SPDX-License-Identifier: Apache-2.0
"""Check opt-in benchmark storage and environment validation on an exact clique."""
import csv
import io
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile

probe=Path(sys.argv[1]).resolve()
with tempfile.TemporaryDirectory() as temporary:
    directory=Path(temporary)
    records=b"".join(struct.pack("<i17f",17,*[float(i==j) for j in range(17)]) for i in range(8))
    (directory/"base.fvecs").write_bytes(records)
    (directory/"queries.fvecs").write_bytes(records)
    (directory/"groundtruth.ivecs").write_bytes(b"".join(struct.pack("<ii",1,i) for i in range(8)))
    for storage in ["fp32","fp16","rabitq8"]:
        environment=os.environ.copy()
        environment["VSAG_GRAPH_STORAGE"]=storage
        result=subprocess.run([str(probe),str(directory),str(directory/(storage+".snap")),"1","2"],env=environment,capture_output=True,text=True)
        assert result.returncode==0,result.stderr
        row=list(csv.DictReader(io.StringIO(result.stdout)))[0]
        assert row["storage"]==storage and int(row["base_count"])==8
        assert float(row["recall_at_k"])==1
    for name,value in [("VSAG_GRAPH_STORAGE","invalid"),("VSAG_GRAPH_EF","0"),("VSAG_GRAPH_EF","12x")]:
        environment=os.environ.copy()
        environment[name]=value
        output=directory/"bad.snap"
        result=subprocess.run([str(probe),str(directory),str(output),"0","1"],env=environment,capture_output=True,text=True)
        assert result.returncode!=0 and not output.exists()
print("PASS: FP32/FP16/RaBitQ CRUD/roundtrip and invalid environment checks")
