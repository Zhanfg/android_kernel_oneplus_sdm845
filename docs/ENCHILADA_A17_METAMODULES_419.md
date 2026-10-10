# Enchilada / uwuAOSP Android 17: Metamodule backends on Linux 4.19

Audit: 2026-10-10. Target: OnePlus 6 (`enchilada`), Linux 4.19.325-cip136, BakaSU pinned `5b76b884c75f729a220bb317aa4a4fc78f0e0e9c`. Purpose: **keep ordinary systemless modules working without bootloop regressions**. No device or kernel modifications are included in this branch.

## Product names: voice-input normalization

- **Mountify** (often transcribed as “Monterey”) — `backslashxx/mountify`.
- **MMRS** = **Meta Magic Mount RS** — `Tools-cx-app/meta-magic_mount-rs`.
- NoMount and Hybrid Mount's optional VFS are *different* kernel VFS providers, not synonyms for the two projects above.

## Verified source-level prerequisites

- `arch/arm64/configs/vendor/sdm845-perf_defconfig`: `CONFIG_OVERLAY_FS=y`, `CONFIG_TMPFS=y`, `CONFIG_TMPFS_POSIX_ACL=y`, `CONFIG_EXT4_FS=y`, `CONFIG_F2FS_FS=y`, `CONFIG_SECURITY_SELINUX=y`. In this kernel's `fs/Kconfig`, `TMPFS_POSIX_ACL` **selects** `TMPFS_XATTR`; check the *generated* `.config` and runtime xattr operations as a second gate.
- BakaSU `userspace/ksud/src/android/module/metamodule.rs` recognizes `metamodule=1` and provides `exec_mount_script`; `init_event.rs` invokes it in the post-fs-data pipeline.
- BakaSU `userspace/ksud/src/android/cli.rs` provides notification that modules have mounted. `uapi/supercall.h` defines `KSU_IOCTL_MANAGE_TRY_UMOUNT` at ioctl number 18, `kernel/supercall/dispatch.c` implements it. These correspond to MMRS's notification/try-umount control path; runtime behavior remains untested.
- **One active metamodule only**: the BakaSU module manager prevents multiple metamodules. We can support several **alternative backends** on the *same kernel*, not run them simultaneously. Test each in an isolated boot/recovery cycle.

## Pin to these known source revisions for audit

| Metamodule | Version or release | Exact Git commit | Mount mechanics / ABI | Preliminary stability verdict |
|---|---|---|---|---|
| Magic Mount RS (MMRS) | v4.0.11, 2026-10-02 | `940ad260338751a676e86826e406df7a8e865c20` | Rust userspace; older `mount(2)` bind/move/tmpfs approach, BakaSU ioctl control. No new kernel patches. | **Priority A: best low-impact first candidate**. Verify on-phone; many bind mounts under heavy modules can affect mount namespace or boot performance. |
| Mountify | 204, 2026-08-25 | `df5d309802623432d49447ed0e5c5d28841ed60e` | OverlayFS, tmpfs+xattr preferred, ext4 sparse fallback. No new kernel patches when overlayfs works. | **Priority A/B: conditionally viable**. Verify tmpfs xattr, Android 17 EROFS lowerdir, restored SELinux contexts, whiteout semantics. |
| Hybrid Mount | v6.2.2, 2026-09-29 | `797fad08037204e89103a6ce8f36841c96de3d81` | OverlayFS, Magic Mount or separate `hybridmount` VFS. No kernel patch for **Magic/Overlay only**; custom 4.19 VFS needs a new port. | **Priority B**. Start `default_mode=magic` or `overlay`, explicitly do not enable the bundled VFS LKM on this kernel. Stable release behind newer VFS/SELinux bugfix commits; monitor upstream. |
| NoMount | v2.1.0, 2026-10-06 | `c7f63e3feb4125d591b6969a33aac04feb40f8ba` | Native inode/dentry/file-ops VFS redirect, requires kernel integration (`CONFIG_NOMOUNT=y`) or exact 4.19 LKM. | **Priority C experimental**. New kernel ABI attack surface, needs CFI/LTO + RCU/refcount + mmap/readdir stress. |
| ZeroMount | beta (upstream tested Linux 5.10 and 6.6 only) | Pin before any experiment | Custom VFS driver and optional SUSFS, plus overlay/magic fallback. | **Defer**. Kernel 4.19 + BakaSU + Android 17 combo not documented as tested. |
| Meta OverlayFS | Official KernelSU reference distribution | Resolve a verified released artifact | OverlayFS with module image and newer mount UAPI possibilities. | **Investigate** compatibility on 4.19; do not assume latest Android/GKI builds work unchanged. |

No mount strategy above should be described as 'stable on this device' until actual OnePlus 6 testing; the ranking is about change surface and feasibility, not empirical failure rates.

### Special MMRS notes

