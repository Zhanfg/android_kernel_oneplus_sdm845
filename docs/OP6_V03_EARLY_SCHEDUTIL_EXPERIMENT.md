# OP6 v0.3 early schedutil experiment

**Isolation:** builds on the user-booted v0.2 BakaSU 4.19.325 source lineage but is not merged into it.

## Change
Only the compile-time default CPU governor Kconfig is changed:
- `# CONFIG_CPU_FREQ_DEFAULT_GOV_PERFORMANCE is not set`
- `CONFIG_CPU_FREQ_DEFAULT_GOV_SCHEDUTIL=y`

The v0.2 running phone reports both CPU policies on schedutil, `up_rate_limit_us=500`, `down_rate_limit_us=20000`, stable 4.19.325 BakaSU and working system/UI. This experiment specifically investigates **early boot before ROM policy selects schedutil**, not interactive speedups from changed throttling. No other governor, clocks, thermal, SELinux, SCHED_WALT, cgroups, KSU, modules, /data or Recovery code altered.

## Checks
- 4.19 kernel compiler, BakaSU and appended DTB integration same as known build
- Explicit CI assert default governor flags, SECCOMP, multi-manager, EROFS, WALT preserved
- CI upload v03 kernel image, ccache stats, .config, DTB hashes and AK3 *experimental*, not signed ROM OTA
- No assertion of energy savings until matched user-device boot and battery/thermal/frequency residence measurements

## Gate for a flashable experimental Boot
Compare baseline and candidate 64 MiB Boot Header, original ramdisk, DTBs (byte/order), AVB Hash Footer, reproducibility and estimated security risk. Image must be test-booted first with a recovery path. Do not flash experimental AK3 from stock AOSP recovery, and do not overwrite slot A merely to measure early boot.

## Local measurement guidance
Use the dedicated read-only residency and phase-timed sampler on both builds under identical screen, charging, brightness, thermal environment. Big-cluster `scaling_cur_freq` snapshots alone do not measure energy. Kernel default governor improvement, if any, is limited to the early boot window where the ROM has not overridden the policy.
