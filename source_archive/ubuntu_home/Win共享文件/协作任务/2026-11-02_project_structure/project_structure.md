# AUAR·雪妃：自主选题初级组项目结构设计

版本：目录设计 V1，2026-11-02。工程根目录建议为 `auar_xuefei/`，正文中的作品名可使用“AUAR·雪妃”。

**提交口径更新：** 当前200M工程RAR按[方案A修订结果](rar_source_layout.md)收集：src对应原aura运行根，保留真实包/配置/资源相对位置及必要输入、脚本和精简说明。本篇507项结构仅作早期规划和内部参考，其路径布局不作为当前运行布局或投稿清单。

这是一份供你后续重新整理项目使用的**全新目录设计**。依据你指定的 AMD 指南、自主选题初级组要求，以及项目的 FPGA、KV260、Windows、视觉、语音、角色、记忆与单轴跟随功能设计；不沿用现有 RAR 的目录，不依赖它作为输入，也没有重新打包或修改现役程序。

下面列出的程序名、脚本名和输出名都是建议目标，**不表示文件已经实现或测试通过**。实际整理时，可将已有模块放入相应职责目录；不必为了符合本树而拆散代码。移入后要同步修正导入、资源定位、启动配置和构建路径。

## 1. 项目应覆盖的范围

| 部分 | 本项目中负责的内容 | 主要保存位置 |
| --- | --- | --- |
| FPGA / PL | DPU 平台、自研运动寄存器与监督、PWM、时钟复位、地址与引脚约束 | `src/fpga/`、`build/`、`board/firmware/` |
| KV260 / PS | 相机、三模型运行和调度、跟踪、人脸身份、单轴跟随、USB 音频、ASR、角色、对话业务、记忆和存储 | `src/kv260/`、`board/` |
| Windows | 局域网模型推理、27B LLM、OmniVoice TTS、GPU 与进程管理、健康接口和性能计时 | `src/windows/` |
| 双端公共约定 | 请求/会话编号、数据格式、取消、期限、错误码、音频格式和播放确认 | `src/common/`、`docs/` |
| 模型与素材 | 模型版本、许可、哈希、取得方法，板端模型、角色、字体、音色参考和固定提示音 | `models/`、`assets/`、`third_party/` |
| 实物硬件 | 接线、电路、供电、隔离、机构、BOM、照片、脉宽与机械位置标定 | `hardware/`、`report/photos/` |
| 正确性与性能 | RTL 仿真、软件测试、板测、参考输出、前后对照、原始记录与统计脚本 | `sim/`、`tests/`、`data/`、`board/evidence/` |
| 赛事交付 | 设计报告、AI 协作记录、Skill、复现手册、许可、视频、照片和上传清单 | `report/`、`skill/`、`docs/`、项目外的 `auar_delivery/` |

板端保存业务与记忆，Windows 提供模型推理，是这份目录的默认职责划分。若你最终改变部署位置，应同时更新架构图、启动说明和协议，避免两端各保存一份互相冲突的权威状态。

声纹如保留，按实际 CPU / ARM 后端归档；不把它写成已运行于 DPU 的第四模型。听声辨位、双 I2S 麦、声源定位 IP、人脸与声纹强绑定不列为本次必备内容。VLM 看图问答、Light-ASD、唤醒词、PYNQ 实板工程也不因历史方案中出现过就自动加入必交功能；只有最终确实采用时才增加对应目录与证据。

## 2. 官方要求与目录之间的关系

依据指定 PDF 第 22–25 页，即页脚 19–22 页的 3.3；决赛海报见 PDF 第 28 页。

1. 初级组与高级组的设计任务、提交内容和评测指标一致；初级组不等于只提交 RTL。Win 端参与作品运行，就应提供相应源码、依赖、配置和运行方法。
2. 3.3.5.1 要求完整工程与实际使用的源码、仿真或验证结果、综合实现报告、上板工程/运行脚本/实测与参考对照、可复现构建脚本。
3. 3.3.5.2 要求 `skill/` 以及说明文件，写清适用范围、用法、失效条件、真实失败来源与验证效果。Skill 可以是工作流、模板、校验脚本或结构化经验，不要求必须有三个，也不要求必须安装为某款助手插件。
4. 3.3.5.3 的设计报告含七类内容：背景创新、原理框图、软硬件划分与接口、优化前后对比、AI 协作、Skill 提炼、从零复现。
5. 3.3.5.4 的八个顶层条目是推荐结构；可扩展，但要在 README 给出目录对照。目录和文件使用英文命名，正文可中文。
6. 3.3.3.3 原文为“强烈要求”在 GitHub 或 Gitee 开源，并采用允许再分发的协议；上传要求另列项目 GitHub 链接字段。最终应准备正式许可、固定提交版本和仓库信息。
7. Vivado / Vitis 2022.2 可按实际保留，但须说明版本选择并保证脚本可复现。PYNQ 是推荐路线，通用 PYNQ Skill 是另行加分项，不是强制改用 PYNQ。

这份结构保留官方八个目录 `src/`、`sim/`、`build/`、`board/`、`data/`、`skill/`、`report/` 及根 README，并补入你这类完整系统需要的配置、模型、素材、实物、测试和工具目录。

## 3. 完整建议目录

本树是设计清单，不是当前磁盘文件清单。`[条件]` 表示仅在最终采用或确有相应材料时建立。其余文件按实际实现整理，不用创建空文件充数。所有脚本名均为后续可采用的命名，并未在本次生成实现。

