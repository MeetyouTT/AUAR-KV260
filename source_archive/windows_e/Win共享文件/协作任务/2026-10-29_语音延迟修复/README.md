# 语音延迟单项修复：运行开关已生效，公平对照待补

用户已要求继续降低延迟，Windows下一项按[进一步降延迟执行单](进一步降延迟_Windows执行.md)推进：先冻结当前新版本，配对测提示缓存/已有紧凑通道兼容、原OmniVoice重复开销与GPU竞争，再分解板端准备；保持模型、音色和回答语义。第二轮暂无候选部署或新提速结果，不重复把已有首句策略或预热写成新增。

## UTC2026-10-29 12:47最新实读

两次新的独占UART只读探测确认，Windows8792已运行 `voice-chat-memory-20261029-r9`，source fingerprint `5a4fa28e8679ffd24b61e940455e7dd2341c02c8ae70e8997aa5682c157471f3`，ready=true、busy=false，compact_grammar=false，其余五项保持。原27B/Paraformer/OmniVoice16保持，启动预热完成。boot55152f95/GUI114923/camera21824保持；监听和跟随关闭。本次没有执行Windows重启、发模型请求、开麦、播放或运动，读取的是现场已有运行结果。

板端现有最近两轮完整业务记录：

| 指标 | generation20 | generation38 |
| --- | ---: | ---: |
| 提交请求到软件起答 | 3.865955秒 | 3.588321秒 |
| 服务端首PCM | 3469ms | 3234ms |
| 请求准备 | 0.00ms | 0.00ms |
| ASR | 78ms | 78ms |
| 首句就绪，累计 | 1891ms | 2016ms |
| 首次TTS生成 | 1559.89ms | 1185.38ms |
| 模型加载 | 2.21ms | 1.55ms |
| TTS缓存命中 | 否 | 否 |

两轮实际backend均Ollama，无质量重试，音频完成。请求准备记录已由旧路径的约0.8–1.19秒变为0.00ms，支持该路径开销已被移除；0.00为测量舍入值。两轮历史上下文分别0/2条，不能据此计算同输入A/B提速率。提交到软件起答不含说完到端点判定的全部等待，也不是外部声学测量；首句时刻是累计值，不能与其包含的阶段重复相加。

当前余下等待主要落在首句形成及TTS，客户端与服务端首PCM差约0.35–0.40秒混有请求传输、协议与播放准备，不能全归为网线耗时。尚未收到Windows独立执行回执或新鲜同输入前后A/B，不能宣称长期稳定3秒或严格提速百分比。下方“运行true/重载待执行”属于07:52–07:56的历史记录，当前开关以本段更新。

最新过滤实证见 `evidence/runtime-20261029T124717Z.json`；原始UART留Ubuntu私有目录。

任务版本：`AURA-VOICE-LATENCY-20261029-r1`。用户已明确同意执行。范围是现有功能的延迟修复，不增加模型或新功能。

## Ubuntu实际完成

- 通过现有独占UART读取板端和Windows健康，无录音、播放、推理、运动或服务切换。主机UTC2026-10-29 07:52:10，boot `55152f95-ea3a-4c6c-82e6-51bd553d96fd`，GUI114923、相机21824。板端IDLE、音频IDLE_READY、监听/跟随关闭、无录音或在途转写。
- Windows8792实时版本已更新为 `voice-timeline-20261028-r2`，source fingerprint为 `bc9b8aaddea9b9d3e4a588d57c4b52b49bd8a61f59fac06c6f856477baf0baae`，ready=true、busy=false、启动预热完成，运行时compact_grammar仍true。这比Ubuntu现有共享源码新，禁止用旧源码覆盖或套用历史完整回退。
- 已使用上一轮准备的脚本修改 `语音共享文件/aura/config/voice_latency.json`，仅把compact_grammar改为false，其他五项语义不变。修改前SHA256：`bc1202bf9f5c15c2416d94f8948225f08eb129699a31e9aaad8276f9f8c4085b`；修改后：`72f3cf4344abdab9b100b94679624c980ce1240e641bf36b6b47468cf6c94111`。
- 原字节备份：`语音共享文件/aura/config/voice_latency.before-native-disable-20261029T075340952071Z.json`。再次只读预览为false、不再写入；尚无Windows同步收件或加载成功证据。

