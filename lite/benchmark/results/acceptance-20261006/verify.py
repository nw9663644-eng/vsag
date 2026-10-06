# Consolidate recorded evidence; no experiment or tuning is performed.
import hashlib
import json
import re
import statistics
from pathlib import Path

root = Path(__file__).resolve().parents[1]
report = root.parent / 'ACCEPTANCE_REPORT_20261006.md'
checked = {}
for name in ['sift-matched-20261006', 'cohere-matched-20261006',
             'mixed-20261006', 'full-reverse-20261006', 'load-memory-20261006']:
    directory = root / name
    manifest = directory / 'SHA256SUMS'
    if manifest.exists():
        hashes = dict((line.split(maxsplit=1)[1].lstrip('*'), line.split()[0])
                      for line in manifest.read_text().splitlines() if line.strip())
    else:
        hashes = json.loads((directory / 'sha256.json').read_text())
    for path, digest in hashes.items():
        assert hashlib.sha256((directory / path).read_bytes()).hexdigest() == digest, path
    checked[name] = len(hashes)

text = report.read_text()
for target in re.findall(r'\]\(([^)]+)\)', text):
    assert (report.parent / target).is_file(), target

rows = []
sift = json.loads((root / 'sift-matched-20261006/summary.json').read_text())
cohere = json.loads((root / 'cohere-matched-20261006/final-summary.json').read_text())
gist = json.loads((root / 'mixed-20261006/aggregate.json').read_text())
for dataset, source in [('SIFT', sift), ('Cohere', cohere), ('GIST', gist)]:
    for cadence in ([10] if dataset == 'GIST' else [1, 10]):
        values = {}
        for mode in ['default', 'diverse']:
            selected = [x for x in source if x['mode'] == mode and int(x['query_every']) == cadence]
            assert selected
            metrics = [x['after'] if dataset == 'Cohere' else x for x in selected]
            key = 'mixed_loop_cpu_ms'
            values[mode] = statistics.median(float(x[key]['median'] if dataset == 'SIFT' else x[key]) for x in metrics)
            for x in metrics:
                recall = x['recall_at_k']['min'] if dataset == 'SIFT' else float(x['recall_at_k'])
                assert recall >= (0.90 if dataset == 'GIST' else 0.95)
            assert f"{values[mode]:.3f}" in text
        change = 100 * (values['diverse'] / values['default'] - 1)
        assert f'{change:+.2f}%' in text or f'{change:.2f}%' in text
        rows.append(dict(dataset=dataset, query_every=cadence, cpu_ms=values, change_percent=change))
full = json.loads((root / 'full-reverse-20261006/summary.json').read_text())
assert len(full) == 6 and all(x['quality_pass'] and x['short_query_events'] == 0 for x in full)
for cadence in [1, 10]:
    value = statistics.median(float(x['after']['mixed_loop_cpu_ms']) for x in full if int(x['after']['query_every']) == cadence)
    assert f'{value:.3f}' in text
memory = json.loads((root / 'load-memory-20261006/summary.json').read_text())
for mode in ['full', 'default', 'diverse']:
    selected = [x for x in memory if x['mode'] == mode]
    assert len(selected) == 7
    for key in ['load_ms', 'loaded_rss_kib', 'process_peak_rss_kib']:
        value = statistics.median(float(x[key]) for x in selected)
        assert (f'{value:.3f}' if key == 'load_ms' else str(int(value))) in text
output = dict(scope='Existing summaries and manifests, not a new raw-data audit', hashes_verified=checked, workload_summary=rows, report_sha256=hashlib.sha256(report.read_bytes()).hexdigest())
(root / 'acceptance-20261006/audit.json').write_text(json.dumps(output, indent=2) + '\n')
print(json.dumps(output, indent=2))