```text
auar_xuefei/
├── README.md                              # 唯一总入口：简介、硬件、环境、启动、复现、目录对照
├── license                                # 队伍原创内容的正式开源许可全文
├── third_party_notices.md                  # 第三方代码、IP、模型、素材的来源与许可边界
├── release.json                            # 源码、固件、模型、配置与报告的统一发布标识
├── checksums.sha256                        # 本次交付文件的 SHA-256 校验清单
├── .gitignore                              # 排除私库、缓存、权重下载、环境和临时构建
├── .gitattributes                          # 文本换行、二进制文件与跨平台处理约定
│
├── src/                                   # 实际参与作品的源码；按运行位置拆分
│   ├── fpga/
│   │   ├── readme.md                       # PL 模块、输入、工具、构建入口与接口说明
│   │   ├── rtl/
│   │   │   ├── visual_servo.sv              # 自研运动逻辑顶层；也可保留现有整块实现
│   │   │   ├── axi_lite_regs.sv             # [条件] 若独立拆分：寄存器与读写响应
│   │   │   ├── command_guard.sv             # [条件] 命令提交、范围、序号和会话监督
│   │   │   ├── lease_timer.sv               # [条件] 已接受命令的执行期限监督
│   │   │   ├── pwm_generator.sv             # [条件] PWM 周期、脉宽与输出使能
│   │   │   └── reset_sync.sv                # [条件] 自研复位同步逻辑
│   │   ├── bd/
│   │   │   ├── system.tcl                  # 重建 PS、DPU、互联及自研 IP 的 BD
│   │   │   └── address_map.json            # AXI 地址、寄存器窗口、中断及版本
│   │   ├── constraints/
│   │   │   ├── pins.xdc                    # 真实引脚、电平、驱动能力与边沿速率
│   │   │   ├── clocks.xdc                  # 时钟、生成时钟、外部时序要求
│   │   │   └── exceptions.xdc              # [条件] 有依据的时序例外及对应说明
│   │   ├── ip/
│   │   │   ├── custom/                     # [条件] 自研封装 IP 的 RTL、component.xml 与脚本
│   │   │   └── configuration/              # 工程确实依赖的 XCI 和 IP 参数
│   │   └── hls/                            # [条件] 实际使用 HLS 时放源码、测试与 directives
│   │
│   ├── common/
│   │   ├── pyproject.toml                  # 公共协议包的安装入口和依赖
│   │   └── aura_contracts/
│   │       ├── __init__.py
│   │       ├── version.py                  # 双端协议版本与兼容规则
│   │       ├── messages.py                 # 请求、响应、状态与错误的数据结构
│   │       ├── request_identity.py         # request_id、session_id、取消代次等
│   │       ├── deadlines.py                # 时钟域、单位、期限与过期判断约定
│   │       ├── audio_format.py             # PCM 参数、分包与序号约定
│   │       └── schemas/
│   │           ├── inference_request.schema.json
│   │           ├── inference_response.schema.json
│   │           ├── playback_ack.schema.json
│   │           ├── health.schema.json
│   │           └── visual_observation.schema.json
│   │
│   ├── kv260/
│   │   ├── readme.md                       # 板端程序入口、依赖及源码职责
│   │   ├── pyproject.toml                  # ARM Python 业务包安装信息
│   │   ├── requirements.txt                # 直接 Python 依赖
│   │   ├── requirements.lock.txt           # 板端实际验证过的固定版本
│   │   ├── aura_board/
│   │   │   ├── __init__.py
│   │   │   ├── main.py                     # 板端业务启动入口
│   │   │   ├── app/
│   │   │   │   ├── lifecycle.py            # 初始化、就绪、退出和恢复
│   │   │   │   ├── state_machine.py        # 聆听、思考、播放、暂停及故障
│   │   │   │   ├── event_bus.py            # 业务事件传递
│   │   │   │   └── service_registry.py     # 相机、音频、推理客户端等实例管理
│   │   │   ├── camera/
│   │   │   │   ├── capture.py              # 唯一相机采集所有者
│   │   │   │   ├── frame_buffer.py         # 缓冲、帧号和采集时间
│   │   │   │   ├── camera_service.py       # 向 UI、检测与跟随提供同一图像源
│   │   │   │   └── recovery.py             # 断连、重连与旧帧丢弃
│   │   │   ├── vision/
│   │   │   │   ├── dpu_runtime.py          # VART/XIR 加载、Tensor、Runner 和生命周期
│   │   │   │   ├── dpu_scheduler.py        # 单 DPU 多任务准入、预算与调度
│   │   │   │   ├── yolox_person.py         # 人体检测与实际模型预后处理
│   │   │   │   ├── yunet_face.py           # 人脸检测与关键点处理
│   │   │   │   ├── sface_embedding.py      # 对齐、人脸特征与有效性判断
│   │   │   │   ├── tracker.py              # ByteTrack 或最终实际跟踪实现
│   │   │   │   ├── observation.py          # 检测结果、轨迹、帧龄与来源
│   │   │   │   └── metrics.py              # 调用计数、等待、耗时、超限与源龄
│   │   │   ├── identity/
│   │   │   │   ├── face_gallery.py         # 人脸登记、查询、删除与 UNKNOWN
│   │   │   │   ├── enrollment.py           # 登记步骤和质量筛选
│   │   │   │   ├── matching.py             # 特征距离、阈值与拒识
│   │   │   │   └── speaker_identity.py     # [条件] 独立声纹身份业务，按实际后端说明
│   │   │   ├── motion/
│   │   │   │   ├── service.py              # 唯一正常运动命令写者
│   │   │   │   ├── follow_controller.py    # 人脸位置到目标脉宽的控制
│   │   │   │   ├── target_selection.py     # 同一目标锁定、丢失与重新选择
│   │   │   │   ├── input_freshness.py      # 源帧龄、来源身份和过期拒绝
│   │   │   │   ├── trajectory.py           # [条件] 实际使用的平滑/轨迹算法
│   │   │   │   ├── fpga_driver.py          # 寄存器读写、ABI、提交、STOP 和状态
│   │   │   │   └── shutdown.py             # 进程退出与控制租约收尾
│   │   │   ├── audio/
│   │   │   │   ├── alsa_device.py          # MCP01 稳定设备选择和格式检查
│   │   │   │   ├── capture.py              # USB 采集与队列
│   │   │   │   ├── frontend.py             # 实际采用的降噪与前端流程
│   │   │   │   ├── vad.py                  # 实际采用的 VAD 与语音段判定
│   │   │   │   ├── asr.py                  # Paraformer 或最终 ASR 的 CPU 调用
│   │   │   │   ├── speaker_embedding.py    # [条件] ECAPA 等 CPU 声纹特征
│   │   │   │   ├── playback.py             # 实际播放、缓冲与设备状态
│   │   │   │   └── playback_ack.py         # 完整播放、取消、迟到结果的确认
│   │   │   ├── dialogue/
│   │   │   │   ├── controller.py           # 板端语音轮次与半双工业务
│   │   │   │   ├── inference_client.py     # 调用 Windows 模型服务
│   │   │   │   ├── context_builder.py      # 经业务筛选的上下文与记忆
│   │   │   │   ├── reply_validation.py     # 输出格式与可消费内容校验
│   │   │   │   └── cancellation.py         # 会话撤销、超时与旧结果丢弃
│   │   │   ├── memory/
│   │   │   │   ├── store.py                # 板端记忆读写唯一入口
│   │   │   │   ├── summarizer.py           # 摘要任务、失败重试与提交
│   │   │   │   ├── retrieval.py            # 同会话与历史记忆查询
│   │   │   │   ├── retention.py            # 原文保留期和清理策略
│   │   │   │   ├── provenance.py           # 记忆来源、修正与派生关系
│   │   │   │   └── forgetting.py           # 撤销/删除后的后续使用约束
│   │   │   ├── storage/
│   │   │   │   ├── database.py             # SQLite 连接、事务及错误处理
│   │   │   │   ├── migrations/             # 版本化建表与升级脚本
│   │   │   │   └── bootstrap.py            # 空白设备的首次数据初始化
│   │   │   ├── ui/
│   │   │   │   ├── main_window.py          # GTK 等实际板端界面入口
│   │   │   │   ├── avatar_view.py          # 角色画面与渲染器连接
│   │   │   │   ├── vision_view.py          # 预览、人脸框与边界显示
│   │   │   │   ├── subtitles.py            # 用户/助手字幕与状态同步
│   │   │   │   ├── settings.py             # 实际提供的设置和控制
│   │   │   │   └── presentation.py         # 单一状态投影和刷新节奏
│   │   │   ├── avatar/
│   │   │   │   ├── native_bridge.py        # C/C++ 原生角色渲染调用
│   │   │   │   ├── expression.py           # 表情与动作选择
│   │   │   │   ├── mouth_sync.py           # 播放驱动口型与时间同步
│   │   │   │   └── character.py            # 人格、台词与资源绑定
│   │   │   └── diagnostics/
│   │   │       ├── health.py               # 业务状态及依赖健康
│   │   │       ├── metrics.py              # 板端计数、阶段耗时和资源
│   │   │       └── log_export.py           # 可公开运行证据的导出
│   │   └── native/
│   │       ├── makefile                    # 本地库的实际构建入口；可用现有构建系统
│   │       ├── dpu_bridge/                 # 自研 VART/OpenCV C/C++ 适配层
│   │       ├── motion_mmio/                # 自研 MMIO/批量提交 C/C++ 实现
│   │       ├── pixel_bridge/               # 自研像素、画面合成与纹理接口
│   │       └── avatar_renderer/            # 自研渲染适配；上游完整代码在 third_party/
│   │
│   └── windows/
│       ├── readme.md                       # Windows 环境、模型、端口和启动方法
│       ├── pyproject.toml                  # Windows 服务包安装信息
│       ├── requirements.txt                # 推理服务依赖
│       ├── requirements.lock.txt           # 与最终实际 GPU 环境匹配的版本锁
│       ├── aura_host/
│       │   ├── __init__.py
│       │   ├── main.py                     # 模型服务启动入口
│       │   ├── server/
│       │   │   ├── api.py                  # 请求、健康和取消接口
│       │   │   ├── request_router.py       # LLM / TTS 路由与队列
│       │   │   ├── ownership.py            # 实例锁、所有者和重复启动检查
│       │   │   ├── cancellation.py         # 请求取消与过期结果处理
│       │   │   └── health.py               # 模型、服务和 GPU 就绪状态
│       │   ├── llm/
│       │   │   ├── ollama_client.py        # 专用 Ollama 实例调用
│       │   │   ├── prompt_builder.py       # 板端上下文到模型输入的适配
│       │   │   ├── output_parser.py        # 实际约定的结构化输出处理
│       │   │   └── model_profile.py        # 模型标签、量化、上下文和参数
│       │   ├── tts/
│       │   │   ├── omnivoice_backend.py    # OmniVoice 推理接口
│       │   │   ├── reference_voice.py      # 选定参考音色的读取与校验
│       │   │   ├── pcm_output.py           # PCM 格式、分段与交付
│       │   │   └── cache.py                # [条件] 实际启用的 TTS 缓存
│       │   ├── runtime/
│       │   │   ├── gpu_policy.py           # 真实 GPU 识别、显存和并发策略
│       │   │   ├── model_manager.py        # 加载、预热与退出
│       │   │   ├── environment.py          # Python/CUDA/PyTorch/Ollama 核对
│       │   │   └── process_guard.py        # 子进程管理与退出收尾
│       │   └── diagnostics/
│       │       ├── metrics.py              # RPC、首个内容、TTS、RTF 等计时
│       │       ├── gpu_sampler.py          # 实际 GPU 资源采样
│       │       └── log_export.py           # 请求与模型指标的公开导出
│       ├── scripts/
│       │   ├── setup.ps1                   # 后续实现：检查环境并准备依赖
│       │   ├── start.ps1                   # 后续实现：启动本项目服务
│       │   ├── stop.ps1                    # 后续实现：停止本项目拥有的进程
│       │   ├── status.ps1                  # 后续实现：健康、所有者和模型状态
│       │   └── collect_environment.ps1     # 后续实现：生成实际主机环境快照
│       └── ollama/
│           └── modelfile                   # 模型导入与推理参数；权重路径可配置
│
├── config/                                # 可移机的配置模板；不保存个人状态
│   ├── readme.md                           # 各项参数、单位、默认值和覆盖顺序
│   ├── common/
│   │   ├── protocol.json                   # 协议版本、格式和超时约定
│   │   ├── logging.json                    # 日志级别、字段和保留策略
│   │   └── network.example.json            # IP、端口与绑定方式的示例
│   ├── kv260/
│   │   ├── camera.example.json             # 设备、格式、分辨率和帧率
│   │   ├── vision.example.json             # 模型路径、任务预算与后处理
│   │   ├── identity.example.json           # 阈值、登记规则与本地数据位置
│   │   ├── motion.example.json             # ABI、校准行程、方向、租约和控制参数
│   │   ├── audio.example.json              # MCP01、采样、前端和播放参数
│   │   ├── dialogue.example.json           # 模型端点、轮次与输出策略
│   │   ├── memory.example.json             # 保留期、摘要与查询参数
│   │   ├── display.example.json            # 屏幕模式、刷新和 UI 参数
│   │   └── character.example.json          # 角色、动作、音色及提示音绑定
│   └── windows/
│       ├── host.example.json               # 推理服务地址、队列与健康接口
│       ├── models.example.json             # LLM/TTS 标签、外部权重路径
│       ├── gpu.example.json                # 实测硬件填入方式；不固定旧 GPU UUID
│       └── ollama.example.json             # 独立服务端口、模型库与参数
│
├── models/                                # 模型工件或可核验的取得方法
│   ├── readme.md                           # 每个模型在哪运行、是否随包、如何取得
│   ├── manifests/
│   │   ├── models.csv                      # 名称、任务、后端、来源、版本、许可、SHA、大小
│   │   ├── yolox.json                      # 实际部署的人体检测模型
│   │   ├── yunet.json                      # 实际部署的人脸检测模型
│   │   ├── sface.json                      # 实际部署的人脸特征模型
│   │   ├── asr.json                        # 实际 Paraformer 等 ASR 模型
│   │   ├── audio_frontend.json             # GTCRN、VAD 等实际模型
│   │   ├── speaker.json                    # [条件] ECAPA 声纹模型，声明 CPU 后端
│   │   ├── llm.json                        # 27B 名称、仓库、revision、量化文件和 SHA
│   │   └── tts.json                        # OmniVoice、tokenizer 与音色依赖清单
│   ├── dpu/
│   │   ├── yolox_person.xmodel             # 在许可和体积允许时提供实际部署字节
│   │   ├── yunet.xmodel
│   │   ├── sface.xmodel
│   │   └── arch.json                       # 与实际 DPU 指纹一致的编译目标
│   ├── quantization/
│   │   ├── readme.md                       # 浮点来源、校准、量化、编译与精度口径
│   │   ├── yunet/
│   │   │   ├── calibration_manifest.csv    # 公开校准数据来源和划分
│   │   │   ├── quant_info.json
│   │   │   ├── compile_config.json
│   │   │   └── evaluation.json             # 精度结果；明确模拟或板端
│   │   └── sface/
│   │       ├── calibration_manifest.csv
│   │       ├── quant_info.json
│   │       ├── compile_config.json
│   │       └── evaluation.json
│   └── scripts/
│       ├── fetch_models.py                 # 后续实现：固定版本下载到明确目标位置
│       ├── verify_models.py                # 后续实现：逐文件 SHA 和完整性检查
│       ├── quantize.py                     # 后续实现：实际采用模型的量化入口
│       └── compile.py                      # 后续实现：实际 DPU 目标编译入口
│
├── assets/                                # 参与运行的非代码资源
│   ├── readme.md                           # 文件用途、资源寻址及授权说明
│   ├── manifest.csv                        # 资源来源、版本、SHA 与再分发条件
│   ├── character/
│   │   └── xuefei/                         # 角色模型、纹理、表情和动作；只放有权交付内容
│   ├── fonts/                             # 实际字体及许可
│   ├── ui/                                # 图标、背景及显示资源
│   └── audio/
│       ├── reference/                     # 有授权的 TTS 参考音色、文本与说明
│       └── cues/
│           ├── arrival.wav                # [条件] 最终实际使用的固定问候音
│           ├── invitation.wav             # [条件] 最终实际使用的邀请音
│           ├── thinking.wav               # [条件] 最终实际使用的思考提示音
│           └── manifest.json              # 文本、采样率、声道、时长、SHA 与生成来源
│
├── hardware/                              # 作品的电气与机械资料
│   ├── readme.md                           # 实物版本、供电与接线索引
│   ├── bom.csv                             # 型号、数量、用途与实际选用项
│   ├── wiring/
│   │   ├── system_connections.svg         # 整机相机、屏幕、MCP01、网络与供电
│   │   ├── servo_connections.svg          # KV260、隔离、独立动力电源及舵机
│   │   └── pin_map.csv                    # 接头位置、FPGA 引脚、网络、电平与方向
│   ├── schematics/
│   │   ├── readme.md                       # 实际电路原件格式与版本
│   │   ├── control_and_power.pdf          # 公开可阅读的真实电路图
│   │   └── source/                        # [条件] 实际自制板/电路的 CAD 原件
│   ├── mechanical/
│   │   ├── readme.md                       # 安装、零位定义、转轴和干涉说明
│   │   ├── assembly.pdf                    # 装配图或带尺寸示意图
│   │   ├── source/                        # [条件] 实际 CAD/STEP/STL 原件
│   │   └── dimensions.csv                 # 实测尺寸、单位及测量方法
│   └── calibration/
│       ├── pulse_angle.csv                 # 实测脉宽、角度、方向和测量条件
│       ├── travel_limits.json             # 实体允许范围、中点与标定版本
│       └── measurement_notes.md           # 仪器、误差、波形和未测范围
│
├── sim/                                   # FPGA 仿真与执行器软件参考
│   ├── readme.md                           # 仿真工具、执行顺序和判断依据
│   ├── rtl/
│   │   ├── tb_registers.sv                 # 实际采用的 AXI 与寄存器测试台
│   │   ├── tb_pwm.sv                       # 周期、脉宽与使能
│   │   ├── tb_command_guard.sv             # 提交、范围、序号、租约与停止
│   │   ├── vectors/                       # 固定与随机种子测试输入
│   │   ├── reference/                     # 独立期望输出
│   │   └── run.tcl                        # xvlog/xelab/xsim 等实际执行入口
│   ├── software_model/
│   │   ├── fake_motion_device.py          # 不接执行器的寄存器/时钟模型
│   │   ├── replay.py                      # 控制输入和时效场景回放
│   │   └── golden.py                      # 可说明来源的独立参考
│   └── results/
│       └── baseline/                      # 一次可追溯的已保存结果；后续大波形写项目外
│           ├── manifest.json
│           ├── result.json
│           ├── run.log
│           └── waveform.vcd
│
├── build/                                 # 工程构建定义与已选定的构建证据
│   ├── readme.md                           # 干净目录构建、导出和复查的方法
│   ├── scripts/
│   │   ├── check_environment.py            # 后续实现：工具、依赖和输入检查
│   │   ├── create_project.tcl              # 后续实现：按相对路径创建 Vivado 工程
│   │   ├── build_fpga.tcl                  # 后续实现：综合、实现、时序、位流与导出
│   │   ├── export_hardware.tcl             # 后续实现：XSA/HWH/位流配套导出
│   │   ├── build_native.sh                 # 后续实现：ARM 原生库构建
│   │   ├── package_firmware.py             # 后续实现：生成和核验固件组合
│   │   └── reproduce.py                    # 后续实现：按模式编排离线/硬件/部署复现
│   ├── manifests/
│   │   ├── toolchain.json                  # Vivado/Vitis/PetaLinux/Vitis AI 及补丁
│   │   ├── platform.json                   # 器件、板卡、DPU、频率、指纹和 ABI
│   │   ├── dependency_sources.json         # IP/参考工程/镜像/SDK 的固定来源与 SHA
│   │   └── build_inputs.sha256             # 这次构建的完整输入指纹
│   └── reports/
│       └── baseline/                      # 某一实际构建的结果；不同 build_id 分目录
│           ├── manifest.json
│           ├── synthesis.rpt
│           ├── utilization.rpt
│           ├── utilization_hierarchical.rpt
│           ├── timing_summary.rpt
│           ├── clocks.rpt
│           ├── check_timing.rpt
│           ├── route_status.rpt
│           ├── drc.rpt
│           ├── cdc.rpt                     # [条件] 工具支持且实际执行时保存
│           ├── build.log
│           └── metrics.json               # 从原报告提取的数值和口径
│
├── board/                                 # KV260 部署材料；与源码和配置分别保存
│   ├── readme.md                           # 新设备准备、部署顺序和运行说明
│   ├── firmware/
│   │   └── release_v1/
│   │       ├── overlay.bit.bin             # 示例名；最终按加载器需要的名称统一生成
│   │       ├── overlay.dtbo
│   │       ├── overlay.xclbin
│   │       ├── shell.json
│   │       ├── pairing.json               # 位流/XSA/设备树/XCLBIN/接口配对关系
│   │       └── checksums.sha256
│   ├── hardware_handoff/
│   │   ├── platform.xsa                    # 与本次固件对应的硬件交付
│   │   └── platform.hwh                    # [条件] 实际需要的硬件元数据
│   ├── binaries/
│   │   └── aarch64/                        # 现役原生库；必须能追溯到源码和构建条件
│   ├── system/
│   │   ├── image_manifest.json             # 原始镜像、内核、rootfs、XRT/VART 与 SHA
│   │   ├── boot_manifest.json              # 实际 QSPI/启动方式与所需启动组件
│   │   ├── packages.txt                    # 系统依赖及实际版本
│   │   ├── sdk_manifest.json               # ARM SDK/sysroot 的来源与匹配关系
│   │   └── petalinux/                      # [条件] 自定义系统时附配置、recipes 和 patches
│   ├── systemd/
│   │   ├── aura-camera.service             # 相机/视觉服务本体
│   │   ├── aura-business.service           # 角色、对话与业务服务本体
│   │   └── dropins/                       # [条件] 最终有效追加配置及加载顺序
│   ├── udev/
│   │   └── 99-aura-devices.rules            # [条件] 已采用的稳定设备规则
│   ├── config/
│   │   ├── deployment_manifest.json        # 相对源文件到目标路径、权限和 SHA 的映射
│   │   ├── startup_manifest.json           # 实际服务入口、源码/资源/配置锁
│   │   └── device_binding.example.json     # boot/PID/源身份字段示例，真实值重新生成
│   ├── scripts/
│   │   ├── stage_rootfs.py                 # 后续实现：在普通电脑生成离线暂存树
│   │   ├── deploy.sh                       # 后续实现：按目标清单安装到确认的设备
│   │   ├── preflight.py                    # 后续实现：固件、模型、音频、显示与绑定检查
│   │   ├── start.sh                        # 后续实现：按依赖顺序启动
│   │   ├── stop.sh                         # 后续实现：停止业务及对应执行者
│   │   ├── status.sh                       # 后续实现：原样读取实际健康状态
│   │   └── collect_evidence.py             # 后续实现：收集本轮版本与板测证据
│   └── evidence/
│       └── acceptance_001/                 # 每轮独立保存；禁止覆盖历史失败结果
│           ├── manifest.json               # release/boot/进程身份、时间及条件
│           ├── firmware_readback.json      # 实际加载项、DPU 指纹与自研 ABI
│           ├── startup.log
│           ├── health.jsonl
│           ├── observation.jsonl           # 实际观测记录与字段单位
│           └── verdict.md                  # 本轮通过、失败、未测及局限
│
├── data/                                  # 可公开的输入、参考与结果
│   ├── readme.md                           # 数据取得方式、许可、划分和评价方法
│   ├── manifest.csv                        # 数据文件、来源、用途、SHA 与发布条件
│   ├── input/
│   │   ├── vision_public/                  # 固定图像/向量；使用公开或有授权的数据
│   │   ├── audio_public/                   # 公开测试语音与人工转写
│   │   ├── dialogue_public.jsonl           # 不含个人历史的对话用例
│   │   ├── motion_replay.jsonl             # 固定视觉/控制回放输入
│   │   └── faults.json                     # 断网、过期、取消等可复现场景
│   ├── reference/
│   │   ├── vision_expected.json             # 检测/识别参考及容差
│   │   ├── audio_transcripts.txt            # ASR 人工参考
│   │   ├── motion_expected.json             # 软件参考和允许误差
│   │   └── dialogue_expectations.json       # 对话、记忆与撤销的判定规则
│   └── results/
│       └── baseline/                      # 每次实验再增加唯一 run_id 子目录
│           ├── manifest.json
│           ├── environment.json            # 实际板端/主机/模型/配置/版本
│           ├── raw/
│           │   ├── vision.jsonl
│           │   ├── voice.jsonl
│           │   ├── resources.csv
│           │   └── motion.jsonl
│           ├── comparison.csv              # 同条件基线与优化后结果
│           ├── summary.json                # 样本数、均值、分位数和失败计数
│           ├── figures/                    # 由原始数值生成的 PNG/SVG
│           └── verdict.md
│
├── tests/                                 # 软件与系统测试；不与 RTL 仿真混计
│   ├── readme.md                           # 各级测试的前提和设备需求
│   ├── protocol/                          # 请求、格式、过期、取消、播放 ACK
│   ├── kv260/                             # 视觉、跟随、音频、UI、身份和记忆逻辑
│   ├── windows/                           # 推理 API、实例管理、输出与错误处理
│   ├── integration/
│   │   ├── test_inference_roundtrip.py      # 固定输入的双端请求链
│   │   ├── test_cancel_and_late_reply.py    # 取消、迟到结果及恢复
│   │   ├── test_disconnect_recovery.py      # 网络断开和恢复
│   │   ├── test_memory_lifecycle.py         # 原文、摘要、查询、修正和删除
│   │   └── test_visual_motion_contract.py   # 视觉来源、期限和运动消费
│   ├── hardware/
│   │   ├── camera.md                       # 相机/框同步/图像质量实测步骤
│   │   ├── audio.md                        # MCP01、识别、实际听音与完整播放
│   │   ├── motion.md                       # 无动力波形、有限运动与停止的步骤
│   │   ├── cold_boot.md                    # 冷启动、显示/USB/服务与绑定重建
│   │   └── joint_run.md                    # 同版多功能运行、资源和失败记录
│   └── fixtures/                          # 测试专用公开小样；不使用真实私库作默认输入
│
├── skill/                                 # 官方要求的可复用经验包
│   ├── README.md                           # 每个 Skill 的范围、入口、效果和限制
│   ├── command_guard_validation/           # 建议主题 A：FPGA 执行监督与故障验证
│   │   ├── readme.md
│   │   ├── workflow.md
│   │   ├── prompts/                       # 经核验的提示词模板
│   │   ├── scripts/                       # 可直接复用的校验或报告工具
│   │   ├── examples/                      # 正例、反例及期望输出
│   │   ├── case_studies.md                 # 真实失败、判断、修正和复测
│   │   └── evidence/                      # 输入、原始日志、结果与环境
│   ├── dpu_workflow_validation/            # 建议主题 B：模型适配、调度和感知时效
│   │   ├── readme.md
│   │   ├── workflow.md
│   │   ├── prompts/
│   │   ├── scripts/
│   │   ├── examples/
│   │   ├── case_studies.md
│   │   └── evidence/
│   ├── voice_runtime_optimization/         # 建议主题 C：LLM/TTS、计时和记忆一致性
│   │   ├── readme.md
│   │   ├── workflow.md
│   │   ├── prompts/
│   │   ├── scripts/
│   │   ├── examples/
│   │   ├── case_studies.md
│   │   └── evidence/
│   └── pynq_contract_testgen/              # [条件] 通用 PYNQ 补充，实际采用才建立
│       ├── readme.md
│       ├── workflow.md
│       ├── contracts/
│       ├── templates/
│       ├── examples/
│       └── evidence/                      # 模拟、真板、跨板和他人复用分别标记
│
├── report/                                # 面向评审的设计和提交素材
│   ├── readme.md                           # 正式文件、草稿及指标来源的索引
│   ├── design_report.md                    # 可维护的正文源稿
│   ├── design_report.docx                  # 按赛事模板填写的可编辑版本
│   ├── design_report.pdf                   # 最终上传的统一 PDF
│   ├── amd_supplement.md                   # [条件] AMD 七项要求补充章节
│   ├── requirements_matrix.csv             # 官方条款 → 文件 → 证据 → 状态
│   ├── metrics.csv                         # 报告数值、单位、样本、条件与来源
│   ├── figures/
│   │   ├── system_architecture.svg         # 整体数据流和部署位置
│   │   ├── fpga_architecture.svg           # DPU、自研 IP、总线和时钟复位
│   │   ├── dialogue_flow.svg               # 采集、ASR、LLM、TTS、播放与 ACK
│   │   ├── memory_flow.svg                 # 存储、摘要、检索和遗忘
│   │   └── performance/                   # 能追溯到原始数据的图表
│   ├── photos/
│   │   ├── overall_front.jpg              # 真实整机照片
│   │   ├── overall_side.jpg               # 真实侧面/结构照片
│   │   ├── board_closeup.jpg              # 开发板高清特写
│   │   ├── wiring_closeup.jpg              # 实际接线和动力/控制连接
│   │   └── display_running.jpg             # 最终版本运行界面
│   ├── ai_collaboration/
│   │   ├── readme.md                       # AI 工具、模型版本、角色和记录边界
│   │   ├── raw/                           # 可公开的真实历史问答导出；不事后编造
│   │   ├── prompts.md                      # 关键原始提示词与对应原记录
│   │   ├── responses.md                    # 关键原回答与来源
│   │   ├── corrections.md                  # 错误、判断依据、修正和复测
│   │   ├── case_index.csv                  # 案例 → 源码/工件/验证/Skill
│   │   └── evidence_index.json             # 来源、SHA、范围和缺失项
│   ├── demo/
│   │   ├── storyboard.md                   # 演示顺序与每段要证明的功能
│   │   ├── demo.mp4                        # 作品介绍视频；上传时独立提供
│   │   └── recording_conditions.md         # 版本、环境、实物和剪辑说明
│   ├── poster/                            # [条件] 按企业通知/决赛要求准备
│   │   ├── poster_en.pptx                 # AMD 模板的一页英文海报
│   │   └── poster_en.pdf                  # 便于检查与 A4 彩色打印
│   └── submission/
│       ├── checklist.csv                   # 后台各字段、格式、大小和最终文件名
│       ├── repository.txt                  # 正式开源地址、tag、commit 与许可
│       ├── authorization_template.pdf      # 官方承诺/使用授权书原模板
│       └── readme.md                       # 签署件、回执的私下保存位置及最终提交说明
│
├── docs/                                  # 使另一位开发者看懂并能复现的说明
│   ├── architecture.md                     # 整体部署、数据流和唯一所有者
│   ├── feature_scope.md                    # 最终功能、删项、候选与未验证边界
│   ├── hardware.md                         # 器件型号、外设、供电与接口
│   ├── platform_lock.md                    # 工具、系统、DPU、ABI 和版本选择理由
│   ├── protocol.md                         # 双端 API、错误、取消与播放确认
│   ├── motion_contract.md                  # PS 源时效、PL 租约、范围与停止语义
│   ├── model_pipeline.md                   # 来源、量化、编译、预后处理和精度验证
│   ├── runtime_layout.md                   # 仓库文件到 KV260/Windows 运行目录的映射
│   ├── windows_setup.md                    # 从空白 Windows 准备依赖、模型和服务
│   ├── kv260_setup.md                      # 从匹配系统准备板端依赖与部署
│   ├── quickstart.md                       # 已准备环境下的日常启动与演示
│   ├── reproduction.md                     # 从取得源码到构建、部署、验证的完整步骤
│   ├── test_plan.md                        # 各级验证、输入、期望与实物前提
│   ├── measurement_methods.md              # 延迟、资源、频率、精度和统计口径
│   ├── known_issues.md                     # 真实失败、影响、复现与尚未关闭的问题
│   └── release_notes.md                    # 每次正式发布的变化与适用证据
│
├── tools/                                 # 构建/取数/归档辅助，不能替代真实结果
│   ├── validate_layout.py                  # 后续实现：文件名、清单及必要路径检查
│   ├── collect_versions.py                 # 后续实现：实际环境快照
│   ├── summarize_results.py                # 后续实现：从原始记录重算统计
│   ├── render_figures.py                   # 后续实现：从统计数据绘图
│   ├── make_checksums.py                   # 后续实现：生成交付 SHA 清单
│   └── export_submission.py                # 后续实现：按清单导出并检查提交体积
│
└── third_party/                           # 实际使用的第三方输入；固定版本和原许可
    ├── readme.md                           # 上游地址、revision、补丁与可再分发范围
    ├── manifest.csv                        # 所有第三方依赖统一登记
    ├── fpga_ip/                           # [条件] 工程依赖且允许提供的非内置 IP
    ├── bytetrack/                         # [条件] 实际使用的跟踪源码
    ├── trajectory/                        # [条件] 实际采用的轨迹库
    ├── avatar_runtime/                    # [条件] 渲染器依赖与原许可证
    ├── omnivoice/                         # [条件] 固定 TTS 源码或可核验取得方法
    └── licenses/                          # 代码、模型、字体、素材等原许可
```

