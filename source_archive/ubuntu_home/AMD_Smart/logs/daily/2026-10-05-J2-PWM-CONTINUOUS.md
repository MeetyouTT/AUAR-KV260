# J2 持续 PWM 准备与验证

最新记录见文末断电后恢复（当地10月5日、UTC10月6日）；下列过程记录为历史。

用户先要求约 5 秒，随后暂停询问波形参数，再明确要求一直输出。持续输出请求作为当前范围：50 Hz、1500 µs，高电平信号测量，舵机保持拔下。先前约一秒版本源码/证据保留；五秒目录仅准备源码，沙箱内 XSim 返回 Tcl unexpected exception，尚未构建/加载，用户请求改为持续输出后不继续五秒分支。

持续版独立目录 `/home/ghmd/kv260-j2-pwm-continuous-20261005`，RUN_FRAMES=0 明确表示持续，显式 START 后运行直到 STOP/复位，默认禁能低电平，重复 START 仍不重置相位。仿真 10 组参数覆盖新增持续模式、STOP/复位、原有限帧模式；AXI 16 种字节使能等接口测试通过。证据 `evidence/20261005T084003.033138Z-sim/`；这是离线仿真，不是引脚波形实测。

新 BUILD_ID 为 `f0206bda`。AArch64 字访问器编译、反汇编及 host 架构拒绝门禁通过，MMIO 仍为 LDR w0 / STR w1 与 DSB SY，启动后确认持续 busy 并返回，不自动 STOP。身份和固件名独立匹配持续版；持续模式尚未上板验证。新增 host 和远端脚本语法检查、3800 字节线长核验通过，最长 inspect/scratch 3771 字节。

构建正在 `evidence/20261005T084116.883020Z-build/` 进行，尚无完成结论。为切换新配置，执行原一秒目录 uart_burst.py restore：`evidence/20261005T084146.680352Z-uart-restore/` 记录 STOP 后卸载候选、重新加载原 `kv260-benchmark-b4096` 成功、原工件哈希及 VART 配置一致、回显恢复；旧 CURRENT_BENCH.candidate_active=false。此时持续候选未加载、持续 START 未发送。

## 持续版离线工件通过，开始上传

Vivado 构建完成，43 项最终核验全部通过，BUILD_ID=f0206bda，WNS=+6.919 ns、WHS=+0.012 ns、DRC 错误 0，输出 H12/LVCMOS33。从本次 XSA 重新用官方 device-tree-xlnx 2022.2（commit 24d29888d0048f26e4f3d6e0b7cd655aede94f31）生成设备树；Linux DTBO 合并基线、32 位 HPM0 LPD AFI、时钟/地址/固件名检查通过。新访问器启动检查失败时完整字 STOP；host 允许错误后仍执行身份受控的 inspect/stop/restore，保持停止通路。最新访问器 ELF SHA-256 `90a6979be38271326cab870d9576afe713faf801c607c584be24ff1c634ae462`，反汇编和架构门禁复核通过。

Linux 包 `evidence/20261005T085002.986293Z-linux-package/`：bit.bin SHA-256 `2f40d4070a81e6e320539af5da9da4ef8562c96648e4935c437954ac74b4c754`，dtbo SHA-256 `b77b9274e0af1ae44c3b92159e5c2141cc524232eaf85b03f9701b1a450e8a4e`。独立应用/固件名为 aura-pwm-probe-continuous / aura_pwm_probe_continuous.bit.bin，DTBO 也使用相同前缀。归档 `evidence/20261005T085026.182747Z-pwm-board-stage/aura-pwm-live-stage.tar.gz` 55,959 字节，SHA-256 `402114dc7641435c1c989deda9689f1ecff72b542acd632c86814e48207f6660`，本地 8 成员/7 文件 manifest 检查通过。开始 UART 上传，上传/加载/启动尚未在此段宣称完成。

用户在切换期间提供 `/home/ghmd/图片/7575.jpg`，可见 STOP、20 ns/div、100 mV/div、10× 与快速重复跳变，不能作为目标 50 Hz PWM 实测证据。持续版当时未加载，信号来源未确认；已提示改为 5 ms/div、1 V/div、自动触发并 RUN。没有把此图当作新持续版输出或明确判定其来源。

