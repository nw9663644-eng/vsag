"""Check snapshot-load probe CLI and both API adapters with existing tiny snapshots."""
import csv
import io
from pathlib import Path
import subprocess
import sys
import tempfile

assert len(sys.argv) in (4, 5)
full, lite, fixtures = sys.argv[1:4]
for binary, name in [(full, 'full'), (lite, 'lite')]:
    snapshot = str(Path(fixtures) / (name + '-fixture.snapshot'))
    result = subprocess.run([binary, snapshot, '16', '8'], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    row = next(csv.DictReader(io.StringIO(result.stdout[result.stdout.index('dim,count,'):])))
    assert int(row['dim']) == 16 and int(row['count']) == 8
    assert int(row['snapshot_bytes']) == Path(snapshot).stat().st_size
    assert float(row['load_ms']) >= 0
    assert min(int(row[key]) for key in ['before_create_rss_kib', 'before_load_rss_kib',
                                       'loaded_rss_kib', 'process_peak_rss_kib']) > 0
    for dim, count in [('-1', '8'), ('16x', '8'), ('0', '8'), ('16', '0'),
                       ('16', '18446744073709551616'), ('16', '9')]:
        bad = subprocess.run([binary, snapshot, dim, count], capture_output=True)
        assert bad.returncode != 0, (binary, dim, count)
    assert subprocess.run([binary], capture_output=True).returncode != 0
    with tempfile.TemporaryDirectory() as tmp:
        missing = Path(tmp) / 'missing'
        assert subprocess.run([binary, str(missing), '16', '8'], capture_output=True).returncode != 0
        missing.write_bytes(b'corrupt')
        assert subprocess.run([binary, str(missing), '16', '8'], capture_output=True).returncode != 0
print('Full/Lite load, positive memory metrics, count mismatch, invalid CLI and corrupt/missing snapshot checks passed.')

# Optional reverse-edge Full profile; pass a separately created force snapshot.
if len(sys.argv) == 5:
    force_snapshot = sys.argv[4]
    for binary, snapshot, profile, success in [
        (full, str(Path(fixtures) / 'full-fixture.snapshot'), 'compressed', True),
        (full, force_snapshot, 'force-remove', True),
        (full, force_snapshot, 'compressed', False),
        (full, str(Path(fixtures) / 'full-fixture.snapshot'), 'force-remove', False),
        (lite, str(Path(fixtures) / 'lite-fixture.snapshot'), 'force-remove', False),
        (full, force_snapshot, 'unknown', False),
        (lite, str(Path(fixtures) / 'lite-fixture.snapshot'), 'unknown', False),
    ]:
        result = subprocess.run([binary, snapshot, '16', '8', profile],
                                capture_output=True, text=True)
        assert (result.returncode == 0) == success, (profile, result.stdout, result.stderr)
        if success:
            row = next(csv.DictReader(io.StringIO(result.stdout[result.stdout.index('dim,count,'):])))
            assert int(row['count']) == 8 and int(row['loaded_rss_kib']) > 0
    print('Optional Full reverse-edge profile, mismatch and invalid profile checks passed.')
