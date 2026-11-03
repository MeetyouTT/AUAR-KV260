# 持续 PWM 板测状态

**2026-10-06 06:39 UTC 审查更正：** 原 PWM 的 J2.1/H12 映射核对正确；43 项工件核验再次通过。本次只读 `20261006T063931.216719Z-uart-inspect` rc=0，同 boot/BUILD、status=5/busy1、PL0=99,999,999Hz，未发送 START/STOP、未重加载。新增固定电平包此前标为 J2.3/D10 是错误：J2.3=E10，D10=J2.5。新包尚未上板，现已禁止加载；以下历史记录中的 J2.3/D10 标签全部以本条更正为准。低电压的实体根因仍未确定。

**断电后重新加载并启动（2026-10-06 05:47 UTC）：** 用户报告误关机后要求重新启动。串口识别新 boot `3b572120-4f45-48ec-99ce-90e377e91036`，当时官方应用正常；新会话复用校验归档、加载默认低、SCRATCH、STOP、START、inspect 均 rc=0。连续 PWM 的 START 状态 7、随后只读状态 5/busy1，BUILD `f0206bda`、PL0=99,999,999Hz，控制运行通过。证据为 `20261006T054450.654403Z-uart-restage`、`054501.604434Z-uart-load-idle`、`054600.500359Z-uart-scratch`、`054613.334314Z-uart-stop`、`054624.465082Z-uart-start`、`054711.332215Z-uart-inspect`。

用户随后报告 720mV、最小200mV、平均330mV；720mV的具体测量项尚未明确，不能直接当作高平台电压。汇总见 `evidence/scope-minmax-720mv-200mv-user-report.json`。外部输出仍未验收。独立 J2.3/D10 固定电平对照 `/home/ghmd/kv260-j2-pin3-static-20261006` 已完成离线准备，51项核验通过（UTC06:29），尚未部署，待确认该脚外接状态；当前本目录 PWM 的最近板端事实以上述回读为准。

**新增离线输出通路审计（2026-10-05 20:34 UTC）：** 最终 routed DCP 核查通过，H12/Bank45/LVCMOS33、普通 OBUF、唯一 FDRE 驱动，未发现用户三态缓冲。43 项既有工件核验通过。结合载板原理图，实体路径还包括 SOM240_1 A17 与 R276；不能从 J2 低幅度直接推断 FPGA 芯片损坏。详见 [OUTPUT_PATH_AUDIT.md](OUTPUT_PATH_AUDIT.md) 与 `CURRENT_OUTPUT_PATH_AUDIT.json`。本轮仅离线读取，最近板端状态仍以 20:25 UTC 记录为准，外部验收未通过。

**最新测量与只读核验（2026-10-05 20:25 UTC）：** 用户最终更正信号高值 680 mV、低值 280 mV（208 mV 已撤回），平台差约 0.400 V；同一示波器测 3.3 V 供电脚的平均值为 3.36 V。此前 341 mV 已确认是信号脚平均值，与万用表信号对地约 0.36 V 相近；之前“相差十倍”的测量倍率推断撤回。新反馈不支持仅用 PWM 平均值解释全部低电压现象，但也不能直接确定器件损坏。实际针位/探头接触尚未独立核验。

较早照片先显示周期 19.99 ms，随后 39.98 ms、正脉宽 1.524 ms，另一次峰峰值 656 mV 且周期/脉宽显示问号；不同采集的读数不能当作稳定时序验收。最新 `evidence/20261005T202543.199585Z-uart-inspect/` rc=0，当前候选/固件/归档哈希及同 boot/BUILD 核验通过，status=5、busy=1、PL0=99,999,999 Hz，串口回显恢复。本轮只读，无重新加载或 START/STOP。持续模式仍运行，外部波形未通过。测量汇总见 `evidence/scope-levels-680mv-280mv-user-report.json`；下一步核对实际 J2.1 与 GND 接点照片。

**当前状态（2026-10-05 19:18 UTC）：已按用户要求重新加载并 START，持续输出模式保持开启。** 输出 J2.1/H12，50 Hz、1500 µs、占空比约 7.5%，RUN_FRAMES=0。当前应用 `aura-pwm-probe-continuous`，BUILD_ID `f0206bda`，boot ID `d1125b5e-3286-40c5-b8ab-6264e4b4eaf0`；当前官方应用暂时卸载。离线原件重新核验 43 项通过，固件包整体哈希核验通过；未重新构建或改变 RTL、XDC。

新会话复用已核验归档，证据 `evidence/20261005T191535.905871Z-uart-restage/`；加载与默认低 `20261005T191551.962719Z-uart-load-idle/`、SCRATCH `20261005T191629.803255Z-uart-scratch/`、STOP `20261005T191645.847236Z-uart-stop/`、START `20261005T191702.742126Z-uart-start/`、后续只读 inspect `20261005T191805.719297Z-uart-inspect/` 均 rc=0、串口回显恢复。START status=7，后续 status=5、busy=1，同 boot/BUILD；5 表示运行中的低相位，并非停止。PL0 实际时钟 99,999,999 Hz，参数推算周期 19.9998002 ms、脉宽 1499.990015 µs，均非示波器实测。

