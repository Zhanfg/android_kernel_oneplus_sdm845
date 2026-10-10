# OnePlus 6 / uwuAOSP Android 17 — Third-party and driver compatibility audit

Audit date: 2026-10-10
Target: OnePlus 6 (enchilada), Snapdragon 845 (SDM845), Linux 4.19.325-cip136-st20-perf, Android 17.
ROM original boot.img was locally inspected (64 MiB, boot header v1, 3 appended SDM845 base DTBs, ROM kernel git version `fd77fc2e307e-dirty`).
Kernel upstream: [awa-xaga/android_kernel_oneplus_sdm845, lineage-23.2-4.19](https://github.com/awa-xaga/android_kernel_oneplus_sdm845/tree/lineage-23.2-4.19), source baseline `366654798a2f17c0d57c702ef3d4f2142437c8f0`.
Experimental root branch: [feature/enchilada-a17-bakasu-manual-hook](https://github.com/Zhanfg/android_kernel_oneplus_sdm845/tree/feature/enchilada-a17-bakasu-manual-hook).
Provenance: the upstream baseline is exactly **one commit** ahead of the boot image git marker (`security/selinux/hooks.c`, genfscon securityfs support), but the original boot image was compiled with dirty tree changes; binary identity is NOT proven.

## Release safety policy

- **No integration into production/main until boot + runtime tests**. A successful GitHub Actions build only demonstrates a compile/package-level result.
- Prefer OnePlus 6/uwuAOSP upstream, CIP 4.19 security patches, and narrow, source-identified fixes. Never wholesale merge drivers from newer Qualcomm SoCs, GKI kernels or other Android devices.
- Preserve DTB/DTBO/firmware/vendor userspace contracts; do not overwrite modem, firmware, vendor or dtbo in experimental AK3.
- One feature group per branch and per test package; keep base/root-only as the regression control.
- No performance claims until repeated benchmarks, temperature and energy measurements under controlled conditions.
- Never silently relax CFI, SELinux, fs-verity, dm-verity, secure boot policy, or charging/thermal hard limits to make a patch build.

## Compatibility decisions (as of audit)

| Component | Source/config evidence | Status | Integration policy |
| --- | --- | --- | --- |
| BakaSU (ReSukiSU successor) | BakaSU revision `5b76b884c75f`, non-GKI manual hooks, current experimental branch | **Compile confirmed; runtime unverified** | Keep current manual-hook root-only baseline until on-device tests succeed. |
| SUSFS | `ZhanfgBuild/kernel_oneplus_sdm845` contains SUSFS v2.1.0; `susfs4ksu/kernel-4.19` has 2025-era patch | **Possible, HIGH risk** | Separate experimental SKU/branch only; port 4.19 kernel patches manually and test VFS, mounts, overlay and SELinux. Never enable by toggling a flag alone. |
| NoMount VFS (upstream v2.1.0, pinned `c7f63e3feb41`) | `maxsteeel/nomount` has a Linux 4.19 built-in integration path (`fs/nomount`, `CONFIG_NOMOUNT=y`); native VFS inode/dentry/fops redirection and a KernelSU/APatch metamodule | **Feasible; high kernel-risk; compile/runtime unverified on this device** | Only on isolated optional AK3 branch, with exact source pin and manual review. Prefer built-in over unrelated GKI LKMs; no production enablement until cold boot + directory/mmap/mount namespace tests pass. |
| SUSFS hook mode conflict | At pinned BakaSU `kernel/Kconfig`, `KSU_MANUAL_HOOK` and `KSU_SUSFS` occur in the same `choice` | **Confirmed mutual exclusivity** | Switch to a validated SUSFS hook path; prove merged `.config` has one intended hook mode. Never claim both modes are active. `SUS_SU` remains disabled for non-GKI. |
| WireGuard | `CONFIG_WIREGUARD=y` in `vendor/sdm845-perf_defconfig` | **Already present in source/config** | No additional wireguard-linux-compat backport; run handshake/network/suspend tests first. |
| eBPF, BPF LSM | `CONFIG_BPF_SYSCALL=y`, `CONFIG_BPF_JIT_ALWAYS_ON=y`, `CONFIG_BPF_LSM=y` | **Already present in config; runtime capabilities vary** | Verify program types/map helpers before porting Android 5.10+/6.x eBPF projects. Avoid sched_ext/modern eBPF backports. |
| F2FS, EROFS, OverlayFS, ZRAM | All enabled in base defconfig | **Already present** | Restrict updates to security/data-integrity fixes; storage + mount stress tests required. |
| Netfilter/ipset/FQ-CoDel, BBR v1 | Netfilter enabled; ABK donor already carries ipset/BBR v1/FQ-CoDel; not all enabled in this baseline | **Moderate risk, optional** | Study only needed options, build and traffic-test independently, preserve cubic/default settings. No BBRv3 default. |
| exFAT | `fs/exfat` exists in source tree; `CONFIG_EXFAT_FS` not found in baseline defconfig | **Potential small opt-in** | Enable only if USB-OTG exFAT demand exists; verify mount, large files, clean eject and SELinux. |
| Baseband Guard | `vc-teahouse/Baseband-guard`, also present in ABK donor | **High false-positive risk** | Only separate, opt-in audited profile; ensure emergency telephony, IMS, modem provisioning, radio and partition OTA behavior remain unaffected. Do not make write-block rules default. |
| NTSYNC / LZ4KD | ABK donor has ports | **Low benefit / substantial backport risk** | Do not integrate by default; require a concrete workload and compatibility tests. |
| MGLRU / sched_ext / Android modern io_uring | Original modern-kernel facilities; backports change mm/scheduler or attack surface | **Not recommended on 4.19 production** | Reject default inclusion. |
| Additional root/hook backends | Competing syscall/LSM modifications overlap BakaSU and SUSFS | **High conflict risk** | No simultaneous second root engine in default kernel. |
| Modern driver replacement | Qualcomm KGSL, qcacld-3.0, OnePlus charging, touch, camera, display, ADSP tied to device firmware/DT | **Not recommended wholesale** | Targeted CVE or functional patches only, with provenance and per-subsystem tests. |

### SUSFS-specific checks

1. Never apply the old `kernel-4.19` patch blindly: its KernelSU patch expects an older layout while BakaSU has a modular `kernel/` tree. Preserve historical provenance and audit source-level symbol/API differences.
2. Review `fs/dcache.c`, `fs/namei.c`, `fs/namespace.c`, `fs/stat.c`, `fs/overlayfs/*`, `fs/proc*`, `include/linux/mount.h`, `include/linux/sched.h`, `kernel/kallsyms.c` and `kernel/sys.c` for hook ordering / concurrency / refcount issues.
3. Compile two variants from one source SHA: root-only control and SUSFS experimental; check config, symbols and root initiation, rather than combining all changes in one release.
4. Test ordinary non-root file access, SAF, media scanner, adoptable/external storage (if used), bind mounts, module systemless mounts, mount namespaces, SELinux enforcing, rollback and read-only paths. SUSFS can cause performance regressions and mount visibility changes.

## Driver update policy and current upstream clues

Original source already contains device-specific code. Recent *existing* upstream commits include:

- BQ27541 capacity / cache: `5bdca3dad63d`, `7a4271b603f6`, `6dd2e0b5419f` (2026-09-15). Important to **read** the actual BQ gauge values rather than forcing battery capacity or charging voltage/current.
- Wi-Fi: qcacld-3.0 Qualcomm update `6ed5ab921adf` (2026-04-30); updated WLAN regulatory database `f9dec3a19a33` (2026-09-20).
- GPU KGSL: event workqueue to kthread `b25c4f30abff` (2026-05-25), other safety/API maintenance.
- Synaptics touchscreen `175701ffc209` / `369a302b32dd` (2026-09-15).
- Display / DC dimming `e68a8fe659ae` (2026-09-15); audio amplifier TFA9874 and MAX98927 updates in same import sequence.
- Camera-kernel Qualcomm tag merge `31fe3dfb9513` (2026-04-30).
- This is evidence of existing maintenance **not evidence of runtime correctness**.

Prioritize regressions or security fixes in the exact version used by the ROM over new feature ports. Firmware images, proprietary camera HAL, radio, Bluetooth controller firmware, GPU userspace blobs and device trees must stay compatible.

## Hardware validation gate (on the actual enchilada + uwuAOSP 17)

1. **Baseline control**: archive original boot.img SHA-256; confirm stock boot, successful UI unlock, backup/restore of correct A/B slot.
2. **Root-only boot**: bootloop watchdog, SELinux enforcing, no repeated init restarts; kernel logs and dmesg snapshot; `uname -a`, `/proc/version`, `/proc/config.gz` or extracted config.
3. **Driver smoke tests**: SIM registration, outgoing/incoming calls and data, emergency dialer availability (do not perform a test emergency call), GPS, Wi-Fi 2.4/5 GHz, Wi-Fi sleep/reconnect, Bluetooth audio and LE, USB data/OTG, fingerprint, touch + gestures, brightness/display/DC dimming, speakers and microphone, camera still/video/flash, charge/discharge, accurate capacity/temperature/thermal limiting.
4. **Power and storage**: 30+ suspend/wake cycles, airplane mode toggles, low-battery reconnect, overnight standby/idle drain, F2FS/EROFS/overlay mount tests, 4+ GiB file transfer and hash, reboot/poweroff/recovery/OTA slot safety.
5. **For SUSFS SKU only**: mount namespace stress tests + repeat all core apps/sensors and Root permissions checks.
6. **Stability promotion**: compile + static config, one successful flash and boot, hardware tests, repeated runtime tests, no data corruption, no unexplained kernel oops. Collect regression logs and record exact commits/AK3 checksum. Stop/revert after the first root or driver regression.

## Source pointers

- https://github.com/awa-xaga/android_kernel_oneplus_sdm845
- https://github.com/Baka-SU/BakaSU
- https://github.com/ZhanfgBuild/kernel_oneplus_sdm845
- https://github.com/Trijal08/susfs4ksu/tree/kernel-4.19
- https://gitlab.com/simonpunk/susfs4ksu
- https://github.com/vc-teahouse/Baseband-guard
- https://cip-project.org/2026/08/ (CIP 4.19 maintenance planned through 2029, restricted supported targets)
- https://www.kernel.org/releases.html (mainstream Linux 4.19 longterm maintenance ended)

**Conservative current decision:** do not merge any third-party feature into the experimental boot/root build yet. First obtain a DTB-verified AK3, then device boot evidence. Next candidate is SUSFS as an isolated optional branch, then opt-in networking options with measurable use cases.
## NoMount (VFS path-redirection) feasibility: 2026-10-10

The user wants to keep **existing systemless modules** in `/data/adb/modules` and replace their file system overlay behavior with **zero additional bind/overlay mounts**.

Evidence: [maxsteeel/nomount](https://github.com/maxsteeel/nomount), [kernel instructions](https://github.com/maxsteeel/nomount/blob/master/kernel/README.md), v2.1.0 release, commit `c7f63e3feb4125d591b6969a33aac04feb40f8ba`. Its `kernel/src/{Kconfig,Makefile,nomount.c,nomount.h}` hooks VFS directory lookup, directory iteration, dentries/inodes/file operations; its `module/metamount.sh` scans enabled modules and generates virtual file replacement and whiteout rules via userspace `nm`. It is not merely the mountless-only mode of metamodules, which **cannot** inject regular module system files.

**Important restrictions:** on legacy 4.19, upstream says prebuilt GKI modules are NOT applicable; compile `CONFIG_NOMOUNT=y` from a pinned upstream revision into the ROM kernel, or build an **exact ABI-compatible** out-of-tree LKM. Do NOT copy GKI `.ko` files or curl-to-shell a moving `dev` branch on a trusted build runner. The source supports 4.19 API guards but that is not evidence of successful compile with our enabled Clang CFI + LTO. Check actual merged Kconfig: `CONFIG_KEYS=y` (keyring transport) and `CONFIG_NOMOUNT=y`; keep BakaSU manual hook configuration unchanged. The pinned BakaSU source `userspace/ksud/src/android/module/metamodule.rs` confirms it recognizes `metamodule=1` and executes `metamount.sh` via `exec_mount_script` in `init_event.rs`; runtime behavior still requires verification on this ROM.

**Compatibility limitations requiring empirical testing:** original ordinary modules *may* work without modifications, but not all semantics are guaranteed: opaque directories, `.replace` handling, bind-mount-specific modules, additional mounts performed directly by scripts, lifecycle script timing, early boot file reads, property and sepolicy changes, dynamically created files, symlinks, APEX mount namespaces, 32-bit ABI, synthetic inode stat/xattr/SELinux labels, exec/load of shared libraries, mmap, SAF/media provider enumeration, and hot disable/remove. Check LSM permission checks are enforced against real underlying files. NoMount uses inode/dentry/file operation redirection; incorrect lifetime/RCU/refcounts can cause data corruption or kernel crashes. Its per-UID exception mechanism does NOT guarantee invisibility to security checks.

**NoMount is NOT the same as SUSFS**, and VFS overlaps make simultaneous introduction a large regression risk. Do one experiment at a time. For the first proof, use a non-critical text file read from a user app, then a small harmless module, then fonts (requires proper init timing and sepolicy labels), then larger modules. Test isolated + non-isolated process namespace, stat/readdir/open/read/mmap, stress concurrent enable/disable, cold boot and reboot, and regression against the stock boot. Never swap camera, Wi-Fi, charging, display or firmware drivers just to enable VFS injection. Keep a known-good original boot.img and a non-NoMount AK3 before any phone flashing.

Status: **source feasibility reviewed, no NoMount code applied to the production kernel, no NoMount AK3 built, no hardware validation**. Audit only; future implementation should use a separate `experiment/enchilada-a17-nomount-4.19` branch.
