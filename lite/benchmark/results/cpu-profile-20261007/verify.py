"""Recompute phase attribution and counters from published raw exports."""
from pathlib import Path
import csv
import gzip
import hashlib
import json
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parent
manifest = json.loads((root / 'sha256.json').read_text())
for name, digest in manifest.items():
    assert hashlib.sha256((root / name).read_bytes()).hexdigest() == digest, name
raw_hashes = json.loads((root / 'raw-sha256.json').read_text())
with tempfile.TemporaryDirectory() as directory:
    target = Path(directory)
    for compressed in root.glob('*.stacks.txt.gz'):
        data = gzip.decompress(compressed.read_bytes())
        name = compressed.name[:-3]
        assert hashlib.sha256(data).hexdigest() == raw_hashes[name], name
        (target / name).write_bytes(data)
        for suffix in ['.self.txt', '.stdout.log', '.stderr.log']:
            companion = name.replace('.stacks.txt', suffix)
            (target / companion).write_bytes((root / companion).read_bytes())
    result = subprocess.run([sys.executable, str(root / 'analyze.py'), str(target)],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert json.loads((target / 'stack-summary.json').read_text()) == json.loads((root / 'stack-summary.json').read_text())
records = json.loads((root / 'stack-summary.json').read_text())
assert len(records) == 8 and sum(x['samples'] for x in records) == 7944
commands = json.loads((root / 'commands.json').read_text())
assert len(commands) == 8 and all(x['exit'] == 0 for x in commands)
for record in commands:
    cmd = record['command']
    assert cmd[:4] == ['sudo', '-n', 'perf', 'record']
    assert cmd[cmd.index('--') + 1:cmd.index('--') + 4] == ['taskset', '-c', '0']
    assert cmd[cmd.index('-F') + 1] == '199'
    assert cmd[cmd.index('-e') + 1] == 'cpu-clock:u'
    assert cmd[-2:] == (['0', '1'] if '-build-' in record['name'] else ['1', '10000'])
for row in json.loads((root / 'stat-summary.json').read_text()):
    counters = {}
    for line in (root / (row['name'] + '.stat.csv')).read_text().splitlines():
        if not line or line.startswith('#'):
            continue
        values = next(csv.reader([line]))
        counters[values[2]] = dict(value=float(values[0]), unit=values[1],
                                   enabled_percent=float(values[4]), derived=values[5:])
    assert counters == row['counters']
    assert all(x['enabled_percent'] == 100 for x in counters.values())
    assert 0.99 <= float(counters['task-clock']['derived'][0]) <= 1.01
for row in records:
    expected = 0.933 if row['name'].startswith('default-crud') else 0.960 if row['name'].startswith(('default-build', 'diverse-crud')) else 0.982
    assert float(row['quality']['recall_at_k']) == expected
print('8 stack exports / 7944 samples, lossless raw hashes, phase attribution, commands, counters and recall verified.')
