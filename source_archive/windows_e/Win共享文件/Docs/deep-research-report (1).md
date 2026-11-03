# AMD Kria KV260 固定式多模态交互玩偶：20 天统一技术方案、三人最终任务书与验收合稿
> ⚠️ **历史材料**：本文的状态名与编号**不是当前口径**。现行口径见 `amd_kv260_full_work_requirements_v3.md`（D5，运动状态为 `DISARMED / NEEDS_REFERENCE / ARMED / TRACKING / AT_LIMIT / FAULT`）与 `D5与AURA框架映射表与基线分工_v1_0.md`；仓库名一律 **`aura`**（2026-09-26）。


本报告以 **2026-09-15** 为研究时点，完整审阅了你上传的三份项目方案与 2026 AMD FPGA 赛道官方选题指南，并用 AMD 官方文档、AMD/Xilinx 官方 GitHub、Vitis AI 官方资料、Qwen 官方模型许可、llama.cpp、sherpa-onnx、OpenCV Zoo 等一手资料进行交叉核验。四份文件分别为：2026 AMD 赛道指南 fileciteturn0file0、KV260 三人 20 天 V2 计划 fileciteturn0file1、KV260 30 天 V1 迁移计划 fileciteturn0file2、历史 FMQL30TAI V3.4 计划 fileciteturn0file3。

为避免把计划、推断和实测混在一起，下文每项关键结论使用你规定的六种标签。**“目标值”不是实测值；所有需要真实板卡、执行器、Windows 主机或现场环境才能确认的数据，均不写成最终成绩。**

| 标签 | 含义 |
|---|---|
| **已有文件明确说明** | 上传文件明确写出的要求、方案、计划或历史内容 |
| **AMD 官方资料确认** | AMD 官方文档、AMD/Xilinx 官方仓库已确认 |
| **开源项目或模型官方资料确认** | 模型或开源项目官方仓库、模型卡、许可证确认 |
| **根据资料推断** | 基于以上资料做出的工程设计选择，不是厂商保证 |
| **必须上板验证** | 需要 KV260、实际软件栈、外设或机械设备实测 |
| **当前无法确认** | 现有材料不足，不能可靠给出结论 |

## 文档审查报告

**已有文件明确说明：** 四份文件并不是四个同级“已完成方案”。2026 赛道指南是比赛规则；V2 是以三人 20 天为约束的执行计划；V1 是更早的 30 天 KV260 迁移草案；FMQL30TAI V3.4 是旧硬件平台方案。V2 自己也明确声明其中命令、文件、参数、指标均是“待实现或待验证项”，不能视为已经完成。fileciteturn0file0 fileciteturn0file1 fileciteturn0file2 fileciteturn0file3

**已有文件明确说明：** 2026 指南中的“自主选题初级组”面向大学一年级至三年级本科生，可使用 AMD 7 Series、Zynq-7000、UltraScale 或 UltraScale+；并没有要求初级组必须使用 KR260，也没有要求必须配 Ryzen AI PC。Ryzen AI PC 是指南中“具身智能赛道”的要求，不能跨赛道移植到自主选题组。指南还要求真实硬件运行、可复现工程、源代码、综合/实现与测试证据，并鼓励提交大模型协作记录和可复用 Skill。fileciteturn0file0

**已有文件明确说明：** V2 的核心方向与当前用户要求最接近：KV260 PL 放 AMD DPU 和自研 `motion_guard_ip`；PS 负责摄像头、后处理、跟踪与板端服务；Windows 主机负责本地 VLM、身份、ASR/TTS；首版采用“按键说话、松开提交”；三方 D5 首次联调、D7 视觉与真实转轴闭环、D10 第一版完整产品、D15 冻结、D16—D20 验证与材料。fileciteturn0file1

**已有文件明确说明：** V1 的主要价值是给出了较完整的 KV260 迁移思想、测试指标结构、安全考虑和寄存器初稿；但它仍按 30 天组织，且自然语言/视觉问答部分较强调豆包等云端服务，与当前“Windows 本地视觉语言模型”的主线存在直接冲突。fileciteturn0file2

**已有文件明确说明：** FMQL30TAI 方案中 ByteTrack-Lite、One Euro/视觉伺服、`presence_session_id`、人脸 embedding 身份记忆、音频代次、FPGA PWM/看门狗/停止等“设计思想”可继承；但是 FMQL30TAI 芯片、ICraft、旧 NPU 工件、旧板卡引脚、旧 DDR/HDMI/资源数字等均属于旧平台，不能作为 KV260 已有实现或板级事实。fileciteturn0file3

**文档间冲突与统一决策：**

| 冲突 | 文件状态 | 统一结论 | 结论标签 |
|---|---|---|---|
| 30 天还是 20 天 | V1 30 天；V2 与当前要求 20 天 | **以 20 天为唯一权威排期** | 已有文件明确说明 |
| 云端豆包还是本地 VLM | V1 偏云；V2/当前要求本地主机 | **Windows 本地 VLM 为主线；公网服务不进入必交闭环** | 已有文件明确说明 |
| 身份识别上 KV260 还是 Windows | V1 有迁板倾向；V2 先 Windows | **20 天版本放 Windows；迁 KV260 属后续增强** | 根据资料推断 |
| 全双工语音还是 PTT | FMQL 追求全双工；V2/当前要求 PTT | **首版严格采用 PTT** | 已有文件明确说明 |
| DPU 与自研 IP 是否分别加载 | 部分旧思路容易形成不同 bitstream | **最终版本必须同一 PL 设计中共存，不能依赖两个完整位流交替覆盖** | 根据资料推断 |
| DPU 是否团队自研 | 文件已提醒不可这样写 | **AMD DPU 是 AMD IP；团队 FPGA 核心成果是 `motion_guard_ip`** | AMD 官方资料确认 |
| 工具是否应直接用“最新版” | 比赛指南推荐新工具；旧计划用 2022.x | **不能简单升级到 2026.1 DPU 流程** | AMD 官方资料确认 |
| 旧 FMQL “已完成”能否继承 | 旧文件有大量实现描述 | **只能作为历史经验；所有 KV260 项必须重新验证** | 已有文件明确说明 |

这里存在本项目最重要的技术版本冲突。**AMD 官方资料确认：** 当前官方 `kria-vitis-platforms` v1.2 已升级到 Vivado/Vitis 2026.1，但官方明确写明：KV260 的 `smartcam`、`aibox-reid`、`defect-detect`、`nlp-smartvision`、`benchmark` 等 DPU overlays 在 2026.1 中被移除，因为 **DPU IP 不支持该 2026.1 工具链**，若要构建这些 KV260 DPU overlays，应使用以前的 release tag。citeturn20search0turn20search4

这意味着“比赛推荐 Vivado/Vitis 2026.1/2025.2”和“KV260 DPU 当前官方可重建参考设计”并不是同一件事。比赛指南允许其他工具版本，只要说明理由并保证工程可复现，因此采用历史 AMD 验证 DPU 栈是合理且可答辩的，而不是“版本落后错误”。fileciteturn0file0

**AMD 官方资料确认：** 对 Zynq UltraScale+ 的 DPUCZDX8G，Vitis AI 官方兼容矩阵给出：Vitis AI 3.0 + DPUCZDX8G 4.1 对应 Vivado/Vitis/PetaLinux 2022.2；Vitis AI 2.5 + DPUCZDX8G 4.0 对应 2022.1。citeturn20search3turn20search5

**根据资料推断：** 对“三人二十天”的项目而言，不应把第一周消耗在“让 2026.1 重新支持已经被官方移除的 KV260 DPU overlay”上。建议 D1—D3 做一次硬性 Go/No-Go：优先尝试团队已有、可证明能重新构建的完整 DPU 栈；若没有，首选历史上 KV260 官方应用已有完整参考的 **2022.1 + Vitis AI 2.5** 路线，或者团队已经实际持有并能重建的 **2022.2 + Vitis AI 3.0** 路线。版本一旦 D3 锁定，20 天内不得为了“更新”再更换主工具链。citeturn20search0turn20search3

**AMD 官方资料确认：** PYNQ 不是必须项。AMD/Xilinx 的 DPU-PYNQ 官方仓库支持 KV260 B4096，但该仓库已进入历史路线，支持组合是 PYNQ 3.0 + Vitis AI 2.5；因此适合作为快速验证/应急参考，不宜宣传为当前最新 KV260 DPU 主线。citeturn20search8

**高风险项排序：**

| 优先级 | 风险 | 判断 | 应对 |
|---|---|---|---|
| 极高 | DPU 版本/平台不可重建 | 2026.1 已明确有 KV260 DPU 断档 | D3 前锁完整历史栈；保留 CPU detector 降级 |
| 极高 | DPU 与 `motion_guard_ip` 不能共同实现/加载 | 直接关系 FPGA 核心答辩 | D6 开始联合平台，D7 为硬 Gate |
| 极高 | 舵机类型、电源、扭矩、真实安全行为未知 | 可能导致机械伤害或烧毁设备 | D1 查型号；独立电源；先仪器后空载再带载 |
| 高 | Windows 主机 GPU/显存目前未提供 | VLM 性能无法预估 | D1 实查 GPU、VRAM、RAM、驱动 |
| 高 | KV260 显示栈与所选镜像不匹配 | 有 HDMI 不等于有现成桌面 | D2—D3 实板验证 |
| 高 | USB 麦克风/声卡兼容性 | 官方只验证部分外设 | D1—D3 实测 UAC |
| 高 | 身份误绑定到错误 track | 会出现“串人” | ID 与 frame/session/track/db_revision 强绑定 |
| 中 | ASR/TTS/VLM 长尾延迟 | 破坏体验但不应破坏运动安全 | Windows 异步服务；运动链完全板端独立 |
| 中 | 机械装配过晚 | D11 才发现扭矩/线束问题会失控 | D5 轻载，D7 小范围闭环，D9 初装 |

**当前无法确认：** 用户目前没有给出实际 KV260 carrier revision、当前 QSPI/SD 镜像版本、现有 Vivado/Vitis/PetaLinux 安装、Windows GPU 型号与显存、USB 摄像头型号、USB 音频型号、屏幕型号、舵机型号/堵转电流/工作电压、机械负载质量、是否有示波器/逻辑分析仪。这些是 D1 必须形成 `hardware_inventory.md` 的硬事实，不能从旧文件推断。