## 4. 六个最容易遗漏的归档边界

### 4.1 FPGA 工程必须能重建

保留实际自研 RTL、BD 构建脚本、约束、IP 配置、依赖来源和工具版本。若构建依赖特定 DCP、旧 IP、参考工程或本机绝对路径，要把输入及获取/校验方法写清，不能只留下一个引用旧电脑路径的 XPR。

`build/` 保存脚本和选定报告；新的综合、布局布线、IP cache、临时 XPR 和大波形输出到仓库外。实际导出的位流、设备树、XCLBIN、XSA 要配套，不能分别从不同构建中挑选。

这份结构中的 `command_guard.sv` 等只是职责建议。若你现有 `visual_servo.sv` 已包含这些逻辑，保留完整文件和测试即可，不用为了目录结构先重构。没有使用 HLS，就不用制作 HLS 源码；没有裸机程序，也不用为了比赛新增一个 ELF。

### 4.2 板端完整内容不等于整张 SD 卡

至少覆盖业务源码、独立相机服务及其实际入口链、原生库源码与构建、资源、模型、服务本体及有效 drop-in、设备规则、系统依赖、固件和部署映射。相机服务与界面业务若采用不同发布树，要各自收齐，不只复制 GUI 所在的文件夹。

若基于官方系统，记录镜像来源、SHA、内核、XRT/VART、ARM Python 与系统包。如果修改过 PetaLinux 配置、设备树、驱动或 recipes，则相应源码/补丁属于工程输入，应提交。个人数据库、临时日志和下载缓存不需要混进公开代码树。

