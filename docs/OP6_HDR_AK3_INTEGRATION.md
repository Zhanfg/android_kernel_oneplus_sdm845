# OnePlus 6 / uwuAOSP 17 (101)：HDR 整合至 AnyKernel3

> 状态：实验性基础设施，默认关闭 HDR 打包。只允许构建完整、已核验且可回退的测试产物。当前**不提供可刷入 HDR ZIP**。

## 目标

最终交付 **一个 AnyKernel3 ZIP**，内含当前 BakaSU/4.19.325 内核，以及与 ROM 完全匹配的 Vendor Composer、平台签名 Settings.apk，通过 AK3 systemless helper 挂载。

系统显示设置中提供“允许原生 HDR 内容”开关：
- **开启：** Android 17 原生 `DisplayManager.setUserPreferredHdrMode(displayId, HDR_PREFERENCE_HDR_ALLOWED)`，仅当真实 HDR 内容和 HAL 能力满足时允许 HDR；非强制将 SDR 转为 HDR。
- **关闭：** 原生 `HDR_PREFERENCE_SDR_ONLY`，限制屏幕使用 SDR。
- 该状态由 Android 系统持久化；不依赖 Root 常驻 daemon、LSP hook 或自定义 sysfs 控制开关。

关联开发：
- HWC 源码 Draft PR：<https://github.com/Zhanfg/platform_vendor_uwu/pull/9>。
- Settings 源码 Draft PR：<https://github.com/Zhanfg/platform_packages_apps_Settings/pull/2>。
- 官方 uwu-17.0 manifest：`hardware/qcom/sm7250/display` 对应 LineageOS sm7250 display。
- 原机 Composer SHA-256：`682e40228e267c3ae07f048ea7ec1e75f38273ce9f85d0ce2612c34f4650c736`。

## 为什么是 AK3 helper 而不是内核 LKM

AnyKernel3 的 `do.modules=1` 和 `do.systemless=1` 组合可使用 KernelSU/Magisk 的 `ak3-helper` 模块映射 Vendor 与 system/system_ext 文件。当前 BakaSU 实验包原本 `do.modules=0`、`do.systemless=0`。

HWC 色彩模式映射是 Vendor 用户空间问题。**不需要为 HDR 改 BOOT/DTBO 内核代码或注入 LKM**，但用户所要求的统一 AK3 交付会继续包含原有内核镜像。

## 现有构建逻辑

普通内核构建未设置 `OP6_HDR_AK3_STAGE`，仍然生成原有纯内核 ZIP；不能把它叫作 HDR 包。

候选 HDR 私有构建要显式设置：
- `OP6_HDR_AK3_STAGE=1`
- `OP6_HDR_STOCK_COMPOSER`、`OP6_HDR_CANDIDATE_COMPOSER`
- `OP6_HDR_STOCK_SETTINGS`、`OP6_HDR_CANDIDATE_SETTINGS`
- `OP6_HDR_ABI_VALIDATOR`：由 vendor/uwu HDR PR 提供的匹配 ABI 校验工具
- `OP6_HDR_SETTINGS_PARTITION=system` 或 `system_ext`，必须与原 ROM 的 `pm path com.android.settings` 一致

构建脚本 `scripts/package-ak3.sh` 会调用 `scripts/stage-hdr-ak3.sh`，但只有以下检查全部通过才会生成 HDR_STAGING ZIP：
1. 原始 Composer SHA-256 与真机 101 基线完全相同。
2. 候选 Composer 是 ARM64 ELF，动态依赖集合与原版一致，Build ID 不同且确实包含补丁。
3. 两个 Settings APK 的包名均为 `com.android.settings`，签名证书 SHA-256 完全一致；仅靠名称或 versionCode 不满足条件。
4. 目标分区、AK3 结构和安全模式未意外改变；systemless 模块所需 `/data`、Root/ROM 信息匹配。
5. 当前无冲突的 `ak3-helper` 模块。
6. 无签名/ABI/匹配材料时**必须终止**，禁止伪造 ZIP。

注意：当前固定 AnyKernel3 代码识别 Magisk 及一部分传统 KernelSU 布局，未证明它能识别 BakaSU 全部变体。因此新增提前终止门槛，仍须在真机验证 updater 的实际模块安装成功反馈，不能仅凭 Shell 代码判定原子性。

## 验收尚未完成

- [x] 真实 Qualcomm HWC 色彩映射函数的主机侧测试
- [x] 官方 uwu-17.0 显示源码候选锁定
- [x] Android 17 原生 HDR 系统偏好 Settings 源码接入
- [x] AK3 单 ZIP systemless 辅助模块的受限打包路径
- [ ] 匹配 101 ROM 的 Composer **Soong 完整编译**
- [ ] 具原平台签名的 Settings.apk 完整编译
- [ ] APK 安装位置、SELinux、VINTF、Root 框架及文件挂载确认
- [ ] 真机测试 AK3 检测失败可在写 BOOT 前退出（当前脚本仅源级验证）
- [ ] 确认 AK3 helper 成功安装、能在 KSU 管理器中可靠卸载/回退
- [ ] SDR 无色偏，HDR10/HLG 实际输出，功耗/温度/重启测试
- [ ] 原 ROM、内核的可回退路径和设置项退出后的状态恢复

**未通过以上验证不得合并稳定分支、不得发布可刷入 HDR ZIP。**
