# AURA / KV260 两项适配工作

本工作目录保存可复现源码与真实证据。当前任务是 OpenCV 人脸软件参考链兼容，以及 B4096＋运动逻辑的联合资源/时序验证。结果写入完成报告；编译、仿真、联合布线和板级验证分别记录。

最终状态：OpenCV 兼容链已通过 KV260 本机 CPU 参考测试；`20261007T032807.973571Z-joint-fit` 已通过单轴联合容量验收（WNS +0.001 ns，setup/hold/pulse 失败 0，bus skew/IO/MMCM 核验通过）。汇总见 [ADAPTATION_RESULT.json](ADAPTATION_RESULT.json)，详细原件见报告。尚未加载候选 PL，正式双轴与机械闭环没有通过结论。

- `identity/face_compat.py`：固定模型的底层 DNN 兼容实现；[使用及来源](identity/README.md)。
- `identity/verify_reference.py`：与 OpenCV 官方高层 API 对照，结果在 `identity/reference/verification.json`。
- `scripts/identity_test.py`：KV260 本机固定图片与特征测试，由 `scripts/board_exec.py` 经既有串口执行；不占用摄像头。
- `fpga/rtl/motion_fit.sv`：单轴控制资源候选；[试验合同](fpga/CANDIDATE_CONTRACT.md)。
- `scripts/fit_checkpoint.tcl`：旧 M3 routed 检查点的独立副本中替换叶节点并重新放置/布线；没有修改旧工程。
- `fpga/tests/tb_fit.sv`：保护逻辑及 AXI 背压仿真，`CURRENT_SIM.json` 指向本次真实结果。
- `evidence/`：每次运行的源码快照、终端原件、日志与结果；失败尝试保留，不作为通过证据。
- [适配验证报告](ADAPTATION_REPORT.md)：两项结果、板测范围与后续 release 的区别。

原完整平台已被 placer 的高利用率检查拒绝。当前验证 `USB_AUDIO_NO_PL_I2S` profile：`python3 scripts/run_fpga.py --usb-audio`。用返回 DECERR 的控制端点替换未使用的旧音频模块，保留 VCU 共享互连；未知物理优化别名禁止任意接地。

从已连接引脚的候选检查点恢复可用 `--resume-bound evidence/<运行目录>/joint_unplaced.dcp`；也可使用已清除路由的 `joint_unrouted.dcp`。检查点限定在本目录内、先核验源哈希再记录到新证据目录。修改过的 routed 网表先 `route_design -unroute`，避免已观察到的 Vivado 2022.2 旧路由清理崩溃。结束后执行 `python3 scripts/verify_fpga_reports.py`，不能用运行返回 0 代替时序与完整性检查。

USB 音频版本保存 `joint_trimmed.dcp`、`joint_optimized.dcp`、`joint_placed.dcp` 及路由后物理优化前的 `joint_preroute_physopt.dcp`；分别可用 `--resume-trimmed`、`--resume-optimized`、`--resume-placed`、`--resume-routed` 恢复。恢复时必须同时指定 `--usb-audio`，阶段、目录、原件哈希与引脚绑定均记录到新证据。已完成的源文件检查不等于整个平台已经通过。

精简后的全局 placer 仍因高利用率估计拒绝，后续采用官方增量实现。最终通过轮的命令为：

```bash
python3 scripts/run_fpga.py --usb-audio --incremental --timing-closure \
  --incremental-reference evidence/20261007T022933.663636Z-joint-fit/joint_routed.dcp \
  --resume-optimized evidence/20261006T160911.661330Z-joint-fit/joint_optimized.dcp
python3 scripts/verify_fpga_reports.py
```

`--incremental` 默认使用已核验哈希的原 M3 routed 参考；`--incremental-reference` 可选择本实验已完整运行结束、硬件源码一致的 `joint_routed.dcp` 作为下一轮物理参考，每次记录完整 SHA 和真实匹配率。负 slack 候选只能作为继续优化的参考，不能作为通过证据。两种方式均不关闭利用率检查。保存参考导入后的 `joint_incremental.dcp`，可用 `--usb-audio --resume-incremental` 恢复；该缓存保留增量布局/布线信息，无须重复导入原参考。所有通过结论取新生成的最终报告，不能取复用报告中携带的历史时序。

若最终报告仍存在负 slack，可从优化检查点重新导入物理参考，并增加 `--incremental --timing-closure`，使用 [AMD 官方 TimingClosure 指令](https://docs.amd.com/r/2022.2-English/ug904-vivado-implementation/Incremental-Directives) 对不满足时序的路径继续优化。`20261007T032807.973571Z-joint-fit` 使用该策略及上轮完整 routed 候选为参考，最终完整验收通过。它不改变时钟频率或放宽验收条件；最终验证核对了原控制 100 MHz、DPU 300/600 MHz 以及其余主时钟周期和实际 MMCM 分频。

验收另要求 [bus skew 报告](https://docs.amd.com/r/2022.2-English/ug835-vivado-tcl-commands/report_bus_skew)、真实 E10 输出属性/驱动与 MMCM 分频值检查。新实现脚本包含这些只读检查；较早快照完成后可运行 `python3 scripts/run_fpga_audit.py` 补充同一个 routed 检查点的报告，核验原件 SHA 未改变。缺少这些报告不能判通过。

已提供 `--resume-routed .../joint_preroute_physopt.dcp --postroute-refine dsp|clock|alternate` 的后续优化入口，分别增加 DSP 寄存器/关键路径优化、真实时钟偏斜优化或其他复制算法，参数依据 [AMD 2022.2 phys_opt_design](https://docs.amd.com/r/2022.2-English/ug835-vivado-tcl-commands/phys_opt_design)。也可从已完整结束、源文件未变且硬件源哈希一致的 `joint_routed.dcp` 继续，避免丢失上轮路由后优化结果。该备用入口仅完成脚本语法检查，尚未运行；它不会改变约束频率，运行后仍须通过同一套完整报告验收。已完成的 TimingClosure 使用启动时的脚本快照，本次通过没有执行这个备用入口。

板端暂存路径 `/home/root/aura-adaptation-20261006/`。完整文件哈希确认后才发布模型文件名；传输超时恢复 115200 波特率。不完整的 `.partial` 文件不参与模型加载。

软件 CPU 参考通过不等于 DPU 身份识别通过；单轴资源候选通过不等于正式双轴控制 release 或机械闭环通过。
