"""Audit published load-only samples, commands, provenance and hashes."""
import csv
import hashlib
import json
import statistics
from pathlib import Path

root = Path(__file__).resolve().parent
rows = json.loads((root / 'summary.json').read_text())
commands = json.loads((root / 'commands.json').read_text())
protocol = json.loads((root / 'protocol.json').read_text())
metrics = json.loads((root / 'audit.json').read_text())
assert len(rows) == len(commands) == 28
for mode in ['full', 'full_reverse', 'default', 'diverse']:
    selected = [x for x in rows if x['mode'] == mode]
    assert len(selected) == 7 and {x['repeat'] for x in selected} == set(range(7))
    for row in selected:
        raw = next(csv.DictReader((root / f"{mode}-rep{row['repeat']}.csv").open()))
        assert all(raw[k] == row[k] for k in raw)
        assert int(row['count']) == 100000 and int(row['dim']) == 768
        assert row['page_cache_control'] == 'warm_uncontrolled'
        assert int(row['process_peak_rss_kib']) >= int(row['loaded_rss_kib']) > 0
    for key, summary in metrics[mode].items():
        values = [float(x[key]) for x in selected]
        assert summary == dict(median=statistics.median(values), min=min(values), max=max(values))
for repeat in range(7):
    order = ['full', 'full_reverse', 'default', 'diverse']
    order = order[repeat % 4:] + order[:repeat % 4]
    assert [x['mode'] for x in rows[repeat * 4:repeat * 4 + 4]] == order
    for mode, cmd in zip(order, commands[repeat * 4:repeat * 4 + 4]):
        assert cmd[:3] == ['taskset', '-c', '0']
        assert cmd[3:6] == [protocol['configs'][mode]['binary'], protocol['configs'][mode]['snapshot'], '768']
        assert cmd[6] == '100000'
        assert (cmd[-1] == 'force-remove') == (mode == 'full_reverse')
for name, expected in json.loads((root / 'sha256.json').read_text()).items():
    assert hashlib.sha256((root / name).read_bytes()).hexdigest() == expected, name
print('28 fresh-process samples, rotated commands, profiles, summary statistics and publication hashes verified.')
