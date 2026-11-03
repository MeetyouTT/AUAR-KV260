# J2 PWM 板测状态（2026-10-05 PDT）

## 当前实测状态

**后续状态更新：**用户要求持续输出，原一秒候选已退出；持续版已在独立目录 `/home/ghmd/kv260-j2-pwm-continuous-20261005` 完成仿真、构建、加载、运行中 STOP 验证及重新启动，现按用户要求保持运行。当前活动 PL 与下一步以 [持续版状态](../kv260-j2-pwm-continuous-20261005/BOARD_BRINGUP_STATUS.md) 为准。以下内容保留一秒版本的实测过程；原目录恢复官方的记录是切换前历史，不代表目前 DPU 活动。

最新操作：用户要求重新设置示波器选项后，明确要求“你重新给一个波形”，已执行第三次有限 START，证据 `evidence/20261005T082114.174627Z-uart-start/`。退出码 0、boot ID 不变、最终 status=4/frames_left=0，回显恢复。重新设置后的单次等待状态未再次收到明确反馈，本轮仪器是否捕获仍待照片确认；没有宣称外部脉冲通过。此前 PROBE COMP 检查计划暂缓，尚无执行结果。

- 用户按 RESET/SW2 后捕获完整启动至 root 提示符，Linux 已恢复。新 boot ID 为 `50909139-fa62-4afc-9243-a2438d57293f`；原官方应用自动启动，四份官方工件哈希一致，目标 GLIBC 2.34 兼容新访问器。证据 `evidence/20261005T072733.549866Z-pwm-uart-readonly/`。这是系统复位，不是已确认的断电冷启动。
- 修正包 57,417 字节、48 帧 UART 上传及整体 SHA 核验通过，新板端路径 `/home/root/aura-pwm-probe-stage/20261005T073059.065037Z/aura-pwm-probe-stage.tar.gz`。
- 候选已重新加载，新 ELF 的非 MMIO 运行入口、文件身份、默认禁能寄存器和 PL0 实际 99,999,999 Hz 检查通过，见 `evidence/20261005T073342.186703Z-uart-load-idle/`。当前占用 PL 的是 `aura-pwm-probe`，不是 DPU 官方配置。
- 新完整 32 位 SCRATCH 两个模式写读并恢复原值通过；STOP 完整字写入及读回通过，见 `evidence/20261005T073601.448435Z-uart-scratch/` 与 `evidence/20261005T073647.959523Z-uart-stop/`。
- 用户本轮确认单次等待后，修正访问器的一次 START 完成，退出码 0、boot ID 不变、最终 status=4/frames_left=0，串口回显恢复。证据 `evidence/20261005T074247.954619Z-uart-start/`。这证明本次启动控制及结束读回通过，不等于外部 50 帧波形已验收。
- 用户随后提供 `65BDDB30782456C8B88E484B04A644CF.jpg`：STOP、5 ms/div、2 V/div、10×、2.48 V 触发，照片可见接近水平的蓝色轨迹，未能辨认重复矩形脉冲。用户补充“有波形”，现场波形形态尚待说明，不能据照片断言无信号或隔离模块故障。
- 随后指导用户将 CH1 改测隔离器输入 VIB/GND1、1 V/div、5 ms/div、约 1.6 V 单次上升沿触发，舵机保持拔下。用户回复“输入端已等待”后发送第二次有限 START，退出码 0、boot ID 不变、最终 status=4/frames_left=0，见 `evidence/20261005T081349.970765Z-uart-start/`。现场接点属于用户就绪报告，尚未独立核实；输入端捕获照片待提供，不能宣称输入脉冲已通过。
- 用户随后报告“我看不到什么也没有”，本轮输入端未取得可验收的波形；尚无本轮截图，原因未定位。当前候选仍活动，最后结束读回的输出寄存器为低；官方应用尚未恢复。下一步将 CH1 探头尖和地夹都从项目电路取下，改测示波器自身 PROBE COMP 信号，按 AUTO 检查已知方波，以区分采集/探头问题和项目信号链路问题。此检查尚待现场执行，未再次发送 START。

## 历史排查过程（以下旧状态不代替顶部当前实测状态）

2026-10-05 PDT 恢复检查：USB 重插后 UART 仍无返回。用户执行管理员 JTAG 检查，USB 权限通过，但调试库报 `FTDMGR wasnt properly initialized`（`evidence/20261005T070509.654725Z-jtag-readonly/`）。改进脚本后用普通用户记录系统调用，确认共享文件打开成功、板卡 USB 总线设备打开返回 `EACCES`（`evidence/20261005T070837.424027Z-jtag-readonly/`）。下一步为用户在本机终端执行 `sudo /usr/bin/setfacl -m u:ghmd:rw /dev/bus/usb/003/006`，只给当前一个设备添加临时用户访问权限，再由助手以普通用户查询目标。非交互 sudo 仍要求密码，ACL 未应用。没有修改永久驱动规则、删除共享文件、复位或下载 FPGA；新 MMIO 与 PWM 未上板测试。详见 `/home/ghmd/AMD_Smart/logs/daily/2026-10-05-J2-PWM-RECOVERY.md`。

