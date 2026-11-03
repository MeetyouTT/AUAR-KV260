# AUAR·雪妃 | KV260 工程交付

AMD 初级组自主命题 · 工程归档 2026-11-02。作品由 KV260、USB 相机、触控显示、MCP01 音频设备、单轴机构及局域网 Windows 推理主机构成。目录名和代码中的 AURA 沿用开发工程标识。

## 在另一台 Ubuntu 20.04 上先跑

将主 RAR 解压到新目录，进入解压出的 aura。两个命令只用 Python 3.8+ 标准库，按顺序使用一个进程执行检查。原始包可放在 U 盘，验证结果写到新目录。首次整包 SHA-256 校验会顺序读一次参考 DCP。

~~~sh
python3 -B build/scripts/verify.py
python3 -B build/scripts/reproduce.py --out "$HOME/auar-check-01"
~~~

第一条逐文件验证，也检查 380 项板端业务文件、启动配置、25 项跟随控制文件、三个 DPU 模型、配套固件和两组 RPC 原记录。第二条运行转轴软件夹具、三个专题技能和独立的 PYNQ 生成测试。每一步的退出码和日志见输出目录的 summary.json。再次运行请选择新的 --out。原机 Ubuntu 20.04 复跑与交付文件复验见随包外的 verification 文件夹。

## 从哪里看工程

| 工作 | 位置 | 可以核对的内容 |
| --- | --- | --- |
| FPGA 设计 | src/fpga、build/scripts、build/reports | 两个自研 RTL 模块、基础和结果 BD、约束、DPU/IP 输入、旧增量参考 DCP、实际时序与资源报告 |
| 仿真与参考 | sim、data/reference、data/results/xsim | 四个 RTL 测试台、仿真波形、期望输出及当前转轴控制的仿真夹具 |
| KV260 业务 | src/software、board | 带原始包布局的 GUI、语音、身份、记忆及设备适配，固件、启动入口与部署清单 |
| 视觉与转轴 | src/camera、src/vision_quantization、src/motion、models | DPU 运行和调度、图像采集、跟随控制、CPU 跟踪及量化/原生接口源码；当前跟随版本在 src/motion/follow |
| 玩偶与 Windows 推理 | src/avatar、src/windows | 原生雪妃渲染 C/C++、选定语音参考、27B 与 TTS 的 Windows 服务和环境锁 |
| 数据与报告 | data、report | 最新性能原始采样、五对公开请求的数据、三份 XIR 实际解析、设计报告、图和 AI 协作记录 |
| 三个技能 | skill | A 运动命令保护、B DPU 调度与感知时效、C 语音大模型运行优化，另附 PYNQ 契约测试生成 |
| 来源与交付边界 | third_party_notices.md、board/readme.md、report/release_status.md | 第三方材料、设备专属配置、验证条件、历史缺陷和当前结果 |

## 三种复现工作

* **复查代码、仿真证据与性能。** 使用上面的低核入口。四个 RTL bench 可在装了 Vivado 的工作站按 skill/command_guard_validation/readme.md 重新运行。性能表可从三模型和两类推理的真实原始记录重算。
* **重建 FPGA。** 见 build/readme.md。Vivado/Vitis 2022.2 和原参考 DCP 对应现役平台。归档中的 board/firmware 是历史实际配套工件。工程创建、从原已布线检查点导出以及 Bootgen 对照均在打包期间独立复跑。
* **准备实物部署。** 见 board/readme.md 和 src/windows/readme.md。板侧根文件系统暂存和 Windows 模型准备均有独立入口。CPU 模型/板端 wheel 在 auar_board_audio_dependencies.zip 中，放在主 RAR 旁。27B、OmniVoice 和工具安装按固定来源准备。已有板上的私有身份、声纹模板与对话数据留在所属设备。

在现役设备上运行与在空白板卡上重新安装是不同的验证条件。已有演示应保留板上个人数据和当次开机绑定，转轴按当前位置继续。下方文档列出实测和未覆盖的部分。
