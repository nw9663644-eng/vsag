# Copyright 2024-present the vsag project
# SPDX-License-Identifier: Apache-2.0
"""Collect fresh validation evidence without rerunning timed loaders."""
import difflib
import gzip
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile

repo = Path.cwd()
out = repo / "lite/benchmark/results/rabitq-safe-link-20261011"
logs = Path("/home/ubuntu/project/vsag-safe-link-20261011")
def sha(blob):
    return hashlib.sha256(blob).hexdigest()
def edit(path, text):
    old = path.read_text() if path.exists() else ""
    if old == text:
        return
    name = str(path.relative_to(repo))
    patch = "".join(difflib.unified_diff(old.splitlines(True), text.splitlines(True),
        fromfile="a/" + name if path.exists() else "/dev/null", tofile="b/" + name))
    subprocess.run(["git", "apply", "-"], input=patch, text=True, check=True)

base = Path("/home/ubuntu/project/vsag-opt-coverage-20261009")
counters = list(base.rglob("*.gcda"))
assert len(counters) == 19
ram = Path(tempfile.mkdtemp(prefix="vsag-load-id-map-gcov-", dir="/dev/shm"))
with (logs / "gcov.log").open("w") as log:
    for path in counters:
        subprocess.run(["gcov", "--json-format", str(path)], cwd=ram,
                       stdout=log, stderr=log, check=True)
files = sorted(ram.glob("*.gcov.json.gz"))
assert len(files) == 19
lines = {}
for path in files:
    for file in json.loads(gzip.decompress(path.read_bytes()))["files"]:
        for line in file["lines"]:
            key = (file["file"], line["line_number"])
            lines[key] = lines.get(key, False) or line["count"] > 0
scopes = {}
for scope in ("lite", "shared_simd", "combined"):
    selected = []
    for (name, _), covered in lines.items():
        lite = ("/src/lite/" in name or "/include/vsag/lite/" in name) and not name.endswith("_test.cpp")
        simd = "/src/simd/" in name and not name.endswith("_test.cpp")
        if (scope == "lite" and lite) or (scope == "shared_simd" and simd) or (
                scope == "combined" and (lite or simd)):
            selected.append(covered)
    scopes[scope] = {"covered": sum(selected), "total": len(selected),
                     "percent": sum(selected) * 100 / len(selected)}
    assert scopes[scope]["percent"] >= 90
(out / "coverage.json").write_text(json.dumps({"fresh_counters": True, "scopes": scopes,
    "scope_note": "Scoped Lite production/public headers and shared SIMD; not whole Full"}, indent=2) + "\n")
with tarfile.open(out / "coverage-raw.tar.gz", "w:gz") as tar:
    for path in files:
        tar.add(path, arcname=path.name)
identity = json.loads((out / "identity.json").read_text())
final_sources = {n: sha((repo / n).read_bytes()) for n in (
    "src/lite/rabitq_graph_state.h", "src/lite/rabitq_backend_test.cpp",
    "src/lite/graph_allocation_test.cpp", "lite/benchmark/graph_crud_quality.cpp")}
assert final_sources["src/lite/rabitq_graph_state.h"] == identity["source_sha256"]["src/lite/rabitq_graph_state.h"]
identity["default_library_sha256"] = sha((repo / "build-lite-fp16-simd-release/libvsag-lite.so").read_bytes())
(out / "identity.json").write_text(json.dumps(identity, indent=2) + "\n")
validation = {"tests": {"release": 6, "asan_ubsan": 5, "fresh_coverage": 5, "disabled": 4},
    "production_change": True, "public_defaults_changed": False, "snapshot_format_changed": False,
    "final_source_sha256": final_sources, "format_version": 15, "tidy_version": 15,
    "decision": "Retain internal opt-in cached safe-link pruning; default remains NONE",
    "limits": ["Observed10k cohorts,not blind", "Not equal-recall speed comparison",
               "No100k/interleaved CRUD or Full remeasurement", "No cold I/O/package claim",
               "Failed non-reverse cache rebuild counters need not roll back"]}
(out / "validation.json").write_text(json.dumps(validation, indent=2) + "\n")
with tarfile.open(out / "raw.tar.gz") as tar:
    raw = {m.name.removeprefix("./"): tar.extractfile(m).read() for m in tar if m.isfile()}
for path in Path("/home/ubuntu/project").glob("vsag-safe-link-*20261011.log"):
    raw[path.name] = path.read_bytes()
raw["candidate.patch"] = subprocess.check_output(["git", "diff", "--",
    "src/lite/rabitq_graph_state.h", "src/lite/rabitq_backend_test.cpp",
    "src/lite/graph_allocation_test.cpp"])