候选已安装和加载，身份、默认禁能状态及 PL0 时钟读回通过；第一次启动旧客户端时发生内核 SError/panic，板端失去响应。用户报告没看到波形，尚无合格的 J2/隔离器 PWM 记录。已保存错误证据、阻止旧客户端继续启动，并准备新的明确 32 位访问器及归档。板卡恢复和新客户端板测尚待完成。

用户在“重新开始”后以“好了”确认完成现场断电重新上电步骤。随后两次沙箱外 UART 只读连接均未收到任何串口字节（各原始记录为 0 字节），无法确认 root 提示符或 Linux 恢复；未发送板端检查命令、未传新包、未加载或 START。证据为 `evidence/20261005T062508.618062Z-pwm-uart-readonly/` 和 `evidence/20261005T062546.762959Z-pwm-uart-readonly/`。USB 串口设备可打开不等于 KV260 系统已启动；启动、供电或串口链路的具体原因仍未确认，已询问板上电源指示灯状态。

用户随后确认电源指示灯亮。沙箱外只读主机检查确认同一 Xilinx USB 设备的 if00–if03 四个接口存在，原固定 if01 仍为 `/dev/ttyUSB1`；没有换口或发送数据到其他接口。主机只有 Wi-Fi `192.168.1.102/24`，目标 `192.168.50.2` 路由走 Wi-Fi 网关，SSH 端口探测超时，因此当前不能以主机网络探测判断板卡是否启动。已询问 KV260 所接显示屏的当前画面；新客户端和 PWM 仍未执行。

用户提供 `0000.jpg` 示波器照片，显示 STOP、5 ms/div、2 V/div、10×、2.48 V 触发及平线；不是 KV260 显示屏画面，不能用于确认 Linux 恢复。用户随后要求“我没看见，重新来”。再次 UART 连接失败（`evidence/20261005T065223.160653Z-pwm-uart-readonly/`）；已为 `uart_preflight.py` 增加 `--capture-boot`，本机语法检查通过。开启监听后请用户再次主电源断开 5 秒重新供电、USB 保持连接，但未收到该次上电确认。120 秒被动监听及随后提示符探测均无字节返回（`evidence/20261005T065315.010557Z-pwm-uart-readonly/`），未发送目标任务命令。该结果不能证明已观察到一次失败的冷启动，因为现场是否在监听期间执行上电尚未确认。下一步建议重插电脑与 KV260 间 USB 串口线后再检查连接；没有自动重启、登录、加载 PL 或执行 PWM。

## 历史准备结果（2026-10-04）

- 最终离线 RTL/位流构建及 41 项核验通过，见 `CURRENT_BUILD.json`、`FINAL_VERIFICATION.json`。测试配置固定 50 Hz、1500 µs、50 帧；输出默认低，显式 START 后约 1 秒结束。
- 使用 Xilinx 2022.2 设备树生成器从本次 XSA 产生覆盖层；补入此板既有 FPGA manager 路线使用的 `fpga-config-from-dmabuf`。Bootgen 从验收的 BIT 生成完整 PL `aura_pwm_probe.bit.bin`，并生成 DTBO 与 `PL_FLAT` `shell.json`。在旧板系统 DTB 上离线合并通过，确认 `firmware-name=aura_pwm_probe.bit.bin`、PL0 99,999,001 Hz、AFI14=`0xa00`、AFI15=`0`、IP 窗口 `0x80080000/0x1000`。包明细与哈希见 `CURRENT_LINUX_PACKAGE.json`。这是文件一致性检查，不是加载成功证明。
- 串口只读状态见 `CURRENT_PREFLIGHT.json`：板端 SD CID `0353445345333247805558c00401a100`，内核 `5.15.36-xilinx-v2022.2`，boot ID `e10b557d-2cca-4486-b5cb-411cd0cf7691`；当前 `kv260-benchmark-b4096` 为活动应用，FPGA manager 为 `operating`，`dfx-mgr` 服务运行。当前 PL0 调试时钟读数为 99,999,999 Hz，是**官方应用当前状态**；候选加载后的时钟尚未测。`/dev/mem` 设备存在，客户端访问仍未尝试。
- 暂存压缩包为 52,661 字节，SHA-256 `69c2e93bad7ac9a7d2b55a2034748c570867374f5da78473ae8ba57b5869d8ec`；串口 44 帧均有回执，板端最终尺寸与 SHA-256 匹配、终端回显已恢复。板端独立路径：`/home/root/aura-pwm-probe-stage/20261005T050807.963306Z/aura-pwm-probe-stage.tar.gz`。见 `CURRENT_BOARD_STAGE.json`。它只是待用归档，PL 未切换。
- 示波器最新照片 `C641A6860AC669BD80FA2215DAC64BD2.jpg`（SHA-256 `05beefad28a56715e9fa1a913d49350b36c18e00f7a8d9f243bc38c6d4840c50`）显示 5 ms/div、2 V/div、CH1 上升沿单次触发、约 2.48 V、`STOP`。画面不能判定为 50 Hz PWM；探头远端落点和舵机插头状态未从照片确认。

