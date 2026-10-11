# OnePlus 6 Linux 4.19 — Power efficiency v1

Parent: `feature/enchilada-io-net-ipset-ep`
Scope: **targeted CPUFreq work reduction**. No changes to device tree, GPU or panel frequencies, voltage, thermal limits, charger, frequencies or touch boost thresholds.

## Implementation

File: `drivers/cpufreq/cpu-boost.c`

Before, `update_policy_online()` invoked `cpufreq_update_policy(cpu)` for *each* online CPU at input boost on and off. In Linux 4.19, several CPUs share `struct cpufreq_policy`. Repeated invocation on siblings leads to redundant `policy->rwsem` acquisition and repeated `cpufreq_set_policy`/notifier processing. Snapdragon 845 normally has one CPUFreq policy per cluster (confirm actual runtime).

After, while `get_online_cpus()` locks CPU hotplug against changing the set of online CPUs, this function gets each CPU's policy with `cpufreq_cpu_get()`, calls the update only when `policy->cpu == cpu`, then releases it with `cpufreq_cpu_put()`. This keeps the policy representative set and avoids an allocation or persistent cache.

- The boost frequencies and `input_boost_ms` are unchanged.
- `cpu_boost` sysfs ABI is unchanged.
- `sched_set_boost()` semantics are unchanged.
- No new timers, kernel threads, or daemon.
- Still runs on the existing boost workqueue and only when input boost is configured.
- **No battery-life or performance improvement claimed until measured**. If only one CPU per policy is online, this change has little effect.

## Verification

1. Compile Linux 4.19 arm64 and DTBs with unchanged BakaSU/CFI/LTO flags.
2. Compare frequency policy transitions, touch latency and p95/p99 frame time with prior branch.
3. Verify CPU hotplug: CPUs move offline/online without missed boost.
4. Check 50 sleep/wake and touchscreen regressions.
5. Measure CPU idle residency and package power in equivalent scenarios, using separate baseline and candidate runs.

Real device boot and power measurements pending. The panel and GPU idle timing remain untouched until the independent read-only power audit establishes a baseline.

Related audit: `docs/ENCHILADA_POWER_DISPLAY_AUDIT.md` in `audit/enchilada-power-display-20261011`.