raw["final-state.h"] = (repo / "src/lite/rabitq_graph_state.h").read_bytes()
raw["final-test.cpp"] = (repo / "src/lite/rabitq_backend_test.cpp").read_bytes()
raw["final-allocation-test.cpp"] = (repo / "src/lite/graph_allocation_test.cpp").read_bytes()
raw["reference-floating-link.cpp"] = (repo / "src/lite/graph_backend.cpp").read_bytes()
raw["native-pruning-strategy.cpp"] = (repo / "src/impl/pruning_strategy.cpp").read_bytes()
for path in logs.glob("*.log"):
    raw[path.name] = path.read_bytes()
for name in ("verify.py", "validation-script.sh", "validation-commands.json", "validation.json",
             "identity.json", "coverage.json", "collect.py"):
    raw[name] = (out / name).read_bytes()
for name in final_sources:
    raw["source-" + Path(name).name] = (repo / name).read_bytes()
with tarfile.open(out / "raw.tar.gz", "w:gz") as tar:
    for name, blob in sorted(raw.items()):
        member = tarfile.TarInfo("./" + name)
        member.size = len(blob)
        tar.addfile(member, io.BytesIO(blob))
(out / "members.json").write_text(json.dumps({n: sha(b) for n, b in sorted(raw.items())},
                                            indent=2, sort_keys=True) + "\n")
