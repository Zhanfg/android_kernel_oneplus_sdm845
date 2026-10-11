# OnePlus 6 / enchilada power-integrated v1 — experimental

Base: `feature/enchilada-io-net-ipset-ep`.
Includes the changes of CPUFreq PR #15 + CPU/DSI correctness PR #18 + KFENCE PR #16 and the read-only power/display probe PR #13.
**No EP/eBPF runtime backport is included.**

- CPU Boost: deduplicated shared-policy updates, without changing boost strengths/timing.
- Init robustness: clean CPU boost resource unwind, error propagation.
- Boot governor: `schedutil` on this device, without restricting maximum CPU clocks; Android Power HAL may override it.
- DSI panel power-off: continue cleanup and preserve first error; no change in display timing, panel refresh (60Hz), ULPS commands, or voltage.
- KFENCE sampling: deferrable work timer; may defer safety sampling during extended idle, but feature remains enabled.
- I/O: selectable Kyber/mq-deadline plus BFQ as existing, no forced active queue switch.
- Networking: BBR v1 + FQ/FQ-CoDel and kernel Netfilter IPSet enabled but not forced as global defaults.

## Safety boundary

The CI only proves the image builds and DTB append ordering stays intact. No boot/run-time compatibility with a specific ROM, no standby drain, frame latency or battery gain is asserted. Back up your matching ROM's original `boot.img`, secure recovery/fastboot before attempting any AK3 flash.

## Validation

- [ ] CFI/LTO arm64 full kernel and AK3 ZIP
- [ ] Kconfig: `CONFIG_CPU_FREQ_DEFAULT_GOV_SCHEDUTIL=y`, `CONFIG_KSU=y`, `CONFIG_KFENCE=y`
- [ ] three SDM845 appended DTBs in ROM order
- [ ] ZIP SHA256 integrity
- [ ] OnePlus 6 real boot, stable display, Wi-Fi/cellular/camera/audio/fingerprint/charging
- [ ] 50x display sleep/resume and screen-off baseline
- [ ] CPUFreq boost A/B and KFENCE sample behavior
- [ ] UFS Hibern8 and GMU deep-idle/power vote comparison

Companion source: `tools/op6-power-display-probe.sh` (read-only, no arguments, Android shell), and `docs/ENCHILADA_POWER_DISPLAY_AUDIT.md`.
