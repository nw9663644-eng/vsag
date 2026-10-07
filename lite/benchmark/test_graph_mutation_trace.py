"""Check exclusion of deleted truth and external-ID edge invariance on an exact clique."""
import csv
import io
from pathlib import Path
import struct
import subprocess
import sys
import tempfile

trace, prepare = sys.argv[1:]
with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    records = b''.join(struct.pack('<i16f', 16, *[float(i == j) for j in range(16)]) for i in range(8))
    (root / 'base.fvecs').write_bytes(records)
    (root / 'queries.fvecs').write_bytes(records)
    (root / 'groundtruth.ivecs').write_bytes(b''.join(struct.pack('<ii', 1, i) for i in range(8)))
    snapshot = root / 'graph.snapshot'
    result = subprocess.run([prepare, str(root), str(snapshot), '0', '1'], capture_output=True)
    assert result.returncode == 0, result.stderr
    result = subprocess.run([trace, str(snapshot), str(root)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    rows_output = result.stdout
    rows = list(csv.DictReader(io.StringIO(result.stdout)))
    assert [int(x['cycle']) for x in rows] == [0, 1, 7]
    for row in rows:
        assert int(row['common_queries']) == 7 and int(row['k']) == 1
        assert [int(row[x]) for x in ['before_hits', 'remove_hits', 'add_hits']] == [7, 7, 7]
        assert [int(row[x]) for x in ['before_edges', 'remove_edges', 'add_edges']] == [42, 42, 42]
        assert all(int(row[x]) == 0 for x in ['remove_dropped', 'remove_added', 'add_dropped', 'add_added'])
    event_path = root / 'events.csv'
    result = subprocess.run([trace, str(snapshot), str(root), str(event_path)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert result.stdout == rows_output
    event_rows = list(csv.DictReader(io.StringIO(event_path.read_text())))
    assert len(event_rows) == 8
    for cycle, row in enumerate(event_rows):
        assert int(row['cycle']) == cycle
        assert int(row['query']) != int(row['id'])
        assert [int(row[x]) for x in ['before_hits', 'remove_hits', 'add_hits']] == [1, 1, 1]
    assert subprocess.run([trace, str(snapshot), str(root), str(event_path)], capture_output=True).returncode != 0
    payload = bytearray(snapshot.read_bytes())
    struct.pack_into('<Q', payload, 24, (1 << 64) - 1)
    overflow = root / 'overflow.snapshot'; overflow.write_bytes(payload)
    assert subprocess.run([trace, str(overflow), str(root)], capture_output=True).returncode != 0
    (root / 'groundtruth.ivecs').write_bytes(struct.pack('<ii', 1, 0))
    (root / 'queries.fvecs').write_bytes(records[:68])
    skipped = root / 'skipped.csv'
    result = subprocess.run([trace, str(snapshot), str(root), str(skipped)], capture_output=True)
    assert result.returncode == 0, result.stderr
    skipped_rows = list(csv.DictReader(io.StringIO(skipped.read_text())))
    assert int(skipped_rows[0]['query']) == -1
    assert [int(skipped_rows[0][x]) for x in ['before_hits', 'remove_hits', 'add_hits']] == [0, 0, 0]
    assert subprocess.run([trace], capture_output=True).returncode != 0
    invalid = root / 'bad.snapshot'; invalid.write_bytes(b'bad')
    assert subprocess.run([trace, str(invalid), str(root)], capture_output=True).returncode != 0
    assert subprocess.run([trace, str(snapshot), str(root / 'missing')], capture_output=True).returncode != 0
    (root / 'groundtruth.ivecs').write_bytes(struct.pack('<ii', 1, 99))
    assert subprocess.run([trace, str(snapshot), str(root)], capture_output=True).returncode != 0
print('8x16 exact clique: common truth exclusion, moved-slot ID edges, checkpoint counts and invalid inputs pass.')
