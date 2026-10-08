# Copyright 2026 The VSAG Authors. Licensed under the Apache License, Version 2.0.
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from export_experiment_tables import export, tables


class ExportTests(unittest.TestCase):
    def test_fences_and_malformed_rows(self):
        text='|Kind|Value|\n|---|---:|\n|fp32|.95|\n\n```\n|fake|row|\n|---|---|\n|x|y|\n```\n'
        self.assertEqual(tables(text)[0]['rows'],[['fp32','.95']])
        self.assertEqual(len(tables(text)),1)
        with self.assertRaises(ValueError):
            tables('|A|B|\n|---|---|\n|one|\n')

    def test_export_provenance_and_rejections(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'benchmark'
            case=root/'results'/'case'
            case.mkdir(parents=True)
            raw='# Test\n\n|Mode|Recall|\n|---|---|\n|base|.89|\n|candidate|.90|\n\nQuality fails.\n'
            (case/'README.md').write_text(raw)
            (root/'FINAL_REPORT.md').write_text('Historical P50 2401 us.\n')
            (root/'ACCEPTANCE_REPORT_20261006.md').write_text('Limited acceptance.\n')
            output=Path(temp)/'export'
            result=export(root,output,'a'*40)
            self.assertEqual((result['report_count'],result['table_count'],result['row_count']),(3,1,2))
            self.assertEqual(result['sources'][0]['sha256'],hashlib.sha256(raw.encode()).hexdigest())
            text=(output/'ALL_EXPERIMENTS.md').read_text()
            self.assertIn('Historical P50 2401 us.',text)
            self.assertIn('Quality fails.',text)
            self.assertIn('Recall=.89',text)
            self.assertEqual(json.loads((output/'tables.json').read_text())['source_revision'],'a'*40)
            with self.assertRaises(FileExistsError):
                export(root,output,'a'*40)
            with self.assertRaises(ValueError):
                export(root,root/'results'/'recursive','a'*40)
            with self.assertRaises(ValueError):
                export(root,Path(temp)/'bad','bad')
            self.assertFalse((root/'results'/'recursive').exists())


if __name__ == '__main__':
    unittest.main()
