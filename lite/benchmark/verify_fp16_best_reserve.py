# Copyright 2024-present the vsag project
# SPDX-License-Identifier: Apache-2.0
"""Verify public FP16 reserve trials independently from raw ordered results."""
import csv
import hashlib
import json
import math
from pathlib import Path
import statistics
import struct
import sys

out = Path(sys.argv[1])
identity = json.loads((out / 'identity.json').read_text())
rows = json.loads((out / 'rows.json').read_text())
commands = json.loads((out / 'commands.json').read_text())
assert len(rows) == 56 and len(commands) == 66
assert all(command['exit']==0 for command in commands)
for name,digest in identity['sources'].items():
    assert hashlib.sha256((out / ('source-' + Path(name).name)).read_bytes()).hexdigest() == digest
original = (out / 'control-graph_backend.cpp').read_text()
marker = '            QueryHeap<Candidate, Closer> best;'
replacement = ('            std::vector<Candidate> best_storage;\n'
    '            best_storage.reserve(ef + static_cast<uint64_t>(ef < Size()));\n'
    '            QueryHeap<Candidate, Closer> best(Closer{}, std::move(best_storage));')
assert original.count(marker) == 1
assert (out / 'candidate-graph_backend.cpp').read_text() == original.replace(marker,replacement)
assert (out / 'archive-members.stdout').read_text().splitlines().count('graph_backend.cpp.o') == 1

def read_csv(path):
    with path.open() as stream:
        return list(csv.DictReader(stream))

summary = {}
for label,receipt in identity['inputs'].items():
    for name in ['queries.fvecs','groundtruth.ivecs']:
        assert hashlib.sha256((out / (label + '.' + name)).read_bytes()).hexdigest() == receipt['hashes'][name]
    raw_truth = (out / (label + '.groundtruth.ivecs')).read_bytes()
    assert len(raw_truth) == 4400
    truth = []
    for offset in range(0,len(raw_truth),44):
        record = struct.unpack_from('<11i',raw_truth,offset)
        assert record[0] == 10 and len(set(record[1:])) == 10
        truth.append(set(record[1:]))
    reference = (out / (label + '-prepare.csv.neighbors.csv')).read_bytes()
    hits = 0
    for row in [r for r in rows if r['dataset']==label]:
        tag = f"{label}-{row['trial']}-{row['variant']}"
        assert (out / (tag + '.neighbors.csv')).read_bytes() == reference
        neighbors = read_csv(out / (tag + '.neighbors.csv'))
        queries = read_csv(out / (tag + '.queries.csv'))
        assert len(neighbors)==1000 and len(queries)==100
        hits = 0
        for q,query in enumerate(queries):
            assert int(query['query']) == q
            ids = []
            for rank,item in enumerate(neighbors[q*10:(q+1)*10]):
                assert int(item['query'])==q and int(item['rank'])==rank
                assert math.isfinite(float.fromhex(item['distance']))
                ids.append(int(item['id']))
            assert len(set(ids))==10 and all(0<=id<receipt['count'] for id in ids)
            hits += len(truth[q].intersection(ids))
        times = sorted(float(q['latency_us']) for q in queries)
        assert all(math.isfinite(t) and t>0 for t in times)
        assert times[49]==row['p50_us'] and times[98]==row['p99_us']
    summary[label] = dict(recall=hits/1000)
    for variant in ['control','candidate']:
        values = [r for r in rows if r['dataset']==label and r['variant']==variant]
        assert sorted(r['trial'] for r in values)==list(range(7))
        summary[label][variant] = {key:statistics.median(r[key] for r in values) for key in ['p50_us','p99_us']}
    for key in ['p50_us','p99_us']:
        ratios = []
        wins = 0
        for trial in range(7):
            pair = {r['variant']:r[key] for r in rows if r['dataset']==label and r['trial']==trial}
            ratios.append(100*(pair['candidate']/pair['control']-1))
            wins += int(pair['candidate'] < pair['control'])
        summary[label][key + '_paired_change_percent'] = ratios
        summary[label][key + '_wins'] = wins
        summary[label][key + '_median_change_percent'] = 100*(summary[label]['candidate'][key]/summary[label]['control'][key]-1)
(out / 'audit.json').write_text(json.dumps(dict(status='PASS',runs=56,queries=5600,neighbors=56000,commands=66,summary=summary),indent=2) + '\n')
print(json.dumps(summary,indent=2))
print('PASS 56 runs / 5600 queries / 56000 ordered public neighbors; source-only reserve overlay')
