# 新源平台生成与实现记录

**最终结论（10:26 UTC）：** 主机端源平台、完整实现、独立最终电路复核及配套封包全部完成。候选包可进入受控板测，尚未加载到 KV260，真实随动未启动。舵机动力断开事实仍待用户回复；单写方真实寄存器 transport、提交预算板测、物理参考脉宽/极性/锚点及联合功能验收仍未完成。`board_test_ready=true` 表示主机工件已就绪，`deployable=false` 和 `physical_actuation_enabled=false` 保持不变。

2026-10-08。用户询问配套描述不匹配如何处理，本轮在独立目录修正源平台，不覆盖原 M3 工程。板端仅做只读检查，没有切换固件或启用动作。

## 已完成的主机工作

- 生成独立运动 IP `aura.local:user:aura_visual_servo:1.0`，RTL 与已仿真候选完全相同，BUILD_ID 为 `0x14da0e60`。
- 将原 `audio_ss_0` 音频层级替换为禁用接口 IP，三个控制端点保持 DECERR 响应，两个数据主口保持静止；保留共享 VCU 通路。包装副本只增加接口声明，移除新增声明后与原 RTL 字节一致。
- 在新 BD 中明确连接 `servo_pwm`，外部旧 `lrclk_tx` 名称取消；E10 / LVCMOS33 / DRIVE 8 / SLEW SLOW；控制地址 `0x80080000—0x80080fff`。
- Vivado `validate_bd_design`、生成目标、IP 完整性检查通过；导出新的 HWH/BD/源 XSA。XSA 经 `validate_hw_platform` 校验通过，未嵌入位流。
- 独立核对 11 项全部通过：新描述输出、版本、地址、禁用音频、保留组件参数、标量连接、AXI 连接、运动 RTL 哈希。保留组件参数变更列表为空；连接差异仅为预期的新 PWM 输出。
- 09:40 UTC 扩展为 13 项，增加 PWM 时钟来源和低有效复位来源，全部通过，证据为 `20261008T094041.401238Z-source-platform-audit`。HWH 时钟端口指向 `clk_wiz_0/clk_100M`，频率声明 99999000 Hz；实现检查点时序定义为 10 ns。总线 CLK_DOMAIN 的 `clk_200M` 字样是时钟 IP 的继承域标签，不作为 PWM 频率测量。实际板端周期仍需测量。
- 候选审阅包完成 Bootgen 全 PL BIN 头核对、DTBO 仅更改固件名的语义比较、DTS 往返、主机 DT 合并、无旧音频节点及完整文件哈希验证。XCLBIN 保留原 DPU 元数据，不含嵌入位流。

证据入口：[源平台](CURRENT_SOURCE_PLATFORM.json)、[描述审查](CURRENT_SOURCE_PLATFORM_AUDIT.json)、[XSA 导出](CURRENT_SOURCE_EXPORT.json)、[候选审阅包](CURRENT_CANDIDATE_BUNDLE.json)。

## 完整源工程实现

完整源工程综合与实现已于 10:17:18 UTC 完成，rc=0、implementation_passed=true、输入文件未变，[状态](CURRENT_SOURCE_IMPLEMENTATION.json)。新位流 `visual_servo_source.bit` 和 `visual_servo_source_implemented.xsa` 来自同一工程；后者校验通过。旧 routed DCP 仅用作布局参考，不代替新综合结果。独立最终检查点复核及新位流封包已完成，[流程状态](CURRENT_SOURCE_RELEASE.json)；旧 netlist 审阅包仍非可部署包。

构建最终报告：WNS +0.001 ns、WHS 0 ns、WPWS +0.071 ns，建立/保持/脉宽失败数均为 0；200452 条可路由连线全部布通，路由错误 0；DRC 0 错误、663 条警告，总线偏斜最差裕量 +2.782 ns；PWM 输出裕量 +95.249 ns。内部无未约束端点；仍有 6 个输入与 2 个输出的外部时序约束缺项，裕量较小且警告保留。构建中间曾出现 DPU 高速路径负裕量，经过拆线重布消除，未修改时钟或绕过失败检查。构建通过不等于板级或正式发布验收。

## 独立验收与最终候选包

`evidence/20261008T101723.076178Z-source-final-audit`：独立重新打开新最终 DCP，rc=0、offline_checkpoint_passed=true、输入未变化。器件 K26、唯一 FDRE INIT=0 驱动、100 MHz 设计时钟、MMCM、E10 约束、DPU/VCU 层级与最终时序/路由/DRC/总线偏斜均重新核对通过。保留 14 条 DPU SRL 优化无法从参考电路重放的 CRITICAL WARNING；最终时序收敛不等于这些平台限制已被正式发布验收消除。

最终封包：`evidence/20261008T102632.391041Z-candidate-bundle/bundle`。Bootgen 完整 BIN、同工程 XSA 中主 HWH 与生成原件字节一致、DTBO 语义往返、当前启动基础 FDT 合并、DPU XCLBIN 元数据与全部文件 SHA256 检查均通过。10:24 首次封包保留；10:26 仅补充明确的剩余验收清单并重新封包，未重建或更换电路，不重复运行已通过的电路检查。