`board/config/deployment_manifest.json` 应逐项包含：仓库相对路径、目标绝对路径、文件类型、权限、SHA、消费者、加载顺序与用途。`startup_manifest.json` 固定软件和资源；当次 boot_id、PID、start ticks 等运行绑定在目标设备重新生成，不把旧启动证明当成新设备有效凭据。

### 4.3 Windows 完整内容包含模型服务周围的工程

不仅是调用大模型的 Python 文件，还包括启动/停止/健康检查、专用 Ollama 配置、模型取得与校验、依赖锁、GPU 实际环境、参考音色、输出格式、取消/超时、实例管理和性能计时。

GPU 型号、显存、UUID、CUDA/PyTorch 组合以你最终实际使用的电脑采集结果填写。不能把旧桌面卡或 Laptop 的参数直接当作新机配置。Windows 的临时请求状态可以本机保存，个人记忆与业务主库的权威位置仍在架构文档明确指定。

### 4.4 模型权重、参考音色与个人数据分别处理

| 内容 | 主工程怎么保存 | 实际运行怎么处理 |
| --- | --- | --- |
| 三份 DPU xmodel | 在许可和体积允许时提供实际部署文件、SHA、编译目标与来源 | 加载前核对 DPU 指纹和模型接口 |
| ASR / VAD / 降噪 / 声纹模型 | 提供来源、版本、许可、文件清单、SHA、准备方法；是否随包视体积与规定 | 按最终板端环境准备，不混用 x86 wheel 与 ARM wheel |
| 27B 大语言模型 | 只保存固定来源、revision、量化文件名、SHA 和准备方法 | 继续放共享目录外，如 `D:/AIModels/`；不在共享目录建立权重副本或目录联接 |
| OmniVoice 模型和 tokenizer | 固定全部必要文件及来源；不能只登记一个主权重 | 在模型专用目录准备，按最终配置定位 |
| 参考音色 / 固定提示音 | 有权交付的资源与文本、采样格式、SHA 和生成来源 | 随配置绑定；不以私人人声录音替代公开样例 |
| 角色、纹理、动作、字体 | 资源清单、来源和许可；自研与第三方分清 | 用相同资源版本复现画面，不把渲染截图当实物照片 |
| 人脸库、声纹模板、个人对话与业务 SQLite | 保存代码、表结构/迁移和公开合成用例 | 由所属设备保存；新设备初始化自己的数据 |

