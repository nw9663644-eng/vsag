# Copyright 2024-present the vsag project
# SPDX-License-Identifier: Apache-2.0
"""Recompute bounded study evidence; no test or performance rerun."""
import gzip
import hashlib
import json
from pathlib import Path
import statistics

report=Path(__file__).resolve().parent
for line in (report/"SHA256SUMS").read_text().splitlines():
    digest,name=line.split(maxsplit=1)
    path=(report/name).resolve()
    assert report in path.parents
    assert hashlib.sha256(path.read_bytes()).hexdigest()==digest,name
m=json.loads((report/"measurement.json").read_text())
assert hashlib.sha256((report/"probe-source.cpp.txt").read_bytes()).hexdigest()==m["probe_source_sha256"]
assert m["scope"]=="Synthetic physical Remove; not general CRUD acceptance"
medians={}
for mode in ["baseline","candidate"]:
    rows=[r for r in m["runs"] if r["mode"]==mode]
    assert len(rows)==7 and {r["repeat"] for r in rows}==set(range(7))
    assert all(r["removes"]==100 and r["count"]==2000 and r["dim"]==128 and r["live_count"]==1900 for r in rows)
    medians[mode]=statistics.median(r["cpu_ms"] for r in rows)
assert medians==m["median_cpu_ms"]
states=json.loads(gzip.decompress((report/"snapshots.json.gz").read_bytes()))
assert len(states)==14
first=bytes.fromhex(states[0]["hex"])
for state in states:
    raw=bytes.fromhex(state["hex"])
    assert raw==first
    row=next(r for r in m["runs"] if r["mode"]==state["mode"] and r["repeat"]==state["repeat"])
    assert hashlib.sha256(raw).hexdigest()==row["final_snapshot_sha256"]
c=json.loads((report/"coverage.json").read_text())
assert c["percent"]>=90
receipt=json.loads((report/"sources.json").read_text())
root=report.parents[3]
current=all((root/p).is_file() and hashlib.sha256((root/p).read_bytes()).hexdigest()==digest for p,digest in receipt["sources"].items())
print(json.dumps(dict(median_cpu_ms=medians,final_states_equal=True,current_source_matches=current,scope="Bounded physical Remove study only")))