## 统一总体方案与技术基线

**AMD 官方资料确认：** KV260 是 K26 SOM 加 Vision AI carrier；K26 基于 XCK26 Zynq UltraScale+ MPSoC。当前 DS987 给出的 PS 包括四核 Cortex-A53、双核 Cortex-R5F、Mali-400 MP2 等；PL 资源包括约 256,200 logic cells、117,120 LUT、234,240 FF、144 个 36-Kb BRAM、64 UltraRAM、1,248 DSP 与 VCU。KV260 starter kit 配 4 GB 非 ECC DDR4。citeturn22search0turn22search1turn22search3

**AMD 官方资料确认：** 生产 K26 SOM 的通用数据表列有 eMMC，但 **KV260 Starter Kit 所搭配的 SOM 不装 eMMC**；KV260 的启动存储是 512 Mb QSPI，OS/应用主要使用 microSD。这是旧方案中很容易混淆的点。citeturn22search1turn22search13

**AMD 官方资料确认：** KV260 carrier 有 1 GbE、4×USB 3.0、HDMI 1.4、DisplayPort 1.2a、一个 12-pin Pmod、microSD、RPi camera 与两路 IAS 接口。官方接口表给出 J5=HDMI、J6=DisplayPort、J10=Ethernet、J11=microSD、J12=12 V、J2=Pmod。citeturn22search1turn22search5

**AMD 官方资料确认：** KV260 要求 12 V / 3 A 输入；每个 USB 端口最多提供 5 V/900 mA，但四口总预算为 2.1 A；Pmod 供电只有 3.3 V/100 mA。因此，**舵机绝不能从 Pmod 3.3 V 电源脚供电**。舵机必须使用与其规格匹配、能覆盖峰值/堵转电流的独立供电支路，同时正确处理信号地和 IO 电平。citeturn22search2turn22search6

**必须上板验证：** “USB 摄像头”和“USB 音频”在 Linux 层面具有合理可行性，但不能把“有 USB 接口”等同于“任意设备都能稳定工作”。AMD 官方测试的 SmartCam USB camera 包括 Logitech BRIO；官方音频参考则包含 Digilent I2S Audio Pmod。你们实际准备使用的 UVC/UAC 设备仍要做 D1—D3 冒烟、重启、热插拔和长期测试。citeturn22search7

**统一系统分工：**

| 计算位置 | 最终职责 | 结论标签 |
|---|---|---|
| KV260 PS/Linux | USB 摄像头采集、DPU 调用、预/后处理、跟踪、目标选择、视觉控制、运动驱动、帧缓存、设备健康；C 的板端 UI/录放音客户端 | 根据资料推断 |
| KV260 PL | AMD DPU；自研 `motion_guard_ip`；Pmod PWM/停止输入等确定性逻辑 | 根据资料推断 |
| Windows 本地主机 | VLM、ASR、TTS、首版人脸身份服务、模型服务 API 与 SQLite 身份库 | 根据资料推断 |
| 局域网 | JPEG/元数据/音频/回复传输；不能处在运动安全闭环中 | 根据资料推断 |
| 机身 | 摄像头、屏幕、麦克风、扬声器、单水平轴、外部停止键 | 已有文件明确说明 |

推荐的数据流是：

```text
实时运动链（不依赖 Windows）
USB Camera
    ↓
KV260 PS frame capture
    ↓
PL DPU / CPU fallback detector
    ↓
PS postprocess → tracker → target selector
    ↓
visual controller
    ↓
A local motion service
    ↓
AXI4-Lite
    ↓
motion_guard_ip → PWM → servo
    ↑
motion_status / fault / applied_seq

对话链
PTT microphone → KV260 capture → Windows ASR
                              ↓
                text + immutable JPEG snapshot
                + frame_id + presence_session_id
                              ↓
                     Windows VLM service
                              ↓
                    dialogue_result
                              ↓
                     Windows TTS
                              ↓
KV260 playback + subtitle + avatar

身份链
current tracked-person ROI / face image
    ↓
Windows YuNet/SFace-class service
    ↓
identity_state bound to
boot_id + frame_id + presence_session_id + track_id + db_revision
    ↓
only accept if target binding is still current
```

**根据资料推断：** 这条划分的核心不是“把能做的都塞进 FPGA”，而是让 PL 承担具有确定时序与可量化贡献的部分：DPU 推理加速和安全运动执行；PS 做频繁变化的策略/跟踪；Windows 做大模型、语音与身份这种更新频繁且内存/GPU 需求大的服务。这样更符合二十天交付和 FPGA 答辩的双重目标。

**AMD 官方资料确认：** “任意本地 VLM 可以编译进 KV260 DPU”是不成立的。Vitis AI DPU 流程要求模型经过量化、编译，并针对具体 DPU `arch.json`；编译器根据 DPU 支持算子进行图划分，目标架构不匹配的 xmodel 不能直接使用。DPUCZDX8G 的主要应用生态是经支持的量化神经网络，而不是一个可以透明执行任意 Transformer/VLM 的通用 GPU。citeturn16search3turn16search5

**开源项目或模型官方资料确认：** llama.cpp 当前明确支持本地 LLM/VLM、CUDA、AMD HIP、Vulkan 和 CPU+GPU 混合推理，因此作为 Windows VLM 运行层是合理候选；具体 GPU 后端要在 D1 根据你们主机实际 GPU 决定。citeturn21search6

**开源项目或模型官方资料确认：** Qwen2.5-VL-3B-Instruct 可以作为“小模型优先”的候选，但官方 3B 权重许可证是 **Qwen Research License，限非商业研究/评估用途**，不能错误写成 Apache 2.0。比赛研究用途通常与其“非商业研究/评估”定位相符，但最终 `MODEL.md` 必须保存许可证文本、来源、commit/revision 和哈希。citeturn21search2

**必须上板验证：** Qwen2.5-VL-3B 的 GGUF 量化级别、实际文件大小、Windows VRAM/RAM 占用、首 token 时间、tokens/s、图片编码耗时都依赖所选量化、上下文、图像尺寸与 GPU，因此现在不能填“实测速度”。这些数字全部由 B 在 D3/D13 实测。

**开源项目或模型官方资料确认：** OpenCV 官方 Zoo 明确包含 YuNet face detector 与 SFace face recognition 示例；Zoo 总体 Apache-2.0，但官方也提醒具体模型要核对各自许可证。它适合做比赛规模的本地身份记忆基线。citeturn21search5turn21search7

**开源项目或模型官方资料确认：** sherpa-onnx 提供 Windows/Linux 等平台的离线 ASR/TTS，包括 SenseVoice 方向和多种中文 TTS 模型，因此适合作为 C 的首版离线语音候选。具体 TTS 模型采样率、许可和中文效果必须对实际模型逐个锁定，而不能统一假定。citeturn12search1turn12search3turn12search0

**根据资料推断：版本锁定策略。** 仓库至少保存：

```text
config/
  toolchain_lock.json
  hardware_inventory.json
  runtime.yaml
  model_lock.json
  audio_manifest.json
  servo_calibration.yaml
  build_manifest.json
```

`toolchain_lock.json` 保存 Vivado/Vitis/PetaLinux/Vitis AI/VART/DPU IP/Ubuntu 或 Linux image/firmware；`model_lock.json` 保存模型仓库、revision、权重 SHA256、量化、输入规格和许可证；`build_manifest.json` 保存 Git commit、bitstream/XSA/xmodel/device-tree 等哈希。版本号之外必须有 **哈希**，否则最后无法证明 D13 测的模型和 D20 演示的是同一份。

**根据资料推断：DPU 模型主线选择。** 二十天项目不应该第一周训练全新 detector。优先级建议如下：

| 候选 | 优点 | 风险/限制 | 二十天定位 |
|---|---|---|---|
| AMD KV260 历史 `refinedet_pruned_0_96` pedestrian | 官方 KV260 AIBox/SmartCam 参考曾使用，人检测路径已被验证 | 老模型、生态老、泛化不一定最佳 | **低风险主候选** |
| AMD `ssd_adas_pruned_0_95` | 官方参考使用，含 person | ADAS 数据域，不一定适合室内玩偶 | 备用 |
| 团队自选小型 YOLO | 现代、可能更准 | 量化/算子/编译/DPU 支持链风险明显提高 | 只有已有跑通工件才选 |
| PS CPU detector | 不受 DPU 构建阻塞 | 性能可能明显低 | **明示降级，不算 DPU 完成** |

AMD 的历史 SmartCam 参考确实列出了 `ssd_adas_pruned_0_95` 和 pedestrian `refinedet_pruned_0_96` 等模型；这说明“能在 KV260 历史 DPU 栈运行”，不代表它们是 2026 年精度最优模型。citeturn15search6turn15search12

**CPU/DPU 公平比较必须这样做：** 同源模型优先；相同输入帧、相同尺寸、相同预处理、相同阈值和后处理、batch=1；分别报告预处理、推理、后处理、端到端；先 warm-up；固定 CPU 线程数和运行模式；报告 P50/P95/P99、FPS、CPU、内存和量化前后效果。如果 CPU 与 DPU 最终用了不同网络，只能称“两个系统配置比较”，不得宣称“DPU 对同模型加速 X 倍”。这是对 V2 规则的统一落实。fileciteturn0file1

**`motion_guard_ip` 最终 RTL 架构，根据资料推断：**

```text
motion_guard_ip.sv
│
├── axi4lite_regs.sv
│    ├─ RO identification/status
│    ├─ command shadow registers
│    └─ atomic COMMIT
│
├── cmd_validator.sv
│    ├─ config/session check
│    ├─ sequence check
│    └─ lease validation
│
├── angle_limiter.sv
├── slew_limiter.sv
├── angle_to_pulse.sv
├── pwm_core.sv
│    └─ only apply new pulse width at PWM frame boundary
│
├── lease_timer.sv
├── estop_sync.sv
├── fault_latch.sv
└── status_snapshot.sv
```