取得脚本与来源说明帮助复现，但不能据此自行认定外链能替代赛事要求的完整源码或必需输入。若体积不足，先按后台允许的交付方式调整，保留完整的取舍清单。

### 4.5 源码、参数、生成物与证据各有一个用途

| 类型 | 位置 | 例子 |
| --- | --- | --- |
| 开发者修改的实现 | `src/` | RTL、Python、C/C++ |
| 可移机配置模板 | `config/` | 相机参数、服务端点、模型外部路径 |
| 构建与部署定义 | `build/scripts/`、`board/scripts/` | 创建工程、编译、固件导出、根文件系统暂存 |
| 固定发布工件 | `board/firmware/`、`board/binaries/`、`models/dpu/` | 与版本清单配套的文件 |
| 结果原件 | `build/reports/`、`sim/results/`、`board/evidence/`、`data/results/` | 工具报告、波形、实测、原始计数 |
| 面向评委的解释 | `report/`、`docs/` | 技术报告、复现、指标定义与限制 |

同一数据只保留一份权威原件，报告引用其路径、run_id 和 SHA。确需复制时登记来源，不靠改文件名区分“最新版”。

### 4.6 测试证据不能跨层替代

RTL 仿真、主机软件模拟、模型量化模拟、板端固定输入、真实图像/声音/运动、完整整机运行和陌生环境复现分别记录。模拟脉宽不等于板外示波器测量，控制范围不等于实际机械角度，首个 JSON 内容不等于扬声器首声。

