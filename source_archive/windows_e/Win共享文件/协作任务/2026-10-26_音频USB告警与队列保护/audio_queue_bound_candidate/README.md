# 音频appsrc内部队列有限保护候选

仅独立本地候选，未修改共享业务源码或现役、未接板/相机/DPU/MMIO/USB/ALSA。主端独占所有板端操作。它修复异常态下可复现的内部队列无上限问题，不宣称是MCP01的xHCI告警根因或告警已经根治。

## 依据与反例

原件`/home/ghmd/Win共享文件/语音共享文件/aura/tools/gstreamer_persistent_engine.py`的SHA为`f257cf2d4cf9749b0d83d377d78c2b963d989496fdfe322131f7f476beb39d8c`，与主端已核验现役一致。其`block=False`、`max-bytes=7680`，没有处理enough-data，也不检查实际current-level-bytes。

[GStreamer官方appsrc说明](https://gstreamer.freedesktop.org/documentation/app/appsrc.html)规定：达到max-bytes后通知应用暂停推送；block=True才使后续push等待。因此block=False配max-bytes不是队列硬上限。current-level-bytes自1.2可用，leaky-type自1.20才有，本候选不依赖后者。

`python3 -B replay_stalled_queue.py`用实际原/新engine配单producer的受控Fake appsrc：push返回OK且不消费，pipeline clock继续前进，sink position不变。原engine两秒推100块/96000B，是配置7680B的12.5倍；Python queue/interval仍为空，snapshot仍IDLE_READY/error空。前轮只检查Python deque的有限性测试没有覆盖内部队列。

新engine同输入最多推8块/7680B；持续满队列两秒后按原fail流程释放管线、明确ERROR，不继续静默持有。这里两秒从首次发现满开始计，故三秒场景已经释放。`QUEUE_REPLAY.json`保存具体数值。此反例不证明实际板卡出现积队，也不证明pipeline clock和sink position在此次硬件告警期间按该方式分离。

## 最小修复

- 保持单管线、block=False、同样的空闲20ms静音、采样/转换参数、worker/API和原播放时钟。
- 每次push之前读取实际current-level-bytes。只有现有字节数加下一块真实长度不超过7680，才从Python内容队列取出并push；末尾短包按实际长度检查。
- 满时不popleft真实语音、不创建interval、不更新last_data_end，不伪造已播放或完成。短暂恢复后原PCM/offset仍按顺序送出。
- 满队列持续2秒走既有fail+release，不无限积队。查询失败/缺失属性或非法level同样明确fault并释放。故障时沿原fail语义取消内容，不默默丢弃并报成功，不自动重放语音或自建恢复owner。
- 不启用block=True，不用会丢真实语音的leaky策略，不调用USBreset，不默认关闭语音。

## 验证与限制

`python3 -B -m unittest discover -s /home/ghmd/aura-pan-follow-shadow-20261024/audio_queue_bound_candidate -p 'test_*.py' -v`

17项主机行为回归通过：原7项内容/暂停/回声/代际/时钟合同加新10项实际队列、短暂阻塞、PCM保序、未入队不计完成、短包、STOP/close响应、查询失败、非法level、有限超时和正常首内容时序一致性检查。旧fixture补充“立即被下游消费时queue level=0”的真实属性合同，没有跳过新检查。

本机`/usr/bin/python3`可加载GStreamer1.16.3，创建无设备appsrc并读取current-level-bytes=0，返回Python int，证明该本机属性可用；未拿本机1.16.3冒充KV260版本或真实ALSA验证。主端另计划KV260 appsrc→fakesink+BLOCK_DOWNSTREAM padprobe进行真实内部队列隔离对照，仍不得当USB/声学验收。

追加`native_queue_benchmark.py`已在本机GStreamer1.16.3完成真实无设备对照：两版实际engine分别运行在自有子进程，真实appsrc→fakesink由临时BLOCK_DOWNSTREAM probe阻断消费，总4.879s；原版最大106560B，仍IDLE_READY/error空；候选最大7680B，持续满后约2.196s明确ERROR并释放。最大单poll耗时0.417/0.313ms。原/新候选指纹均核对，f5d引擎未再改。

脚本有7.7秒总体子进程预算；超时只终止其自行创建的基准子进程，不触碰业务进程。正常与异常finally均移除该测试probe并请求NULL；为避免故障注入本身卡住销毁，包装器在engine请求NULL之前先移除probe。因此该试验不验证真实ALSA阻塞时的释放耗时，不打开MCP01/ALSA/USB、不出声。结果摘要在`HOST_NATIVE_QUEUE_BENCHMARK.json`；KV260需由主端单独串行运行并记录，不能把本机结果当板端通过。

命令：`python3 -B native_queue_benchmark.py --runtime-root <实际aura目录> --baseline-engine <SHA为f257的原engine> --candidate-engine <本候选engine>`。

只在即将push时执行队列检查。若整条pipeline clock冻结且不再计划push，本修复不会冒充完整sink进度看门狗；设备外部健康与受限恢复须另有实际证据。也未处理MCP01硬件告警根因。

## USB复发的下一步只读诊断

`pcm_progress_readonly.py --pcm-root /proc/asound/card1/pcm0p/sub0 --seconds 3`只读ALSA status/hw_params/sw_params及至多300条同窗口kernel日志，记录hw_ptr/appl_ptr、delay、avail和精确slot4ep3告警计数，不打开播放设备、不修改服务。使用前仍应核对card/USB路径是当前MCP01，不能凭历史card1假定设备永不变。

- 指针停住与告警同时发生：证明可见播放进度异常，不能据此直接认定供电、总线带宽或硬件损坏。
- 指针继续前进但出现告警：证明只看RUNNING/IDLE_READY/指针前进不足以作为USB外部健康验收；仍需保留内核告警，不把它们屏蔽。
- 现役worker没有输出appsrc current-level-bytes，外部/proc采样不能反推其内部积队。本候选的异常模型不证明现役已积队。
- 尚无可核验的USB底层根因；一次正常GUI重连恢复只能称恢复，不保证复发消除。不默认关闭语音、重置USB或周期性重启掩盖问题。
