# OnePlus 6 Linux 4.19 — CPU Boost / DSI shutdown stability

Branch: `feature/enchilada-power-correctness`
Parent: `feature/enchilada-power-efficiency-v1` (`21b14a99c78883b55b0e1e35c8ceca25994fc3fa`)

## Stability fixes

1. `drivers/cpufreq/cpu-boost.c` — check each initialization result, do not use a null kobject after allocation failure, do not silently report success if input handler registration fails. On failure remove only created sysfs nodes, release the kobject, unregister the CPUFreq notifier and destroy the workqueue. Successful initialization and runtime tuning behavior unchanged.
2. `techpack/display/msm/dsi/dsi_panel.c` — on shutdown, retain the *first* error from optional panel GPIO/pinctrl/regulator cleanup, while continuing to attempt every later cleanup operation. Previously a later successful regulator operation masked a failed panel suspend pinctrl operation. No display timings, brightness, DSI commands, power sequencing or panel selection modified.

## Review and verification

- CFI/LTO arm64 compile still required.
- Inject error returns in test harness for sysfs allocation/input registration and for pinctrl/regulator shutdown; confirm no null deref, no resource leak and correct error propagation.
- Bootloop rescue image and actual hardware regression remain required.
- This is a **correctness** change, not a measured battery-life gain. It can help diagnosing a screen-off power-path failure, but does not by itself force lower power.
- Do not merge directly to stable until boot and screen-on/off cycles validate.

This branch is not wired into full kernel Actions until the already-running CPUFreq PR #15 compile is checked, to avoid needless parallel whole-kernel rebuilds.

## OnePlus 6 默认 Governor：Schedutil

核查 `drivers/cpufreq/Kconfig`，CPUFreq 默认 `choice` 为 `performance`，即开机时固定最高档；仅 `CONFIG_CPU_FREQ_GOV_SCHEDUTIL=y` 不会把它变成启动默认调频器。本分支专门在 `arch/arm64/configs/vendor/enchilada.config` 设置 `CONFIG_CPU_FREQ_DEFAULT_GOV_SCHEDUTIL=y`，保留 Performance 作为必要的回退实现。同步在对象编译 CI 的 `olddefconfig` 结果中强制校验。

请注意 Android Power HAL 或 init.rc 后续仍可写 governor，实际运行时应读取两个 policy 的 `scaling_governor`。此更改不会降低 CPU 最高频率，实际续航效果尚未验证。
