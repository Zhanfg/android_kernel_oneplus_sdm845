#!/usr/bin/env python3
"""Fail-closed KernelPatch snapshot updater. No auto-merge or kernel installation."""
import argparse
import hashlib
import json
import os
import pathlib
import sys
import urllib.error
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
SNAP = ROOT / "third_party/kernelpatch"
MANIFEST = SNAP / "UPSTREAM_MANIFEST.json"

def get_bytes(url):
    headers = {"User-Agent": "OP6-KPM-upstream-snapshot/1.0", "Accept": "application/vnd.github+json"}
    if os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = "Bearer " + os.environ["GITHUB_TOKEN"]
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=25) as r:
        return r.read()

def git_blob_sha(content):
    return hashlib.sha1(b"blob " + str(len(content)).encode() + b"\0" + content).hexdigest()

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--check", action="store_true")
    p.add_argument("--update", action="store_true")
    opts = p.parse_args()
    if opts.check == opts.update:
        p.error("choose exactly one of --check or --update")
    meta = json.loads(MANIFEST.read_text(encoding="utf8"))
    repo = meta["repository"]
    if repo != "bmax121/KernelPatch":
        raise SystemExit("invalid pinned official upstream repository")
    paths = sorted(meta["files"])
    for path in paths:
        if (not (path.startswith("lkm/") or path.startswith("kernel/"))
            or pathlib.PurePosixPath(path).is_absolute()
            or ".." in pathlib.PurePosixPath(path).parts):
            raise SystemExit("invalid snapshot path: " + path)
    base = "https://api.github.com/repos/" + repo
    latest = json.loads(get_bytes(base + "/branches/main"))["commit"]["sha"]
    old = meta["pinned_commit"]
    print("official_main=" + latest)
    print("pinned=" + old)
    print("changed=" + str(latest != old).lower())
    if opts.check or latest == old:
        return
    tree = json.loads(get_bytes(base + "/git/trees/" + latest + "?recursive=1"))
    if tree.get("truncated"):
        raise SystemExit("GitHub tree truncated; refusing partial upstream update")
    blobs = {e["path"]: e["sha"] for e in tree["tree"] if e["type"] == "blob"}
    changes = {}
    for path in paths:
        if path not in blobs:
            raise SystemExit("upstream removed pinned path: " + path)
        raw = "https://raw.githubusercontent.com/" + repo + "/" + latest + "/" + urllib.parse.quote(path)
        content = get_bytes(raw)
        if git_blob_sha(content) != blobs[path]:
            raise SystemExit("snapshot hash mismatch: " + path)
        changes[path] = content
    # No writes until all expected files have been fetched and checked.
    for path, data in changes.items():
        dst = SNAP / path
        if not dst.parent.is_dir():
            dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(data)
    meta["pinned_commit"] = latest
    meta["files"] = {p: blobs[p] for p in paths}
    # The built kernel adapter is intentionally never updated automatically.
    meta["execution_enabled"] = False
    MANIFEST.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf8")
    print("snapshot_updated=yes; commit for review, never auto-merge")

if __name__ == "__main__":
    main()