## 首次板测与故障记录（历史）

用户随后以“好了”确认舵机插头拔下、探头 VOB/GND2；随后明确“已进入单次等待”。这是用户现场确认，没有替代独立电气测量。安装和加载的成功证据保留在 `evidence/20261005T051832.170321Z-uart-load-idle/`：PWMT `0x50574d54`、ABI `0x10000`、BUILD_ID `0x03cd161b`、状态 4、剩余帧 0，PL0 实际读数 99,999,999 Hz。按该时钟和固定 ticks 计算周期 19.9998002 ms、脉宽 1499.990015 µs，是计算值而非外部仪器实测。

启动失败证据在 `evidence/20261005T052100.955710Z-uart-start/`，原始串口记录 `SError code 0xbf000002`、`Comm: python3`、`Kernel panic - not syncing: Asynchronous SError Interrupt`；无法自动恢复官方应用，控制台回显恢复也未完成。旧 `REJECTED_probe.py` 使用 `struct.pack_into('<I', ...)` 写 MMIO，不能保证完整 32 位存储，而本核控制寄存器要求 `WSTRB=0xf`、不完整写返回 SLVERR。这是当前最可能的原因；缺少故障点目标二进制反汇编/修正后的板测，直接因果仍未证实。参考 [Linux 设备 I/O 文档](https://docs.kernel.org/driver-api/device-io.html) 对明确访问宽度及不能用普通内存复制操作代替 I/O 访问的说明。未声称硬件发过 50 帧或输出已自动停止。

新 `board/mmio32.c` 已交叉编译为 AArch64 ELF，反汇编确认 MMIO 读函数为 `ldr w0, [x0]`、写函数为 `str w1, [x0]`，写前后有 `dsb sy`；板卡/固件/身份/参数门禁、禁能启动门禁、有限时长及 STOP 均在访问器内检查。Python 仅校验 ELF 哈希并调用它，不再直接写映射缓冲区。新工具还增加无 PWM 的 SCRATCH 字读写并恢复原值检查。动态 ELF 需要 GLIBC_2.34，恢复后先核对目标运行库。新包见 `CURRENT_STAGE.json`；本地归档 SHA-256 `4c5be93243704ff214a203e756e9ce4e8bf067198f256f22d9d78e784d839350`，57,417 字节，尚未传到板卡。`evidence/accessor_review.json` 是离线检查，不等于板测通过。

当前 `CURRENT_BENCH.json` 标为不可继续软件访问/待恢复。先保持舵机电池断开、舵机插头拔下，由用户断开 KV260 主电源约 5 秒后重新上电。恢复后只读核验 Linux、当前官方应用和原固件哈希；暂存/核验新包、确认目标 ELF 可运行，再重新加载候选。先只读检查、SCRATCH 完整字写入和 STOP，全部通过后再让示波器重新进入单次等待并执行一次 START。任何门禁失败则停止该步骤并保存证据。

身份和默认状态通过后，让示波器从当前 `STOP` 按 `RUN/STOP` 进入单次等待，再执行一次显式 `board/probe.py --start`。期待 VOB 对 GND2 的周期约 20 ms、高电平约 1.5 ms、最多 50 帧后持续低电平；照片或仪器导出数据才能确认外部波形。测试结束执行 STOP/核验禁能，卸载候选并重新加载原官方应用，核对原固件名、`/etc/vart.conf` 与 FPGA manager 状态。完整 PL 候选占用原 DPU，因此这是临时数字波形测试，不等于正式联合平台或舵机机械标定。

若无法确认现场接线或加载/恢复任一步的前置条件，不访问 `0x80080000`，不发 START。后续板测应保留新证据目录，并分别标记用户现场报告、主机离线验证和目标板实测。
