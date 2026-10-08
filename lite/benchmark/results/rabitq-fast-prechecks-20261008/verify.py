# Copyright 2024-present the vsag project
# SPDX-License-Identifier: Apache-2.0
"""Verify recorded identities and recompute medians; no benchmark rerun."""
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
measurement=json.loads((report/"measurement.json").read_text())
assert hashlib.sha256((report/"probe-source.cpp.txt").read_bytes()).hexdigest()==measurement["probe_source_sha256"]
medians={}
for mode in ["baseline","candidate"]:
    rows=[r for r in measurement["runs"] if r["mode"]==mode]
    assert len(rows)==7 and {r["repeat"] for r in rows}==set(range(7))
    assert all(r["count"]==2000 and r["dim"]==128 and r["updates"]==100 and r["live_count"]==2000 for r in rows)
    if mode=="candidate":assert all(r["snapshot_unchanged"] for r in rows)
    medians[mode]=statistics.median(r["cpu_ms"] for r in rows)
assert medians==measurement["median_cpu_ms"]
change=100*(medians["candidate"]/medians["baseline"]-1)
assert change==measurement["change_percent"]
coverage=json.loads((report/"coverage.json").read_text())
assert coverage["hit"]==2171 and coverage["total"]==2310 and coverage["percent"]>=90
root=report.parents[3]
receipt=json.loads((report/"sources.json").read_text())
current_matches=all((root/name).is_file() and hashlib.sha256((root/name).read_bytes()).hexdigest()==digest for name,digest in receipt["sources"].items())
print(json.dumps(dict(median_cpu_ms=medians,change_percent=change,current_source_matches=current_matches,scope="Synthetic identical Update only; artifact verification")))