- 位流 SHA256：`4c91dc246ad4bdc7342111fdb252f83bc50d7236ff32385ade9457a14e643f0a`。
- 全 PL BIN SHA256：`a8b783038dfe403924dfc6934b2ac2fefac39da7204785b682361153e4de5eba`。
- 新 XSA SHA256：`ff94329742417a121b6dca3b87a0e5cb2af037304ca81b5ec5cd05c34418c2ac`。

封包注明来自同一源工程，没有将此称作形式等价性证明。所有实际板端身份、STOP/到期、PWM 电压/周期/脉宽、DPU/相机/显示共存仍待实测。

## 本次脚本修正与边界

保留所有失败尝试。已修正 IP BUILD_ID 的 bitString 格式、BD 文件名与导入目录、SOM 的载板连接配置、接口重连需要两个完整层级端点、禁用主接口的地址空间与映射。首次描述检查误将 MIPI 子 HWH 也计入主 HWH，改为精确选取主文件；源 XSA 同样精确选择主 HWH。

这些是主机工程与脚本问题，不是板卡故障证据。本轮没有执行 MMIO、PWM 或舵机动作。舵机动力是否已断开的问题已向用户发出，尚无回复时不能认定已断开；当前位置基准脉宽、左右极性及固定摄像头锚点仍未测量。

## 09:28 UTC 板端只读复核

`restart_inventory` 和 `realtime_verify` 均 rc=0；启动仍为 `f7a3ff07-fc20-4804-af12-c314a7a1847a`，官方 `kv260-benchmark-b4096` 活动于 slot 0。USB 相机唯一使用者为 PID 1498，源码哈希与已封存版本一致。3 秒复核中采集帧从 77694 增到 77787、检测帧从 49281 增到 49307、显示帧从 77691 增到 77784；显示器开启，X11 为 1024×600，验证 passed=true。这证明预览在运行，不代表视觉与新 PWM 联合共存已经通过。

证据：`/home/ghmd/kv260-adaptation-check-20261006/evidence/20261008T092825.775107Z-restart_inventory/` 与 `20261008T092854.569009Z-realtime_verify/`。

10:25 UTC 收尾再次只读验证 passed=true：采集 163785→163860、检测 81220→81245、显示 163781→163856，PID 1498 仍独占相机，屏幕 1024×600，boot 不变，未修改 FPGA、未发出运动指令。证据为 adaptation-check 的 `20261008T102506.555425Z-realtime_verify/`，已更新 realtime-vision/CURRENT_RUNTIME.json。

09:35 UTC 继续只读核对设备树：`/fpga-full` 指向官方 B4096 位流、zocl 为 okay，只有一个官方 overlay 为 applied，FPGA manager 为 operating；未发现 I2S/audio-formatter 节点。未访问 MMIO。证据为 adaptation-check 的 `20261008T093522.418547Z-source_platform_prerequisites/`。

09:36 UTC 只读导出当前启动的基础 FDT，45184 字节，SHA256 `98c959df7b3d0c85dcae608296bd6116ec6c281614bc07ba627b3993376083da`。该基础 FDT 与早前完整树快照字节不同，因此不混用；已用当前基础 FDT 进行主机 overlay 合并，rc=0，新固件名正确且无 I2S/audio-formatter 节点。见 [当前基础树](CURRENT_BOARD_DT.json) 和 `evidence/20261008T093723.375077Z-current-boot-dt/`。合并在主机执行，没有应用到板卡。

## 优化后连接提前检查

`evidence/20261008T093112.896697Z-source-early-properties/` 对新 `source_optimized.dcp` 独立打开检查，rc=0：PWM 唯一驱动为 `aura_m3_regs_0/inst/servo_pwm_reg/Q`，FDRE INIT=0；实际连接时钟周期 10 ns，MMCM 参数与预期一致；E10/LVCMOS33/DRIVE 8/SLEW SLOW 和 DPU/VCU 层级检查通过。这是优化后属性检查，尚非最终布局布线验收。

XSA 由 Vivado 命令生成，未手工伪造或修改 HWH。导出行为参考 [AMD Vivado 2022.2 write_hw_platform](https://docs.amd.com/r/2022.2-English/ug835-vivado-tcl-commands/write_hw_platform)。

## 改动文件

新增源平台/实现/封包流程脚本：`scripts/prepare_source_platform.py`、`prepare_source_platform.tcl`、`audit_source_platform.py`、`export_source_platform.tcl`、`implement_source_platform.py`、`implement_source_platform.tcl`、`prepare_candidate_bundle.py`、`finalize_source_platform.py`；扩展 `scripts/audit_joint.py` 和 `audit_joint.tcl` 的源工程最终审查模式。

更新本目录 `README.md`、`PLATFORM_HANDOFF_GAPS.md`、`CONTROL_REFERENCE.md`、本报告与生成的 CURRENT 状态文件；更新 realtime-vision 的 `CURRENT_RUNTIME.json`、`NEXT_INTEGRATION.md` 及 AMD_Smart 当日项目日志。adaptation-check 新增两个只读脚本 `source_platform_prerequisites.py`、`source_platform_dt_export.py`。原 M3 工程、运动 RTL、视觉算法和已有测试文件未修改；本轮验证是实际源工程工具运行、独立电路与封包核验及板端只读预览检查，未重复未修改算法的 35 项历史测试或 HDL 仿真。
