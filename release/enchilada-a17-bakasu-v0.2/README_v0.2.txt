OnePlus 6 / enchilada / Android 17
BakaSU 4.19.325 — v0.2 SAFE PACKAGING RELEASE
2026-10-10

状态：已取得用户反馈：上一版完整 Boot 可以正常启动。
本次 v0.2 的内核和 Ramdisk 字节未更改，仅改进了 AK3 安装器及发布包校验。
本次 AK3 ZIP 尚未在真机恢复环境中验证刷写，绝不能视为正式稳定版。

文件：
1. OnePlus6_A17_BakaSU_4.19.325_v0.2_BOOT_USER_TESTED.img
   与用户先前成功启动的 BakaSU TEST boot.img 逐字节一致。
   可供已解锁引导加载程序的 Fastboot 启动/刷写，不要求手机 Root。
2. OnePlus6_A17_BakaSU_4.19.325_v0.2_AK3_GUARDED_UNTESTED.zip
   限定 OnePlus 6 和当前 Android 17 ROM，针对两个确切的 boot SHA256
   才允许写入启动槽；镜像写入后重新读取和比对哈希。
   这个 ZIP 不是 AOSP Recovery 支持的 OTA 签名包，原生 Recovery sideload 会报 Error 21。
3. OnePlus6_A17_ORIGINAL_BOOT_ROLLBACK.img
   上传的原始 ROM Boot 备份，仅适用于对应的旧 ROM 与槽位，未证明
   可恢复更新后的不同 ROM。请同时备份设备当前真实运行的 boot 分区。
4. RELEASE_MANIFEST_v0.2.json / SHA256SUMS
   每个镜像与 ZIP 的固定校验值；建议下载后先核验。
5. OP6_PostFlash_Smoke_ReadOnly.sh
   手机可无参数执行的只读启动自检脚本，输出 TXT 到 Download。

安装：
- 已经通过上一版 boot 成功启动且管理器、Seccomp 都正常：无需重复刷写 v0.2 Boot。
- 使用 Fastboot 前确认 bootloader 已解锁并备份当前启动槽 boot 镜像。
- 可优先尝试 fastboot boot <v0.2-BOOT_USER_TESTED.img>，不成功时停止。
- 若决定永久写入，请先运行 fastboot getvar current-slot；确保设备和槽位无误，
  只向当前正确的 boot_a 或 boot_b 写入相应镜像。
- 不要把文件刷入 recovery、vendor_boot 或 dtbo；不要清除 userdata。
- 从未验证的新 ROM 或改过的 Boot 上，AK3 安装器会拒绝写入。
- 不能在原生 AOSP Recovery 中 sideload 上述 AK3 ZIP。

本次测试（本地模拟，非手机刷机实测）：
PASS: Android Boot Header v1 / AVB NONE+Hash / 64MiB
PASS: 内核、Ramdisk、3 个 DTB 与指定测试镜像一致
PASS: AK3 ZIP 完整性、执行权限元数据
PASS: ROM Boot -> 测试 Boot 的伪块设备模拟写入
PASS: 已安装同版本 Boot 则不写入
PASS: 未知 Boot、槽位不匹配、丢失 payload 均在写入前拒绝

后续版本：单独测试 CPU/GPU 调度、PSI/ZRAM 和 UFS，确保性能数据和稳定性后再加入。
不要误把安全打包版 v0.2 当成“提升 CPU 性能的新内核”。