- Source tag v4.0.11 uses a `ksu` library in `src/ksucalls.rs`; newer `master` includes a post-release direct-ioctl refactor (`9d401ef41570`). Do **not** silently substitute moving main for the pinned release; validate whichever UAPI path you choose against the BakaSU kernel.
- Its `module/metamount.sh` runs `meta-mm` and reports module-mounted to `ksud`; check the binary location, permissions, and return status on-device.
- `mountsource = "KSU"` is the upstream default; keep it so BakaSU can identify managed mounts. Do not auto-enable unmount/hide policies or modify kernel SELinux.
- Test file replacement, new/absent target files, symlinks, `.replace`, folder recursion, 32-bit consumers, conflicting modules, and rollback of partly created mounts.

### Special Mountify notes

- It supports standard Metamodule mode and uses `skip_mount` to stop another mounting engine from double-mounting modules. Existing modules are otherwise preserved.
- `CONFIG_TMPFS_POSIX_ACL=y` selects `CONFIG_TMPFS_XATTR` in the current kernel Kconfig. This is a **source-level finding**; before testing, check effective `.config`, `getfattr`/`setfattr`, and real `trusted.overlay.opaque` behavior.
- First-test flags: `use_ext4_sparse=0`, `test_decoy_mount=0`, `mountify_stop_start=0`, `enable_lkm_nuke=0`, `mountify_expert_mode=0`, `spoof_sparse=0`, `mountify_custom_umount=0`. Keep default paths unless proven safe. Do not force `setenforce 0` to make it work.
- If the tmpfs backend fails the xattr check, consider ext4 only *as a separate test case*; copying a large font/driver module into staging could increase RAM usage, storage consumption and boot time. Do not conceal failure with experimental sysfs-altering `.ko` loaders.
- Its real overlay mounts remain in mount namespaces and can alter Android 17 init/zygote views; zero mount-table pollution is *not* promised.
- Update `MOUNT_DEVICE_NAME` to `KSU` for an explicit unmount integration test when needed; ensure mount source respects BakaSU's managed-mount contract.

### Special Hybrid Mount notes

- It can mix backends per **module**, but is still **one** metamodule process. Do not mix its own `hybridmount` VFS driver with NoMount; their inode/dentry operation hijacks can conflict.
- VFS releases only ship prebuilt LKMs for supported GKI targets. A 4.19 kernel must use an exact-ABI rebuilt `hybridmount` or built-in version, and is NOT a plug-and-play GKI LKM target.
- Given recent post-v6.2.2 VFS and SELinux fixes on `main`, avoid VFS on this build. No 'stable' guarantee for Magic or Overlay before on-device tests either.
- Do not enable spoofing, ext4 sysfs nuking, or experimental fallback behavior during first smoke test.

## Common runtime verification gate (all backends)

1. Preserve the user-provided original uwuAOSP17 `boot.img` off-device (64 MiB, valid Android boot header), stock AB slot and a recovery/fastboot restore path. Confirm root-only AK3 boot and hardware functions before starting.
2. Confirm `uname -r`, `getenforce` = Enforcing, BakaSU kernel driver, `ksud`, exactly one `metamodule=1`, and correct `metamount.sh` invocation. Inspect `/proc/mountinfo` and `/proc/filesystems` before/after; absence of messages is not success.
3. One tiny non-critical test file, then an ordinary systemless module. For each: read/open/stat/readdir/mmap/execute when appropriate, permission and SELinux labels; original + injected file views from 32-bit and 64-bit apps.
4. Repeat cold boot (10+), suspend/wake (30+), reboot/recovery and module enable/disable cycles; test stage timing and disabled/removed/skip_mount semantics, plus overlapping `.replace` or symlinks.
5. Scale to real font and audio modules only after smoke tests; camera/GPU/wifi/charging/telephony and SELinux regression suite must pass unchanged. Test CPU and RAM footprint and boot time across the same modules and same ROM.
6. If any mount, VFS, init, native library or app boot failure occurs, revert to original boot and previous known-good metamodule. Maintain a backup of `/data/adb/modules` and do not delete existing modules as a shortcut.

## Suggested rollout

- **Kernel baseline**: keep current root-only BakaSU Linux 4.19 build unmodified.
- **Metamodule smoke candidate 1**: MMRS v4.0.11, simplest low kernel-change path.
- **Metamodule smoke candidate 2**: Mountify 204, test tmpfs/OverlayFS on Android17 as alternative to MMRS.
- **Optional**: Hybrid v6.2.2 with *only* Magic/Overlay, if it solves a concrete defect.
- **Experimental separate kernel**: NoMount v2.1.0 (native VFS); SUSFS not combined in first round.
- **Deferred**: ZeroMount and Hybrid VFS until core is proven stable.

## Provenance

- https://github.com/Tools-cx-app/meta-magic_mount-rs/releases/tag/v4.0.11
- https://github.com/backslashxx/mountify/releases/tag/204
- https://github.com/Hybrid-Mount/meta-hybrid_mount/releases/tag/v6.2.2
- https://github.com/maxsteeel/nomount/releases/tag/v2.1.0
- https://github.com/Enginex0/zeromount
- https://kernelsu.org/guide/metamodule.html
- https://github.com/Baka-SU/BakaSU
