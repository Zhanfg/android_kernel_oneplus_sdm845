# OP6 / enchilada / Android 17 — TWRP Recovery Port v0.1

**State: source implemented + host test passes. TWRP binary build and real boot not yet proven. Not for direct flashing.**

This source is an actual Android 14-based TWRP recovery-as-boot device tree for the **current uploaded Android 17 / Linux 4.19.325** `boot.img` (SHA256 `6b305cace01270c797c7ad44a1457154ec91667227ce1e4b35be49156d940a0e`). Directly decompressed from that image, its first-stage and recovery fstab map EROFS **logical** `system`/`vendor`/`odm`, `/metadata` to physical `logdump` ext4 and `/data` to ext4 FBEv2. The prior stale decompression files describing a separate Linux 4.9 image must not be used.

The port uses the matching compiled Linux **4.19.325 BakaSU** kernel from GitHub Actions job #38047144934; the appended SDM845 FDT blobs match this same 4.19 uploaded boot.img byte-for-byte. The recovery userspace is TWRP 14 from nebrassy `twrp-14`, not a retitled old TWRP 11 binary.

Files:
- `device/oneplus/enchilada/{BoardConfig.mk,AndroidProducts.mk,device.mk,twrp_enchilada.mk}`: standalone TWRP product for 64 MiB boot-header v1 Recovery-as-Boot.
- `device/oneplus/enchilada/recovery/root/system/etc/recovery.fstab`: **selected** Android 17 dynamic/EROFS layout extracted from the current boot ramdisk; mounted sensitive partitions read-only and removed dangerous `formattable` flags.
- `.../recovery-retrofit.fstab`: identical current ROM profile, retained explicitly for clarity.
- `.../recovery-legacy.fstab`: historical fallback only for a **different** previous Linux 4.9 image, never the current Android17 default.
- `tools/check_port.py`: verifies 4.19 DTB SHA256, boot v1 ABI, partition limit, safe fstab flags and recovery-image kernel equality.
- `tools/build_4_19_twrp_ci.sh` and `.github/workflows/enchilada-twrp14-build.yml`: automated host source sync and attempted recovery bootimage build, no device modifications.
- `tests/test_port.py`: host unit and fail-closed checks.

Current Github build input `TWRP_LAYOUT=retrofit` is the default; `legacy` is an explicitly marked debugging alternative. The current 4.19 Ramdisk is the authority for target layouts. Build and runtime support of FBEv2/keymaster is not yet established and remains disabled.


Explicitly unsupported in v0.1: Android17 FBE encrypted data decryption, active-slot OTA writeback, AVB resigning, guaranteed dynamic mount, permanent TWRP installation, and verified touch/display/fastbootd operation. `TW_INCLUDE_CRYPTO` defaults false. Neither a test build nor a successful CI compile proves functional recovery.

Never run `fastboot flash recovery` on this A/B Recovery-as-Boot device. Preserve a separately verified working boot.img and a computer-based fastboot restore path. Do not resize/format/erase partitions based on these prototypes.