**根据资料推断：** 使用同一 PL 时钟和 clock-enable 产生 PWM/control tick，避免为 50 Hz 一类低速控制自行制造不必要的 fabric clock。PWM 脉宽应在周期边界双缓冲更新，避免一次 PWM 周期中途改变比较值产生异常脉宽。

**`motion_guard_ip` 建议寄存器表：**

| Offset | 名称 | 访问 | 语义 | 结论标签 |
|---:|---|---|---|---|
| `0x000` | `IP_ID` | RO | 固定 magic / IP 类型 | 根据资料推断 |
| `0x004` | `IP_VERSION` | RO | RTL ABI 版本 | 根据资料推断 |
| `0x008` | `CONFIG_CRC` | RO | 编译时标定/配置 CRC | 根据资料推断 |
| `0x00C` | `CAPABILITIES` | RO | 功能位 | 根据资料推断 |
| `0x010` | `CONTROL` | RW/WO | reference confirm、arm、disarm、clear fault strobes | 根据资料推断 |
| `0x014` | `STATUS` | RO | state/armed/output/lease/estop/fault/reference/limited | 根据资料推断 |
| `0x018` | `FAULT_CODE` | RO | 锁存故障位图 | 根据资料推断 |
| `0x01C` | `REJECT_REASON` | RO | 最近拒绝原因 | 根据资料推断 |
| `0x020` | `CURRENT_SESSION` | RO | 当前运动硬件 session | 根据资料推断 |
| `0x024` | `CMD_SESSION` | RW shadow | 命令所属 session | 根据资料推断 |
| `0x028` | `CMD_SEQ` | RW shadow | 递增命令号 | 根据资料推断 |
| `0x02C` | `TARGET_MDEG` | RW shadow | 目标角，单位毫度 | 根据资料推断 |
| `0x030` | `LEASE_US` | RW shadow | 从硬件接受开始的租约 | 根据资料推断 |
| `0x034` | `COMMIT` | WO | 原子提交 shadow fields | 根据资料推断 |
| `0x038` | `APPLIED_SEQ` | RO | 最近接受的 seq | 根据资料推断 |
| `0x03C` | `LIMITED_TARGET_MDEG` | RO | 安全限幅/限速后的指令角 | 根据资料推断 |
| `0x040` | `CMD_AGE_US` | RO | 最后有效命令年龄 | 根据资料推断 |
| `0x044` | `PWM_PERIOD_TICKS` | RO | 编译时/标定周期回读 | 根据资料推断 |
| `0x048` | `PWM_PULSE_TICKS` | RO | 当前输出比较值 | 根据资料推断 |
| `0x04C` | `ESTOP_COUNT` | RO | 硬件停止触发计数 | 根据资料推断 |
| `0x050` | `WATCHDOG_COUNT` | RO | 看门狗事件计数 | 根据资料推断 |
| `0x054` | `REJECT_COUNT` | RO | 拒绝命令计数 | 根据资料推断 |
| `0x058` | `STATUS_TIME_LO` | RO | 状态时间戳低位 | 根据资料推断 |
| `0x05C` | `STATUS_TIME_HI` | RO | 锁存高位 | 根据资料推断 |

**根据资料推断：** AXI base address 不应现在写死为某个“看起来常见”的地址。由 Vivado Address Editor 在最终 Block Design 中实际分配，写回 `register_map.md` 和软件生成头文件。AMD Vivado 支持对 AXI peripheral 打包并通过 Address Editor 管理地址空间。citeturn17search14turn17search2

**状态机建议：**

```text
RESET_SAFE
    ↓
NEEDS_REFERENCE
    ↓ user/local reference confirmation
DISARMED
    ↓ explicit ARM → new motion_session_id
ARMED_HOLD
    ↓ valid command
ACTIVE
    ├─ command expired ─────────┐
    ├─ watchdog ────────────────┤
    ├─ external stop ───────────┤
    └─ config/session fault ────┘
                               ↓
                         FAULT_LATCHED
                               ↓
           safe physical condition + CLEAR_FAULT
                               ↓
                          DISARMED
```

**必须上板验证：** 无编码器时，复位、断电、PWM 被禁用或人手转动之后，系统不知道真实机械角度。因此重启状态必须是 `NEEDS_REFERENCE`，不能显示“实际角度=0°”，也不能无条件自动高速回中。

**根据资料推断：** lease 从 **PL 接受命令的时刻** 开始，而不是 B 产生图像或 Windows 发网络请求的时刻；重复 seq、错误 session、无效 lease、配置 CRC 不匹配等命令不得刷新租约。这样才能防止一个“还活着但不停重复旧值”的进程掩盖停帧故障。

**根据资料推断：** 外部停止输入最好具备“硬件立即禁止继续产生正常控制脉冲”的独立路径，同时将状态通过同步器安全带入 AXI 时钟域。解除停止不能自动恢复运动；必须 clear fault，再重新 reference/arm。这个学生作品不能宣称“功能安全认证急停”，应准确表述为 **外部硬件停止输入/停止按钮，非安全认证**。

**必须上板验证：** 停止后的“安全 PWM”是输出低电平、停止脉冲还是保持某一安全脉宽，取决于真实舵机/驱动器。不同位置舵机对失去 PWM 的行为不同，因此不应预先把“PWM=0”写成机械一定停止。

**仿真必须至少覆盖：**

| 用例 | 验收 |
|---|---|
| reset | 输出安全、状态=`NEEDS_REFERENCE` |
| 未 reference arm | 拒绝 |
| reference + arm | 建立新的 motion session |
| min/mid/max target | 正确输出 |
| 超限 target | 按冻结策略限幅并置 `limited` |
| slew step | 每 tick 不超过允许变化量 |
| duplicate seq | 拒绝且不续租 |
| old seq | 拒绝且不续租 |
| wrong session | 拒绝 |
| invalid/too-long lease | 拒绝 |
| lease expiry | 进入故障/安全输出 |
| external stop during PWM | 安全路径立即接管；状态随后锁存 |
| stop released | 不自动重新 arm |
| clear fault while stop asserted | 拒绝 |
| reset while active | 回到位置未知 |
| CONFIG_CRC mismatch | 禁止 arm |
| AXI WSTRB partial write | 寄存器行为正确 |
| back-to-back writes | 不丢事务 |
| status timestamp rollover | 高低位读取一致 |
| randomized commands | scoreboard/SVA 无错误 |

**AMD 官方资料确认：** 当前 AMD KV260 base platform 仍可用于新的普通 Vitis 嵌入式设计，而且官方当前平台仓库说明构建平台需要 Linux 主机；2026.1 里 `xilinx_kv260_base` 已改名 `kv260_base`。但这不改变前述“2026.1 当前不提供 KV260 DPU overlays”的事实。citeturn20search1turn20search2turn20search0

**AMD 官方资料确认：** `.xsa`、`.bit/.bin`、设备树 overlay、`.xclbin`、`.hwh` 不应全部机械式地产生。其用途取决于部署流：PYNQ overlay 常用 `.bit + .hwh`；Kria dynamic firmware 可涉及 bit/bin、dtbo 以及 Vitis accelerator 所需 xclbin；Vitis platform 则由 XSA 进入软件/平台构建。最终报告应写“实际采用了哪些”，而不是把所有扩展名堆在提交目录里。citeturn17search0turn17search6turn18search1turn18search12

**20 天内 FPGA 必做与后置：**

| 必须完成 | 后续再做 |
|---|---|
| AXI4-Lite | 编码器闭环 |
| PWM | 双通道冗余停止 |
| target clamp | 安全认证 |
| slew limit | DFX/partial reconfiguration |
| cmd seq/session | 多轴同步 |
| lease/watchdog | 在线可写复杂标定表 |
| external stop | 位置/扭矩反馈控制 |
| fault latch | 高速 telemetry DMA |
| CONFIG_CRC | HLS 图像预处理核 |
| status readback | 自研 DPU |
| reset/unknown-position | 自动机械归零（除非增加传感器） |

## A_FPGA_转轴_KV260_20天任务书.md

**岗位目标——已有文件明确说明：** A 对 KV260 平台、Vivado/Vitis、DPU 与自研 IP 共存、`motion_guard_ip`、PS 驱动、舵机/机构/供电、安全链、仿真/综合/实现/时序和上板数据负最终责任。AMD DPU 的贡献应写“集成、配置和部署”，自研硬件贡献必须落在 `motion_guard_ip`。fileciteturn0file1

**负责范围：** KV260 启动与恢复、工具链、PL platform、AXI、自研 RTL、约束、PS MMIO/UIO/PYNQ 之一、执行器、电源/结构、联合 DPU 位流/固件、板级安全验证。

**不负责范围：** 人体模型算法质量、VLM 提示词、人脸识别模型、ASR/TTS、UI 视觉设计；但 A 必须提供稳定接口和状态给 B/C。

**必须创建的主要文件：**

```text
hardware/
  rtl/
    motion_guard_ip.sv
    axi4lite_regs.sv
    cmd_validator.sv
    lease_timer.sv
    angle_limiter.sv
    slew_limiter.sv
    angle_to_pulse.sv
    pwm_core.sv
    estop_sync.sv
    fault_latch.sv
    status_snapshot.sv
  sim/
    tb_axi4lite_regs.sv
    tb_pwm_core.sv
    tb_motion_guard.sv
    assertions.sv
  constraints/
    kv260_motion.xdc
  platform/
    create_project.tcl
    package_motion_ip.tcl
    integrate_platform.tcl
    build_hw.tcl
board/motion/
  motion_mmio.py
  motion_service.py
  selftest.py
docs/
  register_map.md
  hardware_setup.md
  power_wiring.md
  servo_test.md
  safety_test.md
  toolchain_lock.md
config/
  servo_calibration.yaml
  toolchain_lock.json
```

**A 的 D1—D20 最终排期：**

