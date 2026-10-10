# OP6 / enchilada / Android 17 — TWRP Recovery Port v0.1

**State: source implemented + host test passes. TWRP binary build and real boot not yet proven. Not for direct flashing.**

This package contains actual TWRP Android14 device-tree source, two explicit legacy-vs-retrofit recovery fstab profiles, an Android14-based TWRP manifest sync/build path, host ABI and SDM845 DTB validators, and CI instructions. It uses the compiled Linux **4.19.325 BakaSU** kernel from GitHub Actions run #38047144934. It never silently replaces the user-supplied Linux **4.9.337** boot kernel.

Files:
- `device/oneplus/enchilada/BoardConfig.mk`, `AndroidProducts.mk`, `device.mk`, `twrp_enchilada.mk`: buildable Android-based TWRP product and 64 MiB boot-header v1 Recovery-as-Boot target.
- `device/oneplus/enchilada/recovery/root/system/etc/recovery.fstab`: conservative *legacy* profile matching observed 4.9 boot ramdisk (no system/vendor write access).
- `device/oneplus/enchilada/recovery/root/system/etc/recovery-retrofit.fstab`: opt-in experimental EROFS+logical profile, **not** evidenced by the provided 4.9 Ramdisk. Must match current *running* Android17 ROM before use.
- `tools/check_port.py`: refuses changed 4.19 DTB bytes, wrong boot v1 headers, oversized boot image, dangerous fstab flags and injected nonmatching kernels.
- `tools/build_4_19_twrp_ci.sh`: host-only recovery image builder, with explicit layout selection.
- `.github/workflows/enchilada-twrp14-build.yml`: GitHub Actions source sync, compile and artifact upload. CI produces fastboot-boot **unverified** candidates only if all checks pass.
- `tests/test_port.py`: smoke and negative tests, runnable with stock Python.

Build source pinned project: `https://github.com/nebrassy/platform_manifest_twrp_aosp` / branch `twrp-14`. The TeamWin `android-11` device tree provided hardware context only. The source from the uploaded **4.9.337** image is not an Android17 dynamic layout: `recovery.fstab` uses physical ext4 system/vendor and `fileencryption=ice`; prior claims that it contained EROFS/FBEv2 were wrong and have been corrected. The target 4.19 Android17 ROM fstab remains unverified.

Explicitly unsupported in v0.1: Android17 FBE encrypted data decryption, active-slot OTA writeback, AVB resigning, guaranteed dynamic mount, permanent TWRP installation, and verified touch/display/fastbootd operation. `TW_INCLUDE_CRYPTO` defaults false. Neither a test build nor a successful CI compile proves functional recovery.

Never run `fastboot flash recovery` on this A/B Recovery-as-Boot device. Preserve a separately verified working boot.img and a computer-based fastboot restore path. Do not resize/format/erase partitions based on these prototypes.