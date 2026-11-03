# 2026-10-08 视觉与舵机源平台修复

用户问“那怎么办”，继续修正此前确认的源描述不配套问题。任务目录 `/home/ghmd/kv260-visual-servo-20261007`。本轮仅只读访问板卡，未切换 FPGA、未执行舵机动作。

**10:26 UTC 最终状态：** 主机端完整源工程实现、13 项描述核对、独立最终 DCP 复核和同工程配套封包全部完成。board_test_ready=true 仅指受控板测候选工件就绪；deployable=false、physical_actuation_enabled=false。新配置未加载，真实 transport/提交预算/身份/PWM/STOP/共存与物理参考/极性/左右锚点未验证。舵机动力状态仍待用户回复。原 FPGA 工程及控制 RTL 未修改。

## 已实测的主机结果

- 新源平台生成：`evidence/20261008T085856.495299Z-source-platform`，rc=0，输入文件未变化，Vivado BD 校验及目标生成通过。
- 新 BD/HWH 描述审查：`evidence/20261008T090232.581802Z-source-platform-audit`，11 项全部通过，保留组件参数变更为空，AXI 连接和标量连接与预期一致。
- 固定源 XSA 导出及 `validate_hw_platform` 校验通过，完成时间 09:03:37 UTC；XSA 未包含位流。
- 候选审阅包：`evidence/20261008T090806.655236Z-candidate-bundle`，Bootgen/DT 语义往返/主机合并/文件哈希检查通过。明确不是完整源工程位流发布，`board_test_ready=false`、`deployable=false`。

## 进行中与未验证

09:13 与 09:15 的实现启动因只读属性写入和误选多个 BD 失败，记录已保留。修正后 09:16:18 UTC 启动当前完整源工程实现，状态见 `CURRENT_SOURCE_IMPLEMENTATION.json`，输入的旧 routed DCP 仅作为布局参考。综合与优化已完成；运行未完成，不计作实现通过。新位流的独立时序/路由/DRC、配套封包、板端身份/PWM/停止与视觉共存尚未验证。

09:28 UTC 板端 `restart_inventory` 与 `realtime_verify` 只读检查 rc=0、passed=true；boot ID 仍为 f7a3ff07-fc20-4804-af12-c314a7a1847a，官方 B4096 活动于 slot 0。PID 1498 独占 USB 摄像头，采集/检测/显示帧数增长，Monitor is On，1024×600。未输出运动命令。证据位于 adaptation-check 的 `20261008T092825.775107Z-restart_inventory` 与 `20261008T092854.569009Z-realtime_verify`。

本轮对用户询问舵机动力电源是否已断开，等待实际回复；不把无回复当作断开确认。用户已确认摄像头放稳及保留舵机当前位置，基准脉宽、极性和三个锚点仍为未测量。

失败尝试与日志保留，修正内容和证据说明见任务目录 `SOURCE_PLATFORM_REPORT.md`。原 M3 工程与历史候选不覆盖，不把模拟、源描述生成或主机包检查当作板级验收。

09:31 优化后检查点独立打开属性核对 rc=0，确认唯一 FDRE PWM 输出、INIT=0、10 ns 时钟、MMCM 参数、E10 约束及 DPU/VCU 层级。尚非最终路由验收。09:35 板端设备树/固件只读检查通过，官方 BIN/DTBO 哈希与主机基线一致，FPGA operating、唯一官方 overlay applied，无旧音频节点。09:36 导出的本次启动基础 FDT 已用于主机 overlay 合并验证，rc=0；未在板上应用。09:40 描述核对扩展为 13 项并全部通过，增加实际时钟和复位连接检查。实际硬件频率、PWM、ACK、STOP、DPU 共存仍未验证。

10:17:18 UTC 完整源工程实现完成，rc=0、implementation_passed=true、输入未变，位流及同工程 XSA 导出/校验通过。最终 WNS +0.001 ns、WHS 0 ns，200452/200452 连线完成、路由错误 0、DRC 错误 0/警告 663、总线偏斜最差裕量 +2.782 ns、PWM 输出裕量 +95.249 ns。仍有外部约束缺项 6 输入/2 输出；未隐藏警告或用构建代替板测。独立最终审查和源位流重新封包正在执行，状态见任务目录 CURRENT_SOURCE_RELEASE.json。

10:24 UTC 独立审查完成，rc=0、offline_checkpoint_passed=true、输入未变化，所有最终时序/路由/DRC/偏斜及器件、PWM/时钟/INIT/保留 DPU/VCU 检查通过；14 条参考 DPU SRL 优化无法重放的 CRITICAL WARNING 保留。10:24 首次配套包通过全部检查；10:26 为明确列出 transport 与平台限制等剩余项重新封包，未更换电路。最终包 `evidence/20261008T102632.391041Z-candidate-bundle/bundle`，Bootgen、XSA 主 HWH 字节一致、当前启动基础 FDT 合并、DT 往返及全部文件哈希均通过。位流 SHA 4c91dc246ad4bdc7342111fdb252f83bc50d7236ff32385ade9457a14e643f0a；全 PL BIN SHA a8b783038dfe403924dfc6934b2ac2fefac39da7204785b682361153e4de5eba。CURRENT_SOURCE_RELEASE 与 CURRENT_CANDIDATE_BUNDLE 指向最新状态。

10:25 UTC 收尾只读预览复核通过：采集 163785→163860、检测 81220→81245、显示 163781→163856，PID 1498 独占相机，1024×600，boot 不变，未修改 FPGA、未发送运动指令。realtime-vision 的状态和接续入口、本轮 SOURCE_PLATFORM_REPORT/README/CONTROL_REFERENCE/PLATFORM_HANDOFF_GAPS 已更新。改动文件清单见源平台报告；旧 M3 工程、运动 RTL、算法及其 35 项历史单元测试未修改，未重复跑历史测试或 HDL 仿真。
