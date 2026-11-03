# 空闲音频维护：上层准入和子进程回执候选

2026-10-22，仅主任务、单终端串行执行。接续已通过20项测试的维护引擎，本目录补控制线程、IPC和默认关闭的GTK接线。当前生产仍运行原版本。

本机33项测试通过，包含真实`AvatarRenderWorker`队列调度、真实管道和GStreamer 1.16.3合成`fakesink`。真实队列测试仅替换未使用的图像缩放导入，不是画面/GTK验收。KV260上Python3.9.9复跑同33项也全部通过（不是新增33项），包括真实GStreamer子进程的重建/代次/冷却拒绝/合成PCM完成/关闭。测试前后相机264975、UI215734、Xserver1077保持，检测帧44752→44829，完整覆盖的内核观察窗口新增匹配USB告警0。只在独立目录运行，没有打开ALSA或更改生产源；生产GTK/MCP01/AEC闭环仍未验收。

`candidate/aura/tools/maintenance_recording.py`在原控制线程上建立屏障，检查实际录音对象、未消费语音、转写等待/活动/结果/通道、播放和身份登记状态。维护期间暂停录音/ASR轮询，状态查询使用缓存，空闲视觉控制继续tick。不会调用cancel来制造空闲，也不修改免点击偏好。设置保存和会话选择同时进入原控制线程队列。

`maintenance_audio_output.py`将写管道限定在0.25秒和8192字节内；每条回执匹配worker实例、request ID、token与pipeline epoch。超时、取消、传输失败及错误代次继续保持屏障。收到新管线预热完成仍等待控制线程重新核查空闲，才能放行；旧参考和重复sequence在分发给AEC前丢弃。显式close只处理该对象拥有的子进程，等待超时后terminate/kill，并关闭管道句柄。

`gstreamer_audio_worker.py`仅在显式传入`--maintenance-instance`时加载维护引擎。受理回执先于新代次状态发出；队列未清空或worker不匹配不受理。保留原stop静音保活，关闭和重建仍使用已验证引擎的NULL确认、预热和限次逻辑。新管线就绪始终报告`usb_playback_health=UNVERIFIED`，不以时钟推进宣称USB实际播放健康。

GTK候选仅当`AURA_IDLE_AUDIO_MAINTENANCE=1`时选择新输出和控制器、注册本机`audio_maintenance`命令。默认关闭，无新界面按钮、自动内核监控或USB复位。实际桥接器原有Host/Origin检查保持。未替换当前板卡UI或启动配置。

首版有意保守：保留capture、utterance、channel等对象时，即使表面处于IDLE也拒绝维护。其他服务必须是新鲜actual快照、无排队请求、音频和交互空闲，且明确不具备录音/问图能力；相关旁路提交与维护屏障共用锁。未知或第二音频服务不予受理。完整业务运行后的闲置资源收敛、实际MCP01恢复和生产GTK/AEC验收仍需另做。

本地复现：`python3 -B -m unittest -v test_maintenance_ipc`。需要PyGObject/GStreamer/Pillow；缺少GStreamer时两项native测试会跳过，不能称全套通过。`recovered/`为只读回收依赖，清单含来源及SHA。只使用合成静音PCM，无现场录音、人脸/向量或身份库。
