"""Exercise Full benchmark query options using an exact small fixture."""
import csv
import math
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

binary = str(Path(sys.argv[1]).resolve())
with tempfile.TemporaryDirectory() as temporary:
    root = Path(temporary)
    def vectors(path, rows):
        with path.open('wb') as stream:
            for value in rows:
                vector = [0.0] * 128
                vector[int(value)] = 1.0
                stream.write(struct.pack('<i128f', 128, *vector))
    vectors(root / 'base.fvecs', range(8))
    queries = list(range(8))
    vectors(root / 'queries.fvecs', queries)
    with (root / 'groundtruth.ivecs').open('wb') as stream:
        for query in queries:
            stream.write(struct.pack('<ii', 1, query))
    for name, args, warmup in [('legacy', [], 0), ('warm', ['256', '1'], 1)]:
        snapshot = root / (name + '.bin')
        result = subprocess.run([binary, str(root), str(snapshot), 'fp32', *args],
                                capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
        lines = result.stdout.splitlines()
        header = next(i for i, line in enumerate(lines) if line.startswith('mode,base_count'))
        row = next(csv.DictReader(lines[header:header + 2]))
        assert float(row['recall_at_k']) == 1 and int(row['warmup_rounds']) == warmup, row
        assert int(row['query_ef_search']) == (128 if name == 'legacy' else 256) and float(row['query_loop_cpu_ms']) >= 0
        with Path(str(snapshot) + '.latencies.csv').open() as stream:
            timings = list(csv.DictReader(stream))
        assert len(timings) == 8 and [int(r['query']) for r in timings] == list(range(8))
        values = sorted(float(r['latency_us']) for r in timings)
        for fraction, field in [(0.5, 'search_p50_us'), (0.99, 'search_p99_us')]:
            assert abs(values[math.ceil(fraction * 8) - 1] - float(row[field])) < 0.000002
    for args in [['0'], ['128x'], ['-1'], ['128', '101'], ['128', '-1']]:
        snapshot = root / 'invalid.bin'
        result = subprocess.run([binary, str(root), str(snapshot), 'fp32', *args],
                                capture_output=True, text=True)
        assert result.returncode != 0 and not snapshot.exists()
print('Full legacy/explicit budget, warmup, exact truth, raw timings and invalid options passed')
