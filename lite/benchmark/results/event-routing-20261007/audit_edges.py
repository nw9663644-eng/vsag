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

import math
removed=read(root/'cycle-3000-remove.snapshot');added=read(root/'cycle-3000-add.snapshot');control=read(root/'cycle-3000-single-edge-6727-1707.snapshot')
assert control['ids']==added['ids'] and control['vectors']==added['vectors']
changed=[id for id in added['ids'] if control['edges'][id]!=added['edges'][id]]
assert changed==[6727]
old=added['edges'][6727];new=control['edges'][6727]
assert len(old)==len(new)==16 and sum(x!=y for x,y in zip(old,new))==1
assert set(old)-set(new)=={3000} and set(new)-set(old)=={1707}
def distance(a,b):
 x=struct.unpack('<768f',added['vectors'][a]);y=struct.unpack('<768f',added['vectors'][b]);return math.fsum((u-v)**2 for u,v in zip(x,y))
result=dict(only_changed_source=changed,row_length=16,only_replaced_edge=[6727,3000,1707],
 incoming_1707_removed=sum(1707 in row for row in removed['edges'].values()),incoming_1707_added=sum(1707 in row for row in added['edges'].values()),incoming_3000_added=sum(3000 in row for row in added['edges'].values()),incoming_3000_control=sum(3000 in row for row in control['edges'].values()),double_scalar_distance_6727_1707=distance(6727,1707),double_scalar_distance_6727_3000=distance(6727,3000))
(root/'edge-audit.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.glob('*.snapshot'))}
for p in [root/'replay',root/'inspect',root/'replay.cpp',root/'inspect.cpp',Path('build-lite-fragment-release/libvsag-lite.so'),Path('build-lite-fragment-release/lite_graph_route_probe'),Path('lite/benchmark/graph_route_probe.cpp'),Path('lite/benchmark/graph_mutation_trace.cpp')]:hashes[str(p.resolve())]=hashlib.sha256(p.read_bytes()).hexdigest()
for p in sorted(root.glob('query-*/*')):hashes[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
(root/'host-hashes.json').write_text(json.dumps(hashes,indent=2)+'\n')
