/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef _UAPI_LINUX_OP6_KPM_H
#define _UAPI_LINUX_OP6_KPM_H
#include <linux/types.h>
#include <linux/ioctl.h>
#define OP6_KPM_ABI_VERSION 1
#define OP6_KPM_MAX_FILE (8U * 1024U * 1024U)
#define OP6_KPM_CAP_INSPECT 1U
struct op6_kpm_abi {
    __u32 version, caps, max_file, active_modules;
    __u32 reserved[4];
};
struct op6_kpm_inspect {
    __s32 fd;
    __u32 flags, size, reserved;
    char name[32], version[12], license[32], author[32];
};
#define OP6_KPM_IOCTL_GET_ABI _IOR('K', 0x60, struct op6_kpm_abi)
#define OP6_KPM_IOCTL_INSPECT _IOWR('K', 0x61, struct op6_kpm_inspect)
#endif
