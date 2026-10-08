# Copyright 2024-present the vsag project
# SPDX-License-Identifier: Apache-2.0
"""Verify recorded file identities; does not rerun tests or benchmarks."""
import hashlib
import json
from pathlib import Path

report = Path(__file__).resolve().parent
root = report.parents[3]
for line in (report / "SHA256SUMS").read_text().splitlines():
    digest, name = line.split(maxsplit=1)
    path = (report / name).resolve()
    assert report in path.parents
    assert hashlib.sha256(path.read_bytes()).hexdigest() == digest, name
receipt = json.loads((report / "verification.json").read_text())
for name, digest in receipt["sources"].items():
    path = (root / name).resolve()
    assert root in path.parents
    assert hashlib.sha256(path.read_bytes()).hexdigest() == digest, name
coverage = json.loads((report / "coverage.json").read_text())
assert coverage["hit"] == 2149 and coverage["total"] == 2284
assert coverage["percent"] >= 90
assert receipt["scope"] == "Functional integration; no new performance measurements"
print("PASS: report hashes, source identities and recorded Lite coverage; no test/performance rerun")
