OnePlus 6 / Android 17 / Linux 4.19.325
BakaSU and standard KernelSU compatibility audit — 2026-10-10

CONFIRMED in actual artifact #11667878906 (run #38047957426), kernel.config:
  CONFIG_KSU=y
  CONFIG_KSU_MANUAL_HOOK=y
  CONFIG_KSU_MULTI_MANAGER_SUPPORT=y
  CONFIG_KSU_MANUAL_HOOK_AUTO_SETUID_HOOK=y
  CONFIG_KSU_MANUAL_HOOK_AUTO_INITRC_HOOK=y
  CONFIG_KSU_MANUAL_HOOK_AUTO_INPUT_HOOK=y
  # CONFIG_KSU_DISABLE_MANAGER is not set
  # CONFIG_KSU_DISABLE_POLICY is not set
  CONFIG_SECCOMP=y
  CONFIG_SECCOMP_FILTER=y
  CONFIG_SECURITY_SELINUX=y
  # CONFIG_KSU_SUSFS is not set

IMPORTANT DISTINCTIONS:
- Seccomp = 0 in the BakaSU Manager app refers to the manager process's own
  PR_GET_SECCOMP result, not a kernel compile-time feature flag. A manager
  process may be unfiltered even while system_server or zygote is filtered.
- The active manager list is runtime, signed-APK discovery. It does not have
  an additional kernel Kconfig toggle. The pinned BakaSU kernel accepts its
  own built-in signature and official tiann/KernelSU and KOWX712 signatures;
  custom builds require an approved dynamic signature and appropriate API.
- BakaSU IS a KernelSU downstream with KernelSU-compatible policy and su
  machinery. Do not compile the original KernelSU core and BakaSU together:
  that would create duplicate root hooks/ioctl behavior and stability risks.
- The BakaSU Manager kernelUAPI must match the installed managerUAPI to be
  fully featured. An old or separately signed app may not support modern API.
- Userspace /data/adb/ksud and init event integration are necessary for full
  module lifecycle, even when the root driver is embedded in the boot image.

LIKELY CAUSES of empty "active managers" (not yet device-confirmed):
1. Early post-fs-data manager scan missed APK/package metadata readiness.
2. Boot completed ksud userspace event did not execute.
3. Manager app signature mismatch, unexpectedly different APK/build.
4. Manager kernel/manager UAPI mismatch or list ioctl failure.
5. Home screen simple mode hides the whole list, distinct from "none".

SAFETY-FIRST PATCH CANDIDATE:
If no manager is registered by on_boot_completed, trigger a single synchronous
BakaSU upstream-signed manager scan; otherwise retain normal prune-only path.
No manager is artificially registered, no signature bypass, no universal
Seccomp filter, and no SELinux bypass. This is a hypothesis for real-device
validation; a newly compiled image alone will not prove the condition is fixed.

TO COLLECT REAL EVIDENCE:
Run OP6_BakaSU_KSU_Runtime_ReadOnly_v1.sh with no parameters.
It writes /sdcard/Download/OP6_BakaSU_KSU_Runtime_YYYYMMDD_HHMMSS.txt
(or fallback directory) and changes no kernel or Android settings.
Please also capture BakaSU Manager main page displaying manager version,
kernel UAPI and manager UAPI. Avoid posting complete package databases.