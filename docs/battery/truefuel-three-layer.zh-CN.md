# OnePlus 6 / Android 17 · TrueFuel v0.4 三层适配与实机镜像核验

基线：已通过开机的 BakaSU Linux 4.19.325；用户设备 OnePlus 6 / ONEPLUS A6003 / uwuAOSP 17.0.101。
本分支是**实验源码与只读探针**，不是可刷入的 4500mAh 电量校准包，不修改当前稳定 BOOT、DTBO、VENDOR。

## 一、BOOT / Linux 内核驱动
- 实际芯片：BQ27411 (Device Type 0x0421、固件 0x0109)，总线节点 0-0055。
- 当前日志：BQ SOC=43%、OEM capacity=43%、Qualcomm real_capacity=35%、FCC=3,139,000uAh、Design=3,240,000uAh、remaining_capacity=0。
- 原驱动的 `bq27541_design_capacity()` 从设备 0x3c 读取 DesignCapacity，作为 `bms/charge_full_design` 输出；不是凭 UI 写死。
- `bq27541_remaining_capacity()` 在不允许读取时可能返回局部初始值 0，因此 0mAh 不能证明电芯实际空电。
- 原驱动的 `fg_soc_calibrate` 改写正常对外显示的容量路径；`bms/bq_soc` 绕过该软件平滑，但仍为芯片滤波后的 0x1c。
- 实验内核驱动的 `op6_truefuel_hw` 已改为 **Root-only、按需快照缓存**：读取 sysfs 不会触发 I²C，首次读取仅标记需要采样；原有约 12 秒放电轮询允许读取时，采集 `0x1c/0x30` SOC、`0x0c/0x28` RM、`0x0e/0x2c` FCC、`0x3c` DesignCapacity。60 秒内读取缓存不增加 I²C 事务；充电、快充、休眠和 DataFlash 平滑配置时不强制采样。
- 驱动修复 `bq27541_remaining_capacity` 在禁止读取阶段返回临时变量初始值 0 的问题：改为保留最近一次成功读数，尚无成功样本时初始值仍为 0，绝不推算出虚假 4500mAh。
- LKM v0.3 删除了对 0x55 的独立直接 I2C 访问，防止与内核电量计驱动抢占协议状态。LKM 仅读取原 power_supply；更深的数据需**重新编译后**由内核驱动提供。

## 二、设备树 / DTB / DTBO
当前 `arch/arm64/boot/dts/qcom/enchilada.dtsi` 包括：
- `&mtp_batterydata { #include "OP-batterydata-3300mah.dtsi"; };`
- `&pmi8998_fg` 的 `oem,use_external_fg` 与 `qcom,fg-force-load-profile`
- `&pmi8998_charger` 中 `qcom,fv-max-uv=<4365000>`、`ibatmax-normal-ma=<1950>` 等原厂电流/温度边界
- BQ 0x55 节点带 `qcom,modify-soc-smooth`

以上属于**源文件审计**；不可直接证明 DTBO 覆盖了上述属性。
当前未将 3300 画像替换为所谓 4500 化学参数，也未提高电流。必须先取得换装电芯的实际产品型号、额定/最高电压、热敏参数和充电截止规范，并确认当前有效 DTB 配置。

## 三、VENDOR / ODM / Android Health（已核验用户实际镜像）

