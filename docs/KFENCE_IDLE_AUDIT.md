# OnePlus 6 / Linux 4.19 — KFENCE deferrable sampling experiment

Baseline: BakaSU + I/O/network feature branch at 95858e26d1303427d5156aab1bd04ad4effd5111. This feature is **separate from PR #15's CPUFreq fix**.

## Scope

In `mm/kfence/core.c`, change KFENCE's periodic gate-sampling work item from `DECLARE_DELAYED_WORK` to `DECLARE_DEFERRABLE_WORK`. The Linux 4.19 workqueue implementation defines `DECLARE_DEFERRABLE_WORK` and sets `TIMER_DEFERRABLE`.

The existing sample interval (500 ms) and sample, allocation, memory-safety checks and static-key logic are **unchanged**. A deferrable timer avoids waking an otherwise idle CPU *just* to schedule the next sample. It will still execute during active operation, or after normal wake-up.

This does not disable KFENCE, change SELinux/CFI, change suspend or display timings, or add a daemon. Sampling cadence can become longer during prolonged idle, which is an intentional detection-coverage trade-off and **requires review**.

## Risks and tests

- Run kernel build with CFI/LTO and confirm CONFIG_KFENCE=y still resolves.
- Compare CPU idle residency / wakeup_source counts, wakeups per second and power draw for 30-minute screen-off periods (Wi-Fi and cellular separately).
- Verify KFENCE fault detection still works under an authorized, non-production test scenario (no kernel memory corruption injection on a daily device).
- Check deferred work events immediately after idle exit, boot/resume latency, and system suspend.
- No numerical savings/stability claim until measured.

Do not merge into PR #12 without compile and boot validation. This is a separately revertible optional experiment.
