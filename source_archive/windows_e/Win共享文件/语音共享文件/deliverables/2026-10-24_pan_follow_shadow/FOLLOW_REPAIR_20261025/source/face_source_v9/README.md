v9 是独立的人脸运动观测扩展，部署入口为板端 `pan-face-edge-v5/face-source-v9/entry.py`。冻结的五个运行文件与 SHA256 见 `transfer-files.json`；本目录不修改 r4、v8、DPU/身份调度或恢复预算。

已读源码确认：`r4/candidate/aura/board/vision/ui_camera_service.py:440–444` 本就在原始 Gst capture callback 中执行 `captured → flip → face_targets.offer`，早于 YOLO。YOLO 后的 `IdentityService.offer` 仅在没有 face_targets 时调用；不能将它视为现役 Flow 的入口。

实际修复是扩展层的 offer 次序与锁后帧选择：Flow 先收到相同捕获图像对象、frame_id 和原始 stamp，再调用原检测 offer 一次；worker 获得共享检测状态锁快照后，重新取最新捕获帧，避免继续测量等待锁之前的旧帧。没有替换时间戳、身体跟踪或预测。源期限保持250ms，真实单脸检测锚严格小于500ms；漏检续测仍须正确 continuity_key 与当前新像素高置信匹配。

23项本机检查全部通过，解释器、命令及结果见 `validation.json`，细项说明见 `VALIDATION.md`。未访问 UART/板卡/生产服务，也未在本报告宣称板级或机械效果通过。

只读锁顺序审查未发现当前路径的循环嵌套锁：Flow.condition 在获取 face.lock 前释放，raw offer 在进入原检测锁前释放 Flow.condition，worker 发布后释放 Flow.condition 再通知 _edge_signal。原相机正常退出在未持有 state.lock 时关闭身份/Flow。保留风险：Flow.close 使用2秒 bounded join，但没有在超时后抛出仍存活错误；不能将它单独视为线程已完全退出的强证明。本次未改冻结版。

v9 没有调用 cv2.setNumThreads 或修改全进程 OpenCV 配置。原 r4 ui_camera_service.py:337 的 checked_backend 已执行 cv2.setNumThreads(2)，现役正常启动沿用该2线程配置。本机独立探针在未走 checked_backend 时 getNumThreads() 为18，不能代表现役进程；不建议在现役相机进程里临时改变全局线程数，因为会同时影响预览/检测/身份。先看 v9 的原始投递间隔、锁等待和处理源龄诊断，再在隔离基准中比较线程配置。
