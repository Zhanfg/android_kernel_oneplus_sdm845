#!/usr/bin/env python3
"""Read-only audit of native SUSFS against the actual OnePlus 6 Linux 4.19 tree.

This script NEVER merges, modifies kernel sources, compiles, or flashes a device.
Report status is explicit; a successful audit invocation is NOT a passed port.
"""
import argparse
import pathlib
import re
import subprocess

OLD = "third_party/susfs/legacy-4.19"
NEW = "third_party/susfs/upstream-v2.3.0"


def match(text: str, pattern: str) -> bool:
    return bool(re.search(pattern, text, flags=re.MULTILINE))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default=".")
    ap.add_argument("--report", default="susfs-419-preflight.txt")
    ns = ap.parse_args()
    root = pathlib.Path(ns.source).resolve()
    out = []
    report = root / ns.report

    def record(status: str, text: str):
        out.append(f"[{status}] {text}")

    def read(path):
        p = root / path
        return p.read_text(encoding="utf-8") if p.exists() else ""

    mk = read("Makefile")
    if not match(mk, r"^VERSION\s*=\s*4$") or not match(mk, r"^PATCHLEVEL\s*=\s*19$"):
        record("ERROR", "Expected Linux 4.19 source Makefile; incomplete or incorrect checkout")
    else:
        record("OK", "Source Makefile is Linux 4.19")

    old_h = read(f"{OLD}/susfs.h")
    new_h = read(f"{NEW}/susfs.h")
    if '#define SUSFS_VERSION "v1.5.5"' in old_h:
        record("OK", "Legacy GitLab 4.19 SUSFS header is v1.5.5")
    else:
        record("ERROR", "Legacy 4.19 source version mismatch")
    if '#define SUSFS_VERSION "v2.3.0"' in new_h:
        record("OK", "Modern GitLab baseline SUSFS header is v2.3.0")
    else:
        record("ERROR", "Modern v2.3.0 source version mismatch")

    for label, filename in [
        ("legacy", f"{OLD}/native-4.19.patch"),
        ("modern", f"{NEW}/native-5.15.patch"),
    ]:
        patch = root / filename
        if not patch.is_file():
            record("ERROR", f"Missing {label} patch: {filename}")
            continue
        target_files = re.findall(r"(?m)^diff --git a/([^ ]+) b/([^\n]+)", patch.read_text())
        absent = [f for f, _ in target_files if not (root / f).is_file()]
        record("INFO", f"{label} patch references {len(target_files)} files; {len(absent)} missing from checkout")
        if absent:
            record("NOTE", f"Missing {label} paths: {', '.join(absent[:25])}")
        if label == "legacy":
            cmd = subprocess.run(
                ["git", "-c", "core.safecrlf=false", "apply", "--check", "--verbose", str(patch)],
                cwd=root, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                timeout=120, check=False,
            )
            record("PASS" if cmd.returncode == 0 else "BLOCKED",
                   f"Legacy 4.19 git apply --check exit={cmd.returncode}")
            if cmd.stdout:
                out.extend("    " + line for line in cmd.stdout.splitlines()[:150])

    checks = [
        ("CONFIG_MODULES=y", "arch/arm64/configs/vendor/sdm845-perf_defconfig", r"^CONFIG_MODULES=y$"),
        ("CONFIG_MODVERSIONS=y", "arch/arm64/configs/vendor/sdm845-perf_defconfig", r"^CONFIG_MODVERSIONS=y$"),
        ("non-GKI VFS: old procfs ops", "include/linux/proc_fs.h", r"struct file_operations"),
        ("4.19 custom mount allocator", "fs/namespace.c", r"static DEFINE_IDA\(mnt_id_ida\)"),
        ("4.19 LSM hlist", "include/linux/lsm_hooks.h", r"struct security_hook_heads"),
    ]
    for label, path, pattern in checks:
        record("OK" if match(read(path), pattern) else "CHECK", label)

    bakasu = read("third_party/susfs/bakasu-pinned-Kconfig.txt")
    conf = read("arch/arm64/configs/vendor/enchilada.config")
    choice = re.search(r"(?ms)^choice\b(.*?)^endchoice\b", bakasu)
    if not choice:
        record("ERROR", "Pinned BakaSU hook-choice declaration could not be verified")
    else:
        data = choice.group(1)
        if "config KSU_MANUAL_HOOK" in data and "config KSU_SUSFS" in data:
            record("BLOCKED", "BakaSU Kconfig makes MANUAL_HOOK and KSU_SUSFS mutually exclusive; 4.19 needs independent native fs switch + explicit bridge")
        else:
            record("ERROR", "Pinned BakaSU Kconfig changed; re-audit hook architecture")
    if "CONFIG_KSU_MANUAL_HOOK=y" in conf and "# CONFIG_KSU_SUSFS is not set" in conf:
        record("OK", "Current device fragment remains manual-hook and SUSFS-disabled")
    else:
        record("ERROR", "Device hook baseline changed unexpectedly; stop until reviewed")

    # Explicitly identify why copying 5.15 patch or swapping new source is unsafe.
    record("BLOCKED", "v2.3.0 5.15 VFS/KernelSU integration is not ported to 4.19")
    record("BLOCKED", "v2.3.0 userspace ABI, native 4.19 config and BakaSU bridge not implemented")
    record("BLOCKED", "no 4.19 compile, boot or suspend tests have run")
    record("SAFETY", "Do not package/flash any SUSFS image until all BLOCKED items cleared")
    report.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(report.read_text(encoding="utf-8")[:26000])
    return 0 if all(not x.startswith("[ERROR]") for x in out) else 1


if __name__ == "__main__":
    raise SystemExit(main())
