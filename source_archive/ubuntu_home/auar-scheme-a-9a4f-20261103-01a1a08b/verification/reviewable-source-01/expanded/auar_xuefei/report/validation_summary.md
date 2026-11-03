# Ubuntu 源码及 Tcl 阶段验证

本归档冻结在完成综合、布局和布局后优化，正在布线的阶段。最终 setup/hold、route/DRC、同轮 BIT/XSA 与固件导出尚无回执。完整实现和验包通过后另行交付最终版。

| 项目 | 本阶段实际结果 |
|---|---|
| tb_nominal | xvlog / xelab / xsim 退出码分别为 0, 0, 0，AURA_NOMINAL_TEST_PASS |
| tb_wide | xvlog / xelab / xsim 退出码分别为 0, 0, 0，AURA_WIDE_TEST_PASS |
| tb_pulse_guard | xvlog / xelab / xsim 退出码分别为 0, 0, 0，AURA_V2_PULSE_GUARD_OFFLINE_PASS_NOT_BOARD_RELEASE |
| tb_servo | xvlog / xelab / xsim 退出码分别为 0, 0, 0，AURA_SERVO_TEST_PASS |
| Vivado 2022.2 Tcl | 从空目录重建 IP、BD、约束和 wrapper。四台复验和错误回执拒绝测试均通过。 |
| 综合和布局 | 已完成。由本轮源码生成的 synth、placed 检查点均位于包外。 |
| 模型 | YuNet 与 SFace 由固定 ONNX、数据和工具镜像量化编译，两个新 xmodel 的哈希在 evidence/model_build.json。 |
| 原生库和业务 | 8 个 AArch64 ELF 从源编译；380 个原组件精确还原 9a4f，224 项相机、56 份服务追加配置、15 个语音输入通过离线核验。 |
| 比赛 Skill | 28 份原文件，15 个单元测试与 73 个 mock 用例通过。 |
| 现场执行 | 真实 KV260、机械转轴及 Windows GPU 推理未执行。 |

验证底稿位于 report/evidence。本目录中的 hardware_results/implementation/firmware_fresh 结果待最终实现完成后补齐。正式技术文档可从 report/design_report.md、report/dependencies.md 和 data/metrics.csv 取数。