| 日 | 当日任务和文件 | 当日验收条件 | 依赖 / 审核 / 阻塞回退 |
|---|---|---|---|
| D1 | 盘点 KV260 revision、SD/QSPI、12V 电源、舵机型号、供电、Pmod、仪器；建 `hardware_inventory.md` | 串口/SSH 启动成功；所有“未知硬件”有清单 | B 审核板端可用性；无舵机先完成电气/逻辑 |
| D2 | 取得/启动完整参考 DPU 平台；冻结寄存器 v1；写 `pwm_core.sv`、AXI skeleton | 官方 DPU 单图或参考平台至少一条路线能运行；寄存器表评审通过 | B 与 A 共同验证 DPU；平台不通立即红项 |
| D3 | 完成 PWM、AXI、基本 guard 仿真；决定最终 DPU/toolchain 栈 | `tb_pwm_core`、AXI test 通过；`toolchain_lock.json` 冻结 | B 审核 DPU fingerprint；不允许 D4 再无故升级版本 |
| D4 | 完成 validator、lease、slew、fault；IP Packager；Block Design 接 AXI | Vivado DRC 过；地址分配产生真实 base；未接舵机先逻辑分析 | B 审核 API；C 审核 fault 字段 |
| D5 | 外部停止/超时仿真；PS MMIO/UIO driver；空载 PWM；小角度轻载 | 示波器/逻辑分析仪波形正确；停止输入可锁存；轻载无异常 | 机械未验证则保持实体轴 disabled |
| D6 | DPU + motion IP 联合构建；设备树/固件路径；拒绝错误 session/seq | 联合设计 synth/impl 至少进入可执行状态；driver 可读 IP_ID/CRC | 若资源/时序不足，先减可选 DPU/视频逻辑，不删安全 |
| D7 | 同一 PL 配置同时跑 DPU 推理和 PWM；接 B 控制 | **G3：真实 DPU + motion IP 共存，目标移动能驱动小范围转轴** | 失败则记录“DPU 未完成”，临时 CPU detector 联调 |
| D8 | 完成 fault clear/rearm/reference；错误命令注入；整理线束 | stop/watchdog/session/old seq 全部板级通过 | C 验证 UI fault |
| D9 | 初装转盘/轴承/支架；空载→轻载→实际载荷递增 | 无卡线、撞限位、明显过流；标定有效角度范围 | 扭矩不足则减旋转质量/换执行器 |
| D10 | 保存稳定 bit/XSA/dtbo/xclbin/hwh 中实际所需工件及 SHA256 | 完整产品流程首次成功；硬件 artifacts 可回滚 | B/C 共同签 release snapshot |
| D11 | 调机械空回/振动；完善 `needs_reference` 人工流程 | 10 次 reset/reference 均不突跳至危险状态 | 无编码器不得声称实际角度 |
| D12 | 最终机身固定、散热、线束、独立电源和停止键 | 30 min 整机运行无失控/供电复位 | C 审核外壳可操作性 |
| D13 | 采 ≥1000 个 PWM 周期；综合/实现/资源/时序；保存 waveform/CSV | 周期、pulse、P50/P95/P99/max 有数据；WNS/TNS 有报告 | 数字标“实测值”后才能进答辩 |
| D14 | PS daemon kill、PL reload、reset、stop、wrong seq/session、lease expiry | 每种异常有 log/波形/恢复流程 | 任何可自动误恢复问题为 blocker |
| D15 | 冻结 RTL、标定、bitstream、driver、register ABI | Git tag + hashes；功能冻结 | 后续只修 bug |
| D16 | 2h 长跑支持；温度/供电/机械观察 | 无失控；异常次数有原始记录 | 出错必须保留 failure log |
| D17 | 恢复卡/冷启动/load 顺序/selftest | 非 A 成员按文档可恢复 | B 或 C 审核复现 |
| D18 | 完成 Skill、build README、安全测试报告 | 从干净目录可以重建关键工程 | 不补造历史记录 |
| D19 | 比赛讲解：DPU 与自研 IP 分界、waveform、resource、fault demo | 能现场展示外部停止/过期命令被拒绝 | 准备离线证据视频 |
| D20 | 最终 hardware selftest、哈希核对、备份 | release artifact 与测试 artifact 一致 | 任何改变必须重新跑相关回归 |

**A 的 PS 驱动建议——根据资料推断：** 正式产品中保持一个唯一 `motion_service` 进程拥有寄存器写权限。B 不直接 `mmap` AXI；C 更不能直接写。UIO/MMIO 或匹配 PYNQ overlay 均可，但选一种后固定。PYNQ 方案只有在你们实际采用匹配的 PYNQ image/platform 时才成立。DPU-PYNQ 可验证 KV260 B4096，但其版本属于 PYNQ 3.0/Vitis AI 2.5 历史组合。citeturn20search8

**管脚要求——AMD 官方资料确认：** KV260 Pmod 是 3.3 V 接口，供电预算只有 100 mA；应从所选版本 KV260 carrier 的官方 schematic/board file/XDC 核对实际 Pmod signal 和 carrier revision。不要从旧 FMQL 引脚、网上随手复制的 XDC 或另一块 Kria 板推断。citeturn22search2turn22search9turn22search10

**DPU 联合构建最终步骤——根据资料推断：**

```text
AMD validated KV260 DPU reference
        ↓ reproduce first
freeze tool/IP/runtime/fingerprint
        ↓
open/recreate same hardware platform
        ↓
add packaged motion_guard_ip
        ↓
AXI interconnect + clock/reset + PMOD/stop external ports
        ↓
Address Editor
        ↓
DRC → synth → implementation → timing
        ↓
generate actual deployment artifacts
        ↓
boot/load same platform
        ↓
read IP_ID / CONFIG_CRC
        ↓
run DPU inference concurrently with PWM
        ↓
B visual_controller → A motion_service → PL
```

**必须上板验证：** 任何“DPU 和 motion IP 共存完成”的说法，都必须至少保存一段同一硬件配置下同时进行 DPU 推理和转轴/PWM 控制的日志/视频，且禁止通过“先下载 DPU bit，再下载 motion bit”来冒充。

**舵机验证顺序：**

```text
datasheet & supply check
→ PWM pin disconnected from servo, measure waveform
→ servo only, no mechanical load
→ center / ±small angle
→ light mechanical load
→ restricted actual assembly
→ full intended load
→ repeated motion
→ fault injection while loaded
```

**必须上板验证：** PWM 的周期和脉宽必须以真实舵机数据手册/标定为准。不能把“50 Hz、1–2 ms、180°”写成所有舵机的通用事实。

**A 最终答辩证明本人工作：** 展示 RTL 源码、testbench、仿真 assertion、AXI register map、Vivado block design、synth/implementation/timing/resource、逻辑分析仪/示波器 PWM、external-stop 波形、wrong-session/expired-command 日志、DPU 同时运行时的板级记录、供电与接线图以及实际机械故障恢复视频。

## B_视觉_本地大模型_KV260_20天任务书.md

**岗位目标——已有文件明确说明：** B 负责摄像头、人体检测、DPU 模型、CPU/DPU 对比、跟踪、目标选择、视觉控制、Windows VLM、视觉身份记忆，并向 A/C 提供稳定接口；“检测到 person”不能被包装成“完成视觉理解”，向纯文本模型发送检测框也不能叫真实图片问答。fileciteturn0file1

**负责范围：** 相机单一采集源、frame/detection/scene pipeline、DPU 后端、CPU fallback、tracking、target selector、目标角请求、VLM service、image binding、identity service、模型 provenance。

**不负责范围：** PWM 寄存器、机械供电、UI 渲染、录放音设备；B 只通过接口调用。

**必须创建：**

```text
board/vision/
  capture.py
  frame_store.py
  detector_base.py
  detector_cpu.py
  detector_dpu.py
  preprocess.py
  postprocess.py
  tracker.py
  target_selector.py
  scene_state.py
  visual_controller.py
  snapshot_service.py
host/vlm/
  dialogue_service.py
  llama_client.py
  prompt_policy.py
  image_adapter.py
host/identity/
  face_detector.py
  face_embedder.py
  identity_service.py
  identity_store.py
  enrollment.py
  recognition.py
  schema.sql
tests/
  test_frame_age.py
  test_tracker.py
  test_target_binding.py
  test_identity_binding.py
  benchmark_cpu_dpu.py
  benchmark_vlm.py
docs/
  MODEL.md
  detector_model_card.md
  vlm_model_card.md
  identity_model_card.md
```

**B 的 D1—D20 最终排期：**

| 日 | 当日任务/文件 | 验收 | 依赖 / 审核 / 回退 |
|---|---|---|---|
| D1 | 实查 Windows CPU/GPU/VRAM/RAM/driver；相机；CPU person baseline | PC 相机→检测→框；记录实际 FPS 但不作为 KV260 成绩 | A 提供网络/板卡状态 |
| D2 | 与 A 跑 KV260 DPU 单图；冻结 `frame_packet`/`detection_packet`; 安装 VLM | DPU 单图输出可解释；VLM health 可启动 | A 审核 DPU stack；C 审核 schema |
| D3 | 锁 detector 模型、输入、预处理；VLM 做一次文本+真实图片问答 | `model_lock.json`; 图片内容问题必须依赖图像才能答 | 模型失败即换低风险候选，不训练新模型 |
| D4 | 板端相机单例 capture；CPU fallback；简单 IoU tracker | 实时 `scene_state`; UI mock 可消费 | A 提供 mock motion |
| D5 | target selector、目标角、frame age；`/snapshot` | B→A 模拟/真实运动 request；C 获取准确 frame_id JPEG | G2 三方联调 |
| D6 | DPU 实时后端；队列深度 1；过期帧丢弃 | DPU backend 与 CPU backend 相同 API | DPU 卡住则 CPU fallback，但红项保留 |
| D7 | 与 A 完成真实 visual-follow；开始身份链 | **G3：DPU detection → tracking → motion_guard** | A 为硬依赖 |
| D8 | YuNet/SFace 类 enrollment/recognize/unknown | 单一目标可登记；陌生人可输出 unknown | C 接确认 UI |
| D9 | delete/correction；late identity rejection；VLM image binding | 离开/换目标后旧 identity 不串人；VLM 回传 `used_frame_id` | DB revision 生效 |
| D10 | 冻结 `/dialogue`、`scene_state`、identity API | G4 完整流程可连续演示 | C 审核接口 |
| D11 | 多人、遮挡、目标切换、tracking reset | 目标不频繁乱跳；旧 identity 自动作废 | 简单 tracker 不够再加 ByteTrack-style 关联 |
| D12 | 缩图、线程/队列优化、参数冻结 | 30 min 不积累旧帧；CPU/RAM 有数据 | 不追逐峰值 FPS |
| D13 | 公平 CPU/DPU benchmark；VLM VRAM/RAM/时延 | 原始 CSV + P50/P95/P99；效果/量化差异 | A 提供 DPU config |
| D14 | stale frame、camera stall、tracker restart、DB revision fault | 所有旧请求不产生运动/姓名错误 | C 检查 UI degradation |
| D15 | detector/tracker/VLM/identity 全部冻结 | hashes + thresholds + config tag | 后续只修 bug |
| D16 | 2h 长跑；保存 failure samples | FPS、memory、model latency、失败样例 | 不丢失败帧证据 |
| D17 | 本地离线模型包/下载脚本/许可/哈希 | 断公网仍可运行 VLM/identity | 主机模型全本地 |
| D18 | Visual/VLM/identity Skill 和复现实验 | 新环境可启动服务 | 非 B 成员审核 |
| D19 | 答辩数据和“真实传图”证明 | 展示 snapshot、请求 frame_id 与回答一致 | 准备文本-only 对照 |
| D20 | 最终模型/DB 空库/哈希自检 | 发布包无测试人脸隐私数据 | release 封存 |

