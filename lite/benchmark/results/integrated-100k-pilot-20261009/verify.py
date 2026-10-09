# Copyright 2024-present the vsag project
# SPDX-License-Identifier: Apache-2.0
"""Verify loaded-only raw rows and query identity without extracting or rerunning."""
import csv
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import statistics
import tarfile

report=Path(__file__).resolve().parent
for line in (report/"SHA256SUMS").read_text().splitlines():
    digest,name=line.split(maxsplit=1)
    path=(report/name).resolve();assert report in path.parents
    assert hashlib.sha256(path.read_bytes()).hexdigest()==digest,name
identity=json.loads((report/"identity.json").read_text())
rows=json.loads((report/"rows.json").read_text());assert len(rows)==63
summary=json.loads((report/"summary.json").read_text());assert len(summary)==9
with tarfile.open(report/"raw.tar.gz") as archive:
    members={m.name:m for m in archive.getmembers()}
    assert len(members)==len(archive.getmembers())
    assert all(m.isfile() and not PurePosixPath(m.name).is_absolute() and ".." not in PurePosixPath(m.name).parts for m in members.values())
    def read(name):return archive.extractfile(members[name]).read()
    for row in rows:
        stem=row["dataset"]+"-"+row["storage"];name=f"{stem}-r{row['repeat']}"
        raw=list(csv.DictReader(io.StringIO(read(name+".stdout.csv").decode())))
        assert len(raw)==1 and all(row[k]==v for k,v in raw[0].items())
        assert int(row["count"])==100000 and int(row["first_query_count"])==10
        assert row["page_cache_control"]=="warm_uncontrolled"
        assert int(row["snapshot_bytes"])==identity["snapshots"][stem]["bytes"]
        assert 0<int(row["before_load_rss_kib"])<=int(row["loaded_rss_kib"])<=int(row["load_vm_hwm_kib"])
        assert int(row["process_peak_rss_kib"])>=int(row["load_vm_hwm_kib"])
        expected=list(csv.DictReader(io.StringIO(read(stem+".builder.queries.csv.neighbors.csv").decode())))[:10]
        actual=list(csv.DictReader(io.StringIO(read(name+".first.csv").decode())))
        assert [(int(x["rank"]),int(x["id"]),float.fromhex(x["distance"])) for x in actual]==[(int(x["rank"]),int(x["id"]),float.fromhex(x["distance"])) for x in expected]
        command=json.loads(read(name+".command.json"));assert command["exit_code"]==0
        assert command["command"][command["command"].index("-c")+1]=="0"
        assert not read(name+".stderr.txt")
    for entry in summary:
        selected=[r for r in rows if r["dataset"]==entry["dataset"] and r["storage"]==entry["storage"]]
        assert len(selected)==7 and {int(r["repeat"]) for r in selected}==set(range(7))
        for key in ["load_ms","loaded_rss_kib","process_peak_rss_kib","first_query_us","snapshot_bytes","before_load_rss_kib","load_vm_hwm_kib"]:
            assert statistics.median(float(r[key]) for r in selected)==entry[key]
print("PASS:63 fresh loader rows,630 first-query identities,medians/RSS/VmHWM scopes; no rerun or cold-I/O claim")
