# OnePlus 6 / BakaSU v0.3 - Native KPM milestone 2A

This branch now implements a real in-kernel ABI device and kernel-side ELF metadata inspector, not just a design document.

- Source: drivers/op6_kpm/kpm_core.c; UAPI include/uapi/linux/op6_kpm.h.
- /dev/op6-kpm: 0600, CAP_SYS_MODULE required, no SELinux bypass.
- GET_ABI: version=1, inspect capability, max file 8 MiB, active modules 0.
- INSPECT: regular-file fd, bounded ELF64 little endian ARM64 ET_REL, required KPM metadata and init sections. Does NOT execute arbitrary code.
- Unknown ioctl commands return ENOTTY. LOAD/UNLOAD/CONTROL do not exist yet.
- Build-time CONFIG_OP6_KPM_RUNTIME defaults n. This feature branch alone enables it in OP6 device config.
- tools/op6_kpmctl.c is a native companion CLI source: status, inspect. Requires Android NDK compilation before phone use.
- CI only compiles a real kernel driver object rather than a full boot image at this milestone.

Next: ARM64 ELF relocations, safe symbol resolver, hook and lifecycle engine, BakaSU authorized controlled LOAD/UNLOAD/CTL0, KSU WebUI, rollback. DO NOT claim this driver runs nohello, ReKernel.kpm or any other KPM yet. Original boot-confirmed 719137c7 stays unchanged.