**DPU 模型转换流程——AMD 官方资料确认与根据资料推断：**

```text
source model + license
        ↓
freeze preprocessing
        ↓
run model inspector / operator compatibility check
        ↓
prepare representative calibration set
        ↓
INT8 quantization
        ↓
quantized evaluation
        ↓
Vitis AI compiler
        ↓ target DPU arch.json
compiled xmodel
        ↓
deploy to exactly matching DPU platform
        ↓
VART/DPU runner
        ↓
compare output with reference
```

Vitis AI compiler 的目标 DPU 架构必须与板端实际 DPU 对上，xmodel 不应被当成跨任意 bitstream 通用文件。citeturn16search3turn16search12

**视觉控制器——根据资料推断：** 首版不要一开始上 PID。采用目标中心横向误差、死区、EMA/One-Euro 二选一、比例增量和明确限位即可。核心是新鲜帧，而不是高级控制器。

推荐：

\[
e_x = \frac{c_x-W/2}{W/2}
\]

若 `|e_x| < deadzone` 则不产生新运动；否则：

\[
\Delta\theta = K_p \cdot e_x \cdot \Delta t
\]

随后由 B 做软件安全限制，A 的 PL 再做不可绕过的最终 clamp/slew。B 永远不能认为自己软件限幅足以代替 FPGA 保护。

**目标值——不是实测值：** 初始 `deadzone` 可从画面宽度约 5%—10% 试起；允许运动的帧龄可从 300 ms 起调；motion lease 可从最大约 200 ms 起调。这些值来自 V2 的工程起点，应在 D5—D13 用真实闭环数据重新冻结。fileciteturn0file1

**跟踪策略——根据资料推断：** D1—D10 优先一个简单可靠的单目标 tracker：IoU + 中心距离 + 短时 motion continuity + target hysteresis。只有多人/遮挡测试证明不够时，再加入 ByteTrack-style 的高低置信框两阶段关联。二十天内不要引入重型 ReID tracker；“身份”由独立人脸服务解决。

**VLM Windows 部署——开源项目或模型官方资料确认：** llama.cpp 支持本地 VLM、OpenAI-compatible server、CUDA/HIP/Vulkan 等后端，适合作为一个与 C 解耦的本地服务。citeturn21search6

**真正图片问答的请求路径——根据资料推断：**

```text
C releases PTT
  ↓
ASR text
  ↓
C requests B snapshot
  ↓
B freezes JPEG:
{boot_id, frame_id, capture_mono_ns, sha256}
  ↓
C sends text + exact JPEG + IDs to B /dialogue
  ↓
B passes actual image bytes to multimodal runtime
  ↓
VLM result
  ↓
B returns:
{request_id, used_frame_id, text, model_id, status}
```

这里的关键是 **JPEG/像素本身真正进入 multimodal runtime**。`{"person": true, "bbox": ...}` 传给文本 LLM 只能算“结构化场景问答”，不能算“图片问答”。

**VLM 候选风险表：**

| 方案 | 适配判断 | 风险 | 结论标签 |
|---|---|---|---|
| Qwen2.5-VL-3B + llama.cpp-compatible GGUF | 首选小型候选 | 3B 官方权重是 Qwen Research License；GGUF/mmproj 兼容版本需实测 | 开源项目或模型官方资料确认 citeturn21search2turn21search6 |
| 更大 Qwen-VL | 中文/视觉能力潜力更强 | VRAM、TTFT、长尾延迟上升 | 根据资料推断 |
| ONNX Runtime | 适合许多 ONNX CV/语音模型 | 不等于能自动高效运行任意 Qwen VLM | 根据资料推断 |
| Transformers 原生 | 模型官方兼容性通常直接 | Windows CUDA/显存/依赖较重 | 根据资料推断 |
| VLM 上 KV260 DPU | 不作为 20 天路线 | DPU operator/内存/模型架构都不是通用 Transformer 平台 | AMD 官方资料确认 citeturn16search3turn16search5 |

**身份链——根据资料推断：**

```text
current track bbox
   ↓ crop person
face detector
   ↓
5-point alignment
   ↓
SFace-class embedding
   ↓
gallery comparison
   ↓
top1 + margin + temporal confirmation
   ↓
recognized / unknown
```

登记必须是一个事务：

```text
user requests "remember me as X"
→ current target unique?
→ usable face?
→ C asks explicit confirmation
→ collect multiple good samples
→ write person_id + embeddings + model/version
→ increment db_revision
```

**防串人规则：** 一个身份结果必须携带 `boot_id + source_frame_id + presence_session_id + track_id + db_revision`。结果返回时，任一关键绑定已改变就丢弃；不得把“慢速识别张三的结果”挂到下一位已经进入画面的用户。

**必须上板验证：** 人脸阈值不能直接复制 OpenCV 示例的 benchmark 阈值。官方 SFace benchmark 只能说明模型能力，不能等同于你们机身摄像头、光照、角度和 3—10 人 gallery 下的项目准确率。最终阈值必须用自己严格分开的登记/测试片段调。citeturn21search5

## C_UI_语音音响_KV260_20天任务书.md

**岗位目标——已有文件明确说明：** C 负责屏幕/玩偶 UI、字幕、麦克风、ASR、TTS、音响、PTT、播报取消、对话状态机、B 的模型接口、A 的故障状态、整机启动和日常集成。首版 PTT 是主线，全双工、自动唤醒和复杂 AEC 只能在核心闭环稳定后作为增强。fileciteturn0file1

**必须创建：**

```text
ui/
  index.html
  avatar.js
  state_store.js
  audio_sync.js
  engineering_panel.js
board/interaction/
  capture_audio.py
  playback_audio.py
  dialogue_orchestrator.py
  session_state.py
  service_client.py
  event_gateway.py
  ptt_input.py
host/speech/
  speech_service.py
  asr_backend.py
  tts_backend.py
scripts/
  start_board.sh
  start_host.ps1
  healthcheck.py
  export_logs.py
docs/
  audio_setup.md
  ui_states.md
  startup.md
  demo_script.md
  fault_ui.md
config/
  audio_manifest.json
```

**C 的 D1—D20 最终排期：**

| 日 | 当日任务/文件 | 验收 | 依赖 / 审核 / 回退 |
|---|---|---|---|
| D1 | PC/板端显示和录放音冒烟；设备 inventory | 能显示测试页；录一段 WAV 并回放 | A 确认最终显示接口 |
| D2 | UI 七状态；启动 ASR/TTS；记录 audio device IDs | `idle/attending/listening/thinking/speaking/degraded/fault` 可人工切换 | B 提供 mock scene |
| D3 | 锁定板端 render path、ASR/TTS 模型、音频格式 | 已录 WAV→ASR；固定文本→TTS→播放 | 显示失败则立即固定替代路径 |
| D4 | 写 orchestrator FSM；fixed phrase 驱动玩偶 | UI 由真实 state event 驱动，不直接写 FPGA | A/B mock 均可 |
| D5 | PTT→ASR→B dialogue→TTS→play；取消 | **G2：第一次端到端语音链** | B `/dialogue`; A fault mock |
| D6 | 板端正式 capture/play；取消旧轮 | 取消后迟到 TTS 不重新播放 | 主机慢时 UI 不冻结 |
| D7 | 最终屏幕；实际播放音频驱动简单口型 | `speaking` 只在音频真正开始后进入 | B scene → avatar |
| D8 | 身份登记确认 UI、unknown/fault | 登记必须显式确认 | B identity API |
| D9 | 回访问候、取消、旧 reply drop、音量调节 | 20 次取消不重播旧轮 | B request_id |
| D10 | 完整 idle→attend→listen→think→speak→attend | G4 第一版完整产品 | 三人共同审核 |
| D11 | 连续多轮、audio reconnect、UI race 修复 | 设备拔插后能 degraded/恢复 | 不要求无缝实时恢复 |
| D12 | 安装屏幕/麦克风/扬声器；统一启动 | 冷启动后所有状态一致 | A 负责供电/线束 |
| D13 | 分段 latency：capture/ASR/VLM/TTS/play | CSV + P50/P95/P99 | B 给 VLM timestamps |
| D14 | host down/network down/audio unplug/repeated PTT/A fault | UI 不假装 online；旧回答不播 | 故障测试 |
| D15 | UI/语音/config freeze | Git tag + model/audio manifest | 不加新功能 |
| D16 | 主持 2h 连续运行 | 无 UI/音频关键崩溃；错误完整记录 | 全员 |
| D17 | 新目录冷启动、日志导出 | 非 C 成员可按文档启动 | 审核人 A/B |
| D18 | Skill、speech/UI docs、视频证据整理 | 复现说明完整 | 不补造日志 |
| D19 | 全流程彩排、演示视频 | 主演示与故障备用演示都可运行 | 决赛布置模拟 |
| D20 | 冷启动最终演示、release 封存 | D20 只用冻结版本 | 变更必须重测 |

