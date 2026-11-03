# 联合 PWM 最终电路独立复核

2026-10-08 08:35 UTC。本轮用户确认摄像头放稳、保留舵机当前位置后，已完成加载前的候选电路独立复核；**offline_checkpoint_passed=true，deployable=false，board_accessed=false**。没有启动真实舵机随动。

## 实际复核结果

重新打开 build 0x14da0e60 的最终 joint_routed.dcp，独立生成属性、时序、总线偏斜、DRC 和路由报告。检查前后 DCP、BIT、BIN 及检查脚本哈希未变化，构建输入源码也与归档一致。原件见 [CURRENT_AUDIT.json](CURRENT_AUDIT.json)。

| 项目 | 结果 |
| --- | --- |
| 外部端口 / pad | servo_pwm / E10，LVCMOS33、DRIVE 8、SLEW SLOW |
| 输出驱动 | aura_m3_regs_0/servo_pwm_reg/Q → 唯一 OBUF → pad |
| 输出寄存器 / 初值 | FDRE / 1'b0 |
| PWM 时钟 | clk_100M，约束周期 10 ns；MMCM 参数逐项匹配 |
| DPU / VCU 结构 | DPUCZDX8G_1 和 vcu/vcu_0 存在 |
| setup / hold / pulse-width | WNS +0.001 ns、WHS 0 ns、WPWS +0.071 ns，失败端点均 0 |
| 总线偏斜最差裕量 | +2.782 ns |
| 路由 | 200468 条可路由网络全部完成，路由错误 0 |
| 最终 DRC | 0 Error / Critical Warning；663 项 Warning 原样归档 |
| PWM 至 pad 时序 | +95.378 ns；100 ns 工程预算，实际报告路径延迟 4.622 ns |

WNS 裕量很小，不代表实际板卡所有条件下的裕量或舵机电气验收。100 MHz 是工具时钟约束及 MMCM 参数核对，尚未作板端频率/周期测量；寄存器 INIT 为低不是断电后机构位置的测量。保留 DPU 层级不等于真实推理已验证。

原平台仍有 6 个输入、2 个输出 I/O delay 缺口，集中在 MIPI/I2C；未通过全局 false-path 掩盖。原实现日志包含 100 条 incremental phys_opt replay Critical Warning，与最终 DRC 分别记录，不把“DRC 没有错误”表述为“构建没有警告”。

第一次独立检查将 VCU 层级写为 vcu_0，被结构检查拒绝。核对源 HWH/BD 后修正为实际 vcu/vcu_0，完整重跑复核通过。失败证据保留于 evidence/20261008T082307.745250Z-final-audit；该失败属于复核脚本的路径错误，没有修改电路或板子。

## 工程配套与现场状态

[元数据检查](CURRENT_METADATA_AUDIT.json) 确认原 BD/HWH 与新电路不匹配，见 [配套差异](PLATFORM_HANDOFF_GAPS.md)。尚未生成匹配的新 BD/XSA/HWH、DT/XCLBIN，尚无实测唯一写方 transport、提交延迟和联合无动力板测，因此没有把候选改为可部署。

用户的“好了”记作摄像头放稳、保留当前位置的现场准备反馈；[待标定记录](CALIBRATION_PENDING.json) 的 reference_us、polarity 和三锚点仍为 null，confirmed=false。准备完成不能替代基准脉宽、左右方向和视线映射实测。

下一阶段具体交付是匹配源平台描述及加载包，并核对实际设备树/运行身份；之后在明确无舵机动力的条件下板测，再进行轻载参考与映射标定。原机械零点选择继续沿用用户当前位置，不强制转到 1500 μs。
