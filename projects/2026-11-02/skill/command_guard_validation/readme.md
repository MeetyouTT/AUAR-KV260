# A 技能包 · FPGA 动作命令保护验证

软件提交目标脉宽后，FPGA 应拒绝重放和越界目标，在租约到期时撤销许可，并区分主动 STOP 与允许当前脉冲完成的 QUIESCE。本包提供两种可复跑的检查：公开轨迹审计，以及同一版 wide RTL 的四套 XSim 测试。两种检查均无需板卡、转轴或网络。

## 在低核 Ubuntu 上开始

在本文件所在目录，用系统自带的 Python 3.8 或更高版本运行以下命令。该入口只依赖标准库，顺序运行，不用 Vivado。

~~~sh
sha256sum -c checksums.sha256
python3 -B scripts/run_checks.py > trace_report.json
echo $?
~~~

退出 0 表示三个公开例子的结果与预期一致、单元测试通过、RTL 源文件与合同指纹一致。例子中 trace_fail 的预期就是 FAIL。单独审计已有数据时运行以下命令。

~~~sh
python3 -B scripts/validate_trace.py --trace examples/trace_fail.json --profile config/wide_contract.json
~~~

独立审计的退出码为 0（PASS）、1（FAIL）、2（UNKNOWN）。trace_fail 包含被错误接受的重复序号和 STOP 后仍 active 的记录。trace_unknown 没有事件。对实测采样，请把 evidence_kind 改为实际采集方式，注明设备、时基、采样位置和采样遗漏。time_ms 取同一单调时钟，commit 的时标表示硬件接受决定被观察到的时间。这个时间与输入图像的曝光时间不可互换。

## 四套 RTL 仿真

在 Linux 上准备 Vivado 2022.2 的 xvlog、xelab、xsim 及其运行库。将 VIVADO_BIN 设为实际安装的 bin 目录。输出目录必须尚不存在，运行器只在其中生成仿真文件。四套仿真顺序执行。

~~~sh
export VIVADO_BIN=/opt/Xilinx/Vivado/2022.2/bin
python3 -B scripts/run_rtl.py --vivado-bin "$VIVADO_BIN" --output rtl_run
~~~

| 测试台 | 仿真断言关注点 | 本包实跑记录 |
| --- | --- | --- |
| tb_wide | 500 和 2500 微秒边界、越界拒绝、最短租约、QUIESCE、读回 | evidence/tb_wide/xsim.log |
| tb_servo | 授权顺序、AXI 写通道顺序与背压、重复/上下文错误、到期、复位、STOP、参考位置 | evidence/tb_servo/xsim.log |
| tb_pulse_guard | 3 毫秒拒绝、4 毫秒完整脉冲、100 毫秒到期、紧急 STOP 和 QUIESCE 的区别 | evidence/tb_pulse_guard/xsim.log |
| tb_nominal | 100 MHz 配置下 50 Hz 帧、参考宽度 1450 微秒起步并按帧逼近目标 | evidence/tb_nominal/xsim.log |

2026-11-02 在原构建主机 Ubuntu 20.04.4、Python 3.8.10、XSim 2022.2 上，从一个新目录运行本包。三个公开输入和 18 项 Python 单测结果见 evidence/linux_trace.json。四个 bench 的三阶段退出码、签名、有效测试台 SHA-256 与通过标志见 evidence/linux_xsim.json。每个目录均保留原始 xvlog、xelab、xsim 输出。例如在 tb_pulse_guard 中，4 毫秒租约产生了 2500000 ns 宽的完整模拟脉冲，紧急停止用例截断后的模拟脉冲宽度为 500020 ns。普通电脑不具备 Vivado 时可独立复核日志和文件哈希。

## 合同与证据范围

- 冻结合同 build 0x10282601，允许 500 至 2500 微秒，租约 4 至 500 毫秒，帧 20000 微秒，步进 4 微秒。不同 bench 会缩短分频或改参数以加速边界测试，实际参数见各测试台实例化。
- 公开 JSON 是合成逻辑例，不包含真实操作者数据。轨迹审计接收一次启动内的完整提交决策序列，包括会话/代次、提交序号及 STOP 回读。新 BIND 后第一条提交从 1 开始。STOP 或到期后再获许可的 BIND、REFERENCE、ARM 操作在归一化日志中省略，这组操作由 RTL 台验证。多个时钟、采样丢失或中途开始采集时，先按完整段落分割后使用。
- 轨迹检查只能定位记录过的违规。拒绝原因由记录提供；它不能由日志独立推知所有拒绝是否合理。对“所有命令均拒绝”、缺少 STOP、活动状态缺失等情况保留 UNKNOWN。可在 RTL 层检查的 AXI 写时序、半字节使能、上下文门控等不通过 JSON 审计推断。
- 本版保障从命令生效后计时的相对租约。从视觉事件产生到硬件提交之间的源时限、实际引脚波形及机构运动，需要各自的采样证据。本包没有向板卡写寄存器，也没有执行物理转动。
- 复用到其他工程时先替换实际合同、冻结 RTL 和哈希，再适配绑定流程、寄存器定义、测试台时钟与通过标志。若目标没有对等的确认或停机状态，报告 UNKNOWN 并补充采集项。此版验证了在同一软件版本的新目录复跑，尚无跨板实测或第三方独立验收。

## 来源与复用方法

工程来源为 Ubuntu 构建主目录下 aura-pan-wide-20261028/candidate/rtl/visual_servo.sv 及 candidate/tests 下四个测试台。对照原机逐文件 SHA-256 的结果保存在 evidence/upstream_sha256.txt。技能底稿为 2026-11-01_Skill交付规划 中的 skill_a_content.md、skill_delivery_v1/skill/command-guard-validation。2026-11-02 交付版保留冻结源，修正了相对路径运行、逐测试台通过标志、样例中到期后重建会话的序号，并增加归一化轨迹的边界检查。

可复用的提示词模板：给出冻结合同和哈希，请逐条列出允许与拒绝条件，附一条正常输入和最小反例；标出日志、RTL 与引脚波形各能见到什么。获得建议后先与 RTL 源核对，从合法提交开始，再运行反例、STOP 和租约到期，最后按实际输出登记结果。模板用于复用；本包的执行证据来自上述命令的实际输出。