**显示路径——AMD 官方资料确认：** KV260 硬件有 HDMI 和 DisplayPort，AMD 的一些 Vitis base platform 也明确支持 DP/HDMI 视频输出；但是 platform 是针对具体外设构建的。因此“接口存在”不等于“你们所选 DPU Linux image 自带桌面浏览器并能直接显示 HTML”。D2—D3 必须在所选最终 image 上实测。citeturn22search4turn22search5

**UI 状态合同：**

| 状态 | 进入条件 | 必须显示 |
|---|---|---|
| `idle` | 无当前交互目标 | 待机动画 |
| `attending` | 有稳定目标 | 关注目标、可 PTT |
| `listening` | PTT 按下并成功开始录音 | 收音提示 |
| `thinking` | ASR/VLM/TTS 中 | 当前 request，不假装有回答 |
| `speaking` | 音频设备实际开始播放 | 字幕、简单口型 |
| `degraded` | VLM/ASR/TTS/network 等非安全依赖失败 | 明确当前不可用能力 |
| `fault` | A 报告运动硬件 fault/stop | 故障优先级最高，显示恢复步骤 |

**完整语音数据流：**

```text
PTT press
  ↓
cancel current playback if needed
  ↓
create utterance_id
  ↓
capture PCM
  ↓
PTT release
  ↓
ASR
  ↓
user_text
  ↓
create request_id
  ↓
fetch immutable snapshot from B
  ↓
B /dialogue(text + image + IDs)
  ↓
dialogue_result(request_id, used_frame_id)
  ↓
TTS
  ↓
audio tagged with request_id / utterance_id
  ↓
is request still current?
   ├─ no → discard
   └─ yes → playback
              ↓
        mouth energy animation
```

**音频格式——根据资料推断：** 首版板端 capture 可以统一成 PCM16 mono，并在 C 的 speech client 中重采样到 ASR 模型实际需要的采样率。不要预先规定 TTS 也必须输出 16 kHz；不同 TTS 模型的 native sample rate 不同，应在 `audio_manifest.json` 记录实际值，再由 playback 路径按需转换。

示例：

```json
{
  "capture_device": "stable-device-id",
  "capture_sample_rate_hz": 16000,
  "capture_channels": 1,
  "capture_format": "s16le",
  "asr_model": "...",
  "asr_model_sha256": "...",
  "tts_model": "...",
  "tts_model_sha256": "...",
  "tts_native_sample_rate_hz": 44100
}
```

这里 `44100` 只是示意字段格式，**不能在实际模型未锁定时当项目事实**。

**开源项目或模型官方资料确认：** sherpa-onnx 的 SenseVoice 路线支持普通话等语言并提供离线部署接口；C 可以把 Windows speech service 做成完全独立于 B VLM 的服务，从而避免“B 一个人负责所有 AI”。citeturn12search1turn12search3

**旧回答禁止重新播放——根据资料推断：** C 维护 `active_request_id` 和当前 `utterance_id`。ASR、VLM、TTS 每一阶段的返回都先检查 ID；PTT 新一轮、用户取消、目标切换或严重故障会 invalidate 前一轮。迟到结果只写日志，不进播放队列。

**当前图像与问题绑定——根据资料推断：** 在用户松开 PTT、ASR 得到文本以后获取一张新鲜 snapshot，冻结 `frame_id + SHA256`，再发给 VLM；不能在 VLM 排队 5 秒后随手取“当前最新图”，否则回答的图和用户提问时指向的对象可能已经不是同一个人/物体。

**口型——根据资料推断：** 二十天首版只做输出音频的分窗能量/RMS → `mouth_open`，不做 phoneme-to-viseme 精确口型。这样能证明口型跟随“真正播放的音频”，而不是回复文本。

**为什么本轮不做全双工/AEC——已有文件明确说明：** 全双工意味着同时处理扬声器回灌、AEC、VAD、barge-in、旧音频 cancel、模型流式输出和实际麦克风布局，在三人二十天约束下会明显增加系统不确定性；用户又明确要求首版 PTT。因此 D15 前不得让自动唤醒/AEC 挤占 DPU、转轴、身份和真实图片问答主线。fileciteturn0file1

## 公共接口文档与一页总排期

**根据资料推断：** 公共接口必须首先解决四个最危险的问题：**时效、目标绑定、进程/板卡重启、旧异步结果**。因此“只传 bbox 和 text”不够。

**公共时间规则：**

- `*_mono_ns`：本机单调时钟纳秒。
- `*_ms`、`*_us`：字段名本身携带单位。
- KV260 端帧龄只能用同一 KV260 monotonic clock 计算。
- Windows 时间戳不能直接减 KV260 时间戳来声称单向延迟，除非你们额外实现并验证 NTP/PTP 等同步。
- 跨机请求时延优先在发起方用本机 monotonic 测 RTT/总耗时。
- 所有 packet 带 `schema_version`。
- major version 不兼容直接拒绝；minor version 允许向后兼容字段。

**公共 ID：**

| ID | 定义 |
|---|---|
| `boot_id` | 每次板端系统运行/启动的 UUID；防止旧数据跨重启 |
| `frame_id` | 同一 `boot_id` 内单调递增 |
| `presence_session_id` | 一次连续“当前用户存在”会话；离开/重启后变化 |
| `track_id` | 当前 tracker 的短期轨迹 ID，不是永久身份 |
| `person_id` | 身份库持久 ID |
| `motion_session_id` | A 每次重新 arm 后的新硬件运动会话 |
| `request_id` | 一次 VLM/dialogue 请求 UUID |
| `utterance_id` | 一次录音/语音轮次 UUID |
| `cmd_seq` | 同一 `motion_session_id` 内运动命令序号 |

**`frame_packet`：**

```json
{
  "schema_version": "1.0",
  "boot_id": "uuid",
  "camera_id": "front",
  "frame_id": 12345,
  "capture_mono_ns": 123456789000,
  "width": 640,
  "height": 480,
  "pixel_format": "bgr8",
  "encoding": "jpeg",
  "payload_sha256": "...",
  "payload": "<binary-or-reference>"
}
```

**`detection_packet`：**

```json
{
  "schema_version": "1.0",
  "boot_id": "uuid",
  "frame_id": 12345,
  "model_id": "detector-name",
  "model_sha256": "...",
  "backend": "dpu",
  "infer_start_mono_ns": 0,
  "infer_end_mono_ns": 0,
  "detections": [
    {
      "det_id": 1,
      "class_id": 0,
      "label": "person",
      "score": 0.91,
      "bbox_xyxy_px": [100, 50, 300, 450],
      "cx_norm": 0.3125,
      "cy_norm": 0.5208
    }
  ]
}
```

**`scene_state`：**

```json
{
  "schema_version": "1.0",
  "boot_id": "uuid",
  "frame_id": 12345,
  "generated_mono_ns": 0,
  "presence_session_id": "uuid",
  "target_valid": true,
  "track_id": 7,
  "cx_norm": 0.55,
  "cy_norm": 0.48,
  "person_count": 1,
  "identity": {
    "status": "unknown",
    "person_id": null,
    "name": null
  }
}
```

**`motion_command`：**

```json
{
  "schema_version": "1.0",
  "boot_id": "uuid",
  "presence_session_id": "uuid",
  "motion_session_id": 42,
  "frame_id": 12345,
  "track_id": 7,
  "cmd_seq": 101,
  "target_mdeg": 12500,
  "frame_capture_mono_ns": 0,
  "valid_until_mono_ns": 0,
  "controller_version": "visual-controller-v1"
}
```

**根据资料推断：** A 的 `motion_service` 在实际写 PL 之前重新计算剩余时效；已经过期则不写。PL 收到的是重新计算后的 `LEASE_US`，因此 Windows、大模型或 B 线程卡顿都不能把旧图重新变成“新命令”。

**`motion_status`：**

```json
{
  "schema_version": "1.0",
  "motion_session_id": 42,
  "state": "ACTIVE",
  "applied_seq": 101,
  "limited_target_mdeg": 11800,
  "cmd_age_us": 43000,
  "estop_asserted": false,
  "fault_latched": false,
  "fault_code": 0,
  "reject_reason": "OK",
  "needs_reference": false,
  "config_crc": "0x12345678",
  "output_active": true
}
```

**根据资料推断：** 没有编码器时禁止出现字段名 `actual_angle`；应写 `limited_target_mdeg` 或 `commanded_angle_mdeg`。

**`dialogue_request`：**

```json
{
  "schema_version": "1.0",
  "request_id": "uuid",
  "utterance_id": "uuid",
  "boot_id": "uuid",
  "presence_session_id": "uuid",
  "frame_id": 12345,
  "user_text": "我手里拿的是什么？",
  "image_sha256": "...",
  "scene_state": {},
  "timeout_ms": 15000
}
```

**`dialogue_result`：**

```json
{
  "schema_version": "1.0",
  "request_id": "uuid",
  "status": "OK",
  "used_frame_id": 12345,
  "text": "你手里拿着一个……",
  "expression": "happy",
  "model_id": "...",
  "model_sha256": "...",
  "backend": "llama.cpp"
}
```

**`identity_state`：**

```json
{
  "schema_version": "1.0",
  "boot_id": "uuid",
  "source_frame_id": 12345,
  "presence_session_id": "uuid",
  "track_id": 7,
  "db_revision": 18,
  "status": "recognized",
  "person_id": "uuid",
  "name": "test_user_01",
  "similarity": 0.67,
  "model_sha256": "..."
}
```

**`ui_event`：**

```json
{
  "schema_version": "1.0",
  "event_id": "uuid",
  "request_id": "uuid-or-null",
  "utterance_id": "uuid-or-null",
  "state": "thinking",
  "subtitle": "正在思考…",
  "expression": "thinking",
  "priority": 20,
  "valid_until_mono_ns": 0,
  "source": "dialogue_orchestrator"
}
```

**`audio_packet`：**

```json
{
  "schema_version": "1.0",
  "utterance_id": "uuid",
  "seq": 12,
  "source_mono_ns": 0,
  "sample_rate_hz": 16000,
  "channels": 1,
  "sample_format": "s16le",
  "encoding": "pcm",
  "samples_per_channel": 1600,
  "eof": false
}
```

