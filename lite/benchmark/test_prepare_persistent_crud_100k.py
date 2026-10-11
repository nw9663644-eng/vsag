# Copyright 2024-present the vsag project
# SPDX-License-Identifier: Apache-2.0
import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest

import numpy as np

spec = importlib.util.spec_from_file_location('prepare', Path(__file__).with_name('prepare_persistent_crud_100k.py'))
prepare = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prepare)


class PreparationTests(unittest.TestCase):
    def test_sift_source_and_existing_sources(self):
        self.assertEqual(set(prepare.SOURCES), {'sift100k100', 'gist100k100', 'cohere100k100'})
        self.assertIn('/sift/', str(prepare.SOURCES['sift100k100']))

    def test_fvecs_roundtrip(self):
        vectors = np.array([[1, 2, 3], [4, 5, 6]], dtype=np.float32)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'vectors.fvecs'
            prepare.write_fvecs(path, vectors)
            np.testing.assert_array_equal(prepare.read_fvecs(path), vectors)

    def test_fp64_truth_orders_ties_by_id(self):
        base = np.array([[i, 0] for i in range(12)], dtype=np.float32)
        query = np.array([[5.5, 0]], dtype=np.float32)
        record = struct.unpack('<11i', prepare.truth(base, query))
        self.assertEqual(record, (10, 5, 6, 4, 7, 3, 8, 2, 9, 1, 10))


if __name__ == '__main__':
    unittest.main()
