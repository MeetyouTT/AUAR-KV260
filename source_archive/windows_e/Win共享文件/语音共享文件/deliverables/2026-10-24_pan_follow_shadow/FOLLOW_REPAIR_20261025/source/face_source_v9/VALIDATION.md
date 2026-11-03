v9 本机候选，未访问 UART、板卡、执行器或生产服务。

调用链核查：原 r4 `board/vision/ui_camera_service.py:440–444` 已在 Gst capture callback 中向 FaceTargetService.offer 投递实际 source/fid/stamp；YOLO 后的 IdentityService.offer 仅在没有 face_targets 时调用。因此「Flow 原本只收到 YOLO 后图像」不成立。

本候选只修扩展层：Flow 在原检测 offer 获取共享锁前先收到同一捕获对象与原始 fid/stamp；原检测 offer 入参和调用次数不变。Flow worker 在获取检测状态快照后重新选取最新捕获帧，避免等待共享锁后继续测量等待前的帧。原 r4、v8、身份调度、模型/恢复预算未修改。

23/23 本机软件测试通过，耗时 0.066 秒；Python 3.8.10 运行。覆盖真实 FaceTargetService 漏检、旧 source.install 集成、raw offer 顺序/同对象/一次投递、阻塞快照后换最新帧、重复帧/时间戳拒绝、250ms TTL、500ms 实锚边界、多脸、消失、纹理不符、运动 key 和身份 key 分离。四个运行 Python 文件编译通过。

复验命令：

```sh
/home/ghmd/kv260-adaptation-check-20261006/identity/.venv/bin/python -m unittest discover -s /home/ghmd/aura-pan-follow-shadow-20261024/face_source_v9 -p 'test_*.py' -v
```

motion 源期限仍为 250ms；真实检测锚严格小于 500ms；当前像素模板匹配至少 0.80。count0 必须保留正确 continuity_key 并对当前新图像匹配；不借用身体/yaw/预测，不更新旧帧时间。READY 包增加 evaluated_mono_ms 和 face_detection_age_ms 供核对服务器判定时刻。

face_tracking 诊断新增 offer_source_age_ms、offer_gap_ms（捕获源时间间隔）、offer_arrival_gap_ms（实际投递间隔）、detector_offer_ms、snapshot_wait_ms、source_age_at_start_ms/source_age_at_finish_ms、process_source_gap_ms/process_finish_gap_ms 及间隔最大值。它们用于区分捕获断档、原 offer 共享锁等待、快照等待和处理耗时，不能预先证明已根治实板断档。

transfer-files.json 是五个部署文件的本机路径、板端路径、字节数与 SHA256。实板时延、持续真人随动、机械平滑度以及最终部署均由 root 统一执行与记录；本报告不将本机测试称为板级通过。
