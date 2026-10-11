#!/bin/sh
# OnePlus 6 / Android 17 HDR companion packaging for AnyKernel3
# No CLI args. No ROM/vendor/kernel changes. Optional companion is NOT installed.
set -eu
[ -n "$OP6_HDR_AK3_OUT" ] || { echo "Missing HDR output directory" >&2; exit 1; }
mkdir -p "$OP6_HDR_AK3_OUT"
cat > "$OP6_HDR_AK3_OUT/README.zh-CN.txt" <<'EOF_HDR'
OnePlus 6 / enchilada / uwuAOSP Android 17 - 原生 HDR 扩展
当前文件只是 AK3 HDR 集成占位，不表示已启用 HDR。
真正 HDR 需要修复 Vendor Composer HWC 色彩模式，并通过
完整 Android 17 Soong、ABI、VINTF、SELinux 与真机 HDR 测试。
系统开关的源码由 Settings PR #2 提供，而非 BOOT 内核。
严禁将本目录内的 ZIP 当成内核驱动或直接替换运行中的 Vendor 服务。
https://github.com/Zhanfg/platform_vendor_uwu/pull/9
https://github.com/Zhanfg/platform_packages_apps_Settings/pull/2
EOF_HDR
printf '%s\n' \
 'schema=op6-hdr-addon-v1' \
 'device=enchilada' \
 'rom=uwuAOSP17' \
 'installer=AnyKernel3' \
 'target=user-space-vendor-hwc' \
 'boot_dtbo_changes=no' \
 'automatic_install=no' \
 'settings_build_required=yes' > "$OP6_HDR_AK3_OUT/COMPONENT_INFO.txt"

if [ -z "$OP6_HDR_COMPANION_ZIP" ]; then
  if [ -n "$OP6_HDR_COMPANION_SHA256" ] || [ -n "$OP6_HDR_COMPANION_ELF_SHA256" ]; then
    echo "Incomplete optional HDR release configuration" >&2
    exit 1
  fi
  echo "HDR: documentation only; no vendor binary bundled."
  exit 0
fi
[ -f "$OP6_HDR_COMPANION_ZIP" ] || { echo "HDR module ZIP missing" >&2; exit 1; }
[ -n "$OP6_HDR_COMPANION_SHA256" ] || { echo "Companion SHA256 not supplied" >&2; exit 1; }
[ -n "$OP6_HDR_COMPANION_ELF_SHA256" ] || { echo "Composer SHA256 not supplied" >&2; exit 1; }

python3 - "$OP6_HDR_COMPANION_ZIP" "$OP6_HDR_COMPANION_SHA256" "$OP6_HDR_COMPANION_ELF_SHA256" <<'PY'
import hashlib
from pathlib import Path
import re
import sys
import zipfile

file = Path(sys.argv[1])
archive_digest, elf_digest = sys.argv[2:]
if not all(re.fullmatch(r"[a-f0-9]{64}", x) for x in (archive_digest, elf_digest)):
    raise SystemExit("Invalid SHA256 digest")
if hashlib.sha256(file.read_bytes()).hexdigest() != archive_digest:
    raise SystemExit("Companion archive SHA256 mismatch")
elf = "system/vendor/bin/hw/vendor.qti.hardware.display.composer-service"
with zipfile.ZipFile(file) as z:
    names = z.namelist()
    if any(x.startswith("/") or ".." in Path(x).parts for x in names):
        raise SystemExit("Unsafe ZIP path")
    if len(names) != len(set(names)) or "module.prop" not in names or elf not in names:
        raise SystemExit("Missing required HDR companion members")
    if not re.search(r"^id=op6-native-hdr$",z.read("module.prop").decode(),re.MULTILINE):
        raise SystemExit("Wrong HDR module identity")
    blob = z.read(elf)
    if hashlib.sha256(blob).hexdigest() != elf_digest:
        raise SystemExit("Composer ELF hash mismatch")
    if not (len(blob) >= 64 and blob[:4] == b"\x7fELF" and
            blob[4] == 2 and blob[5] == 1 and
            int.from_bytes(blob[18:20], "little") == 183):
        raise SystemExit("Composer must be AArch64 ELF64")
print("Archive integrity passed; this does not certify a safe HAL or functional HDR")
PY
cp "$OP6_HDR_COMPANION_ZIP" "$OP6_HDR_AK3_OUT/Op6NativeHDR-KSU-COMPANION-UNVERIFIED.zip"
printf 'archive_sha256=%s\ncomposer_sha256=%s\n' \
 "$OP6_HDR_COMPANION_SHA256" "$OP6_HDR_COMPANION_ELF_SHA256" >> "$OP6_HDR_AK3_OUT/COMPONENT_INFO.txt"
echo "HDR companion staged but NOT automatically installed."
