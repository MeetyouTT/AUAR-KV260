# Ubuntu 工程验证摘要

验证环境为 Ubuntu 20.04.4 LTS x86_64、Vivado/Vitis 2022.2。Vivado SW Build 3671981，IP Build 3669848，嵌入 Tcl 8.5.14。以下结果取自这份源码的新输出。

## Tcl 与 XSim

| 测试台 | xvlog | xelab | xsim | 实际标记 |
|---|---:|---:|---:|---|
| tb_nominal | 0 | 0 | 0 | `AURA_NOMINAL_TEST_PASS` |
| tb_wide | 0 | 0 | 0 | `AURA_WIDE_TEST_PASS` |
| tb_pulse_guard | 0 | 0 | 0 | `AURA_V2_PULSE_GUARD_OFFLINE_PASS_NOT_BOARD_RELEASE` |
| tb_servo | 0 | 0 | 0 | `AURA_SERVO_TEST_PASS` |

每行标出实际退出码。12 条实际工具命令、各自源码及日志 SHA 在 `evidence/rtl_xsim.json`。缺少一个台的退出码、模拟编译失败、改动回执源码指纹均被拒绝；直接将坏结果送给 Vivado 时返回 1，未生成工程。

## 新建工程、综合、实现与固件

两份自定义 IP 从源封装，BD 从 Tcl 重建并 validate，完成 target generation、wrapper 和 XDC 加载。当前源产生的综合网表通过 PWM 引脚及寄存器检查。布局布线、物理优化、位流生成、固定硬件平台导出和 validate_hw_platform 均在本轮工作目录执行。

| 项目 | 新实现报告 |
|---|---|
| Setup WNS / TNS | 0.002 / 0.000 ns，违规端点 0 |
| Hold WHS / THS | 0.010 / 0.000 ns，违规端点 0 |
| 路由 | 199333 / 199333 条可路由网络完全布通，路由错误 0 |
| DRC Error | 0，详情和警告分组见硬件回执 |
| CLB LUTs | 66887 / 117120，利用率 57.11% |
| CLB Registers | 123100 / 234240，利用率 52.55% |
| Block RAM Tile | 93.5 / 144，利用率 64.93% |
| URAM | 56 / 64，利用率 87.50% |
| DSPs | 710 / 1248，利用率 56.89% |
| Bonded IOB | 22 / 189，利用率 11.64% |
| BUFGCE | 8 / 112，利用率 7.14% |

控制/DPU 时钟及地址已按新 XSA 的 HWH 对照独立参考核验。新 BIT 与 XSA 内嵌位流配置数据配对通过，Bootgen 已输出 BIT.BIN，目标原底图与新 DTBO 成功合并，XCLBIN 的 8 段通过回读。结果与各文件 SHA 见 `evidence/firmware_fresh.json`。`firmware_reference.json` 单独保存冻结版配对和两个底图测试。

BIT SHA-256 为 `bfb57aea58fd0918d176cf2938465c5a79bb006aa38ead371fb2b36759582509`。XSA SHA-256 为 `26cf31e83102e5226844bb8512731f51b088a8bf21d4a21ad15c1e8d30e7ab04`。原始布局布线检查点保留在 Ubuntu 的包外验证目录。本扩充包增加 board/artifacts_candidate 中的成套候选上板文件，以及按版本登记的历史实测对照。

## 软件、模型、原生库与 Skill

| 项目 | 本轮结果 |
|---|---|
| 框架 doctor、合成业务 demo | PASS。首轮发现公共角色选择文件未按原名归位，归位后两个实际入口的退出码均为 0。 |
| 精确板端文件部署 | PASS。380 项恢复出完整 9a4f 启动清单，224 相机项，33 + 23 份服务配置，15 份外置语音输入；4 个设置读取通过，正式角色 prepare_pair 实核 11 个固定引用。 |
| 现场配置与失败回滚 | PASS。测试现场字段生成独立启动指纹；缺字段或外置文件 SHA 错误时返回 1，未发布半成品。 |
| 原生库 | PASS。用匹配 EXT4 开发文件与 Vitis GCC 11.2.0 从源编译 8 个 ELF64 AArch64 库，其中 3 个与已知历史输入字节一致。构建摘要列出每个库的 SHA。 |
| 原始视觉输入 | PASS。YuNet 与 SFace 的两个 ONNX 哈希匹配。 |
| 视觉模型量化及编译 | PASS。锁定 Vitis AI CPU 镜像，独立输出 SFace、YuNet 两个 xmodel。SHA 与实际阶段日志见 `evidence/model_build.json`。 |
| 比赛 Skill | PASS。28 个原始文件，15 项单元测试，adder 36 个及 CRC32 37 个 mock 用例。 |
| 其他离线入口 | PASS。45 项历史 Windows 主机映射生成独立工作树；原资产选择器正常读取 2 张色条帧；ID/STOP 工具的缺省入口只打印计划。 |

两份编译清单中的 DPU 指纹、batch-one 端口和公共基准评估原始数值见 `evidence/model_build.json`。其中编译完成、公共数据的量化一致性和实板身份验收分别记录。

## 验证边界

未执行的项目为物理 KV260 上电、冷启动、真实相机/麦克风与显示器、机械转动、Windows 8797 GPU 推理、真实 PYNQ 板及跨板复用。`data/metrics.csv` 的 18 条数值来自历史采样，引用时保留对应版本、样本和计时区间。最终 RAR 的整包 SHA、解包检查、逐文件核对及解包后的复跑结果存于压缩包旁的 `archive_verification.json`。

## 上板资料补充

本次补入按原日期和版本登记的目标板记录，并运行147项本地证据复核、439项离线安装文件比对和5项证据反例测试。新物理板测仍未执行。详见 board_evidence_summary.md 与 evidence/board_materials_validation.json。