## 上板控制验证通过，持续输出保持开启

新包 47 帧上传、板端整体 SHA 核验、回显恢复通过（`evidence/20261005T085110.159848Z-uart-stage/`），板端归档 `/home/root/aura-pwm-live-stage/20261005T085110.159848Z/aura-pwm-live-stage.tar.gz`。五阶段准备/解包/安装/卸载官方/加载持续版均通过（`evidence/20261005T085342.389377Z-uart-load-idle/`），非 MMIO 用法入口验证 ELF 可执行，完整身份/config 和默认 status=4/frames_left=0 通过；PL0 实际读数 99,999,999 Hz。

SCRATCH 字写读/恢复（`evidence/20261005T085438.260677Z-uart-scratch/`）、空闲 STOP（`evidence/20261005T085508.880942Z-uart-stop/`）通过；首次 START（`evidence/20261005T085533.869617Z-uart-start/`）读回 status=7，随后运行中 STOP（`evidence/20261005T085553.527428Z-uart-stop/`）读回 status=4，验证停止通路。按用户要求再次 START（`evidence/20261005T085614.667848Z-uart-start/`）读回 status=7，后续只读 inspect（`evidence/20261005T085640.392639Z-uart-inspect/`）读回 status=5，busy 仍为 1。所有操作退出码 0，回显恢复，boot ID 未变；采到内部 PWM 高/低状态，不等于引脚波形时序实测。原官方工件与 VART 配置保护检查均通过。

已生成 `CONTINUOUS_VERIFICATION.json` 并同步当前 BENCH、README、板测状态；离线 accessor_identity 不修改，以保留归档身份。当前持续模式保持运行，候选占用 PL，官方 DPU 尚未恢复，舵机保持拔下。软件设定目标 50 Hz、1500 µs；按实际 PL 时钟计算约 19.9998002 ms 周期、1499.990015 µs 高电平，均为计算值，外部波形、电压和测量接点仍未验收。

用户后续提供 `E5A94F9D376EDA42CCB3488A57AF45AB.jpg` 和 `250.jpg`，量程已变为 5 ms/div、1 V/div，但均为 STOP；后一张触发约 1.56 V 合适，两张都在本轮持续 START 前。分别保存源图 SHA 和读屏观察，提示自动触发与 RUN；未把冻结旧迹线归因持续候选。最后 `/home/ghmd/图片/65656565.jpg` 不存在，无法读取，已请求重发。持续版启动后的真实波形尚待确认，external_waveform_verified=false。

用户重发 `/home/ghmd/图片/4BDFDCFD8A55155C2014727A0F0DA227.jpg`，启动后首次看见重复窄脉冲；设置 STOP、5 ms/div、1 V/div、软件 10×、1.56 V 触发，脉冲高度从照片看偏小。未声称已测得精确 50 Hz/1.5 ms 或 3.3 V，保存 `evidence/4BDFDCFD-photo-observation.json`（源图 SHA 与读屏事实）。再次只读 inspect 通过且持续运行，CURRENT_BENCH 与 CONTINUOUS_VERIFICATION 更新最新证据。已询问 CH1 实体探头倍率，待反馈；下一步按 GND1 参考测 VDD1 稳态电压以区分测量问题与信号电平问题，尚未执行。持续输出保持开启，舵机保持拔下，外部验收 false。

用户随后确认“探头也是10”，已记录实体探头 10× 属于用户现场报告，与照片中的软件 10× 一致；不再把该项当作未知。下一步保持地夹 GND1，仅将尖端从 VIB 改到 VDD1，自动触发并 RUN，1 V/div 下核对约 3.3 V 稳态电压。此测量尚待执行，持续输出保持开启，没有额外软件写操作。

用户反馈“没什么变化”。没有此步截图或电压读数，不能将其记为 VDD1 电压不正常或示波器已损坏。此前照片多次为 STOP，当前先询问左上采集状态，检查是否仍显示冻结画面；暂不继续移动接线或发送新的控制写操作。持续输出未主动停止，外部验收仍 false。

