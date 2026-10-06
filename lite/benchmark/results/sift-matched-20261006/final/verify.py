import csv
import math
from pathlib import Path

root = Path(__file__).resolve().parent
for path in root.glob('*-every*-r*.csv.api.csv.crud.csv'):
    with path.open() as stream:
        row = next(csv.DictReader(stream))
    with Path(str(path) + '.mixed.csv').open() as stream:
        events = list(csv.DictReader(stream))
    with Path(str(path) + '.samples.csv').open() as stream:
        samples = list(csv.DictReader(stream))
    assert len(samples) == int(row['cycles']) == 2000
    assert len(events) == int(row['mixed_queries']) == 2000 // int(row['query_every'])
    values = sorted(float(event['latency_us']) for event in events)
    for fraction, field in [(0.5, 'mixed_search_p50_us'), (0.99, 'mixed_search_p99_us')]:
        assert abs(values[math.ceil(fraction * len(values)) - 1] - float(row[field])) < 0.000002
    assert float(row['recall_at_k']) >= 0.95
assert len(list(root.glob('*-every*-r*.csv.api.csv.crud.csv'))) == 12
print('12 runs: sample counts, quality floors and raw-latency percentiles verified')
