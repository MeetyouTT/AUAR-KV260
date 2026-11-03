# 三个项目技能与通用 PYNQ 补充

| 目录 | 工作对象 | 可在低核 Linux 上检查的内容 |
| --- | --- | --- |
| command_guard_validation | A，运动命令保护 | 命令重放、越界、租约、STOP 与 QUIESCE。附同版 4 套 RTL 测试台及实际 XSim 日志。 |
| perception_freshness_benchmark | B，三模型服务率和感知时效 | 原始窗口计数回放、时钟和过期反例、三份 XIR 元数据。声纹 ECAPA 保留在 ARM CPU。 |
| llm_voice_runtime_optimization | C，LLM/TTS 交互运行优化 | 按次复算 RPC、解码速度和实时率，验证过期播放确认和记忆撤销。 |
| pynq_contract_testgen | 通用补充 | 用契约和合成 HWH 为加法器、CRC 生成可执行桩并与软件参考比对。 |

每个目录的 readme.md 含输入格式、运行入口、具体失败案例、证据和适用范围。在工程根目录执行 build/scripts/reproduce.py 可串行复跑。第四项沿用 Ubuntu 已完成的独立离线工具，PYNQ 真板和跨板复用属于单独验证范围。
