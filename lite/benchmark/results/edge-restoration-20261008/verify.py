"""Audit restoration factors, reference agreement and changed-vector distances."""
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import struct
import tarfile

ROOT = Path(__file__).resolve().parent

def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1048576), b''):
            h.update(block)
    return h.hexdigest()

def archive(path):
    result = {}
    with tarfile.open(path, 'r:gz') as tar:
        for m in tar.getmembers():
            assert m.isfile() and Path(m.name).name == m.name and m.name not in result
            result[m.name] = tar.extractfile(m).read()
    return result

def main():
    for name, value in json.loads((ROOT / 'manifest.json').read_text()).items():
        assert Path(name).name == name and digest(ROOT / name) == value
    raw = archive(ROOT / 'raw.tar.gz')
    members = json.loads((ROOT / 'members.json').read_text())
    assert raw.keys() == members.keys()
    for name, value in members.items():
        assert hashlib.sha256(raw[name]).hexdigest() == value
    previous = ROOT.parent / 'update-trace-20261008'
    for name, value in json.loads(raw['previous-evidence.json']).items():
        assert digest(previous / name) == value
    old = archive(previous / 'raw.tar.gz')
    info = json.loads(raw['prepared.json']); assert info == json.loads(old['prepared.json'])
    count, dim, cycles = info['count'], info['dim'], info['cycles']
    assert (count, dim, cycles) == (100000, 960, 10000)
    assert raw['queries.fvecs'] == old['queries.fvecs']
    assert raw['groundtruth.ivecs'] == old['changed-groundtruth.ivecs']
    rows = lambda data: list(csv.DictReader(io.StringIO(data.decode())))
    def topology(data):
        links = []; offset = 0
        for a in range(count):
            n = struct.unpack_from('<I', data, offset)[0]; offset += 4
            assert n <= 16
            row = struct.unpack_from('<' + 'I' * n, data, offset); offset += 4 * n
            assert len(set(row)) == n and all(0 <= b < count and b != a for b in row)
            links.append(row)
        assert offset == len(data)
        return links
    initial = topology(old['initial-edges.csv.u32'])
    maintained = {v:topology(old[v + '.csv.final-edges.csv.u32']) for v in ['baseline','candidate']}
    updated = {c * 8191 % count for c in range(cycles)}
    queries = [struct.unpack_from('<' + 'f' * dim, raw['queries.fvecs'], q * (4 + 4 * dim) + 4) for q in range(100)]
    truths = [set(struct.unpack_from('<10i', raw['groundtruth.ivecs'], q * 44 + 4)) for q in range(100)]
    assert all(len(t) == 10 for t in truths)
    snapshot = Path(info['snapshot']); host = snapshot.is_file()
    if host:
        assert digest(snapshot) == info['snapshot_sha256']
    identity = json.loads(raw['identity.json']); source_available = all(Path(p).is_file() for p in identity['files'])
    if source_available:
        for p, value in identity['files'].items():
            assert digest(Path(p)) == value, p
    runs = json.loads(raw['runs.json'])
    assert len(runs) == 8 and all(r['exit'] == 0 for r in runs)
    assert {(r['variant'],r['mask']) for r in runs} == {(v,m) for v in ['baseline','candidate'] for m in range(4)}
    summaries = []; all_hits = {}; all_ids = {}; full_hashes = []; distance_checks = 0
    for variant in ['baseline','candidate']:
        reference = rows(old[variant + '.csv.trace-neighbors.csv'])
        for mask in range(4):
            name = variant + '-' + str(mask) + '.csv'
            receipt = json.loads(raw[name + '.receipt.json'])
            assert (receipt['mask'], receipt['cycles'], receipt['count'], receipt['dim'], receipt['max_degree'], receipt['ef_search'], receipt['exit']) == (mask,cycles,count,dim,16,128,0)
            assert receipt['input_snapshot_sha256'] == info['snapshot_sha256']
            edge_name = variant + '.csv.final-edges.csv.u32'
            assert receipt['adjacency_sha256'] == hashlib.sha256(old[edge_name]).hexdigest()
            assert receipt['binary_sha256'] == identity['files'][next(p for p in identity['files'] if p.endswith('/lite_graph_slot_probe'))]
            chosen = [initial[a] if mask & (1 if a in updated else 2) else maintained[variant][a] for a in range(count)]
            assert receipt['restored_rows'] == (10000 * bool(mask & 1) + 90000 * bool(mask & 2))
            edge_count = sum(map(len, chosen)); assert receipt['explicit_edges'] == edge_count
            if host:
                h = hashlib.sha256()
                with snapshot.open('rb') as source:
                    magic = source.read(8); fields = list(struct.unpack('<7Q',source.read(56)))
                    assert magic == b'VSAGLT01' and (fields[0],fields[1],fields[2],fields[4],fields[5],fields[6]) == (2,dim,count,2,16,128)
                    fields[3] = 16 + 16 * count + 4 * count * dim + 8 * edge_count
                    h.update(magic + struct.pack('<7Q',*fields)); h.update(source.read(8 * count))
                    for first in range(0,count,256):
                        n = min(256,count-first); data = bytearray(source.read(n * dim * 4)); assert len(data) == n * dim * 4
                        for a in range(first,first+n):
                            if a in updated:
                                offset = (a-first)*dim*4
                                value = struct.unpack_from('<f',data,offset)[0]
                                struct.pack_into('<f',data,offset,value+0.125)
                        h.update(data)
                    for row in chosen:
                        h.update(struct.pack('<Q',len(row)))
                        h.update(struct.pack('<'+'Q'*len(row),*row))
                assert h.hexdigest() == receipt['control_sha256'], name
            if mask == 3:
                full_hashes.append(receipt['control_sha256'])
            states = rows(raw[name]); neighbors = rows(raw[name + '.neighbors.csv'])
            assert len(states) == 800 and len(neighbors) == 8000
            primary_ids = []; hits = []; vectors = {}; source = snapshot.open('rb') if host else None
            for q in range(100):
                primary = []
                for slot_mask in range(8):
                    state = states[q * 8 + slot_mask]
                    assert int(state['query']) == q and int(state['mask']) == slot_mask and state['eligible'] == '1' and state['k'] == '10'
                    assert state['baseline_native_ids_equal'] == ('1' if slot_mask == 0 else '0')
                    group = neighbors[(q*8+slot_mask)*10:(q*8+slot_mask+1)*10]
                    keys = []
                    for rank, row in enumerate(group):
                        assert (int(row['query']),int(row['mask']),int(row['rank'])) == (q,slot_mask,rank)
                        identifier,distance = int(row['id']),float.fromhex(row['distance'])
                        assert 0 <= identifier < count and math.isfinite(distance) and distance >= 0
                        keys.append((distance,identifier))
                        if source and slot_mask == 0:
                            if identifier not in vectors:
                                source.seek(64+8*count+4*dim*identifier); vector = list(struct.unpack('<'+'f'*dim,source.read(4*dim)))
                                if identifier in updated:
                                    vector[0] = struct.unpack('<f',struct.pack('<f',vector[0]+0.125))[0]
                                vectors[identifier] = vector
                            exact = sum((float(a)-float(b))**2 for a,b in zip(queries[q],vectors[identifier]))
                            assert math.isclose(distance,exact,rel_tol=3e-6,abs_tol=1e-6)
                            distance_checks += 1
                    assert keys == sorted(keys) and len({i for _,i in keys}) == 10
                    if slot_mask == 0:
                        primary = keys; primary_ids.append({i for _,i in keys}); hits.append(len(primary_ids[-1]&truths[q]))
                    else:
                        assert keys == primary
                        assert all(state[k] == states[q*8][k] for k in ['hits','truth_visited','visited_nodes','expanded_nodes','distance_evaluations','tie_comparisons'])
                    assert int(state['hits']) == len({i for _,i in keys}&truths[q])
                    assert int(state['hits']) <= int(state['truth_visited']) <= 10
                    assert 0 < int(state['expanded_nodes']) <= int(state['visited_nodes']) <= count
                if mask in [0,3]:
                    ref = reference[(0 if mask==0 else 1000)+q*10:(0 if mask==0 else 1000)+(q+1)*10]
                    assert primary == [(float.fromhex(r['distance']),int(r['id'])) for r in ref]
            if source: source.close()
            all_hits[variant,mask] = hits; all_ids[variant,mask] = primary_ids
            summaries.append(dict(variant=variant,mask=mask,recall=sum(hits)/1000,explicit_edges=edge_count,
                                  mean_visited_nodes=sum(int(states[q*8]['visited_nodes']) for q in range(100))/100,
                                  visited_not_returned=sum(int(states[q*8]['truth_visited'])-hits[q] for q in range(100))))
    assert len(set(full_hashes)) == 1
    for result in summaries:
        v,m = result['variant'],result['mask']; delta = [b-a for a,b in zip(all_hits[v,0],all_hits[v,m])]
        result.update(net_hits=sum(delta),wins=sum(d>0 for d in delta),losses=sum(d<0 for d in delta),ties=sum(d==0 for d in delta),
                      gained_truth=sum(len((all_ids[v,m][q]-all_ids[v,0][q])&truths[q]) for q in range(100)),
                      lost_truth=sum(len((all_ids[v,0][q]-all_ids[v,m][q])&truths[q]) for q in range(100)))
    print(json.dumps(dict(pass_checks=True,host_snapshot_verified=host,host_sources_verified=source_available,
                          unique_factor_query_states=800,native_calibrations=800,slot_query_states=6400,
                          slot_factors_identical=True,distance_checks=distance_checks,results=summaries),indent=2))

if __name__ == '__main__':
    main()
