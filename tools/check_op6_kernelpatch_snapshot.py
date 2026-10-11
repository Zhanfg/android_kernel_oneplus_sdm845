#!/usr/bin/env python3
"""Verify every pinned KernelPatch vendor blob offline, no dependencies."""
import hashlib, json, pathlib
R = pathlib.Path(__file__).resolve().parent.parent
P = R / "third_party/kernelpatch"
m = json.loads((P/"UPSTREAM_MANIFEST.json").read_text())
assert m["repository"] == "bmax121/KernelPatch"
assert m["execution_enabled"] is False
assert len(m["files"]) >= 20
for name, expected in m["files"].items():
    assert not pathlib.PurePosixPath(name).is_absolute()
    assert ".." not in pathlib.PurePosixPath(name).parts
    src = (P/name).read_bytes()
    actual = hashlib.sha1(b"blob " + str(len(src)).encode() + b"\0" + src).hexdigest()
    assert actual == expected, (name, actual, expected)
print("OK: " + str(len(m["files"])) + " upstream files verified against Git blob SHAs")
