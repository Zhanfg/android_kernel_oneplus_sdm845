# OnePlus 6 enchilada: native SUSFS 2.3.0 port onto Linux 4.19.325

**Development only. NOT integrated, NOT compiled, NOT tested on-device, and NOT flashable.**
This branch is isolated from the existing BakaSU Android 17 ROM kernel.

## Exact upstream provenance (2026-10-11)
- Kernel target: `Zhanfg/android_kernel_oneplus_sdm845` / `feature/enchilada-a17-bakasu-manual-hook` at `a0950e97a8c90e797149c03b8b99fbba32331b38`; Makefile Linux 4.19.325.
- BakaSU pin: `Baka-SU/BakaSU` at `5b76b884c75f729a220bb317aa4a4fc78f0e0e9c`; manual-hook mode enabled.
- GitLab SUSFS 4.19 historical baseline: `simonpunk/susfs4ksu`, branch `kernel-4.19`, SHA `001e69919c6271f690fd00b17e4c721c9e599152`; header **v1.5.5**, NOT 2.3.0.
- GitLab SUSFS actual 2.3.0 baseline: branch `gki-android13-5.15`, SHA `687d2d18d94cb2e3e72d1074778d58384d58e379`; header **v2.3.0**.
- Sources are copied byte-for-byte into `third_party/susfs/legacy-4.19/` and `third_party/susfs/upstream-v2.3.0/`. They are **not** part of the active kernel's fs/ or include/ trees. Original authors' GPL-2.0 terms must be preserved.
- Additional non-GKI v2.3.0 research reference: `wxx9248/susfs4ksu`, branch `kernel-4.9-v2`, pinned SHA `71345ded5af28f55d76ebcdc7a9df9cea56111e1`, stored in `third_party/susfs/nongki-v2.3.0-4.9-reference/`. Third-party code is **not** canonical GitLab, not a Linux 4.19 patch, and has not been applied.

## Measured baseline incompatibilities (GitHub Actions preflight)

The GitLab v1.5.5 4.19 VFS patch references 19 kernel paths but `git apply --check` **fails** on the live 4.19.325 tree. Rebase and review these conflicts rather than use fuzzy application or `--reject` in any shipping build:

| Rebase area | Rebase considerations |
| --- | --- |
| fs/Makefile | object list diverged; add source only behind independently validated Kconfig |
| fs/namei.c | may_create, lookup and open code differs; preserve vendor LSM and proper error semantics |
| fs/namespace.c | mount ID lifetime and namespace locking; no leaked/reused ids |
| fs/proc/cmdline.c | vendor command line additions; retain A17 boot parameters |
| fs/proc/task_mmu.c | changed include sequence, VMA lifecycle; no unsafe pointers |
| include/linux/mount.h | Android KABI/reserved slots differ; NEVER take nonexistent KABI reserve or overwrite kernel-private state |

Note: the 5.15 v2.3.0 native patch refers to 24 kernel files, including features absent/differently arranged in the 4.19 tree. It cannot be blindly applied even after reworking the v1.5.5 patch.

## Critical BakaSU integration collision

Pinned BakaSU `kernel/Kconfig` places **KSU_MANUAL_HOOK** and **KSU_SUSFS** in one `choice`. These are two mutually exclusive BakaSU hook strategies. Current `arch/arm64/configs/vendor/enchilada.config` selects `CONFIG_KSU=y` and `CONFIG_KSU_MANUAL_HOOK=y`, and explicitly disables `CONFIG_KSU_SUSFS`.

DO NOT flip `CONFIG_KSU_SUSFS=y`: it would switch the Root hook path, potentially disabling existing manual hooks or selecting an unsupported 4.19 strategy. A native filesystem configuration (proposed `CONFIG_SUSFS_NATIVE_419`) and an explicit BakaSU 4.19 ABI bridge must be designed and compiled separately. Its name cannot be simply aliased to the existing `CONFIG_KSU_SUSFS` symbol because the symbol controls BakaSU's alternative hook method.

## Source-to-source tasks that remain before declaring 2.3.0

1. Rebase each 4.19 native VFS hook against exact vendor source, one reviewed subsystem commit at a time. Never modify kernel mode implicitly or with fuzzy hunks.
2. Port v2.3.0 core + ABI declarations, `sus_path_loop`, mount hiding, kstat, `open_redirect`, mapping and procfs features with proper 4.19 function prototypes, and do not remove SELinux permission enforcement.
3. Bridge BakaSU supercalls and credential/UID predicates without replacing its existing manual hooks. Check `reboot` interception and initialize-before-use rules.
4. Ensure 32-bit compat syscall and file APIs work; retain 4.19-specific `file_operations`, not 5.15 `proc_ops`. Include all offsets and errno behavior in unit tests.
5. Audit mount allocator and ID reuse, RCU memory lifetimes, lock order, namei hot path; ensure no allocation/sleep from atomic context and no stale references on unload.
6. Add ABI source tests matching pinned upstream `SUSFS_VERSION=v2.3.0`; reject merely changing version strings or copying code without native VFS wiring.
7. Build Linux 4.19.325 from exact source+toolchain in CI with `CONFIG_SUSFS_NATIVE_419=y` and the existing `CONFIG_KSU_MANUAL_HOOK=y`; require complete link and zero new build errors; do not make flashable zip until build+functional testing succeeds.
8. Check no root regression; test path lookup/stat, namespace clone, bind mount, recursive mount, concurrent updates, SELinux, camera, modem, WLAN, encrypted userdata, charging, and recovery.
9. For low power and performance: avoid persistent polling / daemon; keep unmatched rules in O(1) fast rejection path, no RCU stalls, compare p50/p95 lookup/open/stat with control kernel and 100 suspend/resume cycles; collect actual idle power rather than claim savings.
10. Preserve verified known-good boot image/rollback; release any boot image only after real boot and repeated functional validations.

## CI interpretation

`susfs-419-native.yml` is a **read-only preflight**, intentionally not a native port build. A green run indicates the audit completed and produced its artifact, not that patch integration works. Treat any `[BLOCKED]` line as release-blocking.

When implementation truly compiles, rename or add a separate job with a hard requirement `SUSFS_VERSION=v2.3.0`, `CONFIG_SUSFS_NATIVE_419=y` and a real `Image.gz-dtb` link. Until then: keep this PR as Draft and keep the current OnePlus 6 kernel unchanged.
