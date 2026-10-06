"""Exercise actual FORCE_REMOVE/readd and audit mixed sample accounting on tiny data."""
import csv
import io
import math
from pathlib import Path
import struct
import subprocess
import sys
import tempfile

binary = str(Path(sys.argv[1]).resolve())
with tempfile.TemporaryDirectory() as temporary:
    root = Path(temporary)
    data = root / 'data'
    data.mkdir()
    for name in ['base', 'queries']:
        with (data / (name + '.fvecs')).open('wb') as output:
            for row in range(8):
                output.write(struct.pack('<i16f', 16, *[float(i == row) for i in range(16)]))
    with (data / 'groundtruth.ivecs').open('wb') as output:
        for row in range(8):
            output.write(struct.pack('<ii', 1, row))
    def run(name, options):
        snapshot = root / name
        result = subprocess.run([binary, str(data), str(snapshot), *options],
                                capture_output=True, text=True)
        return snapshot, result
    for every in [1, 2]:
        snapshot, result = run('mixed' + str(every), ['fp32', '128', '1', '4', str(every)])
        assert result.returncode == 0, result.stderr + result.stdout
        summary = next(csv.DictReader(Path(str(snapshot) + '.crud.csv').open()))
        mutations = list(csv.DictReader(Path(str(snapshot) + '.crud.samples.csv').open()))
        queries = list(csv.DictReader(Path(str(snapshot) + '.mixed.csv').open()))
        assert len(mutations) == 4 and len(queries) == 4 // every
        assert [int(row['cycle']) for row in mutations] == list(range(4))
        assert all(float(row[key]) >= 0 for row in mutations
                   for key in ['update_us', 'restore_us', 'remove_us', 'readd_us'])
        assert 0 <= float(summary['end_recall_at_k']) <= 1
        # FORCE_REMOVE may alter connectivity; a completed workload is not a quality pass.
        assert abs(float(summary['mixed_recall_at_k']) -
                   sum(int(row['hits']) for row in queries) / len(queries)) < 1e-6
        assert all(0 <= int(row['hits']) <= int(row['returned_count']) <= 1 for row in queries)
        assert [int(row['query']) for row in queries] == list(range(4 // every))
        latencies = sorted(float(row['latency_us']) for row in queries)
        for field, fraction in [('mixed_p50_us', .5), ('mixed_p99_us', .99)]:
            assert float(summary[field]) == latencies[max(1, math.ceil(len(latencies)*fraction))-1]
        assert int(summary['mixed_queries']) == len(queries)
        assert snapshot.is_file()
    snapshot, result = run('diagnostic', ['fp32', '128', '1', '4', '1', 'diagnose'])
    assert result.returncode == 0, result.stderr
    assert 'DIAGNOSTIC ONLY' in result.stderr
    diagnostic = list(csv.DictReader(Path(str(snapshot) + '.diagnostic.csv').open()))
    assert all(int(row['ef_search']) in [128, 512, 100000] for row in diagnostic)
    assert len(diagnostic) % 3 == 0
    assert all(0 <= int(row['hits']) <= int(row['returned_count']) <= 1 for row in diagnostic)
    snapshot, result = run('legacy', ['fp32', '128', '1'])
    assert result.returncode == 0, result.stderr
    row = next(csv.DictReader(io.StringIO(result.stdout[result.stdout.index('mode,base_count,'):])))
    assert float(row['recall_at_k']) == 1 and not Path(str(snapshot)+'.crud.csv').exists()
    invalid = [ ['fp32', '128', '1', '4'], ['fp32', '128', '1', '0', '1'],
                ['fp32', '128', '1', '4', '0'], ['fp32', '128', '1', '4', '5'],
                ['fp32', '128', '1', '4x', '1'], ['rabitq1', '128', '1', '4', '1'],
                ['fp32', '128', '1', '100001', '1'],
                ['fp32', '128', '1', '4', '1', 'other'] ]
    for i, options in enumerate(invalid):
        snapshot, result = run('invalid'+str(i), options)
        assert result.returncode != 0 and not snapshot.exists()
print('Full mixed: two cadences, four mutations, raw accounting, legacy path, diagnostic mode and eight invalid CLIs passed')
