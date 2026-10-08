from pathlib import Path
import hashlib
import json
import shutil
import tarfile

HOST = Path(__file__).resolve().parent
REPO = Path('/home/ubuntu/project/vsag-lite-baseline-v01')
OUT = REPO / 'lite/benchmark/results/scored-old-candidates-20261008'
WHOLE = Path('/home/ubuntu/project/vsag-lite-whole-vector-20261008')

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
    assert name not in items and path.is_file(), (name, path)
    items[name] = path

for name in ['plan.json', 'identity.json', 'cohorts.json', 'runs.json', 'run.log',
             'candidate.patch', 'graph_backend.cpp', 'fixture.cpp', 'build.py',
             'build-receipts.json']:
    add(HOST / name, 'candidate-graph_backend.cpp' if name == 'graph_backend.cpp' else name)
add(REPO / 'src/lite/graph_backend.cpp', 'parent-graph_backend.cpp')
for variant in ['release', 'asan']:
    for name in ['build.log', 'fixture.log', 'baseline-fixture.log', 'existing-tests.log']:
        add(HOST / variant / name, variant + '-' + name)
for path in sorted(HOST.glob('coordinate-*.csv*')) + sorted(HOST.glob('whole-*.csv*')):
    add(path)
for path in sorted(HOST.glob('*.log')):
    if path.name != 'run.log':
        add(path)
for protocol in ['coordinate', 'whole']:
    for dataset in ['sift', 'cohere', 'gist']:
        folder = HOST / ('coordinate-' + dataset) if protocol == 'coordinate' else WHOLE / dataset
        for name in ['queries.fvecs', 'groundtruth.ivecs', 'changed-groundtruth.ivecs']:
            add(folder / name, f'input-{protocol}-{dataset}-{name}')
members = {name: sha(path) for name, path in sorted(items.items())}
with tarfile.open(OUT / 'raw.tar.gz', 'w:gz', compresslevel=9) as archive:
    for name, path in sorted(items.items()):
        archive.add(path, arcname=name)
(OUT / 'members.json').write_text(json.dumps(members, indent=2) + '\n')
for source, target in [('verify.py', 'verify.py'), ('package.py', 'package-host.py'),
                       ('run.py', 'run-host.py'), ('build.py', 'build-host.py'),
                       ('candidate.patch', 'candidate.patch'), ('README.md', 'README.md')]:
    shutil.copyfile(HOST / source, OUT / target)
print(OUT)