## Windows接续执行

1. 先读本任务和[Ubuntu回执](Ubuntu_执行回执.md)，核对当前8792实际监听进程、命令行和配置路径，保留当前voice-timeline-r2及其未同步新源码。不要依据旧共享文件重建或恢复整个语音项目。将接手声明写入本任务的`Windows_执行回执.md`，Ubuntu不代填。
2. 核对上述配置SHA和六个开关。若Windows实际配置不同，先比较实际六项，使用[已有单项脚本](../2026-10-28_整机联动与舵机范围/disable_failed_native_route.py)指定真实配置路径，仅改compact_grammar并备份；不要覆盖其他新设置。不要删除原生runner的版本/模板/上下文验证。
3. 自然空闲时再次确认8792 ready且非busy、板端无播放/录音/在途转写，监听保持原有选择。用Windows当前的进程归属/Job流程仅重载8792及其持有的TTS工作进程，沿用当前实际启动入口和原环境。不要盲用历史activate_pc.ps1，也不要批量终止Python、Ollama或其他服务。8791/8795/8796、11435、板端GUI/相机、固件、模型、音色和记忆不变。
4. 验证8792恢复ready，运行时`latency_options.compact_grammar=false`，其他五项不变，当前源码指纹、27B标签、Paraformer、OmniVoice16及音色配置保持。服务自带的warmup已有代码，不重复增加同样逻辑；检查实际预热耗时和Ollama驻留，不能只凭startup_warmup_complete认定始终驻留。
5. 以公开固定WAV和独立合成测试会话做修复前/后对照，不读写真实个人档案，不打开麦克风或主动播放。记录原始样本哈希、输入/上下文/模型版本、缓存命中、实际backend、原生fallback原因、request_preparation_ms、首句和首PCM。若新版本无法重现旧失败，按本次实际情况报告，不沿用旧18轮结论替代新基线。
6. Windows本机与板端网线客户端使用同一输入核对，分别记录上传/首PCM接收/播放准备；不要用跨机单调时钟直接相减。无实际播放则不填声学起答验收。启动预热与暖态重复分开，不为了制造冷态卸载其他正在使用的模型。
7. 把实际命令、当前进程/源码/配置指纹、重载前后health与数值结果写入自己的回执和本任务evidence/windows目录。共享证据不包含私人正文、音频、数据库、模板、令牌或模型权重。窗口内没有完整A/B就保留未验证，不预填节省1秒。

## 已知限制和回退

Ubuntu本机在172.23无线网段，提升权限后直接连接192.168.50.1:8792超时；可以通过板卡读health，但没有已配置Windows远程命令入口。当前服务没有在已同步版本里提供配置重载管理API，不能由读health推断能够重启Windows。

回退只针对本次开关：核对当前六项和备份，把compact_grammar恢复为true，保留期间其他有效改动，再由Windows在空闲状态按同样归属流程重载8792。原字节备份用于核查，不用于覆盖之后出现的其他设置。

本机现有回归执行13项，其中9项通过，4项因系统Python3.8不支持ThreadPoolExecutor.shutdown(cancel_futures=...)而受阻，原失败日志保留。当前Windows语音环境是另一版本，必须使用真实运行环境补验；没有为消除环境报错修改生产语音代码。

当前状态：`RUNTIME_FLAG_FALSE_VERIFIED / PAIRED_AB_PENDING`。已有两轮暖态起答结果，Windows执行回执、同输入前后对照、冷态和持续真人体验尚待补齐。
