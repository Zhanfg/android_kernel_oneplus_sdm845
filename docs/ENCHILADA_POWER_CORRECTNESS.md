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
