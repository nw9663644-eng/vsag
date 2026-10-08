"""Audit scored-old candidate activation, topology, and route mechanism."""
import csv
import hashlib
import io
import json
from pathlib import Path
import struct
import tarfile

ROOT = Path(__file__).resolve().parent
REPORTS = ROOT.parent

def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()

def unpack_archive(data):
    result = {}
    with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as bundle:
        for member in bundle.getmembers():
            assert member.isfile() and Path(member.name).name == member.name
            assert member.name not in result
            result[member.name] = bundle.extractfile(member).read()
    return result

def rows(data):
    return list(csv.DictReader(io.StringIO(data.decode())))

def topology(data, count=100000):
    result = []
    offset = 0
    for source in range(count):
        assert offset + 4 <= len(data)
        degree = struct.unpack_from('<I', data, offset)[0]
        offset += 4
        assert degree <= 16 and offset + 4 * degree <= len(data)
        row = list(struct.unpack_from('<' + 'I' * degree, data, offset))
        offset += 4 * degree
        assert len(row) == len(set(row)) and all(0 <= target < count and target != source for target in row)
        result.append(row)
    assert offset == len(data)
    return result

def reachability(graph, reverse=False):
    if reverse:
        edges = [[] for _ in graph]
        for source, row in enumerate(graph):
            for target in row:
                edges[target].append(source)
    else:
        edges = graph
    seen = bytearray(len(graph))
    seen[0] = 1
    stack = [0]
    while stack:
        source = stack.pop()
        for target in edges[source]:
            if not seen[target]:
                seen[target] = 1
                stack.append(target)
    return sum(seen)

def truth_sets(data):
    result = []
    offset = 0
    while offset < len(data):
        count = struct.unpack_from('<I', data, offset)[0]
        offset += 4
        assert count == 10
        result.append(set(struct.unpack_from('<10i', data, offset)))
        offset += 40
    return result

def phase_ids(data, phase='changed'):
    result = {}
    for row in rows(data):
        if row['phase'] == phase:
            result.setdefault(int(row['query']), set()).add(int(row['id']))
    return result