PS 对视觉源帧龄的判断与 PL 接受命令后的执行租约分开解释；除非实际 RTL 已实现并测试，否则不宣称 PL 能核验绝对视觉源期限。三模型完成频率不等于硬件 DPU 利用率；UI 暂停时的资源记录不等于语音与跟随全开的整机满载。

## 5. 建议的机器运行目录

以下是**重做后的推荐部署布局**，不要求现在迁移任何现役路径。仓库与运行目录分开，避免服务运行后改写待提交的校验包。源码包不应固定依赖 `/home/ghmd/` 或某块电脑的盘符。

### KV260

```text
/opt/auar/
├── releases/
│   └── release_v1/                       # 由工程部署生成的代码、依赖和发布资源
└── current/                              # 部署工具维护的当前版本入口

/etc/auar/                                # 本设备配置；由 example 模板生成
/var/lib/auar/                            # 本设备业务状态、数据库、身份与记忆
/var/log/auar/                            # 运行日志与本机诊断
/run/auar/                                # 当次启动的锁、PID、socket 与运行绑定
/lib/firmware/xilinx/                     # 按实际 xmutil/加载器规定安装配套固件
```

根文件系统权限不足或现有系统布局不同，可选择普通用户目录部署，但必须在 `docs/runtime_layout.md` 写明。服务名、固件名和加载器元数据要整体一致，不能单独重命名位流而保留旧引用。

