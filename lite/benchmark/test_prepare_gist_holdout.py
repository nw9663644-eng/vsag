"""Check query-offset provenance and exact truth using a known synthetic dataset."""
from pathlib import Path
import json
import struct
import subprocess
import sys
import tempfile


def fbin(path, values):
    data = bytearray(struct.pack('<II', len(values), 960))
    for first in values:
        data.extend(struct.pack('<960f', first, *([0.0] * 959)))
    path.write_bytes(data)


def main():
    preparer = str(Path(sys.argv[1]).resolve())
    script = Path(__file__).with_name('prepare_gist_holdout.py')
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        base, queries = root / 'base.fbin', root / 'queries.fbin'
        fbin(base, list(range(20)))
        fbin(queries, [100.0] * 100 + [7.0, 8.0])
        output = root / 'prepared'
        command = [sys.executable, str(script), preparer, str(base), str(queries),
                   str(output), '--base-count', '20', '--offset', '100', '--count', '2']
        subprocess.run(command, check=True, capture_output=True)
        manifest = json.loads((output / 'holdout-manifest.json').read_text())
        assert manifest['selected_rows_half_open'] == [100, 102]
        truth = (output / 'scale-20/groundtruth.ivecs').read_bytes()
        assert struct.unpack_from('<ii', truth, 0) == (10, 7)
        assert struct.unpack_from('<ii', truth, 44) == (10, 8)
        selected = (output / 'scale-20/queries.fvecs').read_bytes()
        assert struct.unpack_from('<if', selected, 0) == (960, 7.0)
        assert struct.unpack_from('<if', selected, 3844) == (960, 8.0)
        result = subprocess.run(command, capture_output=True, text=True)
        assert result.returncode != 0 and 'output already exists' in result.stderr
        for offset, message in [('99', 'offset>=100'), ('101', 'exceeds source')]:
            invalid = command.copy()
            invalid[5] = str(root / ('invalid-' + offset))
            invalid[9] = offset
            result = subprocess.run(invalid, capture_output=True, text=True)
            assert result.returncode != 0 and message in result.stderr
    print('Held-out dataset preparation fixtures passed')


if __name__ == '__main__':
    main()
