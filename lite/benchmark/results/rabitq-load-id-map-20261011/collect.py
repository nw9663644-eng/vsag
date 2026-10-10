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
out = repo / "lite/benchmark/results/rabitq-load-id-map-20261011"
logs = Path("/home/ubuntu/project/vsag-load-id-map-20261011")
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
identity["source_sha256"] = {n: sha((repo / n).read_bytes()) for n in (
    "src/lite/rabitq_snapshot.h", "src/lite/rabitq_graph_state.h",
    "src/lite/rabitq_backend_test.cpp", "lite/benchmark/graph_crud_quality.cpp")}
identity["default_library_sha256"] = sha((repo / "build-lite-fp16-simd-release/libvsag-lite.so").read_bytes())
(out / "identity.json").write_text(json.dumps(identity, indent=2) + "\n")
validation = {"tests": {"release": 6, "asan_ubsan": 5, "fresh_coverage": 5, "disabled": 4},
    "production_change": True, "public_defaults_changed": False, "snapshot_format_changed": False,
    "format_version": 15, "tidy_version": 15, "decision": "Retain removal of redundant load-only ID set",
    "limits": ["Warm RAM/page cache, not cold I/O", "Not query or CRUD benchmark",
               "Not Full or100k acceptance", "Inherited getrusage HWM is not loader peak evidence",
               "Malformed duplicate IDs rejected later; error text/order not preserved"]}
(out / "validation.json").write_text(json.dumps(validation, indent=2) + "\n")
with tarfile.open(out / "raw.tar.gz") as tar:
    raw = {m.name.removeprefix("./"): tar.extractfile(m).read() for m in tar if m.isfile()}
for path in logs.glob("*.log"):
    raw[path.name] = path.read_bytes()
for name in ("verify.py", "validation-script.sh", "validation-commands.json", "validation.json",
             "identity.json", "coverage.json", "collect.py"):
    raw[name] = (out / name).read_bytes()
for name in identity["source_sha256"]:
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
report = ["# RaBitQ snapshot load: remove duplicated ID validation (2026-10-11)", "",
    "Source evidence: load_mutable_snapshot created an unordered_set to reject duplicate IDs;",
    "MutableGraphState already rejects them through slots_.emplace(...).second while building",
    "the required ID-to-slot map. Remove only the first set and its header include. No map reserve,",
    "graph layout,model,query,CRUD,public policy,SIMD,API or VSAGLQ01v1 format changes.", "",
    "## Matched warm loading", "",
    "Default reverse=false / NONE for both variants. Parent e017145 control and candidate have",
    "identical frozen Lite headers except removal of this set. CPU0,single process;GIST960 and",
    "Cohere768 each10k,degree16/build128/query512. Two zero-round builders generate valid current",
    "snapshots,not a repeated CRUD benchmark. Fifteen alternating fresh-process pairs per dataset.",
    "All60 native Load/Save round trips have the exact input SHA;known graph/code/map byte counts",
    "are identical. Source/dependency/compile receipts and raw CSV/stdout are retained.", "",
    "|Dataset|Old/new load median ms|Change|Old/new baseline-subtracted RSS KiB|Faster pairs|",
    "|---|---:|---:|---:|---:|"]
for label, data in result["summary"].items():
    report.append("|%s|%.6f / %.6f|%+.2f%%|%.0f / %.0f|%d/15|" % (
        label, data["control"]["load_ms"], data["candidate"]["load_ms"],
        data["load_change_percent"], data["control"]["resident_increment_kib"],
        data["candidate"]["resident_increment_kib"], data["candidate_faster_pairs"]))
