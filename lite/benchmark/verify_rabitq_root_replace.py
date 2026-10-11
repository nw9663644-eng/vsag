# Copyright 2024-present the vsag project
# SPDX-License-Identifier: Apache-2.0
"""Independent raw-result checks for the isolated bounded-heap candidate."""
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
assert len(rows) == 56 and len(commands) == 68
assert all(command['exit'] == 0 for command in commands)
for name, digest in identity['sources'].items():
    assert hashlib.sha256((out / ('source-' + Path(name).name)).read_bytes()).hexdigest() == digest
original = (out / 'control-rabitq_graph_state.h').read_text()
begin = original.index('inline GraphSearchResult\ngraph_search_impl(')
end = original.index('inline GraphSearchResult\ngraph_search(', begin)
body = original[begin:end]
def rewrite(body):
    marker = '''        best.push(next);
        if (best.size() > ef) {
            best.pop();
        }'''
    assert body.count(marker) == 1
    body = body.replace(marker, '''        if constexpr (prune_rejected and select_without_pop) {
            if (best.size() == ef) {
                best.ReplaceTop(next);
            } else {
                best.push(next);
            }
        } else {
            best.push(next);
            if (best.size() > ef) {
                best.pop();
            }
        }''')
    return body

body = rewrite(body)
assert (out / 'candidate-rabitq_graph_state.h').read_text() == original[:begin] + body + original[end:]
heap = (out / 'control-query_heap.h').read_text()
marker = '    [[nodiscard]] const std::vector<T>&'
method = '''    // Caller admits only values better than the nonempty heap's current root.
    void
    ReplaceTop(T value) {
        const uint64_t count = this->c.size();
        uint64_t hole = 0;
        while (hole < count / 2) {
            uint64_t child = 2 * hole + 1;
            if (child + 1 < count and this->comp(this->c[child], this->c[child + 1])) {
                ++child;
            }
            if (not this->comp(value, this->c[child])) {
                break;
            }
            this->c[hole] = std::move(this->c[child]);
            hole = child;
        }
        this->c[hole] = std::move(value);
    }

'''
assert heap.count(marker) == 1
assert (out / 'candidate-query_heap.h').read_text() == heap.replace(marker, method + marker)

def read_csv(path):
    with path.open() as stream:
        return list(csv.DictReader(stream))

summary = {}
for label, receipt in identity['inputs'].items():
    for name in ['queries.fvecs','groundtruth.ivecs']:
        assert hashlib.sha256((out / (label + '.' + name)).read_bytes()).hexdigest() == receipt['hashes'][name]
    raw_truth = (out / (label + '.groundtruth.ivecs')).read_bytes()
    assert len(raw_truth) == 4400
    truth = []
    for offset in range(0,len(raw_truth),44):
        record = struct.unpack_from('<11i', raw_truth, offset)
        assert record[0] == 10 and len(set(record[1:])) == 10
        truth.append(set(record[1:]))
    reference = (out / (label + '-native-parity.neighbors.csv')).read_bytes()
    reference_counts = None
    for row in [r for r in rows if r['dataset'] == label]:
        tag = f"{label}-{row['trial']}-{row['variant']}"
        assert (out / (tag + '.neighbors.csv')).read_bytes() == reference
        neighbors = read_csv(out / (tag + '.neighbors.csv'))
        queries = read_csv(out / (tag + '.queries.csv'))
        assert len(queries) == 100 and len(neighbors) == 1000
        counts = [(q['hits'],q['visited'],q['reordered']) for q in queries]
        if reference_counts is None:
            reference_counts = counts
        assert counts == reference_counts
        for q, query in enumerate(queries):
            assert int(query['query']) == q
            ids = []
            for rank, item in enumerate(neighbors[10*q:10*(q+1)]):
                assert int(item['query']) == q and int(item['rank']) == rank
                assert math.isfinite(float.fromhex(item['distance']))
                ids.append(int(item['id']))
            assert len(set(ids)) == 10 and all(0 <= id < receipt['count'] for id in ids)
            assert len(truth[q].intersection(ids)) == int(query['hits'])
        times = sorted(float(q['latency_us']) for q in queries)
        assert all(math.isfinite(t) and t > 0 for t in times)
        assert times[49] == row['p50_us'] and times[98] == row['p99_us']
        assert sum(int(q['hits']) for q in queries)/1000 == row['recall']
        assert sum(int(q['visited']) for q in queries)/100 == row['average_visited']
    summary[label] = {}
    for variant in ['control','candidate']:
        values = [r for r in rows if r['dataset']==label and r['variant']==variant]
        assert sorted(r['trial'] for r in values) == list(range(7))
        summary[label][variant] = {key: statistics.median(r[key] for r in values)
            for key in ['p50_us','p99_us','recall','average_visited']}
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
(out / 'audit.json').write_text(json.dumps(dict(status='PASS', runs=56, queries=5600, neighbors=56000, commands=68, summary=summary), indent=2) + '\n')
print(json.dumps(summary, indent=2))
print('PASS 56 runs / 5600 queries / 56000 ordered neighbors; visit/rerank counts exact; bounded-heap overlay')
