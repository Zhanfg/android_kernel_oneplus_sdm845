# OnePlus 6 Android 17 — BakaSU / ReSukiSU integration (experimental)

Base: `awa-xaga/android_kernel_oneplus_sdm845` branch `lineage-23.2-4.19`, commit `366654798a2f17c0d57c702ef3d4f2142437c8f0`. Linux 4.19.325, Non-GKI.

This feature branch adds the documented manual hooks for stat, execveat, faccessat and reboot, and enables BakaSU (formerly ReSukiSU) only in the `enchilada.config` device fragment. It intentionally does not touch the original Lineage branch and does **not** enable SuSFS.

BakaSU source is pinned at `5b76b884c75f729a220bb317aa4a4fc78f0e0e9c` (2026-10-09); `sh scripts/setup-bakasu.sh` adds a local `KernelSU/` checkout and connects `drivers/kernelsu` to its Kconfig/Makefile. These files are not vendored into the kernel tree. Run the setup again after a clean checkout, then merge the `sdm845-perf_defconfig` and `enchilada.config` when building.

GitHub Actions builds Image.gz-dtb, assembles a **test-only, manual-flash AnyKernel3 (AK3)** ZIP from a pinned upstream AnyKernel3 revision, verifies archive integrity and uploads ZIP + SHA256 + config + build metadata. The AK3 script replaces the active boot kernel only; it never flashes a standalone DTBO image. The ZIP is **experimental and not yet device-validated**. It is NOT a boot.img or a ROM ZIP.

Before distributing a flashable ZIP, confirm ROM's kernel/DTBO and firmware ABI expectations, test boot with rollback available, and validate cellular, Wi-Fi, camera, fingerprint, charging and suspend. Keep the original ROM `boot.img` for rollback.
