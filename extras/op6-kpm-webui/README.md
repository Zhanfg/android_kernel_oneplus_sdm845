# OP6 KPM WebUI — UI-only preview (no executable KPM loader)
- KernelSU-compatible webroot/index.html; works when installed by BakaSU KSU module manager with WebUI support. Standalone preview *only*.
- No service.sh, post-fs-data.sh, boot.img, loader, KPM binary, or independent root management.
- Device status uses the KSU WebUI privileged exec bridge for fixed **read-only** commands; no text is spliced into a shell command.
- An unavailable KPM runtime or missing WebUI bridge is shown as unavailable. LOAD/UNLOAD/CTL are deliberately disabled until kernel ioctl ABI exposes verified capabilities, tests, and rollback.
- After kernel engine is complete, package a minimal kpmctl static Android executable inside this WebUI shell to forward authorized ioctl calls; no background daemon.
- Do not publish this as a completed KPM manager, and do not merge to stable v0.3 before runtime validation.
