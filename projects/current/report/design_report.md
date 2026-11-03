# 技术文档取数页

## 系统组成

Kria KV260/K26 的 PL 包含单核 B4096 DPU 和自定义可视转轴寄存器 IP，器件为 `xck26-sfvc784-2LV-c`。DPU 承担 YOLOX、YuNet、SFace 三模型分时推理。板端 Linux 组织相机流程、业务状态、语音前端、角色界面与动作。历史 27B 和 TTS 推理在独立 Windows GPU 服务完成，接口端口 8797。

## 可引用的数据位置

| 文档内容 | 依据 |
|---|---|
| 场景、功能分工及端到端数据流 | `src/board/vision`、`src/board/interaction`、`src/board/runtime`、`src/host/model_service` 以及两个 systemd 单元和最终 drop-in |
| 模块、使用方法与依赖 | 根 README，`build/env.json`，`board/deploy.json`，`src/models/inputs` |
| PL 架构与实现 | `src/fpga/bd/address_map.json`、`src/fpga/rtl/visual_servo.sv`、`src/fpga/constraints/pin.xdc` 以及本次 Vivado 报告摘要 |
| IP 寄存器、时钟及外部接口 | 伺服基址 0x80080000，DPU 基址 0xA0010000，区间各 4 KiB。寄存器时钟 99,999,000 Hz，DPU 两路 299,997,000 和 599,994,000 Hz。PWM 经 E10，LVCMOS33，驱动 8 mA，下降/上升速率配置 SLOW。BUILD_ID 为 0x10282601，脉宽范围 500 至 2500 µs，中心 1500 µs，步长 4 µs。 |
| 验证过程和结果 | `report/validation_summary.md` 区分本轮 Ubuntu、历史采样与尚待实板执行的项目，`report/evidence` 保存精简回执 |
| 性能数据与口径 | `data/metrics.csv` 的 18 条历史记录。179.773885 秒业务窗口内 YOLOX 9.907 次/秒，YuNet 9.862 次/秒，SFace 0.740 次/秒。表中保留分母、阶段名称与样本数。 |
| 比赛 Skill 与 AI 协作 | `skill/README.md`，`report/ai_collaboration.md` 及 `report/ai_evidence` |

正式技术文档可把板端实测、Ubuntu 软件/硬件工具验证分别列栏。重复采样应保存固件指纹、软件清单、时段、计数起止和设备条件，便于与已有窗口对照。
