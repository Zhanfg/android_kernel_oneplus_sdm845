# OP6 / BakaSU v0.3 — Native KPM Runtime design (NOT IMPLEMENTED YET)

**Status:** Design and first-stage offline ELF preflight only. This branch CANNOT load any KPM in a running kernel. Never describe it as a native loader or a flashable update.

## Goal
- Keep the exact boot-confirmed OP6 Android17 BakaSU v0.3 image at commit 719137c7 as recovery baseline.
- Build **source-level KPM runtime** inside the kernel once, then load standard ARM64 .kpm modules without running \`kpatch\` or binary patching BOOT again.
- KPM must retain KernelPatch ELF metadata and init/ctl0/exit ABI. Standard Linux .ko is not a compatible substitute.
- Root policy remains solely BakaSU; do NOT import KernelPatch credential escalation, SELinux bypass or alternate root manager.

## Upstream audit (checked 2026-10-11)
- KernelSU-Next/KPatch-Next (main SHA 456744b29efb9989445463ab29e368fa59a103c4, 2026-08-30): genuine loader is \`kernel/patch/module/module.c\` plus \`relo.c\`, \`insn.c\`, symbol linker, executable-memory/hook allocator; user interface is \`SUPERCALL_KPM_{LOAD,UNLOAD,CONTROL,LIST,INFO}\` via syscall number 45 and native \`user/kpm.c\`.
- **DO NOT** import its \`supercall.c\`, \`accctl\`, \`bypass_kcfi\`, SELinux bypass or root management. Patching syscall 45 / truncate is fragile and conflicts with policy.
- SukiSU-Ultra/builtin (SHA 6c284e957feaa9a388a9f1c37dc4ec80d95e434b) has \`CONFIG_KPM\` but its \`kernel/kpm/kpm.c\` implementation exported to KSU is largely **Stub function**; enabling CONFIG_KPM alone does not provide a working ELF runtime.
- Re:Kernel PR #23 is an *application-specific Binder/Signal monitoring backend*; it is NOT the general-purpose KPM loader. Keep it independent; combining ReKernel.kpm with native Re:Kernel duplicates work.

## Native ABI and control plane (target)
\`\`\`
Authorized KernelSU WebUI
      |
  kpmctl --json [status | list | inspect FILE | load FILE | unload NAME | ctl0 NAME ARGS]
      |
 /dev/op6-kpm [ioctl ABI v1, not writable /proc or string-parsed commands]
      |
 in-kernel registry+ELF parser+ARM64 relocation+safe RX memory+Hook backend
\`\`\`
1. \`GET_ABI\`, \`GET_CAPS\`, \`LIST\`, \`INFO\` read-only. \`LOAD\`, \`UNLOAD\`, \`CTL0\` mutation requests.
2. Only BakaSU-verified authorized manager/daemon identity and matching SELinux context may mutate. UID 0 by itself is not sufficient. Limit module count, memory, file size, arguments, copy_to/from_user lengths.
3. Load from a verified, private, root-owned location; reject symlinks, writable-by-app paths, incompatible ELF, unknown ABI, duplicate names and non-approved hashes. Never accept arbitrary WebUI-provided absolute file paths.
4. Validate ELF and metadata outside the kernel first, then repeat authoritative checks inside the kernel; offline verifier is NOT a code-security guarantee.
5. Use W^X memory with proper ARM64 icache handling. Do not bypass CFI or SELinux globally. Pin lifecycle state under mutex; reject unload for active hooks without safe quiescence. Never blindly write arbitrary kernel addresses.
6. For boot persistence use an opt-in \`post-fs-data\`/boot-completed service to replay **approved** modules, one at a time after Android starts, with a rollback journal; never auto-execute unverified KPM before userspace.
7. Circuit breaker: on repeated boot failure, disable replay; rescue mode defaults to zero KPM. Preserve pristine v0.3 BOOT for Fastboot rollback, even when WebUI data is damaged.
8. The UI is a consumer of \`kpmctl\`, not privileged independently. Use the existing KernelSU WebUI environment for authorization. HTML has no direct access to the kernel.

## Explicitly deferred
- True build-time embedded KPM: optional later. Requires explicit allowlisting and recovery plan; avoid embedding changing third-party ELF modules into BOOT.
- External kpatch-next KPM A/B tests are not prerequisite for the native loader, but new runtime needs its own smoke tests on real hardware.
- PR #23 native Re:Kernel is optional; no reason to force it into the KPM platform.

## Milestone gates
1. (This commit) pin upstream, formalize ABI, preflight ARM64 ET_REL ELF metadata with negative fixtures in CI.
2. Port relocation + symbol resolver + KPM lifecycle backend into BakaSU 4.19 with no Root or syscall-45 code, behind \`CONFIG_OP6_KPM_RUNTIME\` **default n**.
3. Independently test KPM hello/ctl0/unload with malformed binary rejection, weak memory pressure, W^X and hook tests. Then expose verified KPM CLI.
4. Build a thin KernelSU WebUI, validate permissions and safe-mode recovery. Only afterwards produce a Fastboot BOOT for real-device validation.