用户提供 `737BA06CF9397B13840A90AF9EA8888B.jpg`，左上 AUTO、RUN/STOP 绿灯、右侧触发方式自动，确认此图采集正在运行；5 ms/div、1 V/div、10×、约 1.56 V 触发，仍可见重复窄脉冲。尚未明确探头尖是否确已从 VIB 移到 VDD1；因此不能据图判断 VDD1 供电异常或已完成 3.3 V 参考测量。保存 `evidence/737BA06C-photo-observation.json`，询问实际测点，并要求下一张拍清探头尖、地夹及隔离板端口标识。持续输出未停止，不重复软件 START。
# 19:18 UTC：重新加载并持续 START

用户明确要求“现在请你重新输出pwm”，且此前确认第一排无外接设备。重新核验既有连续版 43 项全部通过，复核 UART 传输脚本 SHA；新增 `scripts/uart_restage.py`，从板端旧归档验证 SHA/尺寸后建立新会话目录，保留旧证据，未重建 RTL/位流。

本次新会话 `/home/ghmd/kv260-j2-pwm-continuous-20261005/evidence/20261005T191535.905871Z-uart-restage/`。加载、默认低、SCRATCH、STOP、START、inspect 均 rc=0，串口回显恢复。START 证据 `20261005T191702.742126Z-uart-start/` status=7；后续 `20261005T191805.719297Z-uart-inspect/` status=5，busy=1，BUILD_ID f0206bda、boot ID d1125b5e-3286-40c5-b8ab-6264e4b4eaf0 保持。

当前 `aura-pwm-probe-continuous` 运行于 J2.1/H12：50 Hz、1500 µs、持续输出，官方应用暂时卸载。更新连续版、旧 square10/static-high 当前状态与报告，旧独立 AI 审查 ZIP 保持原快照。实际 PL0 99,999,999 Hz，寄存器推算周期 19.9998002 ms、高脉宽 1499.990015 µs。板端控制通过不等于实体电压/波形通过；外接状态仅用户报告，实际针位、幅度与时序仍待现场验收。旧固定电平低读数问题未定位。正常 3.36 V、7.5% PWM 的理想 DC 平均约 0.252 V，不能由平均读数判定实体峰值。

## 20:25 UTC：测量配对澄清，信号高低电平偏低

用户确认示波器平均 341 mV 与万用表约 0.36 V 均测信号/GND，而供电/GND 的示波器平均值为 3.36 V。“示波器读数小十倍”的此前推断源于混淆测点，已经向用户撤回。最新高值 680 mV、低值 280 mV，先前 208 mV 被最新消息覆盖；平台差为 0.400 V，尚不能验收为 3.3 V PWM。此前独立截图为周期 19.99 ms 后又 39.98 ms、正脉宽 1.524 ms、另一帧峰峰值 656 mV/时间项问号，时序稳定性也未通过。

只读 inspect `/home/ghmd/kv260-j2-pwm-continuous-20261005/evidence/20261005T202543.199585Z-uart-inspect/` rc=0，同 boot d1125b5e-3286-40c5-b8ab-6264e4b4eaf0、BUILD f0206bda，状态 5/busy1、PL0 99,999,999 Hz、周期/脉宽寄存器保持，串口回显恢复；无板端控制写入或重载。内部运行通过不能证明物理引脚电压合格。测量以用户报告/对话照片为源，实际针位与接触未独立核验；根因未知，不断言 FPGA 损坏。汇总保存 `evidence/scope-levels-680mv-280mv-user-report.json`。下一步请用户拍清实际 J2 接点与探头尖、地夹，继续区分测量接触/针位与板端信号通路。

## 20:34 UTC 启动：最终布线与载板输出通路离线审计

用户要求详细检查 FPGA 内部电路。读取 RTL、XDC、构建脚本、32 位访问器，重新核验既有工件 43 项通过；未重新仿真或构建位流。新增 `scripts/audit_output_path.tcl`，Vivado 2022.2 打开原 routed DCP，断言输出 H12/OUT/LVCMOS33/DRIVE4/SLEWSLOW、普通 OBUF 和唯一驱动 FDRE 均通过，rc=0；未发现 OBUFT/IOBUF/STARTUP 用户实例。证据 `evidence/20261005T203451.360132Z-output-path-audit/` 与 `CURRENT_OUTPUT_PATH_AUDIT.json`。

