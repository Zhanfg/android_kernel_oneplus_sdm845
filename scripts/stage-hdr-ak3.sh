#!/bin/sh
# Stage verified HDR userspace components in a ONE-ZIP AnyKernel3 installer.
# No arguments. Host CI build script only; never execute on the phone.
# Requires a separately built, matching and signed Settings.apk and Composer.
set -eu
fail() { printf 'HDR AK3 BLOCKED: %s\n' "$*" >&2; exit 1; }
ROOT=$(CDPATH= cd "$(dirname "$0")/.." && pwd)
AK3_DIR=$(printenv OP6_HDR_AK3_DIR 2>/dev/null || true)
[ -n "$AK3_DIR" ] && [ -f "$AK3_DIR/anykernel.sh" ] || fail "Missing AK3 staging directory"
[ -f "$AK3_DIR/tools/ak3-core.sh" ] || fail "Missing pinned AK3 core"
[ -f "$ROOT/scripts/verify-appended-dtbs.py" ] || fail "Wrong kernel checkout"

# All inputs must be explicitly provided by a private release build.
for name in OP6_HDR_STOCK_COMPOSER OP6_HDR_CANDIDATE_COMPOSER OP6_HDR_STOCK_SETTINGS OP6_HDR_CANDIDATE_SETTINGS OP6_HDR_ABI_VALIDATOR OP6_HDR_SETTINGS_PARTITION; do
    value=$(printenv "$name" 2>/dev/null || true)
    [ -n "$value" ] || fail "$name is unset"
done
for name in OP6_HDR_STOCK_COMPOSER OP6_HDR_CANDIDATE_COMPOSER OP6_HDR_STOCK_SETTINGS OP6_HDR_CANDIDATE_SETTINGS OP6_HDR_ABI_VALIDATOR; do
    value=$(printenv "$name" 2>/dev/null || true)
    [ -s "$value" ] || fail "$name is not a nonempty regular file"
done
case "$OP6_HDR_SETTINGS_PARTITION" in
    system|system_ext) ;;
    *) fail "Settings partition must be verified as system or system_ext" ;;
esac
for cmd in sha256sum python3 apksigner aapt awk sed grep; do
    command -v "$cmd" >/dev/null 2>&1 || fail "Missing host program: $cmd"
done

STOCK_SHA=682e40228e267c3ae07f048ea7ec1e75f38273ce9f85d0ce2612c34f4650c736
ACTUAL_SHA=$(sha256sum "$OP6_HDR_STOCK_COMPOSER" | awk '{print $1}')
[ "$ACTUAL_SHA" = "$STOCK_SHA" ] || fail "Original composer differs from OP6 A17 101 recorded baseline"
python3 "$OP6_HDR_ABI_VALIDATOR" "$OP6_HDR_STOCK_COMPOSER" "$OP6_HDR_CANDIDATE_COMPOSER" ||
    fail "Composer postbuild ABI comparison failed"
# Prevent replacing Settings with a package signed by another Android platform.
stock_cert=$(apksigner verify --print-certs "$OP6_HDR_STOCK_SETTINGS" |
    sed -n 's/^Signer #1 certificate SHA-256 digest: //p' | head -n 1)
candidate_cert=$(apksigner verify --print-certs "$OP6_HDR_CANDIDATE_SETTINGS" |
    sed -n 's/^Signer #1 certificate SHA-256 digest: //p' | head -n 1)
[ -n "$stock_cert" ] && [ "$stock_cert" = "$candidate_cert" ] ||
    fail "Settings platform signing certificate differs; never inject this APK"
for apk in "$OP6_HDR_STOCK_SETTINGS" "$OP6_HDR_CANDIDATE_SETTINGS"; do
    aapt dump badging "$apk" | grep -q "package: name='com.android.settings'" ||
        fail "Wrong package (expected com.android.settings)"
done
# Verify AK3 has never been configured to inject another untrusted module.
grep -q '^do.modules=0$' "$AK3_DIR/anykernel.sh" ||
    fail "AK3 module support unexpectedly already configured"
grep -q '^do.systemless=0$' "$AK3_DIR/anykernel.sh" ||
    fail "AK3 systemless support unexpectedly already configured"

# Only after ALL checks pass do we stage any files.
mkdir -p "$AK3_DIR/modules/vendor/bin/hw"
mkdir -p "$AK3_DIR/modules/$OP6_HDR_SETTINGS_PARTITION/priv-app/Settings"
cp "$OP6_HDR_CANDIDATE_COMPOSER" \
    "$AK3_DIR/modules/vendor/bin/hw/vendor.qti.hardware.display.composer-service"
cp "$OP6_HDR_CANDIDATE_SETTINGS" \
    "$AK3_DIR/modules/$OP6_HDR_SETTINGS_PARTITION/priv-app/Settings/Settings.apk"

sed -i 's/^do.modules=0$/do.modules=1/' "$AK3_DIR/anykernel.sh"
sed -i 's/^do.systemless=0$/do.systemless=1/' "$AK3_DIR/anykernel.sh"

# Do not modify boot if the recovery cannot mount the current Vendor and /data.
# This check is inserted before dump_boot, and uses AK3's own abort function.
python3 - "$AK3_DIR/anykernel.sh" "$STOCK_SHA" <<'PY'
import pathlib, sys
p=pathlib.Path(sys.argv[1])
s=p.read_text()
marker=". tools/ak3-core.sh;\ndump_boot;"
if marker not in s:
    raise SystemExit("Unsupported AK3 installer structure")
guard="""\
. tools/ak3-core.sh;
# HDR is only permitted if module files can be staged and ROM is exact.
[ -r /vendor/bin/hw/vendor.qti.hardware.display.composer-service ] ||
  abort "HDR requires Vendor mounted read-only in recovery; aborting before boot modification";
[ -d /data/adb ] && [ -d /data/data/android ] ||
  abort "HDR requires unlocked /data and KernelSU/Magisk module access";
[ -d /data/adb/magisk ] || [ -d /data/data/me.weishu.kernelsu ] ||
  abort "HDR requires an initialized KernelSU/Magisk installation";
[ ! -d /data/adb/modules/ak3-helper ] ||
  abort "Existing AK3 helper module: manual conflict review required";
ACTUAL_VENDOR_SHA=$(sha256sum /vendor/bin/hw/vendor.qti.hardware.display.composer-service | awk '{print $1}');
[ "$ACTUAL_VENDOR_SHA" = "__SHA__" ] ||
  abort "Current Vendor Composer is not the expected baseline";
dump_boot;"""
s=s.replace(marker,guard.replace("__SHA__",sys.argv[2]))
p.write_text(s)
PY
grep -q '^do.modules=1$' "$AK3_DIR/anykernel.sh"
grep -q '^do.systemless=1$' "$AK3_DIR/anykernel.sh"
echo "HDR: staged verified ARM64 Composer and platform-signed Settings in AK3 systemless helper."
echo "NOTICE: candidate still requires actual Android 17 boot/HDR/rollback validation."
