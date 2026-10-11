# SUSFS 2.3.0 -> Linux 4.14 (non-GKI): isolated research gate

Status: **RESEARCH / NOT PORTED / NOT FLASHABLE** — 2026-10-11.

## Verified baselines

- OnePlus 6 (enchilada) Android 17 working research tree: `Zhanfg/android_kernel_oneplus_sdm845`, branch `feature/enchilada-a17-bakasu-manual-hook`, **Linux 4.19.325**, manual-hook BakaSU; no integrated SUSFS source in this branch.
- This `research/susfs-2.3.0-nongki-4.14` branch is derived from the 4.19 tree **for tracking/tests only**. It does NOT become a Linux 4.14 kernel just because of its branch name.
- Canonical SUSFS non-GKI `kernel-4.14` at `simonpunk/susfs4ksu`, GitLab SHA `77905b5a071e6f3669e3b1814cea30147c0801da` (2025-02-23), is **older than 2.3.0**.
- The canonical 2.3.0 source used for protocol/semantic comparison is `gki-android13-5.15`, SHA `687d2d18d94cb2e3e72d1074778d58384d58e379` (2026-09-26). Its GKI VFS changes must not be cherry-picked wholesale into Linux 4.14.

Canonical source: https://gitlab.com/simonpunk/susfs4ksu

## No-argument source readiness check

From an actual 4.14 kernel source root:

```sh
sh /path/to/verify-2.3.0-linux-4.14.sh
```

Or set `KERNEL_TREE` to the 4.14 tree and run the script without arguments. Exit 0 only means the **basic source prerequisites** were found, NOT that a build/boot is verified. Exit 2 means not Linux 4.14; exit 1 means missing or incomplete integration.

The CI job deliberately proves the current 4.19 tree is rejected and an unpatched 4.14 tree is rejected. **Green preflight CI is not proof that SUSFS works.**

## Porting sequence (not yet implemented)

1. Obtain a real target **Linux 4.14** vendor kernel + exact device tree, vendor interface, defconfig and toolchain. OnePlus 6's current 4.19 tree is NOT a usable 4.14 target; official OnePlus 6 sources originated from Linux 4.9. Do not cross-flash kernel families.
2. Diff canonical old `kernel-4.14` file system patch, userspace ABI and `susfs.c/h` against v2.3.0. Port functionality in small commits with original license and provenance.
3. Map new **TIF thread flags**, `i_mapping->flags`, `vfsmount.mnt_flags`, `nameidata`, `statx`, `openat`, `readdir`, `/proc/maps` and mount namespace semantics to actual 4.14 structures. Avoid stealing occupied state bits. Correctly implement RCU/seqlock lifetime and lock ordering, preserving failure/rollback paths.
4. Integrate one KernelSU/ReSukiSU su-compat hooking strategy. The manual hooks in the 4.19 OnePlus 6 branch MUST NOT be blindly combined with SUSFS inline su hooks; duplicate hook paths are a stability and security risk.
5. Match kernel and userspace SUSFS ABI **v2.3.0**; validate all commands including path-loop, mount hiding and open redirect with correct UID scheme. Do not rename the version string as a shortcut.
6. Opt-in features by Kconfig; keep expensive debug logging disabled in release. Ensure disabled features cost essentially zero in the VFS hot path. Avoid periodic daemon, polling timers, unbounded lists, globally held locks, and allocations in atomic context.
7. Run a reproducible CI matrix on the precise 4.14 vendor tree: configuration, compiler warnings, image size, module ABI, unit tests, fsstress/ltp, mount/unmount race, namespace churn, credential transitions, SELinux denial regression, suspend/resume.
8. Only after passing CI on the **actual** device's ROM/vendor ABI, create a test-only boot image with rollback. Then compare battery and latency against the same original baseline on-device.

## Required release gates (all pending)

| Gate | Minimum evidence | Status |
| --- | --- | --- |
| P0 4.14 source identity | vendor source + exact SHA/defconfig/toolchain | MISSING |
| P1 2.3.0 full backport | source patch review, userspace ABI, Kconfig integration | MISSING |
| P2 CI build | reproducible arm64 kernel build, no errors or W=1 regressions | MISSING |
| P3 VFS races | fsstress/ltp, parallel mount namespace tests, lockdep/KASAN where feasible | MISSING |
| P4 Functional | ReSukiSU root, SUSFS features, Wi-Fi, modem, camera, Bluetooth, encryption, SELinux | MISSING |
| P5 Stability | 100 suspend/resume cycles, repeated cold boots, long-idle drain, memory leak checks | MISSING |
| P6 Performance | same ROM/governor/battery/thermal conditions; report 95th percentile open/stat/path lookup latency, throughput, idle and active power relative to baseline | MISSING |
| P7 Recovery | tested original boot recovery and full rollback path | MISSING |

### Performance policy

Optimize **disabled/unmatched hot path first**: fast negative lookups and no allocations; only benchmark optional optimizations. Do not weaken SELinux, filesystem checks, error handling, thermal controls or CPU idle to inflate benchmarks. No always-on userspace agent is needed for the kernel feature itself.

### Separation rule

Until a 4.14 source tree, patch integration and test evidence exist, **no merge to the 4.19 default branch, no AnyKernel3 flash zip, no Stable label**.
