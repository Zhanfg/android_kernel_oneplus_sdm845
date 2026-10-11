# OnePlus 6 Linux 4.19: I/O + Network + AxIPSet + EP

Development branch: `feature/enchilada-io-net-ipset-ep` (based on experimental BakaSU manual-hook branch, **not** upstream stable). All functionality below is experimental until real-device testing.

## What this revision actually implements

- Add an **opt-in Kconfig fragment** `arch/arm64/configs/vendor/enchilada-perf-experimental.config`.
- Enable selectable `mq-deadline` and `kyber` I/O schedulers; original BFQ remains available. **No runtime/default scheduler switch.**
- Compile selectable FQ and FQ-CoDel queueing and upstream Linux 4.19 BBR v1. **No default TCP/qdisc switch**; no unverified BBRv3 backport.
- Enable kernel-native dual-stack IPSet hashes and existing Netfilter set matcher. This uses existing kernel data structures instead of introducing an additional per-packet hook.
- Add `tools/axipset.sh`: own small interactive **AxIPSet management layer**, IPv4 + IPv6 hash:net sets, add/delete/test and staged-file import. It does **not** install, alter, or flush firewall rules.
- Add read-only `tools/op6-perf-probe.sh`: inventories storage schedulers, current TCP/qdisc, kernel IPSet and EP/BPF prerequisites. Results are saved to `/sdcard/Download` when available.

The **AxIPSet control plane is our own; the in-kernel IPSet engine is the established Netfilter implementation**. An original in-kernel engine/algorithm should be considered only if measurements demonstrate a reproducible bottleneck. This avoids redundant memory, new lock contention and mobile idle-power regressions.

## Why no default performance tuning yet?

The OnePlus 6 uses UFS. Optimal scheduler settings cannot be assumed from desktop/storage benchmark data. CPU wakeups, mixed read-write tail latency, fsync p95/p99, background app restore and suspend residency matter as much as raw throughput.

Proposed A/B matrix on the same boot image, storage occupancy, thermal baseline and workload:

| Area | Baseline | Candidate | Measurements |
| --- | --- | --- | --- |
| I/O | actual UFS scheduler | mq-deadline / kyber / BFQ where supported | mixed IOPS, p95/p99 latency, CPU% and watts |
| TCP | actual runtime default (likely CUBIC) | BBR v1 on selected test sockets | latency under load, fairness, retransmits |
| Qdisc | actual runtime default | fq_codel / fq when attachable | p95 RTT under upload and download saturation |
| IPSet | direct rules | AxIPSet hash:net | rule count, lookup latency, memory, update delay |
| EP | current no-EP kernel | gated prototype | Binder latency, ANR/overflow detection accuracy, event drop, idle drain |

A config flag being present **does not prove the feature is active on UFS/wlan/cellular**, nor that it is faster.

## EP (Re:Kernel eBPF) status: not integrated yet

The existing Re:Kernel project has two materially different paths:
1. Legacy <= 5.4 in-tree binder/signal/network hooks in `Integrate/rekernel`.
2. Modern eBPF and LKM sources with separate userspace protocol and kernel API expectations.

Linux 4.19.325 does not inherit modern BTF/CO-RE, fentry, or LKM 5.10+ guarantees. Replacing kernel Binder paths or registering global Netfilter handlers before inspecting the exact driver/hook API is unsafe. Do not claim `CONFIG_BPF_SYSCALL=y` means the modern eBPF EP backend is operational.

**Required for EP completion**, as a separate auditable PR: confirm Binder tracepoints (transaction/reply/free-buffer-full), frozen-state access, signal lifecycle, network wake events, compatible userspace protocol; implement bounded ring events; enforce privileged-only control; keep all hot-path tracing off until registered; benchmark event overhead and test boot/SELinux/ANR regression. Neither LKM nor eBPF userspace is bundled here.

## Running the tools

On an Android root shell capable of executing `.sh` files:

- `sh op6-perf-probe.sh` (read-only; no arguments, report goes to Download).
- `sh axipset.sh` (interactive; no arguments; requires root and available `ipset` userspace executable).

AxIPSet import: absolute path to a text file with one IPv4/IPv6 address or CIDR per line, `#` comments allowed. Each family is replaced by a separate atomic swap, not an all-family transaction. Do **not** use it for production firewall policy before verifying set references and restore behavior on the real device. `ipset` lists are initially unreferenced and have no packet-flow effect.

## Before any flash

Build Verified != Boot Verified != Runtime Verified. Preserve original ROM `boot.img` and rescue capability. CI ZIP is only experimental. Do not flash a bare `Image.gz-dtb` as `boot.img`. Keep source branch/commit, SHA256 and actual ROM version in the test report.