**公共错误码：**

```text
OK
INVALID_SCHEMA
VERSION_MISMATCH
WRONG_BOOT
STALE_FRAME
SESSION_MISMATCH
TARGET_CHANGED
LEASE_EXPIRED
SEQ_REJECTED
ESTOP_ASSERTED
FAULT_LATCHED
NEEDS_REFERENCE
CONFIG_MISMATCH
MODEL_UNAVAILABLE
MODEL_TIMEOUT
NO_IMAGE
ASR_EMPTY
AUDIO_DEVICE_LOST
DB_REVISION_CHANGED
CANCELED
INTERNAL
```

**目标超时值——根据资料推断，不是实测：**

| 项目 | 初始目标值 | 最终冻结方式 |
|---|---:|---|
| movement input frame age | ≤300 ms | D5—D13 实测控制延迟后调整 |
| PL command lease | ≤200 ms | 保证明显短于“失控可持续时间”并经负载测试 |
| local health heartbeat | 1 s 量级 | 按服务频率调 |
| identity result | 必须 session/track 一致；建议 ≤2 s | D9 实测 |
| dialogue overall timeout | 目标 15 s | D13 P95 后冻结 |
| TTS timeout | 目标 5 s | D13 实测 |
| UI stale status | 由事件类型分别设置 | C 冻结 |

**一页二十天总排期：**

| 天 | A | B | C | 全队 Gate |
|---|---|---|---|---|
| D1 | KV260/供电/执行器盘点 | PC/相机/CPU detector | 屏幕/录放音 | BOM、未知项 |
| D2 | DPU ref + AXI/PWM | DPU 单图 + schema + VLM | UI states + ASR/TTS | API v1 |
| D3 | 仿真 + toolchain lock | 模型 lock + 真图片问答 | display/audio lock | **G1 环境冻结** |
| D4 | IP package/BD/MMIO | capture/tracker | orchestrator | mock 全链 |
| D5 | stop/lease + 轻载 | snapshot + motion target | PTT 对话 | **G2 首次三方联调** |
| D6 | DPU+IP build | DPU realtime | 正式板端 audio | 联合平台 |
| D7 | DPU+PWM 同时上板 | visual follow | 实体屏/口型 | **G3 视觉转轴闭环** |
| D8 | fault/rearm | identity enrollment | identity UI | 登记 |
| D9 | 初装机械 | re-ID/delete/binding | greeting/cancel | 回访 |
| D10 | 硬件 snapshot | service freeze v1 | full flow | **G4 完整产品首演** |
| D11 | 机械/重启恢复 | 多人/遮挡 | 设备重连 | 串人/race 修复 |
| D12 | 实体装配/散热 | 参数优化 | 音响/屏幕固定 | **G5 30min 整机** |
| D13 | PWM/资源/时序 | CPU-DPU/VLM benchmark | 语音 latency | 第一版实测表 |
| D14 | fault injection | stale/id faults | network/audio faults | 异常回归 |
| D15 | 硬件冻结 | 模型冻结 | UI/语音冻结 | **G6 功能冻结** |
| D16 | 长跑硬件 | 长跑视觉/model | 主持 2h | soak |
| D17 | 恢复卡/自检 | 离线模型包 | 冷启动 | **G7 复现** |
| D18 | FPGA Skill/docs | Visual/VLM Skill | UI/Speech Skill | 提交材料 |
| D19 | FPGA 答辩 | AI 答辩 | 演示总彩排 | **G8 彩排** |
| D20 | 最终 selftest | model/hash check | 冷启动演示 | **G9 发布** |

**重复职责检查：**

| 模块 | Owner | Reviewer | 不再由谁重复实现 |
|---|---|---|---|
| DPU hardware platform | A | B | B 不做第二套 FPGA platform |
| DPU model/xmodel | B | A | A 不改 B 模型算法 |
| motion register writer | A | B | B/C 不直接 mmap |
| visual controller | B | A | A 不做第二个 tracker |
| VLM service | B | C | C 不直接绑定 llama.cpp 内部协议 |
| ASR/TTS | C | B | B 不维护第二套 speech service |
| identity algorithm/db | B | C | C 只负责确认 UI |
| UI/orchestrator | C | B | B 不写第二个对话状态机 |
| hardware fault source | A | C | C 只显示/调度，不清硬件 fault |
| integration leadership | C | A/B | 模块缺陷仍归原 Owner |

**D5 前置条件：** A 至少有 mock/真实 motion service；B 有 `scene_state`/snapshot；C 有 PTT/ASR/TTS 和 UI。  
**D7 前置条件：** A 联合平台已加载；B DPU 后端与 tracker 可连续输出；C 不是关键前置。  
**D10 前置条件：** D7 闭环、B 真图 VLM、B identity、C PTT/播放、A fault status 均至少最小通过。  
**D15 前置条件：** 所有必做功能必须真实接入；不能通过“冻结”把未完成项目变成完成项目。

## 验收、风险、最终演示与提交清单

**已有文件明确说明：** 比赛指南强调真实硬件结果、测试证据、源代码、工程和可复现性，因此最终成绩表必须把“目标值”和“实测值”分开；没有真实数据的位置保留 `TBD / not measured`，不得用官方 benchmark、模型卡数据或旧 FMQL 数据填充。fileciteturn0file0

**最终验收矩阵：**

| 测试 | 方法 | 目标值/通过规则 | 必交证据 |
|---|---|---|---|
| KV260 boot | 冷启动 ≥3 次 | **目标：3/3** 正常进入规定流程 | 串口 log、启动视频 |
| DPU detector | 固定测试视频 ≥1000 帧 | FPS/latency **实测，不预填** | CSV、模型 hash |
| CPU/DPU | 同源模型优先、同帧/同阈值 | 报 P50/P95/P99/FPS，不只平均值 | benchmark script/CSV |
| PWM | ≥1000 周期 | 周期/脉宽依实际舵机标定 | scope/logic analyzer CSV |
| PWM under load | DPU+USB+UI 同时工作 | 不丢失/异常脉冲 | waveform/video |
| visual follow | 左/中/右、慢/快移动 | **目标：20 次无撞限位、不持续振荡** | video + frame/cmd logs |
| stale frame | 人为堵塞 pipeline | 过期帧不提交运动 | log |
| command lease | kill B/A clients | lease 到期安全处理 | PL waveform |
| old seq/session | 重放旧命令 | 100% 拒绝 | reject logs |
| external stop | ≥10 次 | 逻辑进入预期安全状态；机械停止时间另测 | scope + video |
| reset/unknown | 非中位 reset | 不冒充已知位置、不自动危险转动 | video |
| identity enroll | 3 名测试者 | 明确确认、可写库 | DB/event logs |
| re-ID | 每人离开重返多次 | **目标：≥13/15 正确**，另报 reject/false ID | CSV/video |
| unknown | 陌生测试 | 不强行命名；单独报误认 | CSV |
| delete | 删除后重现 | 不再使用已删 identity | DB revision log |
| image QA | 20 道真正依赖图片问题 | **目标：≥16/20**；人工判定规则预先定义 | prompt + exact JPEG + response |
| image binding | 人/物快速切换 | `used_frame_id` 与 request 一致 | API log |
| ASR | 30 句固定中文任务句 | **目标：≥27/30 关键内容正确** | WAV + transcript |
| dialogue latency | ≥30 轮 | **目标：PTT release→首个实际音频 P95 ≤8 s** | trace CSV |
| cancel | ASR/VLM/TTS/play 各阶段 | **目标：20/20 不重新播放旧回答** | request logs |
| Windows crash | kill model process | 板端运动链仍工作；UI degraded | video/log |
| network down | 拔网线 | motion 独立；对话 degraded | video |
| audio unplug | 运行中拔设备 | 明确 fault/degraded，不锁死 UI | log |
| continuous run | 实体完整配置 | **目标：2 h 无失控/关键崩溃** | monitoring log |
| full demo | 固定流程 20 次 | **目标：≥18/20 完成** | trials.csv + continuous video |

上表所有数字均为 **目标值**，除非 D13—D20 把对应单元格替换为带环境说明的实测结果。V2 中已有类似目标设定，但它本身明确不是实测证据。fileciteturn0file1

**风险与正式降级表：**

| 失败项 | 主路线 | 降级路线 | 可以声称什么 | 绝对不能声称什么 |
|---|---|---|---|---|
| DPU build 失败 | DPU + motion 同 PL | PS CPU detector + motion PL | “CPU 视觉 + 自研 FPGA 转轴闭环完成” | “DPU 加速完成” |
| DPU 与 IP timing 失败 | 调 DPU config/删可选视频逻辑 | CPU detector | “自研硬件控制完成” | “DPU/IP 共存已验证” |
| VLM 显存不足 | 减量化/上下文/图像尺寸或换更小 VLM | 文本本地 LLM | “本地文本对话” | “视觉问答完成” |
| VLM 图片接口失败 | 修 multimodal backend | SceneState 文本问答 | “结构化场景问答” | “真实图片问答” |
| ASR 失败 | sherpa-onnx/其他离线 ASR | typed input | “文字+图像本地问答” | “完整语音链” |
| TTS 失败 | 替代离线 TTS | 预录系统提示/字幕 | “视觉/文字交互” | “自然 TTS 完成” |
| identity 不可靠 | unknown + 人工确认 | 关闭自动识别 | “登记接口/unknown” | “稳定重识别” |
| 屏幕板端驱动失败 | 修平台/display flow | Windows 外屏过渡 | “外部主机显示” | “KV260 本地显示完成” |
| 舵机/机构不安全 | 降载/换舵机/限制范围 | 屏幕显示虚拟转角 | “控制逻辑验证” | “实体视觉随动闭环” |
| USB audio 不兼容 | 换已验证 USB 设备 | PC 端麦克风/音箱 | 明示 host-assisted audio | “机身板端音频完成” |
| 网络不稳 | 有线局域网 | 本地视觉/运动仍工作 | “安全闭环离线” | “完整 VLM 对话离线在 KV260” |

**二十天内不应做：**

