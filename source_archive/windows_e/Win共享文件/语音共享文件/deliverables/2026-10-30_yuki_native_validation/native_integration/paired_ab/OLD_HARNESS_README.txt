独立旧remote16 / 新Yuki16配对测试宿主（脚本交付，板端由root执行）

1. isolated_portrait_server.py
默认只check；执行必须加--execute及新--ready-file。--aura=Windows实际aura目录，--source-config=现portrait_host.local.json，--board-manifest=fresh board_source/manifest.json，--expected-revision=实板remote config revision，--port=0（默认）。只监听192.168.50.1上OS空闲端口、只接192.168.50.2，记录实际PID/端口/source/snapshot/config hash与ready。它创建独立PortraitRenderer，绝不调用/修改8796、现役selected、config、防火墙或systemd。参数路径必须由root审查；root负责启动、终止及复制ready证据到板端测试目录。

2. paired_renderer_harness.py（统一入口，委托old_renderer_harness.py实现）
默认仅check；--execute才导入Gtk/Gst、创建独立屏内opaque/non-focus窗口。--backend old|old_nojpeg|new（默认old）。公共必需参数：
 --runtime 当前fresh r3 runtime绝对路径
 --board-manifest fresh board_source/manifest.json
 --fresh-baseline paired_ab/fresh-baseline.json
 --server-proof Windows独立server生成的READY JSON副本
 --scenario A/B共用scenario JSON
 --pcm 公开24k mono PCM16 WAV
 --envelope 与WAV对应的hop_seconds/gains/levels JSON（两边同hash）
执行时另需--output（runtime外新目录）、--window（同423x438屏内opaque配置）、--execute。
B额外传--yuki-root paired_ab/yuki-root.json；可显式传--candidate-manifest native_integration/ui_candidate/manifest.json，默认按现目录结构找到同文件。worker默认读取同目录ui_candidate/aura/tools/board_avatar_worker.py（可用--candidate-aura另指其aura目录），native_yuki/egl读取yuki-root.root/tools。先逐文件核yuki-root.files及三份Python的ui_candidate manifest pin，再由真实prepare_portrait执行资源/profile约束与哈希校验。默认check不会导入Gtk/Gst/native模块或建socket。
不接受8796/生产remote端口；仅在内存里把旧remote config复制并替换为独立server端口。绝不改现役文件或selected。窗口默认例子x590/y80、423x438，结束按worker/presenter→video→pixels→audio→window顺序销毁，不调用present()/焦点、录音、pan机械或相机服务。

3. old_harness_support.py
可供B复用相同PreparedPcmJobs、真实GstAudioEngine同步fakesink、真实fresh RealtimeController与旧core factory，避免A跑完整业务、B跑SimpleNamespace。create_controller默认legacy_native_pixels=True供A，严格保留NativePixels threads3、cache_sequences12与8态预热；B必须传False，才与新候选UI相同使用configure_board_rendering fallback且不预热旧8态，不给新人物强加旧pixel backend。
FSM单独禁止state-change publication，与Windows pinned renderer的隔离方式相同；不启动RecordingController/ASR/TTS/模型/身份/机械或完整业务UI。这些共同背景负载/相机采样归root统一提供并保持ABBA一致，不能只A额外创建完整BoardAvatarStage。

真实旧显示/诊断功能全保留：
NativePixels旧初始化、PortraitOffload独立session/endpoint、AvatarRenderWorker interval1/24+visual16（与旧Gtk一致）、FramePresenter原延迟/代次/过期策略、PreviewEncoder原>=0.2秒quality85后台JPEG、NativeVideo原Gst/XID、原public快照节流和PerformanceRecorder。
JPEG最多5Hz；16fps离散offer下常接近4Hz，不应假称每秒精确5次。

