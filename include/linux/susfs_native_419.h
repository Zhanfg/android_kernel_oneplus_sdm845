/* SPDX-License-Identifier: GPL-2.0 */
#ifndef _LINUX_SUSFS_NATIVE_419_H
#define _LINUX_SUSFS_NATIVE_419_H

/* Translate SUSFS 2.3.0 ABI without changing BakaSU's manual-hook selector. */
#ifdef CONFIG_SUSFS_NATIVE_419_PATH
#define CONFIG_KSU_SUSFS_SUS_PATH 1
#endif
#ifdef CONFIG_SUSFS_NATIVE_419_MOUNT
#define CONFIG_KSU_SUSFS_SUS_MOUNT 1
#endif
#ifdef CONFIG_SUSFS_NATIVE_419_KSTAT
#define CONFIG_KSU_SUSFS_SUS_KSTAT 1
#endif
#ifdef CONFIG_SUSFS_NATIVE_419_UNAME
#define CONFIG_KSU_SUSFS_SPOOF_UNAME 1
#endif
#ifdef CONFIG_SUSFS_NATIVE_419_LOG
#define CONFIG_KSU_SUSFS_ENABLE_LOG 1
#endif
#ifdef CONFIG_SUSFS_NATIVE_419_HIDE_SYMBOLS
#define CONFIG_KSU_SUSFS_HIDE_KSU_SUSFS_SYMBOLS 1
#endif
#ifdef CONFIG_SUSFS_NATIVE_419_CMDLINE
#define CONFIG_KSU_SUSFS_SPOOF_CMDLINE_OR_BOOTCONFIG 1
#endif
#ifdef CONFIG_SUSFS_NATIVE_419_OPEN_REDIRECT
#define CONFIG_KSU_SUSFS_OPEN_REDIRECT 1
#endif
#ifdef CONFIG_SUSFS_NATIVE_419_MAP
#define CONFIG_KSU_SUSFS_SUS_MAP 1
#endif

#ifdef CONFIG_SUSFS_NATIVE_419
#include <linux/cred.h>
#include <linux/jump_label.h>
#include <linux/sched.h>
#include <linux/thread_info.h>
#include <linux/susfs_def.h>
#include <linux/susfs.h>
extern bool susfs_is_current_ksu_domain(void);
extern struct static_key_true susfs_is_sdcard_android_data_not_decrypted;
extern bool susfs_is_inode_sus_path(struct inode *inode);
extern const struct qstr susfs_fake_qstr_name;
extern struct filename *susfs_open_redirect_spoof_do_sys_openat(struct inode *inode);
struct mount;
extern int susfs_get_non_sus_mnt_id_from_mnt(struct mount *orig_mnt);
extern struct vfsmount *susfs_get_non_sus_vfsmnt_from_vfsmnt(struct vfsmount *mnt);
#endif

#endif /* _LINUX_SUSFS_NATIVE_419_H */
