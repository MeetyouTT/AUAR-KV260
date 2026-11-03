# FPGA 源码参考与接入边界

`rtl/visual_servo.sv` 原样来自既有 VSRV 项目，`board/motion/vsrv_driver.py` 是对应注入式寄存器驱动参考。SHA、来源和平台能力分别记录在 `config/source_import_manifest.json` 与 `platform/platform_manifest.json`。

当前源码实现相对租约监督，**没有 PL 绝对源期限监督**。本框架没有生成、复制或加载新的 bitstream/overlay，没有打开 MMIO，没有 ARM 舵机。实际引脚/XDC、完整平台构建、DPU 工件及旧板测证据仍在原 FPGA 工程，应按项目资料导航定位，不能仅凭这一份 RTL 重建最终平台。

后续 A 岗应实现并冻结：源帧归属与绝对期限 ABI、PS/PL 时钟映射、来源/恢复代次、重复旧源不续期、期限到达关输出、状态与错误原因。先做 RTL 仿真，再集成 DPU 共存平台，回读平台/模型哈希和指纹，最后完成 PS 停顿、源过期和恢复必须有新证据的板测。

`board/motion/guard.py` 是可执行的软件合同模型，依赖软件轮询；它可辅助生成测试场景，不能证明 FPGA 独立停止。新运行时只使用该软件模型或禁用运动，物理执行入口不在本次框架授权范围中。

机构、单轴方向、限位和 PWM 标定等待用户的 3D 模型。`config/servo_calibration.json` 保持未验证，不预填未知角度或引脚。
