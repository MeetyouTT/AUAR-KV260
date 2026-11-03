# 正在进行：声音断续与现有素材丰富度

## 最新进展（本段替代下方“尚未测试”）

- 音频58过、1个Windows平台skip，报告audio_tests_verified.xml/.log。首次audio_tests.log与audio_tests_effective.log保留失败：旧Windows测试不含现机appsrc.get_property、临时父目录没创建及旧factory传idle_body参数不符；修正为现机已绑定夹具，且仅为FakeSource补get_property=0，AST核对所有原断言不变，fixture_adaptation.json有记录，正式appsrc队列fail-closed保护未删除。测试不要自动收集本目录全部test*.py，使用run_audio_tests.py指定范围。
- 原生ARM/GStreamer fakesink+自建4096字节管道受控背压对照 PASS，native_ipc_comparison.json：原同步上报最大调度阻塞220.72ms、供音间隔199.98ms、9次>80ms、PTS缺口180ms；候选最大调度11.29ms、供音24.57ms、0次>80ms、PTS缺口0。两版144000字节公开正弦PCM哈希完全相同。无ALSA/麦克风/显示/运动设备，不能说实体听音通过。48条回声参考在故意240ms背压下按50ms期限丢弃，保留序号间隙，插话监视器遇gap关闭而保留当前播报；不能删这个故障安全逻辑。首轮因ARM fcntl缺F_SETPIPE_SZ导出失败，native_ipc_comparison_setup_failure.json保留，后用Linux ABI1031且断言返回4096。
- 动画候选已暂存在candidate/shared/tools（idle_body_compositor/realtime_facials），candidate/board/tools（facial_layers、controller等），candidate/windows/tools/portrait_renderer.py，candidate/renderer_snapshot（旧快照复制后只改blink关联body_asset）。均未部署、未改A正式代码。prepare_visual_inputs.py、patch_eye_tracks.py已跑不要重跑覆盖。
- 离屏真实素材预览PASS：visual_preview.png/.json（4行neutral-a/neutral-b/happy/sad，3列closed/speech/blink）。已经view_image确认形象、嘴型、眨眼正常：happy出现实际举手素材；body_assets为idle_normal/idle_present/talking_normal/talking_low。两种平静姿态体态尺度不同是原素材，是否需要短过渡还待视觉验证。没有新生成素材。
- 实现：IdleBodyTrack新增expressive=False兼容旧调用；RealtimeFacials默认expressive_body=False兼容旧demo，但candidate RealtimeController和PortraitRenderer显式True。BodyTrack.FAMILIES保留嘴源anchor，BODY_STATES为4套已注册39pose原身体；用当前显示body的face_matrix+源嘴anchor→目标anchor变换；在原speaking身体上始终画PCM闭口/开口（gain0也用闭口覆盖），不能让原动画嘴在静音时乱动。BlinkLayer原有效快照早已支持pose，但硬编码idle_normal，候选两端只改为meta.body_asset以跟随正确身体。
- material_variant(g,n)=(g^(g>>1))%n：在常见+2代次间交替且同一轮稳定，本地/远端一致；seed_speaking_materials在StreamingController.start和PortraitRenderer新owner时选择已有同语义嘴池，保持长句6秒换池策略。Body中性同代次选idle_normal/idle_present，高低情绪用talking_normal/low。CPU warmup预解码4套身体，板端懒加载；尚需正式视觉回归/性能/内存检查。
- visual_bootstrap.py用于离屏QA：加载candidate renderer_snapshot的FSM/AvatarPlayer/FacialLayers/demo_script，将__file__设真实A路径以复用原资源，然后加载candidate shared模块。不要用P/aura/tools/demo_script直接创建core：它传idle_body而旧preview_script不支持；现役CPU和板端都用旧有效factory（不传参数），QA已按有效快照加载。
- 下步：补视觉测试（静音闭口、眨眼/嘴位跟踪、同轮稳定/短轮变体、四身体差异、burst不覆盖），构建严格新renderer manifest（新增使用的原body PNG及shared新代码SHA，不能绕过hash）。需要配套更新板端期望revision、启动器与Windows CPU8796，保留旧81fd快照。audio58测试在共享视觉候选加载后应再复核。Windows语音r9 8792/其他模型无需重启，别修改LLM/音色/16步。
- 部署建议：一次合并板端音频+动画薄客户端修复。用户已要求解决，按既有授权推进；先经原UI暂停监听并双确认空闲/跟随false/无活动运动。以实际root及pending startup-speed完整配置为基线，复制新受控runtime，继承pending优化launcher+参数，仅更新变更组件hash和portrait revision，不回退它。机械JSON/发布引用/旧boot值保持原字节，绝不“修正”为当前boot。不要向旧运行目录写代码；不重启相机、不增加第二真实音频sink/显示sink。CPU8796新资源配置要让root start_portrait.ps1后续重启仍可用，避免改旧快照历史证据；可新增canonical portrait_host.local.json+本目录hidden启动器并更新根wrapper。尚未写这些部署脚本。

