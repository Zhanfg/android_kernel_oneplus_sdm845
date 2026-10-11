# OnePlus 6 / Android 17 · TrueFuel v0.3 三层适配记录

基线：已通过开机的 BakaSU Linux 4.19.325；用户设备 OnePlus 6 / ONEPLUS A6003 / uwuAOSP 17.0.101。
本包是**实验源码与只读探针**，不是可刷入的 4500mAh 电量校准包，不修改当前稳定 BOOT、DTBO、VENDOR。

## 一、BOOT / Linux 内核驱动
- 实际芯片：BQ27411 (Device Type 0x0421、固件 0x0109)，总线节点 0-0055。
- 当前日志：BQ SOC=43%、OEM capacity=43%、Qualcomm real_capacity=35%、FCC=3,139,000uAh、Design=3,240,000uAh、remaining_capacity=0。
- 原驱动的 `bq27541_design_capacity()` 从设备 0x3c 读取 DesignCapacity，作为 `bms/charge_full_design` 输出；不是凭 UI 写死。
- `bq27541_remaining_capacity()` 在不允许读取时可能返回局部初始值 0，因此 0mAh 不能证明电芯实际空电。
- 原驱动的 `fg_soc_calibrate` 改写正常对外显示的容量路径；`bms/bq_soc` 绕过该软件平滑，但仍为芯片滤波后的 0x1c。
- 已在实验内核驱动增加 `op6_truefuel_hw` 只读 sysfs 属性，使用原 I2C 驱动读路径与互斥保护，读取芯片 `0x30` 未滤波 SOC、`0x28` 未滤波剩余容量、`0x2c` 未滤波 FCC、`0x3c` 设计容量。充电/休眠/芯片状态未就绪时拒绝读。
- LKM v0.3 删除了对 0x55 的独立直接 I2C 访问，防止与内核电量计驱动抢占协议状态。LKM 仅读取原 power_supply；更深的数据需**重新编译后**由内核驱动提供。

## 二、设备树 / DTB / DTBO
当前 `arch/arm64/boot/dts/qcom/enchilada.dtsi` 包括：
- `&mtp_batterydata { #include "OP-batterydata-3300mah.dtsi"; };`
- `&pmi8998_fg` 的 `oem,use_external_fg` 与 `qcom,fg-force-load-profile`
- `&pmi8998_charger` 中 `qcom,fv-max-uv=<4365000>`、`ibatmax-normal-ma=<1950>` 等原厂电流/温度边界
- BQ 0x55 节点带 `qcom,modify-soc-smooth`

以上属于**源文件审计**；不可直接证明 DTBO 覆盖了上述属性。
当前未将 3300 画像替换为所谓 4500 化学参数，也未提高电流。必须先取得换装电芯的实际产品型号、额定/最高电压、热敏参数和充电截止规范，并确认当前有效 DTB 配置。

## 三、VENDOR / ODM / Android Health
- 当前 ROM 已测 `/vendor` 与 `/odm` 为 EROFS 只读的逻辑分区；需要在设备上识别实际 Health HAL。
- LineageOS SDM845 Common 的较新设备树将 `android.hardware.health-service.qti` 放入 Vendor；这是**上游参考**而非对当前 uwuAOSP 用户手机的确认。
- 默认 Health HAL 消费 `power_supply/*/{capacity,charge_full,charge_full_design,current_now,voltage_now,temp,...}`，任何额外 UI 算法应先查明其真实存在才修改。用户日志的 Android level=43 与 BQ=43 一致。
- 优先修正内核电量计提供的真实数据，并验证 HAL 单位与节点映射；不替换用户现有 Vendor blob、不修改 SELinux 授权、不挂载未知 HAL。

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