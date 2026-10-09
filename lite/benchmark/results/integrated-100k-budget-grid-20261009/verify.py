# Copyright 2024-present the vsag project
# SPDX-License-Identifier: Apache-2.0
"""Verify recorded CSV and frozen grid selection; not a raw-query truth audit."""
import csv
import hashlib
import io
import json
from pathlib import Path

report=Path(__file__).resolve().parent
for line in (report/"SHA256SUMS").read_text().splitlines():
    digest,name=line.split(maxsplit=1);path=(report/name).resolve()
    assert report in path.parents and hashlib.sha256(path.read_bytes()).hexdigest()==digest
plan=json.loads((report/"plan.json").read_text());rows=json.loads((report/"rows.json").read_text())
assert plan["budgets"]==[128,512,2048,8192] and len(rows)==36
selected=[]
for dataset in ["sift","gist","cohere"]:
    for storage in ["fp32","fp16","rabitq8"]:
        group=[r for r in rows if r["dataset"]==dataset and r["storage"]==storage]
        assert {int(r["quality_ef"]) for r in group}==set(plan["budgets"])
        for row in group:
            name=f"{dataset}-{storage}-ef{row['quality_ef']}"
            raw=list(csv.DictReader(io.StringIO((report/(name+".stdout.csv")).read_text())))
            assert len(raw)==1 and all(row[k]==v for k,v in raw[0].items())
            assert int(row["quality_queries"])==100 and int(row["count"])==100000
            assert not (report/(name+".stderr.txt")).read_bytes()
        passed=[r for r in group if float(r["recall_at_k"])>=plan["floors"][dataset]]
        assert passed
        selected.append(min(passed,key=lambda r:int(r["quality_ef"])))
assert selected==json.loads((report/"selected.json").read_text())
print("PASS:36 CSV cells and frozen floor selection; no independent query-truth rerun")