### Windows

```text
E:/Win共享文件/共享文件夹/auar_xuefei/     # 你后续可采用的工程源码主目录
D:/AURARuntimes/                          # 独立 Python / CUDA 等运行环境
D:/AIModels/                              # 项目外模型存储；27B 不放共享目录
D:/AURAData/
├── config/                               # 本机实际配置与解释器路径
├── logs/                                 # Windows 运行与资源日志
├── requests/                             # 临时推理状态；按保留策略管理
└── cache/                                # 可重新生成的缓存
```

这里的盘符是布局建议，实际位置通过配置填写。同步源码/文档和在本机运行服务是不同工作；Windows 与 Ubuntu 各写自己的执行回执，不代填对方“已收到”。

## 6. 完整工程、源码仓库和上传材料怎么对应

`auar_xuefei/` 是完整工程主档。Git 中排除机器生成的临时目录、私库、权重下载和大日志；赛事交付根据清单导出指定发布工件与证据。演示原片、完整 SD 备份和全量工具输出可以本机另存，不自动全部塞入 200M 代码包。

上传导出目录放工程之外，避免把压缩包再次压进自己：

```text
auar_delivery/
├── code/
│   ├── auar_xuefei_source.rar             # 全部代码与必要工程输入，按上传要求 200M 内
│   └── code_contents.csv                 # 包内目录、必需外部输入与对应方式
├── report/
│   └── auar_xuefei_design_report.pdf      # 最终设计报告，50M 内
├── video/
│   └── auar_xuefei_demo.mp4               # MP4 / AVC(H.264)，建议 3 分钟内、300M 内
├── photos/
│   ├── overall.jpg                        # 真实作品全局
│   └── board_closeup.jpg                  # 开发板高清特写
├── authorization/
│   └── authorization_signed.pdf          # 按官方表单签署；不默认进入公开源码仓库
├── repository/
│   └── repository.txt                    # URL、tag、commit、许可与对应源码 SHA
├── poster/                               # 按企业/决赛通知要求提供
│   └── poster_en.pptx
├── upload_manifest.csv                   # 后台字段、文件、字节数、SHA 与提交状态
└── receipts/                             # 实际提交后的回执；只在真实发生后填写
```