spec = importlib.util.spec_from_file_location("audit", out / "verify.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
result = mod.derive(out)
(out / "summary.json").write_text(json.dumps(result, indent=2) + "\n")

# Report and canonical hashes are generated below after audited results.
import statistics
import random

report = ["# RaBitQ cached incoming-safe link pruning (2026-10-11)", "",
    "Source evidence: floating src/lite/graph_backend.cpp::link scans distance-ranked edges",
    "from farthest to nearest,avoiding removal of an existing target's sole incoming edge.",
    "Adapt exactly that incoming-count gate to encoded MutableGraphState::link. New edges can",
    "be dropped if their target already has another incoming edge;old edges require indegree>1.",
    "If no safe edge exists,retain the original farthest-edge fallback. This is NOT diversity",
    "pruning or proof that every orphan/connectivity loss is eliminated.", "",
    "Internal ConfigureIncomingProtection gains a final protect_link=false argument,valid only",
    "with CACHED. Count preparation occurs before inserting the new link. The existing incremental",
    "count synchronization and rollback paths remain. No new reverse index or pairwise distances.",
    "Public adapter remains NONE,reverse=false. API,degree/ef,model/rotation/scoring and VSAGLQ01v1",
    "remain unchanged. This is internal opt-in experimental code,not enabled public behavior.", "",
    "## Frozen paired quality/cost study", "",
    "Parent22fa22c control versus candidate;BOTH adapters CACHED with all post-Add/Remove flags",
    "false. Only candidate enables link protection. Thus this is NOT public NONE versus CACHED,",
    "and not the older incoming-count-cache speed study. Both retain existing Update protection.",
    "10k GIST960/Cohere768,600 previously observed queries,k10,degree16/maintenance128/query512,",
    "CPU0,BLAS/OMP/MKL1. Three full-ID true whole-vector Update/Remove/Add passes,90000 calls",
    "per builder;three alternating pairs per dataset,12 builders and1080000 mutation calls.",
    "No builds/tests ran during timing. Original data/recipe/SHA and raw neighbor/hit/latency",
    "records are retained. No budget/threshold/seed tuning after seeing results.", "",
    "|Dataset|Final recall old/new|Gain percentage points|CRUD median old/new ms|CRUD change|",
    "|---|---:|---:|---:|---:|"]
for label, comp in result["comparison"].items():
    groups = [[r for r in result["summary"] if r["dataset"] == label and r["variant"] == v]
              for v in ("control", "candidate")]
    first, second = [statistics.median(r["final"]["recall"] for r in g) for g in groups]
    report.append("|%s|%.6f / %.6f|%+.3f|%.3f / %.3f|%+.2f%%|" % (
        label, first, second, (second-first)*100, comp["control_median_ms"],
        comp["candidate_median_ms"], comp["median_change_percent"]))
report += ["", "|Dataset|Post-CRUD query old P50/P99 us|New P50/P99 us|",
           "|---|---:|---:|"]
for label in result["comparison"]:
    groups = [[r for r in result["summary"] if r["dataset"] == label and r["variant"] == v]
              for v in ("control", "candidate")]
    vals = [[statistics.median(r["final"][k] for r in g) for k in ("p50_us","p99_us")]
            for g in groups]
    report.append("|%s|%.3f / %.3f|%.3f / %.3f|" % (label,*vals[0],*vals[1]))
report += ["", "|Dataset/operation|Old P50/P99 us|New P50/P99 us|","|---|---:|---:|"]
for label in result["comparison"]:
    for operation in ("update","remove","add"):
        groups = [[r for r in result["summary"] if r["dataset"] == label and r["variant"] == v]
                  for v in ("control", "candidate")]
        vals = [[statistics.median(r["operations"][operation][k] for r in g)
                 for k in ("p50_us","p99_us")] for g in groups]
        report.append("|%s/%s|%.3f / %.3f|%.3f / %.3f|"%(label,operation,*vals[0],*vals[1]))
report += ["", "All initial ordered ID/hex-distance/hit records are byte-identical. Final graphs",
    "and results intentionally differ. Each of12 builders natively verifies exact Save/Load",
    "ordered ID/distance equality. Snapshot bytes remain11284416/9363552;degree limits unchanged.",
    "Final queries are before/after maintenance,NOT interleaved into the mutation loop.", "",
    "Both candidate recalls still miss the pre-existing study floors GIST.90/Cohere.95.",
    "These are study targets,not OSPP official numerical thresholds. Query timings compare",
    "different final qualities;higher recall can cost more traversal. No equal-recall query",
    "speed win,public-default improvement,Full comparison or complete acceptance is claimed.",
    "Repeated deterministic graph outcomes on the same observed queries are not independent",
    "quality samples or blind generalization. Raw paired per-query wins/losses are in summary.",
    "Known permanent count storage is the same8N between both CACHED variants;no memory saving",
    "is claimed. External peak includes input matrices/staging/two indexes,not mutation-only peak.", "",
    "## Validation", "",
    "Release6,ASan/UBSan5,fresh coverage5,RaBitQ-OFF4,format/tidy15 pass. Rule tests cover newly",
    "added versus existing targets,no-safe-edge fallback,invalid input and policy rejection.",
    "A concrete saturated-row Add fixture verifies the old policy leaves a target with zero",
    "incoming edges while protected policy retains one,with reverse off/on. Continued mixed",
    "changes and exact mutable persistence pass. Existing public/default golden behavior passes.",
    "Allocation regression explores24000 internal positions (8000 safe-policy cold/warm positions)",
    "plus6000 public positions. Reverse on/off,Update/Add/Remove,hole/last/singleton,failure/retry",
    "and continued changes pass without state mismatch. Non-reverse rollback invalidates cache;",
    "diagnostic attempted-rebuild counters may advance. The initial expanded fixture incorrectly",
    "required these counters to roll back like reverse-copy mode;failed log retained,assertion",
    "corrected to the existing contract. Persistent snapshots and retry goldens remain strict.",
    "Final graph fixture was added after timing;production header remained byte-identical.",
    "Measured test source and final validated source are separately retained.",
    "Scoped Lite coverage%d/%d=%.2f%%,not whole Full coverage." % (
        scopes["lite"]["covered"],scopes["lite"]["total"],scopes["lite"]["percent"]), "",
    "## Evidence and reproduction", "",
    "Run python3 lite/benchmark/results/rabitq-safe-link-20261011/verify.py to audit hashes,",
    "1080000 schedules,14400 truth intersections,operation/query quantiles,initial byte equality,",
    "paired hit deltas,10 final command exits and the fresh19-counter coverage union.",
    "It does not regenerate exhaustive changed-data truth or reread deleted large snapshots.",
    "New RAM snapshots were deleted only after native exact Load/Save checks/hash/archive;",
    "old datasets/source/raw/binaries were preserved. No Full/OS cache privileges changed.", "",
    "For host replay,use a NEW result directory,matching parent source/build objects/SIMD/data",
    "and actual archived measured-run-host.py,candidate-state.h and recorded adapter build commands.",
    "Final run-host.py pins the measured candidate header from this raw archive;syntax-checked",
    "only,not rerun. Original absolute host dependencies/input SHA remain authoritative.", "",
    "Decision: retain this promising internal opt-in candidate,NOT enable public default yet.",
    "Next isolate remaining route misses and test a bounded candidate/diversity rule separately,",
    "then100k/interleaved real CRUD and fresh native Full configuration/SIMD/quality alignment.",
    "Cold I/O,complete package sizing and final adoption decision remain pending.", ""]
edit(out / "README.md","\n".join(report))
canonical=["README.md","run-host.py","verify.py","collect.py","validation-script.sh",
    "validation-commands.json","validation.json","coverage.json","coverage-raw.tar.gz",
    "identity.json","rows.json","raw.tar.gz","members.json","summary.json"]
(out/"SHA256SUMS").write_text("".join(sha((out/n).read_bytes())+"  "+n+"\n" for n in canonical))
print(json.dumps({"comparison":result["comparison"],"paired":result["paired"],
                  "coverage":scopes},indent=2))
