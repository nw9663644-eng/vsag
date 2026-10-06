import csv
import math
from pathlib import Path

root = Path(__file__).resolve().parent / 'warm'
for repeat in [1, 2, 3]:
    lines = (root / f'warm-r{repeat}.log').read_text().splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith('mode,base_count'))
    row = next(csv.DictReader(lines[start:start + 2]))
    assert float(row['recall_at_k']) >= 0.95
    assert int(row['query_ef_search']) == 128 and int(row['warmup_rounds']) == 1
    with (root / f'warm-r{repeat}.snapshot.latencies.csv').open() as stream:
        samples = list(csv.DictReader(stream))
    assert len(samples) == 300 and [int(s['query']) for s in samples] == list(range(300))
    values = sorted(float(sample['latency_us']) for sample in samples)
    for fraction, field in [(0.5, 'search_p50_us'), (0.99, 'search_p99_us')]:
        assert abs(values[math.ceil(fraction * 300) - 1] - float(row[field])) < 0.000002
print('3 Full warm runs: quality, query options, 900 raw samples and percentiles verified')
