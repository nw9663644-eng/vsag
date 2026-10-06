"""Regression checks for query ranges and exact subset truth."""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import h5py
import numpy as np

with tempfile.TemporaryDirectory() as temporary:
    root = Path(temporary)
    source = root / 'source.hdf5'
    with h5py.File(source, 'w') as dataset:
        dataset.attrs['distance'] = 'euclidean'
        dataset['train'] = np.repeat(np.arange(8, dtype=np.float32)[:, None], 128, axis=1)
        dataset['test'] = np.repeat(np.arange(8, dtype=np.float32)[:, None], 128, axis=1)
    prepare = Path(__file__).with_name('prepare_sift.py')
    def run(output, offset, queries=2):
        return subprocess.run([sys.executable, str(prepare), str(source), str(output),
                               '--counts', '8', '--queries', str(queries), '--k', '2',
                               '--query-offset', str(offset)], capture_output=True, text=True)
    output = root / 'valid'
    assert run(output, 3).returncode == 0
    directory = output / 'scale-8'
    manifest = json.loads((directory / 'manifest.json').read_text())
    assert manifest['query_rows'] == [3, 5] and manifest['queries_prefix'] is None
    vectors = np.fromfile(directory / 'queries.fvecs', dtype='<f4').reshape(2, 129)
    assert np.all(vectors[:, 1:] == np.array([3, 4])[:, None])
    truth = np.fromfile(directory / 'groundtruth.ivecs', dtype='<i4').reshape(2, 3)
    assert truth.tolist() == [[2, 3, 2], [2, 4, 3]]
    assert run(output, 3).returncode != 0
    for offset in [-1, 7, 8]:
        invalid = root / f'invalid-{offset}'
        assert run(invalid, offset).returncode != 0 and not invalid.exists()
    prefix = root / 'prefix'
    assert run(prefix, 0).returncode == 0
    assert json.loads((prefix / 'scale-8/manifest.json').read_text())['queries_prefix'] == 2
print('SIFT query-offset, exact truth, prefix compatibility and rejection checks passed')
