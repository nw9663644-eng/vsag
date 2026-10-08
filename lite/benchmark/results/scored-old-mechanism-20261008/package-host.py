from pathlib import Path
import hashlib
import json
import shutil
import tarfile

HOST = Path(__file__).resolve().parent
REPO = Path('/home/ubuntu/project/vsag-lite-baseline-v01')
OUT = REPO / 'lite/benchmark/results/scored-old-mechanism-20261008'

def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()

OUT.mkdir(parents=True, exist_ok=False)
items = {}
def add(path, name=None):
    path = Path(path)
    name = name or path.name
    assert path.is_file() and name not in items, (path, name)
    items[name] = path

for name in ['activation.json', 'analysis.json', 'runs-v3.json', 'trace-receipt.json',
             'previous-evidence.json', 'build-receipts.json', 'graph_backend.cpp',
             'fixture.cpp', 'diagnostic.patch', 'format.log', 'tidy.log',
             'coordinate-gist-candidate-final.u32']:
    add(HOST / name)
for variant in ['release', 'asan']:
    for name in ['build.log', 'fixture.log', 'baseline-fixture.log', 'existing-tests.log']:
        add(HOST / variant / name, variant + '-' + name)
for path in sorted(HOST.glob('*-v3.events.csv')):
    stem = path.name.removesuffix('.events.csv')
    for suffix in ['.events.csv', '.csv', '.csv.neighbors.csv', '.csv.updates.csv', '.log']:
        add(HOST / (stem + suffix))
for name in ['coordinate-gist-trace.csv', 'coordinate-gist-trace.csv.neighbors.csv',
             'coordinate-gist-trace.csv.updates.csv', 'coordinate-gist-trace.csv.routes.csv',
             'coordinate-gist-trace.csv.route-truth.csv',
             'coordinate-gist-trace.csv.trace-neighbors.csv',
             'coordinate-gist-trace.log']:
    add(HOST / name)
members = {name: sha(path) for name, path in sorted(items.items())}
with tarfile.open(OUT / 'raw.tar.gz', 'w:gz', compresslevel=9) as bundle:
    for name, path in sorted(items.items()):
        bundle.add(path, arcname=name)
(OUT / 'members.json').write_text(json.dumps(members, indent=2) + '\n')
for source, target in [('README.md', 'README.md'), ('verify.py', 'verify.py'),
                       ('package.py', 'package-host.py'), ('diagnostic.patch', 'diagnostic.patch')]:
    shutil.copyfile(HOST / source, OUT / target)
print(OUT)
