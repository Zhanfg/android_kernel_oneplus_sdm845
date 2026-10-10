#!/bin/sh
# Package the Enchilada BakaSU/ReSukiSU kernel with a pinned AnyKernel3.
set -eu
ROOT=$(CDPATH= cd "$(dirname "$0")/.." && pwd)
cd "$ROOT"
KERNEL_IMAGE="$ROOT/out/arch/arm64/boot/Image.gz-dtb"
[ -s "$KERNEL_IMAGE" ] || { echo "Missing Image.gz-dtb" >&2; exit 1; }
command -v zip >/dev/null 2>&1 || { echo "zip not installed" >&2; exit 1; }
command -v unzip >/dev/null 2>&1 || { echo "unzip not installed" >&2; exit 1; }
AK3_SHA=1c9a500dd4aa8081952523126e97eb155aed941b
KERNEL_SHA=$(git rev-parse HEAD)
SHORT_SHA=$(printf '%s' "$KERNEL_SHA" | cut -c1-12)
OUT_DIR="$ROOT/dist"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT HUP INT TERM
mkdir -p "$OUT_DIR" "$TMP/ak3"
git -C "$TMP/ak3" init -q
git -C "$TMP/ak3" remote add origin https://github.com/osm0sis/AnyKernel3.git
git -C "$TMP/ak3" fetch -q --depth=1 origin "$AK3_SHA"
git -C "$TMP/ak3" checkout -q --detach "$AK3_SHA"
[ "$(git -C "$TMP/ak3" rev-parse HEAD)" = "$AK3_SHA" ]
test -s "$TMP/ak3/tools/ak3-core.sh"
rm -rf "$TMP/ak3/.git" "$TMP/ak3/.github"
cp "$KERNEL_IMAGE" "$TMP/ak3/Image.gz-dtb"
python3 "$ROOT/scripts/normalize_enchilada_dtbs.py" "$TMP/ak3/Image.gz-dtb"
cat > "$TMP/ak3/anykernel.sh" <<'AK3SCRIPT'
### AnyKernel3 Ramdisk Mod Script
## osm0sis @ xda-developers
properties() { '
kernel.string=OnePlus6 Android17 ReSukiSU/BakaSU 4.19.325 EXPERIMENTAL
do.devicecheck=1
do.modules=0
do.systemless=0
do.cleanup=1
do.cleanuponabort=0
device.name1=enchilada
device.name2=OnePlus6
device.name3=
supported.versions=
supported.patchlevels=
supported.vendorpatchlevels=
'; }
BLOCK=boot;
IS_SLOT_DEVICE=auto;
RAMDISK_COMPRESSION=auto;
PATCH_VBMETA_FLAG=auto;
. tools/ak3-core.sh;
dump_boot;
write_boot;
AK3SCRIPT
cat > "$TMP/ak3/README-EXPERIMENTAL.txt" <<EOF
OnePlus 6 / enchilada / Android 17
ReSukiSU (renamed BakaSU) — Linux 4.19.325
EXPERIMENTAL: BOOT AND RUNTIME NOT YET VERIFIED.
Kernel repository commit: $KERNEL_SHA
BakaSU commit: 5b76b884c75f729a220bb317aa4a4fc78f0e0e9c
AnyKernel3 commit: $AK3_SHA
Build artifact: Image.gz-dtb kernel replacement only.
No DTBO, vendor, firmware, or data partition modification is intended.
Only flash on a compatible enchilada ROM after saving the original boot.img.
Do not assume it is compatible merely because the ROM runs Android 17.
EOF
(
cd "$TMP/ak3"
sha256sum Image.gz-dtb > KERNEL_SHA256SUMS
)
PACKAGE="$OUT_DIR/OnePlus6_A17_ReSukiSU-BakaSU_4.19.325_AK3_EXPERIMENTAL_${SHORT_SHA}.zip"
(cd "$TMP/ak3" && zip -q -r -9 "$PACKAGE" .)
unzip -tqq "$PACKAGE"
unzip -Z1 "$PACKAGE" | grep -qx 'anykernel.sh'
unzip -Z1 "$PACKAGE" | grep -qx 'Image.gz-dtb'
unzip -Z1 "$PACKAGE" | grep -qx 'tools/ak3-core.sh'
[ "$(unzip -p "$PACKAGE" Image.gz-dtb | sha256sum | cut -d' ' -f1)" = "$(sha256sum "$TMP/ak3/Image.gz-dtb" | cut -d' ' -f1)" ]
(cd "$OUT_DIR" && sha256sum "$(basename "$PACKAGE")" > "$(basename "$PACKAGE").sha256")
cp out/.config "$OUT_DIR/kernel.config"
cp "$TMP/ak3/README-EXPERIMENTAL.txt" "$OUT_DIR/BUILD_INFO.txt"
printf 'Created %s\n' "$PACKAGE"
