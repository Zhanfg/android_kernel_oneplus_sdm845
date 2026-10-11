#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
import importlib.util
import struct
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("kpm", Path(__file__).resolve().parents[1] / "tools/op6_kpm_elf_preflight.py")
kpm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(kpm)


def sample(machine=183, metadata=b"name=hello\0version=1.0\0", init=b"\0" * 8):
    names = b"\0.shstrtab\0.kpm.info\0.kpm.init\0"
    blocks = [names, metadata, init]
    cursor = 64
    offsets = []
    body = bytearray()
    for block in blocks:
        offsets.append(cursor)
        body.extend(block)
        cursor += len(block)
    cursor = (cursor + 7) & ~7
    body.extend(b"\0" * (cursor - 64 - len(body)))
    hdrs = [
        (0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
        (1, 3, 0, 0, offsets[0], len(names), 0, 0, 1, 0),
        (11, 1, 2, 0, offsets[1], len(metadata), 0, 0, 1, 0),
        (21, 1, 2, 0, offsets[2], len(init), 0, 0, 8, 8),
    ]
    ident = b"\x7fELF" + bytes((2, 1, 1)) + b"\0" * 9
    eh = kpm.EH.pack(ident, 1, machine, 1, 0, 0, cursor, 0,
                     64, 0, 0, 64, 4, 1)
    return eh + body + b"".join(kpm.SH.pack(*s) for s in hdrs)


class PreflightTests(unittest.TestCase):
    def test_valid(self):
        d = kpm.verify(sample())
        self.assertEqual(d["name"], "hello")
        self.assertFalse(d["runtime_safe"])

    def test_not_elf(self):
        with self.assertRaises(ValueError):
            kpm.verify(b"not elf")

    def test_wrong_machine(self):
        with self.assertRaises(ValueError):
            kpm.verify(sample(machine=62))

    def test_missing_name(self):
        with self.assertRaises(ValueError):
            kpm.verify(sample(metadata=b"license=GPL v2\0"))

    def test_invalid_name(self):
        with self.assertRaises(ValueError):
            kpm.verify(sample(metadata=b"name=hello world\0"))

    def test_duplicate_name(self):
        with self.assertRaises(ValueError):
            kpm.verify(sample(metadata=b"name=a\0name=b\0"))

    def test_no_init(self):
        with self.assertRaises(ValueError):
            kpm.verify(sample(init=b""))

    def test_truncated_section(self):
        with self.assertRaises(ValueError):
            kpm.verify(sample()[:-20])

    def test_reject_non_rel(self):
        blob = bytearray(sample())
        struct.pack_into("<H", blob, 16, 2)
        with self.assertRaises(ValueError):
            kpm.verify(bytes(blob))


if __name__ == "__main__":
    unittest.main()
