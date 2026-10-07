"""Event-specific topology/slot-order controls; not a graph policy candidate."""
from pathlib import Path
import csv, hashlib, json, struct, subprocess
root = Path(__file__).resolve().parent

def read(path):
    data = path.read_bytes()
    assert data[:8] == b'VSAGLT01'
    version, dim, count, payload, kind, degree, ef = struct.unpack_from('<7Q', data, 8)
    assert version == kind == 2 and payload + 48 == len(data)
    ids = list(struct.unpack_from(f'<{count}q', data, 64))
    assert len(set(ids)) == count
    offset = 64 + count * 8
    vectors = {id: data[offset + i * dim * 4:offset + (i + 1) * dim * 4] for i, id in enumerate(ids)}
    offset += count * dim * 4
    edges = {}
    for i, id in enumerate(ids):
        n = struct.unpack_from('<Q', data, offset)[0]; offset += 8
        row = struct.unpack_from(f'<{n}Q', data, offset); offset += n * 8
        assert n <= degree and all(x < count and x != i for x in row) and len(set(row)) == n
        edges[id] = [ids[x] for x in row]
    assert offset == len(data)
    return dict(dim=dim, degree=degree, ef=ef, ids=ids, vectors=vectors, edges=edges)

def write(graph, ids, edges, target):
    assert not target.exists() and len(set(ids)) == len(ids)
    slots = {id: slot for slot, id in enumerate(ids)}
    links = {id: [x for x in edges[id] if x in slots] for id in ids}
    assert all(len(row) <= graph['degree'] and len(set(row)) == len(row) and id not in row for id, row in links.items())
    count = len(ids); dim = graph['dim']
    payload = 16 + count * (16 + dim * 4) + 8 * sum(map(len, links.values()))
    parts = [b'VSAGLT01', struct.pack('<7Q', 2, dim, count, payload, 2, graph['degree'], graph['ef']),
             struct.pack(f'<{count}q', *ids), b''.join(graph['vectors'][id] for id in ids)]
    for id in ids:
        row = links[id]
        parts.extend([struct.pack('<Q', len(row)), struct.pack(f'<{len(row)}Q', *(slots[x] for x in row))])
    target.write_bytes(b''.join(parts))
    checked = read(target)
    assert checked['ids'] == ids and checked['edges'] == links
    assert checked['vectors'] == {id: graph['vectors'][id] for id in ids}
    return dict(path=str(target), sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
                vector_bytes_equal_by_id=True, ordered_edges_equal_to_requested=True,
                count=count, edges=sum(map(len, links.values())))

receipts = []; commands = []; changed = []
for cycle, query, deleted in [(1099, 99, 1909), (3000, 0, 3000), (7112, 12, 4392)]:
    stages = {phase: read(root / f'cycle-{cycle}-{phase}.snapshot') for phase in ['before','remove','add']}
    before, removed, added = [stages[x] for x in ['before','remove','add']]
    assert before['vectors'] == added['vectors']
    assert removed['vectors'] == {id: v for id, v in before['vectors'].items() if id != deleted}
    for left, right in [('before','remove'), ('remove','add')]:
        a = {(s,t) for s,row in stages[left]['edges'].items() for t in row if s != deleted and t != deleted}
        b = {(s,t) for s,row in stages[right]['edges'].items() for t in row if s != deleted and t != deleted}
        for action, pairs in [('dropped',a-b),('added',b-a)]:
            changed.extend(dict(cycle=cycle,phase=right,action=action,source=s,target=t) for s,t in sorted(pairs))
    if cycle == 1099:
        original_order = [id for id in before['ids'] if id != deleted]
        cases = [('remove-original-order', removed, original_order, removed['edges']),
                 ('remove-detached', removed, removed['ids'], before['edges']),
                 ('remove-detached-original-order', removed, original_order, before['edges'])]
    else:
        cases = [('add-original-order', added, before['ids'], added['edges']),
                 ('add-original-topology', added, added['ids'], before['edges'])]
    for name, graph, ids, edges in cases:
        stem = f'cycle-{cycle}-{name}'; path = root / f'{stem}.snapshot'
        receipts.append(write(graph, ids, edges, path))
        cmd = ['taskset','-c','0','build-lite-fragment-release/lite_graph_route_probe',str(path),str(root/f'query-{query}'),str(root/f'{stem}.csv'),'128','uniform','preserve','1']
        result = subprocess.run(cmd,capture_output=True)
        (root/f'{stem}.stdout.csv').write_bytes(result.stdout); (root/f'{stem}.stderr.log').write_bytes(result.stderr)
        commands.append(dict(command=cmd,exit=result.returncode)); assert result.returncode == 0, result.stderr
        print(stem, (root/f'{stem}.csv').read_text().splitlines()[-1],flush=True)
with (root/'changed-survivor-edges.csv').open('w') as f:
    writer = csv.DictWriter(f,fieldnames=['cycle','phase','action','source','target']); writer.writeheader(); writer.writerows(changed)
(root/'control-receipts.json').write_text(json.dumps(receipts,indent=2)+'\n')
(root/'control-commands.json').write_text(json.dumps(commands,indent=2)+'\n')