核对 Xilinx Rev B03 载板原理图第 6、17 页及 AMD DS987：H12/HDA11 经 SOM240_1 A17、0Ω R276 到 J2.1；R274/C370 为串联 RC 接地支路，不是直流电阻分压。Bank45 的 VCCO_HDA 由载板经 SOM240_1 B13/B14 供给。电源脚 3.36 V 不足以替代芯片侧供电与实体输出通路验证。现场板版本/接点未独立核验，不能确定损坏元件。

新增 `/home/ghmd/kv260-j2-pwm-continuous-20261005/OUTPUT_PATH_AUDIT.md`，同步板测状态。结论为未发现当前数字逻辑/约束/实现连接错误，实体输出低电平幅度异常原因仍待分段测量；内部状态不等于 pad 电压反馈。本轮无板端访问、START/STOP 或重载，最近实际板端读取仍为 20:25 UTC。换已确认空载引脚做同逻辑对照、核查 R276 两端及 VCCO_HDA 均仅为下一步计划，未执行。

## UTC 2026-10-06 05:44～05:47：断电后恢复连续 PWM

用户报告误关机并要求重启，串口已可访问且识别新 boot `3b572120-4f45-48ec-99ce-90e377e91036`，官方应用当时正常。复用板端旧归档，核对55,959字节与SHA-256 `402114dc7641435c1c989deda9689f1ecff72b542acd632c86814e48207f6660`，建立新会话。

`20261006T054450.654403Z-uart-restage`、`054501.604434Z-uart-load-idle`、`054600.500359Z-uart-scratch`、`054613.334314Z-uart-stop`、`054624.465082Z-uart-start`、`054711.332215Z-uart-inspect` 全部rc=0且回显恢复。加载默认status4；START返回7，随后inspect返回5、busy1、BUILD f0206bda，PL0实际99,999,999Hz。重新加载后的连续PWM控制运行通过，外部电压与波形未验收。

用户随后报告720mV、最小200mV、平均330mV。720mV的具体测量项尚未明确，不能直接等同高平台；记录 `evidence/scope-minmax-720mv-200mv-user-report.json`，同步当前BENCH与连续验证。用户问下一步处理，开始准备独立J2.3/D10固定高/低对照；尚未部署，需要确认新的J2.3外接状态。

## 2026-10-06 06:42 UTC 针脚与软件审查更正

上文历史J2.3/D10标注错误：J2.3=E10，D10=J2.5；新固定电平包从未上板，现禁止加载，新增实体针脚→XDC→最终IO报告校验在串口前正确拒绝。源约束/位流/归档冻结作追溯，未假装完成E10重建。原J2.1/H12对照厂家资料正确；43项工件核验再次通过，原输出通路审计原件显示FDRE→OBUF，无用户三态缓冲。

本轮只读证据 `20261006T063931.216719Z-uart-inspect`、`20261006T064224.066415Z-uart-inspect` 均rc0，同boot3b572120-4f45-48ec-99ce-90e377e91036/BUILDf0206bda、status5/busy1、PL0=99,999,999Hz，仍为约50Hz/1.5ms连续PWM。修正 `uart_burst.py` 中 `output_register_low` 曾误用not-running的显示错误，改读status bit1，后一条实测内部低标记true；不代表引脚电压反馈。本轮未START/STOP、未加载。

最后的一致性断言首次发现BENCH最新inspect指针没有随只读脚本更新；已补齐inspect分支持久化并对齐当前汇总，不修改硬件。修正后重新核验机器状态文件与实际回读证据一致。

低幅度根因未知；720mV具体测量项未确认，平均低电压不能独立证明幅度异常，未配置第二排也不是固定高电平正常对照。已更新当前记录和新增 `CONNECTOR_AND_PWM_REVIEW.md`，列明软件错误影响范围、官方来源、实际检查、文件改动和仍未验证的实体电气项。