report += ["", "This is a small warm-load/allocator-retention improvement,not a permanent index layout",
    "reduction or a statistical guarantee. Current RSS is sampled after load before re-saving.",
    "The removed temporary set can leave allocator-resident pages after destruction;known",
    "resident index capacity is unchanged. getrusage ru_maxrss retains a launcher-related floor",
    "and is explicitly NOT claimed as clean-loader peak improvement. RAM/page-cache warm is not",
    "cold filesystem I/O. Initial query evidence is setup validation,not query/CRUD/Full advantage.", "",
    "## Correctness and limitations", "",
    "Malformed duplicate-ID snapshots remain INVALID_BINARY;new tests cover negative,zero and",
    "INT64_MIN/MAX duplicates near the start/end. Public Save/Load bytes remain identical.",
    "Duplicate rejection now occurs in the constructor after graph parsing/adjacency expansion:",
    "malformed duplicate input may do more work before rejection;error message/validation order",
    "is not preserved. Existing count/dimension/graph bounds remain. Do not claim earlier rejection",
    "or constant-memory parsing. Allocation-failure tests still pass;exception handling unchanged.", "",
    "Release6,ASan/UBSan5,fresh coverage5,RaBitQ-disabled4,format/tidy15 production and probe pass.",
    "Fresh scoped Lite coverage%d/%d=%.2f%%;not whole Full coverage." % (
        scopes["lite"]["covered"], scopes["lite"]["total"], scopes["lite"]["percent"]), "",
    "## Reproduction", "",
    "From repository root,on the recorded host,use a new results directory and run run-host.py.",
    "It freezes all Lite headers from e017145 and derives the exact candidate minimal patch;",
    "existing cached10k vectors/truth paths are required and hashed. It refuses completed-row",
    "overwrite. Builders/probe compile commands,environment,input hashes,snapshot hashes,source",
    "and validation logs are retained. Large fresh RAM snapshots/round-trip files were removed",
    "only after exact re-save hashes and durable receipts;old datasets/results were not removed.",
    "Snapshot hashes cannot independently prove missing snapshot bytes;native round-trip receipts",
    "are evidence from the measured host. verify.py audits retained artifacts without replay:", "",
    "~~~bash", "python3 lite/benchmark/results/rabitq-load-id-map-20261011/verify.py", "~~~", "",
    "Fresh original performance reproduction is not performed by the verifier. collect.py is",
    "an evidence-generation recipe tied to fresh validation logs/counters,not a portable benchmark.", "",
    "Still pending: mixed real-value CRUD quality floors,100k/interleaved endurance,fresh native",
    "Full configuration/SIMD/quality-aligned comparison,cold I/O and complete installed package.",
    "Public default policies and PR2904/2926 remain untouched;project is not fully accepted.", ""]
edit(out / "README.md", "\n".join(report))
en = ("\n## RaBitQ load-only ID validation optimization (2026-10-11)\n\n"
      "The [matched loader study](../../../../../lite/benchmark/results/rabitq-load-id-map-20261011/README.md) "
      "removes a temporary duplicate-ID set;the required constructor slot map still rejects duplicates. "
      "Default reverse=false/NONE and snapshot bytes are unchanged. Fifteen alternating10k pairs per "
      "dataset show GIST/Cohere warm-load medians6.483486->6.243492ms (-3.70%) and "
      "5.721933->5.503448ms (-3.82%),with baseline-subtracted RSS472/416KiB lower and60 exact "
      "native round trips. This is allocator-retention/warm-load evidence,not index capacity,query,"
      "CRUD,cold I/O,Full or100k improvement. Malformed duplicates are rejected later after graph "
      "parsing;INVALID_BINARY remains but validation order/error text is not preserved. Quality and "
      "final acceptance remain pending.\n")
zh = ("\n## RaBitQ 加载路径 ID 校验优化（2026-10-11）\n\n"
      "[同快照加载对照](../../../../../lite/benchmark/results/rabitq-load-id-map-20261011/README.md)"
      "移除临时重复 ID 集合，构造函数必需的槽位表仍拒绝重复 ID。默认 reverse=false/NONE、快照字节不变。"
      "每数据集15组交替10k对照，GIST/Cohere 暖加载中位数6.483486→6.243492ms（-3.70%）、"
      "5.721933→5.503448ms（-3.82%），扣除进程基线的加载后 RSS 少472/416KiB，60次原生加载再保存哈希完全一致。"
      "这是分配器页驻留与暖加载证据，不是索引容量、查询、CRUD、冷 I/O、Full 或100k优势。"
      "重复 ID 坏输入会在图解析后更晚拒绝，仍为 INVALID_BINARY，但校验顺序和错误文本不保证保持。"
      "质量及终验仍待完成。\n")
for name, text in (("docs/docs/en/src/development/lite_first.md", en),
                   ("docs/docs/zh/src/development/lite_first.md", zh)):
    path = repo / name
    edit(path, path.read_text() + text)
path = repo / "lite/benchmark/README.md"
edit(path, path.read_text() + "\n## RaBitQ snapshot load-only optimization\n\n"
     "See [matched warm loaders](results/rabitq-load-id-map-20261011/README.md):remove the "
     "redundant ID set,retain constructor duplicate rejection. GIST/Cohere warm load about3.70/3.82% "
     "lower in15 paired10k trials;60 native round-trip hashes exact. No query/CRUD/Full/cold I/O "
     "claim;malformed duplicate inputs may be rejected later. Public defaults/PRs unchanged.\n")
canonical = ["README.md", "run-host.py", "memory-probe.cpp", "verify.py", "collect.py",
             "validation-script.sh", "validation-commands.json", "validation.json", "coverage.json",
             "coverage-raw.tar.gz", "identity.json", "rows.json", "raw.tar.gz", "members.json", "summary.json"]
(out / "SHA256SUMS").write_text(json.dumps({n: sha((out / n).read_bytes()) for n in canonical},
                                           indent=2, sort_keys=True) + "\n")
print(json.dumps(result, indent=2))