用户确认第一排信号未接外部设备，作为本次空载状态依据；针位与探头接点未独立核实。外部电压与波形仍未验收，旧固定高 0.622 V / 固定低 0.282 V 原因仍未知。正常 3.36 V 高电平、7.5% 占空比的直流平均值约 0.252 V，因此不能拿本次 PWM 的低平均读数单独判定输出幅度异常。请勿按 RESET，复位会重新进入默认程序。

以下为此前各阶段的历史记录，当前状态以本节及 `CURRENT_BENCH.json` / `CONTINUOUS_VERIFICATION.json` 为准。

**历史状态（2026-10-05 09:39 UTC）：** 用户要求换波形，本 50 Hz 版本曾 STOP、卸载并恢复官方应用，证据 `evidence/20261005T093908.195150Z-uart-restore/`，原固件哈希与 VART 配置核验一致。

当前目标为用户要求的一直输出：50 Hz、1500 µs，显式 START 后持续运行，STOP 或复位后输出低。舵机保持拔下，仅测数字信号。

离线仿真和构建完成，43 项核验通过，BUILD_ID `f0206bda`，WNS +6.919 ns、WHS +0.012 ns、DRC 错误 0。匹配的 Linux 包与新 32 位访问器已归档，55,959 字节，SHA-256 `402114dc7641435c1c989deda9689f1ecff72b542acd632c86814e48207f6660`。DT 从本次 XSA 重新生成并核验 AFI/时钟/地址；只改变独立测试配置，原官方固件保持保护。

原一秒候选已 STOP/卸载并在切换前恢复官方应用，原哈希及 VART 配置一致，证据在原目录 `evidence/20261005T084146.680352Z-uart-restore/`。随后新包 47 帧上传及板端整体哈希通过（`evidence/20261005T085110.159848Z-uart-stage/`），解包、运行库兼容、独立安装、卸载官方、加载持续版和默认低电平检查通过（`evidence/20261005T085342.389377Z-uart-load-idle/`）。

当前运行 `aura-pwm-probe-continuous`，显式 START 已发送且保持运行，官方 DPU 临时卸载。SCRATCH 完整字写读恢复通过（`evidence/20261005T085438.260677Z-uart-scratch/`），空闲 STOP 通过（`evidence/20261005T085508.880942Z-uart-stop/`）；首次持续 START 返回 status=7（`evidence/20261005T085533.869617Z-uart-start/`），运行中 STOP 返回 status=4（`evidence/20261005T085553.527428Z-uart-stop/`），随后再次 START 返回 status=7（`evidence/20261005T085614.667848Z-uart-start/`），后续 inspect 返回 status=5、busy 仍为 1（`evidence/20261005T085640.392639Z-uart-inspect/`）。全部退出码 0、回显恢复，boot ID 均为 `50909139-fa62-4afc-9243-a2438d57293f`。内部 PWM 状态采到高/低，不代表引脚时序和电压已实测。

最新用户照片 `7575.jpg` 显示 STOP、20 ns/div、100 mV/div、10×，不是目标 PWM 的可验收证据，信号来源未知。持续版当时未加载。输入端 VIB/GND1 接点与舵机拔下来自用户此前就绪报告，尚未独立核实。

后续照片 `E5A94F9D376EDA42CCB3488A57AF45AB.jpg` 显示 STOP、5 ms/div、1 V/div、80 mV 触发、874.59468 Hz，持续版当时仍未加载。`250.jpg` 显示 STOP、5 ms/div、1 V/div、1.56 V 触发、低电平附近轨迹，此图在本轮持续 START 前。已提示自动触发并按 RUN/STOP 运行；等待启动后的实时照片确认外部周期约 20 ms、高电平约 1.5 ms。`CONTINUOUS_VERIFICATION.json` 仅记录控制检查通过，external_waveform_verified=false 保留。用户随后发图路径 `65656565.jpg` 不存在，已请求重新发送，没有虚构图像结果。

停止入口：`python3 -B /home/ghmd/kv260-j2-pwm-continuous-20261005/scripts/uart_burst.py stop`。恢复原官方配置入口为同一脚本 `restore`，内部先 STOP 再卸载。持续 START 前需本次加载会话 SCRATCH/STOP 通过；检查失败后仍保留身份受控的 inspect/stop/restore 通路。

用户重发 `4BDFDCFD8A55155C2014727A0F0DA227.jpg`，首次在持续版启动后看到重复窄脉冲；屏幕为 STOP、5 ms/div、1 V/div、软件 10×、1.56 V 触发。形状接近目标 PWM，但幅度从照片看明显偏小，精确周期、脉宽、电压及接点尚未测定。已再次只读核实持续模式仍运行，记录源图 SHA 与观察，询问实体探头倍率；下一步用同一 CH1 的 GND1 参考测 VDD1 稳态供电，检查测量倍率/接点。输出保持开启，external_waveform_verified=false。

用户已确认实体探头同为 10×，与软件倍率一致（现场报告）。下一步保持 GND1 地夹，仅将尖端移到 VDD1，以自动触发和 RUN 核对输入侧约 3.3 V 稳态电压；该测量尚待现场结果，未停止持续 PWM。

后续照片 `737BA06CF9397B13840A90AF9EA8888B.jpg` 确认 AUTO 自动触发且绿灯运行，排除本张画面处于 STOP 的情况。仍有重复窄脉冲，实际尖端是否接 VIB 或 VDD1 未确认；暂不判定供电故障或倍率错误，待实际探头接点照片。持续模式保持开启。
