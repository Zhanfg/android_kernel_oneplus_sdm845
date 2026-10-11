# Native KernelPatch for OP6 — Stage 2B (2026-10-11)

## Unambiguous goal
KPM loader, AArch64 ET_REL relocation, hook engine and lifecycle integrated at source level into the OnePlus 6 (Linux 4.19.325, Android 17, BakaSU) kernel. Boot binary must never require an external KPatch-Next binary injection. BakaSU remains the **only** root and permission manager. The external UI should be only a KSU WebUI; no APatch service, syscall-45 root backdoor or second SU stack.

## Upstreams
- Latest current official KernelPatch main: `bmax121/KernelPatch@f36f3d1377004871f8c964f7cd3276712eeba943`, dated 2026-10-10 UTC.
- Latest official release observed: `0.13.9`, published 2026-09-24.
- KPatch-Next legacy comparison only: `KernelSU-Next/KPatch-Next@456744b29efb9989445463ab29e368fa59a103c4` dated 2026-08-30.
- All upstream files are kept verbatim under third_party/kernelpatch; see UPSTREAM_MANIFEST.json.
- Upstream is GPL licensed; preserve original SPDX and attribution. Update via review PR, not blind source replacement.

## Actually implemented at this commit
- Existing Stage 2A ARM64 KPM ELF64 inspector, versioned `/dev/op6-kpm` ioctl, capability checks and CLI.
- **New:** Linux 4.19 adapted KernelPatch upstream ELF RELA relocation and AArch64 instruction immediate encoder, built into standalone objects with explicit `CONFIG_OP6_KPM_RELOCATION`.
- Fix a 64-bit immediate width integer-overflow bug from the imported version (no 32-bit `1 << 64`).
- No changes to boot-tested v0.3 branch or its BakaSU core.
- New branch-specific object-build CI for relocation code.

## Still required before executable KPM can be enabled
1. ELF loader: strict section/range validation and unsigned relocation checks before mapping executable memory.
2. Symbol resolver whitelist/ABI, including CFI/LTO jump-table handling, validate no second SU hooks.
3. Hook engine port (ARM64 instruction rewriting, text patching safety and suspend/resume), architecture-specific 4.19 and SDM845 hardening.
4. Kernel-owned LOAD, UNLOAD, CONTROL, LIST and event lifecycle ioctl operations, verified BakaSU authorization and SELinux enforcement.
5. Minimal WebUI module, with two-stage confirmation and safe disable after a bootloop; optional persistence **off by default**.
6. Build & real device A/B tests for plain KP core, one KPM at a time, clean fallback Fastboot BOOT. No unknown boot or ROM image combinations.
7. Upstream sync should be a machine-opened review PR and run compilation on the pinned snapshot; never auto-merge.

## Safety notice
**NOT FLASHABLE FOR KPM USE.** The relocation objects are compiled but no executing KPM module loader is wired to the ABI. Existing `/dev/op6-kpm` still exposes INSPECT only. Re:Kernel-native PR #23 is not a substitute for KPM support.