def main():
    manifest = json.loads((ROOT / 'manifest.json').read_text())
    for name, expected in manifest.items():
        assert Path(name).name == name and digest(ROOT / name) == expected
    raw = unpack_archive((ROOT / 'raw.tar.gz').read_bytes())
    members = json.loads((ROOT / 'members.json').read_text())
    assert raw.keys() == members.keys()
    for name, expected in members.items():
        assert hashlib.sha256(raw[name]).hexdigest() == expected

    previous = {}
    evidence = json.loads(raw['previous-evidence.json'])
    for report, hashes in evidence.items():
        folder = REPORTS / report
        for name, expected in hashes.items():
            assert digest(folder / name) == expected
        previous[report] = unpack_archive((folder / 'raw.tar.gz').read_bytes())
    scored = previous['scored-old-candidates-20261008']
    update = previous['update-trace-20261008']
    restoration = previous['restoration-validation-20261008']

    builds = json.loads(raw['build-receipts.json'])
    source_hash = hashlib.sha256(raw['graph_backend.cpp']).hexdigest()
    assert {item['variant'] for item in builds} == {'release', 'asan'}
    for item in builds:
        assert item['source_sha256'] == source_hash
        assert '-DVSAG_LITE_EXPERIMENT_SCORED_OLD_UPDATE' in item['compile']
        assert raw[item['variant'] + '-fixture.log'].decode().strip() == 'Scored-old Update fixtures passed'
        assert raw[item['variant'] + '-baseline-fixture.log'].decode().strip() == 'Scored-old Update fixtures passed'
        assert 'All tests passed (545120 assertions in 14 test cases)' in raw[item['variant'] + '-existing-tests.log'].decode()
    assert raw['format.log'] == b'' and 'error:' not in raw['tidy.log'].decode()
    patch = raw['diagnostic.patch'].decode()
    assert 'VSAG_LITE_SCORED_OLD_TRACE' in patch and 'selected_total' in patch

    expected_activation = {
        'coordinate-sift': (10000, 391, 1101, 1000),
        'coordinate-cohere': (10000, 1159, 2638, 2436),
        'coordinate-gist': (10000, 3460, 9436, 8315),
        'whole-sift': (1000, 75, 107, 104),
        'whole-cohere': (1000, 148, 256, 239),
        'whole-gist': (1000, 146, 198, 190),
    }
    activation = {}
    runs = json.loads(raw['runs-v3.json'])
    assert len(runs) == 6 and all(item['exit'] == 0 and item['neighbors_match_previous'] for item in runs)
    for stem, expected in expected_activation.items():
        event_rows = rows(raw[stem + '-v3.events.csv'])
        assert all(None not in row for row in event_rows)
        summaries = [row for row in event_rows if row['type'] == 'summary']
        candidates = [row for row in event_rows if row['type'] == 'candidate']
        selected = [row for row in candidates if row['selected'] == '1']
        cycles, active, qualified, kept = expected
        assert len(summaries) == cycles
        assert [int(row['sequence']) for row in summaries] == list(range(cycles))
        assert all(int(row['slot']) == i * 8191 % 100000 for i, row in enumerate(summaries))
        assert sum(int(row['qualified']) > 0 for row in summaries) == active
        assert sum(int(row['selected_total']) > 0 for row in summaries) == active
        assert sum(int(row['qualified']) for row in summaries) == len(candidates) == qualified
        assert sum(int(row['selected_total']) for row in summaries) == len(selected) == kept
        assert all(0 <= int(row['rank']) < 16 for row in selected)
        protocol, dataset = stem.split('-', 1)
        assert raw[stem + '-v3.csv.neighbors.csv'] == scored[stem + '-candidate-0.csv.neighbors.csv']
        activation[stem] = {
            'updates': cycles,
            'qualified_updates': active,
            'qualified_candidates': qualified,
            'selected_candidates': kept,
            'selected_update_rate': active / cycles,
            'mean_examined': sum(int(row['examined']) for row in summaries) / cycles,
        }
    assert activation == json.loads(raw['activation.json'])

    baseline = topology(update['baseline.csv.final-edges.csv.u32'])
    candidate = topology(raw['coordinate-gist-candidate-final.u32'])
    updated = {cycle * 8191 % 100000 for cycle in range(10000)}
    changed_ordered = []
    changed_set = []
    removed = 0
    added = 0
    categories = {}
    def bump(key):
        categories[key] = categories.get(key, 0) + 1
    for source, (old, new) in enumerate(zip(baseline, candidate)):
        if old != new:
            changed_ordered.append(source)
        old_set, new_set = set(old), set(new)
        if old_set != new_set:
            changed_set.append(source)
        for target in old_set - new_set:
            removed += 1
            bump('removed_source_updated' if source in updated else 'removed_source_other')
            bump('removed_target_updated' if target in updated else 'removed_target_other')
        for target in new_set - old_set:
            added += 1
            bump('added_source_updated' if source in updated else 'added_source_other')
            bump('added_target_updated' if target in updated else 'added_target_other')
    incoming = []
    for graph in [baseline, candidate]:
        counts = [0] * 100000
        for row in graph:
            for target in row:
                counts[target] += 1
        incoming.append(counts)

    selected_events = [row for row in rows(raw['coordinate-gist-v3.events.csv'])
                       if row['type'] == 'candidate' and row['selected'] == '1']
    survive = sum(int(row['candidate']) in candidate[int(row['slot'])] for row in selected_events)
    absent_baseline = sum(int(row['candidate']) not in baseline[int(row['slot'])] for row in selected_events)
    survive_distinct = sum(int(row['candidate']) in candidate[int(row['slot'])] and
                           int(row['candidate']) not in baseline[int(row['slot'])]
                           for row in selected_events)

    baseline_route_rows = rows(restoration['gist-supplement-baseline-0.csv'])
    baseline_route = {int(row['query']): row for row in baseline_route_rows if int(row['mask']) == 0}
    candidate_route = [row for row in rows(raw['coordinate-gist-trace.csv.routes.csv'])
                       if row['phase'] == 'maintained']
    assert len(baseline_route) == len(candidate_route) == 300
    route_delta = []
    for row in candidate_route:
        query = int(row['query'])
        old = baseline_route[query]
        route_delta.append({
            'hits': int(row['hits']) - int(old['hits']),
            'truth_visited': int(row['visited_truth']) - int(old['truth_visited']),
            'visited_nodes': int(row['visited_nodes']) - int(old['visited_nodes']),
            'expanded': int(row['expanded']) - int(old['expanded_nodes']),
        })
    truth = truth_sets(scored['input-coordinate-gist-changed-groundtruth.ivecs'])
    baseline_ids = phase_ids(scored['coordinate-gist-baseline-0.csv.neighbors.csv'])
    candidate_ids = phase_ids(raw['coordinate-gist-trace.csv.neighbors.csv'])
    assert candidate_ids == phase_ids(scored['coordinate-gist-candidate-0.csv.neighbors.csv'])
    route_truth = {}
    for row in rows(raw['coordinate-gist-trace.csv.route-truth.csv']):
        if row['phase'] == 'maintained':
            route_truth[int(row['query']), int(row['id'])] = (int(row['visited']), int(row['returned']))
    lost = []
    gained = []
    for query in range(300):
        lost += [(query, item, route_truth[query, item][0])
                 for item in (baseline_ids[query] - candidate_ids[query]) & truth[query]]
        gained += [(query, item, route_truth[query, item][0])
                   for item in (candidate_ids[query] - baseline_ids[query]) & truth[query]]
    analysis = {
        'baseline_edges': sum(map(len, baseline)),
        'candidate_edges': sum(map(len, candidate)),
        'changed_ordered_sources': len(changed_ordered),
        'changed_neighbor_set_sources': len(changed_set),
        'changed_set_updated_sources': sum(source in updated for source in changed_set),
        'changed_set_other_sources': sum(source not in updated for source in changed_set),
        'removed_edges': removed, 'added_edges': added, 'edge_categories': categories,
        'zero_incoming_baseline': sum(value == 0 for value in incoming[0]),
        'zero_incoming_candidate': sum(value == 0 for value in incoming[1]),
        'incoming_changed_nodes': sum(a != b for a, b in zip(*incoming)),
        'incoming_delta_sum_abs': sum(abs(a - b) for a, b in zip(*incoming)),
        'forward_reachable_from_zero_baseline': reachability(baseline),
        'forward_reachable_from_zero_candidate': reachability(candidate),
        'reverse_reachable_to_zero_baseline': reachability(baseline, True),
        'reverse_reachable_to_zero_candidate': reachability(candidate, True),
        'immediate_selected_edges': len(selected_events),
        'selection_sources': len({int(row['slot']) for row in selected_events}),
        'selected_edges_surviving_final': survive,
        'selected_edges_absent_baseline_final': absent_baseline,
        'selected_edges_surviving_and_distinct_final': survive_distinct,
        'route_net_hits': sum(row['hits'] for row in route_delta),
        'route_query_wins': sum(row['hits'] > 0 for row in route_delta),
        'route_query_losses': sum(row['hits'] < 0 for row in route_delta),
        'route_query_ties': sum(row['hits'] == 0 for row in route_delta),
        'mean_visited_nodes_delta': sum(row['visited_nodes'] for row in route_delta) / 300,
        'mean_expanded_delta': sum(row['expanded'] for row in route_delta) / 300,
        'net_truth_visited_delta': sum(row['truth_visited'] for row in route_delta),
        'lost_truth_ids': len(lost),
        'lost_truth_unvisited_candidate': sum(visited == 0 for _, _, visited in lost),
        'gained_truth_ids': len(gained),
        'gained_truth_visited_candidate': sum(visited == 1 for _, _, visited in gained),
    }
    assert analysis == json.loads(raw['analysis.json'])
    print(json.dumps({'pass_checks': True, 'activation': activation,
                      'gist_coordinate_mechanism': analysis,
                      'decision': 'distance-only reuse changes routing coverage; test diversity/connectivity gate'}, indent=2))

if __name__ == '__main__':
    main()
