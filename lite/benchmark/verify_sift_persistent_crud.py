#!/usr/bin/env python3
# Copyright 2024-present the vsag project
# SPDX-License-Identifier: Apache-2.0
"""Audit schedules, exact truth intersections and raw latency quantiles."""
import csv
import hashlib
import json
import math
from pathlib import Path
import struct
import sys


def read_csv(path):
    with path.open() as source:
        return list(csv.DictReader(source))


def truth(path):
    data = path.read_bytes()
    assert len(data) == 100 * 44
    result = []
    for offset in range(0, len(data), 44):
        record = struct.unpack_from('<11i', data, offset)
        assert record[0] == 10 and len(set(record[1:])) == 10
        result.append(set(record[1:]))
    return result


def quantile(values, fraction):
    ordered = sorted(values)
    return ordered[max(1, math.ceil(len(ordered) * fraction)) - 1]


def main():
    root = Path(sys.argv[1])
    rows = json.loads((root / 'rows.json').read_text())
    identity = json.loads((root / 'identity.json').read_text())
    receipt = json.loads((root / 'receipt.json').read_text())
    for filename in ['queries.fvecs', 'groundtruth.ivecs', 'changed-groundtruth.ivecs']:
        assert hashlib.sha256((root / filename).read_bytes()).hexdigest() == receipt['files'][filename]['sha256']
    for filename, digest in identity['sources'].items():
        assert hashlib.sha256((root / ('source-' + Path(filename).name)).read_bytes()).hexdigest() == digest
    assert [row['storage'] for row in rows] == ['fp32', 'fp16', 'rabitq8']
    summary = {}
    for row in rows:
        mode, metrics = row['storage'], row['metrics']
        operations = read_csv(root / (mode + '.queries.csv.operations.csv'))
        assert len(operations) == 90000
        timings = {kind: [] for kind in range(3)}
        for position, operation in enumerate(operations):
            cycle, kind = divmod(position, 3)
            round_number, index = divmod(cycle, 10000)
            assert int(operation['cycle']) == cycle
            assert int(operation['operation']) == kind
            assert int(operation['id']) == (round_number * 65537 + index * 8191) % 100000
            latency = float(operation['latency_us'])
            assert math.isfinite(latency) and latency >= 0
            timings[kind].append(latency)
        for suffix, truth_name, recall_name in [
            ('', 'changed-groundtruth.ivecs', 'recall_at_k'),
            ('.initial', 'groundtruth.ivecs', 'initial_recall_at_k')]:
            expected = truth(root / truth_name)
            neighbors = read_csv(root / (mode + '.queries.csv' + suffix + '.neighbors.csv'))
            hits = read_csv(root / (mode + '.queries.csv' + suffix))
            assert len(neighbors) == 1000 and len(hits) == 100
            total = 0
            for query in range(100):
                group = neighbors[query * 10:(query + 1) * 10]
                assert all(int(neighbor['query']) == query and int(neighbor['rank']) == rank
                           for rank, neighbor in enumerate(group))
                ids = {int(neighbor['id']) for neighbor in group}
                assert len(ids) == 10 and all(0 <= value < 100000 for value in ids)
                assert all(math.isfinite(float.fromhex(neighbor['distance'])) for neighbor in group)
                count = len(ids & expected[query])
                assert count == int(hits[query]['hits'])
                total += count
            assert abs(total / 1000 - float(metrics[recall_name])) < 1e-9
        latencies = [float(item['latency_us']) for item in read_csv(root / (mode + '.queries.csv.latencies.csv'))]
        assert len(latencies) == 100
        assert abs(quantile(latencies, .5) - float(metrics['search_p50_us'])) < 1e-6
        assert abs(quantile(latencies, .99) - float(metrics['search_p99_us'])) < 1e-6
        summary[mode] = dict(api_mutations_per_second=90000000 / float(metrics['crud_ms']),
            operation_us={['update', 'remove', 'add'][kind]:
                dict(p50=quantile(values, .5), p99=quantile(values, .99))
                for kind, values in timings.items()})
    print(json.dumps(dict(audit='pass', operations=270000, truth_query_states=600,
                         summary=summary), indent=2))


if __name__ == '__main__':
    main()