## 初始调查与约束

用户先报自打断，随后明确现在不会自己打断；当前任务为“声音断断续续，句子中间停顿”及“动作素材丰富性没体现”。不要继续无根据调整插话判定阈值；两项新问题都要处理。没有代理授权，不派子代理，无新自动任务。

现役Windows仍r9，未改源码/重载。板端实际运行入口仍605eaf50 boot、UI1296/相机1333、/home/root/aura-boundary-nav-20261029/gui-page-sync-v2/startup/config.json，279组件。systemd下次启动已由并行任务改为/home/root/aura-avatar-startup-speed-20261029/config.json，不能回退。每次操作仍需重新从/proc/MainPID/cmdline发现实际运行入口。机械FAULT/benchmark平台不匹配，禁止MMIO、改绑定、启用运动。

初次脱敏调查 ../2026-10-29_self_interrupt/board_snapshot.json：插话14次，AEC健康/0 gaps，ASR确认new_speech，Windows无503。用户随后表示自打断不再发生。本目录baseline.json捕获当前对话/动作及源代码，源码逐字节核对pin；最初read_text改变CRLF导致助手采集失败，已改read_bytes.decode保留字节，不是板端源码不匹配。

证据：14个完成的流式回答，仅2次动作，13次单段TTS、1次双段。音频不能全归于TTS分段。音频worker.stderr为空，无ALSA告警；可能是显式填静音/进程IPC阻塞，不能声称已证明实体欠载。gstreamer_audio_worker.py在GLib音频调度线程同步print/flush状态100Hz与回声PCM，慢接收端可阻塞供音；已在candidate/board暂存非阻塞、有界、保序IPC，需先回归及真实ARM无设备的fakesink/管道背压对照，再部署。本目录prepare_audio.py已跑，勿重跑覆盖候选。尚未改任何正式源/设备状态。

音频候选5文件：worker含NonBlockingAudioPublisher（latest state+8 reference，非阻塞os.write，保留部分包，不篡改PCM，过时ref>50ms丢弃保留序号间隙）；persistent_engine仅增加queued_ms/turn_underrun/max_poll_gap/late_rebases计数，不改原60ms排程/AEC时基；realtime_controller/streaming_controller暴露无文本音频指标；barge_in_capture在永久reference gap时关闭monitor，保留正在播放回答并允许下一轮正常收听，禁止无参考原始声音触发插话。新音频测试见test_audio_flow.py/run_audio_tests.py，准备就绪但截至本接续尚未跑。

动作重要发现：RealtimeFacials.apply把所有MouthBank说话素材的完整身体替换为IdleBodyTrack的IDLE；因此happy/sad身体素材被掩盖。短句另有素材池在PortraitRenderer每代reset后清零，6秒轮换从未到达。下一步计划：在现有素材/跟踪几何基础上让high/low用对应body，neutral可用语义相近idle_normal/idle_present，并严格把闭口、眨眼层映射到当前body的面部轨迹；短轮素材按代次稳定选择以保证板端本地fallback和Windows一致，不新生成位图，不加无关机械动作。必须先做真实素材离屏像素/对齐验证和截图预览，保持嘴部由PCM驱动。

相关：aura/tools/realtime_facials.py、idle_body_compositor.py、facial_layers.py；deliv 2026-10-06_voice_blink/blink_profile.json只含idle_normal/present/listening/thinking、talking_normal/low（每套39poses），没有talking_neutral。ReusePreviewPlayer在2026-10-06_avatar_reuse/preview_script.py（P的版本较旧，实际渲染snapshot/demo_script已支持idle_body参数；以有效快照为准）。当前Windows8796资源81fd...的renderer_snapshot包含AvatarPlayer、fsm、facial_layers、demo_script；manifest.project_sources含realtime_facials、idle_body等，任何新body素材帧也须补进manifest并更新资源revision，配套板端期望值，不能绕过哈希。检查这些文件先前已有逐段读取，避免重复巨量输出。

部署应使用当前实际运行根为基线，并继承并行startup-speed的新启动器/配置（当前running和pending不同，不能把unit误当running）。保留全部非本任务组件、机械、相机与身份库。源修复需要重启UI时，先经原UI停监听并确认IDLE_READY/无活动运动；最后不自动开麦/播放/运动。当前用户曾手动启用后又暂停，runtime_logs.json时command_results显示enabled=false。每次仍动态复核，不按旧true恢复。

Windows其他模型运行与D盘LLM存储保持；恢复记录../2026-10-29_service_recovery有真实私有库WMI快照及检查方法。当前用户对话已经增加，不用旧144/276或187/183当新基线，不回滚旧库。私有音频/图像/身份库不复制共享树。允许公开合成PCM、离屏图及不含真实对话的诊断，stage UI截图要避免个人预览区域。用户期望完成修复后集中现场复测，不只停在计划。