- 用户重新提取的逻辑 `vendor.img`：**369344512 字节**，SHA-256 `76a4dffc4fe39f6fb4146567fc5509a01845437478185b6a318a64a82e4d82c0`。EROFS 文件系统目录遍历 2156 条、错误 0；超级块 CRC32C 与 AVB vendor hashtree 均匹配。构建标识为 OnePlus6 / Android 17、2026-09-29，符合运行设备记录。
- **Android Health 主服务**：`/vendor/bin/hw/android.hardware.health-service.qti`，`etc/vintf/manifest/android.hardware.health-service.qti.xml` 声明 `android.hardware.health` AIDL v4、`IHealth/default`。
- **Lineage Health 充电服务**：`/vendor/bin/hw/vendor.lineage.health-service.default`，声明 `vendor.lineage.health` AIDL v2，`IChargingControl/default` 及 `IFastCharge/default`。它是充电控制接口，不能代替 BQ27411 SOC/化学模型校准。
- **OEM Dash**：`/vendor/bin/dashd` 可在真实镜像中找到，但仅凭 ELF 存在不能证明快充正在运行或已与内核成功握手。
- **Qualcomm 充电策略**：`/vendor/etc/init/vendor.qti.hardware.charger_monitor@1.0-service.rc` 在开机和关机充电路径启动 `/vendor/bin/init.qti.chg_policy.sh`。此脚本主要调整 `power_supply` 和 IIO 节点权限，并不是电芯容量校准服务。
- 所有上述路径都来自**实际用户提供的 VENDOR 文件树**，不是借用 Lineage 官方 ROM 的猜测。我们仍未完成 HAL 运行时 binder 连接/行为测试，不宣称已经修复 Android 显示电量。
- 同一用户上传的**物理** `vendor_a.img` 是与运行系统不同的 EXT4 数据，且目录损坏；**物理** `odm_a.img` 与该 AVB 目标根哈希不符。这两份都不能作为刷入镜像。当前正确的逻辑 VENDOR 无需再提取，若要动 ODM 需另获取真正挂载的逻辑 ODM。
- `vbmeta_a.img` 的 RSA-4096/SHA-256 **数学签名验证通过**，但其 flags=3（验证/hashtree 声明禁用）。此处不等于 bootloader key trust，也不等于整包 OTA ZIP 签名。
- 安卓 Health AIDL 的 `batteryLevel` 单位为百分数，`batteryFullChargeDesignCapacityUah` 是微安时；仅改设计容量元数据不会使芯片真实剩余电量或 SOC 自动准确。

## 四、编译与可加载性边界

- 先前 GitHub Actions 运行 `38121789524` 编译成功，产出 `op6_truefuel.ko`，其中 `vermagic=4.19.325-cip136-st20-perf-g5a6245762072-dirty`。
- 用户当前已刷入内核为 `4.19.325-cip136-st20-perf-g9ad0027fcccb-dirty`，**这份 KO 版本不一致，不能使用，严禁强制加载**；`CONFIG_MODVERSIONS=y` 时符号 CRC 可能也不同。
- v0.4 新驱动更改后必须重新跑 CI；但即便编译通过，也不自动确认 KO 与手机匹配或允许刷入。
- VENDOR 原始 EROFS 经过核验后保持不动，不重签名、不修改 SELinux、不自动替换 HAL。

## 合并门槛与回退
1. CI 编译新内核、DTB、LKM，并核对 Module.symvers + vermagic。
2. 当前手机运行无参只读探针，比对三层实际配置。
3. 临时启动可回退的测试 BOOT 验证新驱动，进行充放电/休眠/温度测试。
4. 再制定经资料验证的 BQ27411 专有 DataFlash 备份、编程与完整读回步骤。设计容量 4500 ≠ FCC 已学习为 4500。
5. **直到前述通过，才可考虑**改动系统 SOC 输出或充电策略。未知电芯规格、充电温度 40°C 时不提高充电电流。
6. 在完整内核版正式集成前保留草稿 PR，不合并稳定分支。

## 上游规范
- TI BQ27411-G1 TRM: https://www.ti.com/lit/ug/sluuas7b/sluuas7b.pdf
- Android Health HAL: https://source.android.com/docs/core/perf/health
- 正在进行的 PR: https://github.com/Zhanfg/android_kernel_oneplus_sdm845/pull/17

注意：源码完成/CI 成功 ≠ 手机实测完成 ≠ 电芯已经校准。