- VLM 编译进 DPU；
- 板上通用大语言模型；
- 自训练大型人体检测器；
- 双轴或 360° 旋转；
- 编码器闭环，除非现成机构已经具备；
- DFX/局部重配置；
- 复杂 HLS 视频核；
- 全双工语音；
- 自研 AEC；
- 自动唤醒；
- 复杂声源定位；
- 多摄像头 ReID；
- 活体检测/门禁级身份认证；
- 安全认证；
- 高精度 phoneme/viseme 口型；
- 复杂 agent 自动控制执行器。

**根据资料推断：最终演示流程应固定成一条可重复的 4—6 分钟主线：**

```text
冷启动
  ↓
KV260 / DPU / motion_guard / Windows services health
  ↓
UI idle
  ↓
来访者进入
  ↓
person detection + track
  ↓
target lock
  ↓
FPGA-controlled horizontal follow
  ↓
UI attending
  ↓
按住 PTT 问一个必须看图才能回答的问题
  ↓
松开
  ↓
ASR → exact JPEG → local VLM → TTS
  ↓
subtitle + audio + mouth
  ↓
“记住我，我叫……”
  ↓
UI confirmation → face enrollment
  ↓
来访者离开
  ↓
重新进入
  ↓
new track_id but recovered person_id
  ↓
personalized greeting
  ↓
展示 external stop
  ↓
PL fault latch + UI fault
  ↓
人工恢复/reference
  ↓
拔掉/禁用 Windows network or kill VLM
  ↓
UI degraded but KV260 visual tracking + safe motion remains
  ↓
结束展示 CPU/DPU、PWM 和故障数据
```

这个演示顺序能非常直观地区分三个层次：**AI 看见人 → FPGA 安全地驱动物理世界 → 本地多模态模型进行真正看图问答**。

**比赛中 A 的个人证明：** 打开 `motion_guard_ip.sv`、寄存器表、仿真波形、implementation/resource/timing、真实 PWM/stop scope、故障注入和 DPU 共存证据。  
**比赛中 B 的个人证明：** 打开 detector CPU/DPU 相同输入数据、frame age 日志、tracker/target-binding、VLM 请求中的真实 JPEG、identity session binding、模型 hash/license。  
**比赛中 C 的个人证明：** 打开 PTT 状态机、ASR/VLM/TTS trace、request cancel 日志、UI fault/degraded、真实 playback-driven mouth 和冷启动脚本。

**最终建议目录：**

```text
fogmirror-kv260/
├── README.md
├── LICENSES/
├── docs/
│   ├── architecture.md
│   ├── interface.md
│   ├── hardware_setup.md
│   ├── register_map.md
│   ├── power_wiring.md
│   ├── startup.md
│   ├── test_plan.md
│   ├── known_issues.md
│   └── demo_script.md
├── hardware/
│   ├── rtl/
│   ├── sim/
│   ├── constraints/
│   ├── platform/
│   └── report/
├── board/
│   ├── motion/
│   ├── vision/
│   └── interaction/
├── host/
│   ├── vlm/
│   ├── identity/
│   └── speech/
├── ui/
├── common/
│   ├── schemas/
│   └── error_codes.json
├── config/
│   ├── toolchain_lock.json
│   ├── hardware_inventory.json
│   ├── model_lock.json
│   ├── runtime.yaml
│   ├── servo_calibration.yaml
│   └── audio_manifest.json
├── models/
│   ├── MODEL.md
│   └── download_and_verify.*
├── tests/
├── metrics/
│   ├── metrics.csv
│   ├── logs/
│   ├── scripts/
│   └── evidence/
├── scripts/
│   ├── build_fpga.*
│   ├── deploy_board.*
│   ├── start_board.*
│   ├── start_host.*
│   ├── healthcheck.*
│   └── export_logs.*
└── skill/
    ├── README.md
    ├── kv260_dpu_motion_integration/
    ├── motion_guard_debug/
    ├── multimodal_request_binding/
    └── recovery_workflow/
```

比赛指南特别要求提交物跨平台可复现，并建议目录/文件名使用纯英文小写字母、数字、下划线或连字符；中文可放正文，因此任务书的中文标题适合文档内容，但真正提交仓库目录应按指南转换成英文规范命名。fileciteturn0file0

**最终必须归档的 FPGA 工件：**

- RTL、testbench、assertions；
- Vivado Tcl / Block Design 源；
- XDC；
- `.bit/.bin`；
- 实际工作流需要的 `.xsa`；
- 实际动态 firmware 路线需要的 `.dtbo`；
- 若用了 Vitis accelerator，则保存匹配 `.xclbin`；
- 若用了 PYNQ，则保存匹配 `.bit + .hwh`；
- synthesis、implementation、utilization、timing、DRC；
- 波形；
- 示波器/逻辑分析仪原始数据；
- register map；
- firmware/build SHA256。

**最终必须归档的模型工件：**

```text
model name
upstream owner
repository/model page
revision/commit
original filename
SHA256
quantization
input shape
preprocessing
postprocessing
runtime
target hardware
license
download date
actual RAM/VRAM measured
actual latency measured
known limitations
```

**最终必须归档的测试证据：**

```text
metrics/metrics.csv
metrics/logs/dpu_cpu_*.csv
metrics/logs/motion_*.csv
metrics/logs/dialogue_*.jsonl
metrics/logs/identity_*.csv
metrics/logs/fault_*.jsonl
metrics/logs/soak_*.csv

metrics/evidence/
  rtl_sim/
  pwm_scope/
  estop_scope/
  dpu_cpu/
  visual_follow/
  identity/
  image_qa/
  audio/
  faults/
  cold_boot/
  soak/
  demo/
```

**Skill 建议至少提交四类：** KV260 DPU 与自研 AXI IP 共存构建；`motion_guard_ip` 故障诊断；frame/request/session 多 ID 绑定方法；冷启动/故障恢复。比赛指南把可复用 Skill 和真实大模型协作过程作为重要提交方向，因此应保存实际提示词、AI 输出、人工修改、验证失败以及最终结果，而不是 D18 临时编几段“AI 使用记录”。fileciteturn0file0

**仍然无法确认、必须由团队实际验证的事项：**

| 项目 | 当前状态 | D 日截止 |
|---|---|---:|
| KV260 carrier revision | 当前无法确认 | D1 |
| QSPI/boot firmware | 当前无法确认 | D1 |
| 实际 microSD/Linux image | 当前无法确认 | D1 |
| 已安装 Vivado/Vitis/PetaLinux | 当前无法确认 | D1 |
| 团队是否已有可重建 KV260 DPU platform | 当前无法确认 | D2 |
| 2022.1/2.5 与 2022.2/3.0 哪个实际可用 | 必须上板验证 | D3 |
| DPU architecture/fingerprint | 必须上板验证 | D3 |
| Windows GPU 型号/VRAM | 当前无法确认 | D1 |
| Qwen/VLM 实际量化和速度 | 必须上机验证 | D3/D13 |
| USB camera 型号/延迟 | 当前无法确认 | D1—D3 |
| USB audio 型号/稳定性 | 当前无法确认 | D1—D3 |
| 实际屏幕与最终 HDMI/DP 显示路径 | 必须上板验证 | D3 |
| 舵机类型 | 当前无法确认 | D1 |
| 舵机 PWM 参数 | 当前无法确认 | D1—D5 |
| 堵转/启动电流 | 当前无法确认 | D1—D5 |
| 3.3 V control input 是否可靠 | 必须上板验证 | D5 |
| 机械范围/回差/扭矩 | 必须上板验证 | D5—D12 |
| 安全停止时应该断 PWM 还是保持安全脉宽 | 必须上板验证 | D5 |
| Pmod 具体输出管脚与 carrier revision 对应 | 必须上板验证 | D4 |
| DPU + motion IP resource/timing closure | 必须上板验证 | D6 |
| DPU 与 motion 同时运行稳定性 | 必须上板验证 | D7 |
| CPU/DPU 加速倍数 | 必须上板验证 | D13 |
| visual-follow P95 | 必须上板验证 | D13 |
| PWM jitter | 必须上板验证 | D13 |
| ASR 准确率 | 必须上机验证 | D13 |
| TTS/VLM P95 latency | 必须上机验证 | D13 |
| 身份阈值/准确率/误认率 | 必须上机验证 | D9—D13 |
| 连续 2 h 稳定性 | 必须上板验证 | D16 |
| 最终冷启动可复现性 | 必须上板验证 | D17—D20 |

**最终总体结论——根据资料推断：** 三人二十天做出“摄像头看见人 → KV260 DPU/CPU 检测 → PS 跟踪 → 自研 FPGA 安全控制单轴 → PTT 语音 → Windows 本地 VLM 真正接收图片 → TTS → 屏幕玩偶 → Windows 身份记忆”的**最小可演示整机是可行的，但只有在 D3 前锁定完整 KV260 DPU 工具链、D7 前完成 DPU 与 `motion_guard_ip` 共存、并坚决放弃全双工/AEC、多轴、VLM 上 DPU、DFX 和额外 FPGA 视频加速等扩展的条件下才具有合理成功率**。AMD 当前 2026.1 KV260 DPU overlay 的官方断档是本项目最大的技术版本风险，必须在开工前三天正面处理，而不能到 D7 才发现。citeturn20search0turn20search3

**最终总体结论——已有文件明确说明：** 旧 FMQL30TAI 工程可以提供交互、安全、身份和测试方法方面的经验，但它没有证明任何 KV260 FPGA、DPU、管脚、显示、音频或运动功能已经完成。最终答辩应把“从旧产品需求迁移过来的设计思想”和“在 KV260 上真实重新实现并实测的成果”明确分开。fileciteturn0file3

**最终总体结论——AMD 官方资料确认：** 本项目最有说服力的 FPGA 核心不应是“我们使用了 AMD DPU”，而应是：在 K26 的 PS/PL 异构体系中，团队把 AMD DPU 与自己的 `motion_guard_ip` 放进同一可运行系统，由自研 AXI-Lite/PWM/session/lease/watchdog/stop/fault/reference 逻辑把非确定性的 AI 感知可靠地转换为受限制、可测量、可故障注入的真实物理动作。KV260 本身提供的 Zynq UltraScale+ PS/PL 和可定制 PL 正适合构建这种软硬件闭环。citeturn22search0turn22search3turn22search10