公开RAW流式ASR与完整combined前端共存probe；未部署、未由本代理跑模型

入口probe_coexist.py默认只inspect，root显式--run才启动本次公开试验。新模型仅在root已隔离的/home/root/aura-public-streaming-asr-20261031/68c9c943840f7d9c；26,342,340B的CTC模型SHA68c9c943...，tokens SHA6fed8c6c...。不复制任何模型进共享目录，不修改正式v14 39b102a4/378pins、Paraformer3threads/身份/记忆/16fps/相机。

接线与数据合同
  原PacedPublicPcm：每20ms供给640B、320samples的16k PCM16。
  原BoardAutomaticCapture + BoundedPcmCaptureMixin：仍8帧/160ms raw queue。
  原SpeechEndpoint.feed：先照常调用combined GTCRN/Silero、500ms pre-roll、700ms silence。
  实例RAW observer：把同一个不可变640B RAW对象offer到独立ASR在途预算；只加锁/排队/更新少量metadata，不执行模型、不sendall、不等ACK。
  sender/reader线程：仅私有socketpair的有界传输/ACK，decode不在这里。
  独立subprocess：唯一OnlineCTC(num_threads=1)，逐RAW帧做原PCM16→float32/32768规范化，accept_waveform后drain is_ready；每次drain完成才ACK。

首选RAW输入，GTCRN仅VAD，保持现正式ASR输入预处理。没有denoised替换实验。另已核GTCRN真实FFT hop256=16ms；虽然调用输入20ms，GTCRN单次输出可为0/256/512即0/16/32ms，不能当10ms或固定20ms。CTC约0.64s模型块是算法内部readiness，绝不把单次约0.4秒decode塞进capture feed/GUI。

ASR传输预算固定16000 RAW samples=1秒=32KiB，不是原capture queue扩容。它统计本地排队+已发未ACK总量，所以kernel socket buffer不会藏额外积压；最大50个320sample帧。预算满立即标ctc_backlog_overflow并整轮失败，绝不丢帧/拼接/重试增大容量。CTC结果只有在完整END的序号/总样本/流hash一致且所有ACK后可见；0.66秒零尾仅官方模型上下文，立即送入input_finished，不额外睡0.66秒。RAW输入及原endpoint输出公共clip校验逐字节不变。

边界
本次CTC接收“公开文件起点到原endpoint停止”的RAW全流，明确没有实现生产500ms pre-roll/onset/tail与最终capture clip逐字节绑定，更没有captok→job一次性claim、partial转写发布、Store授权或播放。不能把本probe当正式流式ASR桥；生产方案由memory review另门审查。新模型前轮与Paraformer结果不同、无gold参考，准确率未通过。

额外驻留及CPU
正式GUI/相机保留，正式mic须暂停，生产GTCRN/Silero模型仍resident。本probe另建一份combined前端及一个CTC进程，必须标明extra frontend/model RAM，不能声称复用了当前actor。当前actor只有GUI私有socketpair，AUTO_START会开arecord；没有可安全外部附着的公开PCM口。为避免改生产入口，本probe沿已验证公开源/原queue/endpoint组件执行。
前端probe使用原已验证ProbeProcessPriority(-10)，只作用自己的TGID/线程并恢复；CTC在提优先级之前创建，保持nice0，1线程；不绑核。原模型/阈值/queue8不变。
前轮RAW CTC约2.75–2.86秒decode CPU/5.615秒公开音频，平均约半核；与前端近一核、相机约一核和GUI竞争，不能仅凭尾350–435ms就认定共存可用。

root调用（仅复用原运输方式，无发布器）
需要本probe、已冻结guard210925ca...及已冻结旧公共pipeline ac0af16c...。旧pipeline只使用PacedPublicPcm与ProbeProcessPriority，不调用其旧Paraformer/运行时更换入口。
python3 -B probe_coexist.py --pipeline-source <board existing runtime-probe-ac0af16c9f783b55.py> --pipeline-sha256 ac0af16c9f783b5590ab0e1562ece179b8cc50ade3912c8b08e8b8592778e093 --boot-id <fresh> --ui-pid <fresh supervisor> --ui-birth <fresh ticks> --camera-pid <fresh> --camera-birth <fresh ticks>
上述默认inspect不构造模型；同参数--run执行。可显式--guard-source更改到同SHA常规文件，--wav/--wav-sha256选择root合成公共样本。默认仍旧公开0.wav SHA1a6bf940...，默认MemAvailable门1500MiB（最低不低于512）；root须再根据实际RSS决定头寸。外层root subprocess设置整体有限期限（建议120秒），本次自己的CTC启动读45秒、通信3秒、最终等待12秒、关闭1+2+2秒均有界。源/启动模型原生构造仍由外层截止保护。只清理自己的CTC子进程，不信号生产进程；没有arecord启动路径。

前置/后置原guard：同boot/startup/当前组件pins、UI/camera PID+birth+cmdline、暂停mic、无任务/播放、host空闲/内存余量。后台memory活动前后变化只标background_changed，保留测量，不据此声称收益。root可另用原metadata探针观察GUI/native，脚本没有改变16fps设置，但实际FPS未测，不能标通过。

待测数值
raw queue peak/overflow及供给迟到；frontend完整gate wall mean/max、thread CPU；固定ASR credit peak/oldestACK/overflow；CTC decode calls/max/p95/CPU、final flush；最后真实样本调度结束→final、原endpoint结束→final分别报告；公共结果hash/字符数、模型构造计数、CTC peakRSS；与原clip的样本起点/长度/hash；生产GUI故障、camera帧/epoch/身份新鲜度、native FPS由root独立观察。
通过只表明有限公开源的资源共存，不是新模型准确率、实体录音/听音、正式业务或长稳验收。先0.wav，再由root决定8条TTS公共短句，不先扩大输入量或缓冲到通过。

本地10主测试/4子例通过，覆盖非阻塞source、1秒全链credit、非法RAW帧、原endpoint返回值不改、溢出全失败、ACK乱序/提前final拒绝、close线程回收、真实worker协议+fake recognizer单实例/1线程/RAW转换/官方零尾。未跑模型、设备、真实库或生产服务。