你本机另有《2026FPGA创新设计赛道作品上传要求.pdf》：明确代码包为 **RAR / 200M 内**、报告 **PDF / 50M 内**，视频 **MP4 / AVC(H.264)，建议 3 分钟内、300M 内**，并列出授权书、项目链接、作品照片及企业要求的海报。其原文截止为 **2026 年 11 月 4 日 18 时**，未注明时区；最终字段与有效提交以队伍后台及后续通知核对。

体积检查可保守按十进制上限 `200000000 / 50000000 / 300000000` 字节留余量。视频、签署文件和高清照片按独立栏目提交，通常不需要重复装入代码 RAR。若后台只有一个报告栏，把赛事模板正文和 AMD 必要补充组织为一份最终 PDF，不假设存在第二报告栏。

AMD 决赛海报条件：进入决赛的自主选题队伍按 AMD PPT 模板制作一页英文海报；不包含队伍信息，A4 彩色打印带现场。不能据此推断初赛后台必收同一份海报，按实际企业通知执行。视频按上传要求避免学校、指导教师等与作品无关的信息。

## 7. 每次发布和每项实测至少登记什么

`release.json` 建议登记：作品名、release_id、生成时间、源码 commit、各源码清单 SHA、固件组合与 ABI、DPU 指纹、模型版本及 SHA、配置和素材版本、实际系统/主机环境、对应报告与证据索引、已知问题。未知填 `null` 或 `UNKNOWN`，不要预填“通过”。

实验 `manifest.json` 建议登记：run_id、release_id、实验类型、输入 SHA、工具/硬件/系统、实际模型和配置、开始结束时间、单调时钟范围、是否冷态/暖态、缓存情况、有效样本数、失败/丢弃数、原始文件及 SHA、统计脚本版本、判定规则、实际结论和未验证范围。

关键实验建议分别保存：三模型固定输入与质量对照、调度前后同条件对照、跟随与失源/停止、MCP01/ASR/播放、LLM/TTS 冷暖与缓存分层、记忆保留/摘要/检索/遗忘、显示与冷启动、断网恢复、整机联合运行和干净环境复现。列表用于检查工程完整性，具体试验长度由项目目标与测量方法确定，不是指南统一规定的秒数。

## 8. 重新整理时的落地顺序

1. 先建立总 README、`docs/feature_scope.md`、`docs/architecture.md`、`release.json` 和模型/第三方清单，确定最终功能与双端职责。
2. 将实际使用的 FPGA、板端、Windows 和公共协议源码分别收齐；为独立相机入口、原生库、角色资源与提示音单独核对消费者。
3. 把可移机模板与本机私有配置分开，逐项建立部署映射；整理固件配对、模型依赖、系统/SDK 和工具链输入。
4. 补齐实际可执行的构建、离线校验、Windows 启停和板端部署入口。脚本中消除原电脑专用的绝对路径，必须固定的路径则由配置显式传入。
5. 选择一个 release，按测试计划保存同版仿真、板测、原始指标与参考对比。历史成功和失败独立保留，不改写为新版本通过。
6. 按官方七项写报告，整理真实 AI 记录，从实际失败提炼至少一个可复用 Skill。三主题拆分和 PYNQ 补充按实际投入选择。
7. 在新目录验证离线复查，在匹配环境验证构建/部署/运行，分别注明通过层级。补实物照片、视频、许可与授权文件，再导出上传目录。

目录本身不会使缺少的代码、原始问答、照片或实板验收变为已完成。本次仅交付结构设计，你可按此逐项重新制作；目录说明、文件用途和官方映射已经给出。

## 9. 本次依据和交付范围

- 指定指南：[AMD 赛题指南](../../参赛资料/全国大学生嵌入式芯片与系统设计竞赛'2026FPGA赛道选题指南-AMD.pdf)，重点 3.3.1–3.3.5、第六部分。
- 本机上传要求：`/home/ghmd/下载/2026FPGA创新设计赛道作品上传要求.pdf`，用于补全材料类型、格式和大小；没有登录队伍后台。
- 项目范围：完整资料包中的 README、无声源定位方案和 A/B/C 分工；结合项目日志和共享文档中的实际双端职责及后续删项，不用历史方案替代实测。
- 目录按你最后要求独立设计，不以现有 RAR 的布局、文件清单或验收状态决定本方案。
- 配套附件：[纯文本目录树](project_tree.txt)、[逐路径用途清单](directory_catalog.csv)、[官方要求映射](requirements_matrix.csv)、[校验记录](validation.json)、[依据索引](source_index.json)。

本次没有创建上述业务源码、空白占位工程、构建/部署脚本或正式比赛压缩包；没有连接 KV260、运行模型或操作 Windows 服务。新增内容都是供你后续整理使用的文档和索引。
