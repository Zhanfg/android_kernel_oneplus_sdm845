/* SPDX-License-Identifier: GPL-2.0 */
#ifndef _LINUX_SUSFS_NATIVE_419_H
#define _LINUX_SUSFS_NATIVE_419_H

/*
 * The pinned BakaSU Kconfig has mutually exclusive hook choices:
 * KSU_MANUAL_HOOK and KSU_SUSFS.  Keep MANUAL_HOOK selected, and
 * translate independently gated 4.19 VFS features only in those
 * source files which intentionally include this header.  Do NOT
 * globally define CONFIG_KSU_SUSFS: that would switch root hooks.
 */
#if defined(CONFIG_SUSFS_NATIVE_419_UNAME)
#define CONFIG_KSU_SUSFS_SPOOF_UNAME 1
#endif

#if defined(CONFIG_SUSFS_NATIVE_419_PATH)
#define CONFIG_KSU_SUSFS_SUS_PATH 1
#endif

#endif
