#!/usr/bin/env python3
# Copyright 2024-present the vsag project
# SPDX-License-Identifier: Apache-2.0
"""Audit expanded native-Full comparisons and ELF-closure accounting."""
import collections
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import statistics
import struct
import tarfile


def digest(payload):
    return hashlib.sha256(payload).hexdigest()


def csv_rows(payload):
    return list(csv.DictReader(io.StringIO(payload.decode())))


def main():
    root = Path(__file__).resolve().parent
    for line in (root/"SHA256SUMS").read_text().splitlines():
        value, name = line.split("  ", 1)
        assert digest((root/name).read_bytes()) == value
    identity = json.loads((root/"identity.json").read_text())
    assert identity["native_full_profile"] == "small"
    assert identity["arguments"]["ef"] == 512
    assert identity["arguments"]["full_ef"] == 128
    assert identity["reference_library_sha256"] == \
        "9aeaa550703f116bef2959769d4f2f03da254b07c906ba941d8186224cc70c72"
    records = json.loads((root/"rows.json").read_text())
    audit = []
    loads = states = 0
    with tarfile.open(root/"raw.tar.gz") as archive:
        payloads = {}
        for member in archive:
            assert member.isfile() and member.name.startswith("./")
            name = member.name[2:]
            assert "/" not in name and name not in payloads
            payloads[name] = archive.extractfile(member).read()
        members = json.loads((root/"members.json").read_text())
        assert set(payloads) == set(members)
        def read(name):
            return payloads[name]
        for name, value in members.items():
            assert digest(read(name)) == value
        for record in records:
            tag = f"{record['dataset']}-{record['storage']}-{record['trial']}-{record['name']}"
            full = record["name"] == "full"
            latency = csv_rows(read(tag+(".latencies.csv" if full else
                                         ".queries.csv.latencies.csv")))
            times = sorted(float(x["latency_us"]) for x in latency)
            assert len(times) == 600 == int(record["build"]["query_count"])
            assert all(math.isfinite(x) and x >= 0 for x in times)
            for fraction, key in [(0.5, "search_p50_us"), (0.99, "search_p99_us")]:
                assert abs(times[math.ceil(len(times)*fraction)-1] -
                           float(record["build"][key])) <= 1e-6
            metadata = json.loads(read(record["dataset"]+".dataset.json"))
            for name in ["queries.fvecs", "groundtruth.ivecs"]:
                payload = read(record["dataset"]+"."+name)
                assert digest(payload) == metadata[name]["sha256"]
                assert len(payload) == metadata[name]["bytes"]
            payload = read(record["dataset"]+".groundtruth.ivecs")
            assert len(payload) == 600*44
            truth = []
            for offset in range(0, len(payload), 44):
                assert struct.unpack_from("<i", payload, offset)[0] == 10
                values = set(struct.unpack_from("<10i", payload, offset+4))
                assert len(values) == 10 and all(0 <= x < 10000 for x in values)
                truth.append(values)
            neighbors = collections.defaultdict(list)
            suffix = ".neighbors.csv" if full else ".queries.csv.neighbors.csv"
            for row in csv_rows(read(tag+suffix)):
                query = int(row["query"])
                assert 0 <= query < 600
                assert int(row["rank"]) == len(neighbors[query])
                value = float.fromhex(row["distance"])
                assert math.isfinite(value)
                if neighbors[query]:
                    assert value >= neighbors[query][-1][1]
                neighbors[query].append((int(row["id"]), value))
            assert len(neighbors) == 600
            hits = []
            for query in range(600):
                ids = [x[0] for x in neighbors[query]]
                assert len(ids) == len(set(ids)) == 10
                assert all(0 <= x < 10000 for x in ids)
                hits.append(len(set(ids) & truth[query]))
                states += 1
            recall = sum(hits)/6000
            assert abs(recall-float(record["build"]["recall_at_k"])) <= 1e-6
            if not full:
                actual = csv_rows(read(tag+".queries.csv"))
                assert [int(x["hits"]) for x in actual] == hits
            else:
                config = json.loads(read(tag+".parameters.json"))
                assert config["build"]["index_param"]["build_thread_count"] == 1
                assert config["build"]["index_param"]["base_io_type"] == "memory_io"
            assert int(read(tag+".peak_kib")) == record["build"]["external_peak_rss_kib"]
            assert len(record["loads"]) == 3
            for sample, expected in enumerate(record["loads"]):
                lines = read(tag+f"-load-{sample}.stdout").decode().splitlines()
                start = next(i for i,x in enumerate(lines) if x.startswith("dim,count,"))
                row = csv_rows(("\n".join(lines[start:start+2])+"\n").encode())[0]
                for key, value in row.items():
                    assert value == expected[key]
                assert int(read(tag+f"-load-{sample}.peak_kib")) == expected["external_peak_rss_kib"]
                loads += 1
            audit.append({"tag": tag, "recall": recall,
                          "query_qps_from_latency_sum": 600*1e6/sum(times)})
    summary = json.loads((root/"summary.json").read_text())
    for row in summary:
        selected = [r for r in records if (r["dataset"],r["storage"],r["name"]) ==
                    (row["dataset"],row["storage"],row["name"])]
        assert len(selected) == 3
        for key in ["recall_at_k", "build_ms", "search_p50_us", "search_p99_us",
                    "save_ms", "snapshot_bytes", "external_peak_rss_kib"]:
            assert abs(statistics.median(float(r["build"][key]) for r in selected)-row[key]) <= 1e-6
        for key in ["load_ms", "loaded_rss_kib", "process_peak_rss_kib",
                    "before_create_rss_kib", "before_load_rss_kib"]:
            values = [float(s[key]) for r in selected for s in r["loads"]]
            assert abs(statistics.median(values)-row[key]) <= 1e-6
    closure = json.loads((root/"closure.json").read_text())
    assert digest((root.parents[1]/"measure_elf_closure.py").read_bytes()) == closure["script_sha256"]
    for name in ["lite", "full"]:
        report = closure[name]
        assert set(report["ldd"]) == set(report["files"])
        for file, receipt in report["files"].items():
            assert set(receipt["dependencies"]) <= set(report["files"])
            assert receipt["stripped_bytes"] <= receipt["source_bytes"]
        for prefix in ["source", "stripped"]:
            assert report["closure_"+prefix+"_bytes"] == \
                sum(r[prefix+"_bytes"] for r in report["files"].values())
        assert report["files"][report["root"]]["source_sha256"] == \
            identity["lite_library_sha256" if name == "lite" else "reference_library_sha256"]
    reduction = (1-closure["lite"]["closure_stripped_bytes"] /
                 closure["full"]["closure_stripped_bytes"])*100
    assert abs(reduction-closure["stripped_closure_reduction_percent"]) < 1e-10
    assert audit == json.loads((root/"query-audit.json").read_text())
    assert (len(records), states, loads) == (36, 21600, 108)
    print("36 builders, 21600 truth intersections, 108 loads, raw quantiles/medians, "
          "ELF accounting and artifact hashes passed")
    return audit


if __name__ == "__main__":
    main()
