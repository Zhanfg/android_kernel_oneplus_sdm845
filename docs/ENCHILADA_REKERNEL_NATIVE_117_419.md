# OnePlus 6 / Android 17 / Linux 4.19.325 — Re:Kernel native integration

## Source provenance
- Official upstream: https://github.com/Sakion-Team/Re-Kernel
- Reviewed latest official release at implementation time: 11.7 (2026-09-16).
- Pinned upstream main commit: `ac08296174d7fb2801c0eee1084f067a34f8a0fe` (2026-09-20).
- User-provided ReKernel-X v9.2 fork: `myflavor/ReKernel-X@6f9f96dfc725ce12410c8258464a6edd7ec8ca36`; not applied blindly, because v9.2 patches are older.
- Native integrate sources preserved under `drivers/rekernel` with minimum Linux 4.19 compatibility and safety adjustments.
- License: upstream GPL-2.0.

## Integration decisions
- Kernel baseline remains *boot-confirmed* clean BakaSU v0.3 `719137c71bb5c3e59d0745a1c4ad712fedd59494`. No edits to this baseline.
- Re:Kernel added as a built-in option with `CONFIG_REKERNEL=y` in the OP6 device config only. Native Netfilter path deliberately disabled by default: `CONFIG_REKERNEL_NETWORK=n`.
- Preserve BakaSU manual hooks, CFI, LTO, CPU governor, existing binder queue mechanics, exact 3 DTBs and RAMDISK/boot headers.
- Integrate Binder reply, normal transaction, low async space (rate-limited), and termination signal event reporting. Never replace or evict Binder transactions from a queue.
- Re:Kernel netlink/proc setup at boot `late_initcall`, not lazily from Binder critical path.
- Apply JOBCTL_TRAP_FREEZE import and Cgroup freezer v1/v2 compatibility to native header.
- No KernelPatch core, no KPM payload, no automatic KPM loading. This is **not** a fix or proof of compatibility for external kpatch-next/nohello/ReKernel KPM.

## Safety
- Experimental. Compile pass != successful device boot. Maintain original clean v0.3 fastboot image.
- Do not load `ReKernel.kpm` while native Re:Kernel is active; this duplicates its event backend.
- CI: full kernel + DTBs + exact byte order + AK3 artifact. Production flash blocked until phone boot, binder activity, suspend and root regressions pass.