时间与统计：
新进程cold包括来源hash预检、import/core/后端初始化/first observed matching-mode handoff；A包括NativePixels与8态预热，B包括yuki-root proof逐文件哈希和真实prepare_portrait校验（这项额外证明开销明确计入B）。ready在相同200ms轮询观察，量化误差不超过一个采样周期及调度延迟。Windows独立server先warm ready（符合当前remote服务常驻），OS page cache不清。warm期由ready加scenario.warmup_seconds界定。root应在A/B使用相同定义，ABBA不混冷暖。
scenario事件按10ms调度进入原worker.request队列；expensive worker.read/native stats仅按旧native_ui_tick_ms=200ms读，不加每帧Python observer。原C++NativeVideo保留240个时间点/239间隔，p95索引floor(n*.95)、p99=floor(n*.99)（239个间隔分别227/236）；B用尾240个swap完成时间同公式。A时间点是identity handoff回调入口、位于ximagesink之前，B是swap提交完成，两者都不是物理scanout，不能声称显示扫描延迟同一观测层。
记录wire mode、discard/failure、FramePresenter.presented/dropped/expired以及native pushed/received；C push返回2时不入队且wrapper不报错，presented-pushed可提示这类拒帧，pushed-received不能捕获全部drop。A按现役协议在submit/cancel/状态重同步时可短暂local8；strict_remote_mode_entire_measurement=false单独不判无效，结合mode_spans/observed_target_mode_fraction及offload状态判断正常恢复或服务故障。mode跨度由200ms public快照近似，不是假称每帧精确归因。B mailbox.fail/渲染故障仍立即失败。

B使用真实candidate worker+LocalPortrait fps16+create_gl_area，公共PCM/jobs/output/RealtimeController/scenario与A一致。B没有FramePresenter/JPEG/NativeVideo，保留候选真实每render快照16Hz行为；A保留旧native-video快照最多10Hz。B额外frame_observer仅append(stats.paint_at)到尾240 deque，host本身会复制一次stats字典，额外成本计B，无GPU读回。

C控制：--backend old_nojpeg与A使用完全相同参数，不传yuki-root。只在独立进程中、旧AvatarRenderWorker构造前把其模块全局PreviewEncoder替换为old_harness_support.NoPreviewEncoder。它显式__bool__=True，offer/offer_rgb/close无操作、read返回b''，没有线程/锁/队列；不把preview_encoder置None，避免触发同步PIL JPEG分支。实际RGB处理、三线程NativePixels/八态预热、remote16、FramePresenter、NativeVideo/Gst、PerformanceRecorder及10Hz public节流全部保留。实例构造后检查truthy空编码器、presenter与pixels存在，失败直接报错。原worker源码文件哈希不变；summary.source_patches记录精确替换、原始来源hash与替换实现hash。C专属别名old-nojpeg-summary.json，公共summary.json等格式不变。

结果统一ready.json、measurement-ready.json、summary.json、samples.json、commands.json，另保留old-summary.json/new-summary.json别名。summary.stages.measurement_start_monotonic/measurement_end_monotonic供OS对齐；commands包含命令outcome，samples含状态、播放时钟、预览JPEG字节数与显示层计数。测量结束后才写大结果，避免热路径每帧落盘。尾240帧区间统计与整段received差值分别记录。

功能边界：
新pipeline当前不生成旧诊断JPEG。A-B比较整条替换pipeline；A-C用于估计旧JPEG编码/编码线程/队列等子系统的边际成本（并发调度有交互，不能把差值视为精确可加常数）；C-B两者均无JPEG，但仍含remote传输、FramePresenter/Gst与本地EGL、快照10/16Hz、初始化等差异，不能直接称纯renderer CPU收益。C是诊断控制，缺失Web预览，不是已授权的生产替代方案。CPU/进程家族/RSS/PSS/GPU raw/相机业务/ABBA及C-B-B-C调度/资源窗口由root负责；harness不改ACK、系统设置或服务。

当前本子任务验证：本地4份Python AST、3场景约束、12秒24kmonoPCM/envelope覆盖及尾240个时间点量化公式PASS；本代理未发送RPC、未加载任何板端renderer或跑A/B。独立Windows server已由root审查后启动（PID32652/port61584），主代理审查统一CLI后先做pilot。脚本存在与静态PASS不等于性能证据。
