#!/usr/bin/env python3
import gzip
import hashlib
import struct
import unittest
from normalize_enchilada_dtbs import normalize, sha, DTB_ORDER

def sample():
    raw = (b'Linux version 4.19.325 test' + b'x'*400)
    gz = gzip.compress(raw)
    def dtb(n):
        return struct.pack('>II', 0xd00dfeed,64) + bytes([n])*56
    fdt = [dtb(n) for n in (0,1,2)]
    expected = tuple(sha(x) for x in fdt)
    unordered = gz+fdt[0]+fdt[2]+fdt[1]
    ordered = gz+b''.join(fdt)
    return unordered, ordered, expected

class TestNormalize(unittest.TestCase):
    def test_reorders_only_dtbs(self):
        unordered, ordered, hashes = sample()
        self.assertEqual(normalize(unordered,hashes), ordered)
    def test_idempotent(self):
        _, ordered, hashes = sample()
        self.assertEqual(normalize(ordered, hashes), ordered)
    def test_unknown_rejected(self):
        unordered, ordered, hashes=sample()
        with self.assertRaisesRegex(ValueError, 'fingerprint'):
            normalize(unordered, DTB_ORDER)
    def test_truncated_rejected(self):
        unordered, _, hashes = sample()
        with self.assertRaises(ValueError):
            normalize(unordered[:-5],hashes)
    def test_duplicate_rejected(self):
        unordered, _, hashes = sample()
        import zlib
        stream=zlib.decompressobj(16+zlib.MAX_WBITS)
        stream.decompress(unordered);stream.flush()
        gz=unordered[:-len(stream.unused_data)]
        b=stream.unused_data[:64]
        with self.assertRaises(ValueError):
            normalize(gz+b+b+b, hashes)
    def test_wrong_magic_rejected(self):
        unordered, _, hashes = sample()
        with self.assertRaises(ValueError):
            normalize(unordered.replace(b'\xd0\x0d\xfe\xed',b'\x00\x0d\xfe\xed',1),hashes)

if __name__=='__main__':unittest.main()