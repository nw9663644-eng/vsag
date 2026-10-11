#!/usr/bin/env python3
"""Matched-host synthetic BuildGraph allocation diagnostic, not a Full comparison."""
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import statistics
import subprocess
import tempfile

repo = Path(__file__).resolve().parents[4]
out = Path(__file__).resolve().parent
build = repo / "build-lite-fp16-simd-release"
assert not (out / "rows.json").exists(), "Use a fresh evidence directory"
scratch = Path(tempfile.mkdtemp(prefix="vsag-owned-topology-", dir="/dev/shm"))
parent = "0444bf9426d38a794137e30871957c95e33283f1"
commands = []
rows = []
def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()
def run(tag, cmd, cwd=repo, env=None):
    result = subprocess.run(cmd, cwd=cwd, env=env, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (out / (tag + ".stdout")).write_text(result.stdout)
    (out / (tag + ".stderr")).write_text(result.stderr)
    commands.append(dict(tag=tag, command=cmd, cwd=str(cwd), exit=result.returncode))
    (out / "commands.json").write_text(json.dumps(commands, indent=2) + "\n")
    assert result.returncode == 0, tag
    return result.stdout
old = scratch / "control"
(old / "lite").mkdir(parents=True)
for source, target in [("src/lite/rabitq_graph_state.h", old / "lite/rabitq_graph_state.h"),
                       ("src/lite/rabitq_backend.cpp", old / "adapter.cpp")]:
    content = subprocess.check_output(["git", "show", parent + ":" + source], cwd=repo)
    target.write_bytes(content)
    (out / ("control-" + Path(source).name)).write_bytes(content)
identity = json.loads((repo / "lite/benchmark/results/rabitq-safe-link-20261011/identity.json").read_text())
variant = identity["variants"]["control"]
compile_cmd = variant["compile"][:]
compile_cmd = [("-I" + str(old)) if x.startswith("-I/dev/shm/") else x for x in compile_cmd]
compile_cmd[compile_cmd.index("-o") + 1] = str(old / "adapter.o")
compile_cmd[-1] = str(old / "adapter.cpp")
run("compile-control", compile_cmd)
deps = compile_cmd[:compile_cmd.index("-o")] + ["-MM", str(old / "adapter.cpp")]
dep_text = run("deps-control", deps)
assert str(old / "lite/rabitq_graph_state.h") in dep_text
link_cmd = variant["link"][:]
link_cmd[link_cmd.index("-o") + 1] = str(old / "libvsag-lite.so")
link_cmd = [str(old / "adapter.o") if x.endswith("/adapter.o") else x for x in link_cmd]
run("link-control", link_cmd, build)
probe = scratch / "probe"
run("compile-probe", ["/usr/bin/c++", "-O3", "-DNDEBUG", "-std=c++17",
    "-I" + str(repo / "include"), str(out / "probe.cpp"),
    "-L" + str(build), "-Wl,-rpath," + str(build), "-lvsag-lite", "-o", str(probe)])
paths = {"control": old, "candidate": build}
sources = {str(p.relative_to(repo)): sha(p) for p in [
    repo / "src/lite/rabitq_graph_state.h", repo / "src/lite/rabitq_backend.cpp",
    repo / "src/lite/rabitq_backend_test.cpp", out / "probe.cpp"]}
(out / "identity.json").write_text(json.dumps(dict(parent=parent, hostname=run("hostname", ["hostname"]).strip(),
    source_sha256=sources, libraries={k: sha(v / "libvsag-lite.so") for k,v in paths.items()},
    shapes=[[10000,17],[100000,17]], degree=16, construction_ef=128,
    query_ef=512, cpu=0, trials=3, policy="public default NONE, reverse false",
    scratch=str(scratch)), indent=2) + "\n")
for count in [10000,100000]:
    for trial in range(3):
        order = ["control","candidate"] if trial % 2 == 0 else ["candidate","control"]
        pair = []
        for name in order:
            tag = f"n{count}-t{trial}-{name}"
            env = dict(os.environ, LD_LIBRARY_PATH=str(paths[name]),
                OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1")
            snapshot = scratch / (tag + ".snapshot")
            text = run(tag, ["taskset","-c","0",str(probe),str(count),"17",str(snapshot)], env=env)
            parsed = list(csv.DictReader(io.StringIO("\n".join(text.splitlines()[:2]))))[0]
            record = dict(variant=name, trial=trial, count=count,
                metrics={k: float(v) if k=="build_ms" else int(v) for k,v in parsed.items()},
                snapshot_sha256=sha(snapshot), snapshot_bytes=snapshot.stat().st_size,
                ordered_query_sha256=hashlib.sha256("\n".join(text.splitlines()[2:]).encode()).hexdigest())
            pair.append(record)
            rows.append(record)
            (out / "rows.json").write_text(json.dumps(rows,indent=2)+"\n")
            assert snapshot.resolve().parent == scratch.resolve() and snapshot.is_file()
            snapshot.unlink()
            print(tag, record["metrics"], flush=True)
        assert pair[0]["snapshot_sha256"] == pair[1]["snapshot_sha256"]
        assert pair[0]["ordered_query_sha256"] == pair[1]["ordered_query_sha256"]
summary = {}
for count in [10000,100000]:
    summary[str(count)] = {}
    for metric in ["build_ms","hwm_kib","ordinary_new_requests","ordinary_new_bytes"]:
        med = {name: statistics.median([r["metrics"][metric] for r in rows
               if r["count"]==count and r["variant"]==name]) for name in paths}
        summary[str(count)][metric] = dict(med, change_percent=100*(med["candidate"]/med["control"]-1))
(out / "summary.json").write_text(json.dumps(summary,indent=2)+"\n")
print(json.dumps(summary,indent=2),flush=True)
