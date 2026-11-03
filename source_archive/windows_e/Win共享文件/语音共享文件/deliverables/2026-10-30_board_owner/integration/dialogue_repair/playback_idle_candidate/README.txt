空闲播放IPC最小候选（仅源码，未由本代理上板）

现役来源：v14 startup39b102a4… / manifest a2545970…；tools/gstreamer_audio_worker.py基线SHA63fd37185b6aa6909134945a440be2c33781ed95d2e81dfd95905afe4e17dce7。before原字节保留；只将该worker的逻辑空闲重复state IPC限为1秒一次。

实质源点：原worker的glib.timeout_add(10,tick)每10ms无条件poll、JSON序列化state、flush；PersistentGstAudioEngine在IDLE_READY仍每50Hz推静音保持设备暖就绪。当前voice_barge_in=false已不导出reference IPC，不能把CPU归因于不存在的base64参考出口。实际空闲播放进程约16%单核是整进程数值，未证明全由重复JSON造成。

保留：10ms engine.poll、50Hz静音、60ms预送、完整PCM命令、活动/WAITING_PCM/暂停100Hz状态、reference处理/50ms新鲜度、每tick stdout pending flush、错误/EOF/close清理。LLM、Store、逐包授权fresh检查和完整ACK路径均未改。

门只适用engine.active isFalse、非paused、persistent且device_ready、IDLE_READY且无error/audible。初次、命令、稳定逻辑字段变化、token、EOS和错误立即发布；动态clock/answer_clock/started_at与计数不参与空闲相等判断，仍随1Hz心跳更新。异常清门状态，避免相同idle恢复被吞。

1Hz依据：现役SelectedAudioOutput只按token接收snapshot，不记录接收时间/age；ready/finished读取ready、active/error/done。StreamingController以finished+network完成；RealtimeController和GTK未对空闲音频IPC设陈旧门。视觉STALE规则不属于此链。消费者源SHA与路径见consumer_sources.json；相应原音频源码见source_provenance.json。活动播放始终保持原频率，EOS首包不等待心跳。

验证：12项unittest主用例通过（另含close/EOF的2个subtest），实际调用候选main和嵌套tick，以假GLib/engine/时间和内存stdout驱动；未加载GStreamer、模型、音频设备或私库。110个tick仍有111次poll（含warmup检查），稳定idle发初次与1秒心跳2个state。活动/等待PCM/暂停、EOS、token/done/ready变化、命令/取消、错误恢复、部分写入、reference和关闭边界均覆盖。详细结果见test_result.json。

运行测试：python -m unittest discover -s "<本目录>/tests" -p test_idle_worker.py -v
源码候选：after/tools/gstreamer_audio_worker.py；before保留63fd基线；candidate.patch为审查diff。

本地fake只证明发布行为与边界，不证明ARM CPU节省、首声、实际FPS或长期稳定。root须以受控新source pins发布并对照；本代理没有替换正式worker、重启服务或做板测。初步可减少的是空闲JSON/pipe及GUI解析工作，不能声称省掉持续静音/ALSA/采样转换的固有开销。
