#!/usr/bin/env python3
# Copyright 2024-present the vsag project
# SPDX-License-Identifier: Apache-2.0
"""Closure accounting, recursive resolution and copy-only strip regressions."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from measure_elf_closure import dependencies, digest, measure


class ClosureTest(unittest.TestCase):
    def test_resolution_and_unresolved_guard(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            target = root/"lib runtime.so"
            target.write_bytes(b"ELF")
            alias = root/"alias.so"
            alias.symlink_to(target)
            output = f"linux-vdso.so.1 (0x1)\nlib.so => {alias} (0x2)\n{target} (0x3)\n"
            self.assertEqual(dependencies(output), {target.resolve()})
            with self.assertRaises(ValueError):
                dependencies("missing.so => not found\n")

    def test_recursive_cycles_deduplicated_and_sources_unchanged(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            engine = root/"engine.so"
            library = root/"runtime.so"
            engine.write_bytes(b"ENGINE")
            library.write_bytes(b"RUNTIME")
            scratch = root/"copies"
            scratch.mkdir()
            before = [digest(engine), digest(library)]
            def ldd(command, env, text):
                self.assertNotIn("LD_PRELOAD", env)
                self.assertEqual(env["LD_LIBRARY_PATH"], str(root))
                dep = library if command[1] == str(engine) else engine
                return f"{dep} (0x1)\n"
            def strip(command, check):
                self.assertEqual(command[:2], ["strip", "--strip-unneeded"])
                target = Path(command[2])
                self.assertEqual(target.parent, scratch)
                target.write_bytes(target.read_bytes()[1:])
            with patch("measure_elf_closure.subprocess.check_output", side_effect=ldd), \
                 patch("measure_elf_closure.subprocess.run", side_effect=strip), \
                 patch.dict("measure_elf_closure.os.environ", {"LD_PRELOAD": "unsafe.so"}):
                report = measure(engine, scratch)
            self.assertEqual(len(report["files"]), 2)
            self.assertEqual(report["closure_source_bytes"], 13)
            self.assertEqual(report["closure_stripped_bytes"], 11)
            self.assertEqual(report["root_stripped_bytes"], 5)
            self.assertEqual([digest(engine), digest(library)], before)


if __name__ == "__main__":
    unittest.main()
