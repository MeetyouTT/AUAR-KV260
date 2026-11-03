# 字幕修复候选

现役 `984d3ca24067bf5129e9ce3b0054f32cced717b6b8824eab347476bef2f9e502` 的字幕生命周期会把正常新请求误判成失效请求。`RecordingController._queue_transcription` 先记录 `requested_at`，随后调用 `BoardDialogueJobs.submit`；后者调用 `_invalidate`，触发 `generation_changed` 并更新 `invalidated_at`。因此正常新 `start` 的请求时间也早于失效时间，`PresentationLifecycle.channel` 拒绝建立当前显示槽。识别文字和回答共用这个入口，所以两者都为空。普通 GTK 投影和单次 metadata 投影没有造成这个问题。

本候选仅修改 `tools/production_memory_presentation.py`，增加 24 行、删除 1 行：成功 submit 后，登记一份有界的“当前 owner + epoch”凭据；仅允许该新请求跨过 submit 自身触发的一次失效。凭据在首个接受的 start 后消费，任何后续失效会清空。外层沿用 jobs 的同一 RLock，随后进入 presentation 锁；没有 presentation → jobs 的反向取锁。Store 提交若插在原 submit 返回和登记之间，失效计数不再等于原计数加一，登记被拒绝。并发取消在同一 jobs 锁后清空凭据，不能复活。

原始 `requested_at` 没有改动，字幕硬截止仍为 `min(now, requested_at) + 300` 秒。取消、更正、遗忘、清空、成功压缩提交和关闭仍清空当前文本及凭据；已授权当前命令的“只显示新确认回答”既有例外保持。正文仍只在 GTK 当前 RAM 槽出现，localhost/API 投影保持 metadata only。原单次投影优化保留。

## 本地验证

- `test_submit_lifecycle.py`：18 项通过。对当前 380 项 manifest 匹配字节后，直接抽取真实 `_queue_transcription`、`_poll_transcription`、`submit`、`_invalidate` 和 `poll` 方法执行，未导入或启动设备运行时。现役正常调用顺序可稳定复现两槽为空，候选可显示两槽。
- 包括提交失败、返回值/异常原样保持、不同 owner/generation、Store 提交和取消竞争、原五分钟截止、迟到 start、实例隔离、确认回答例外、GTK widget 写入和 API 脱敏。
- `test_preserved_projection.py`：现役 984d 与候选比较，10 项及 500 个固定种子嵌套状态案例通过。每次 bridge 发布只遍历一次状态树。
- 仅本地公开构造的零 PCM、测试文字、假时钟、RAM 假 Store/GTK widget；没有真实 GTK/板端运行验证，没有访问设备、模型、私库、录音、照片或身份。

`public_arm_validation.tar.gz` 可在独立公开临时目录解包后，用 Python 3.10 或更新版本执行 `python3 -B -X utf8 run_portable_validation.py`，或 `sh run_public_arm.sh`。包内夹具从自身相对路径读取，运行不依赖共享盘或生产目录。已在 Windows 用该同一可移植入口重跑通过；本窗口没有执行 ARM。唯一设备窗口负责是否运行以及记录实际 ARM 结果。

## 交接与回退

候选 SHA256：`de04c6cd22e3672ff17c2cfb71f5539f6908c98daf74e8d94d154c8fd280d4c2`。

父窗口独立审查 `repair.patch` 后，由既有唯一设备窗口在暂停聆听的窗口发布。此目录的 `BUNDLE_MANIFEST.json` 是本地审查包清单，不是板端发布 manifest；不提供服务启停或设备操作。发布时只改这一项来源，由设备窗口更新相应完整发布清单。另 379 项保持当前值。

实机验收只需当前正常请求的字符数、`showing`、epoch 和现有播放指标，加现场观察字幕；不得读回正文、截图或解禁 API 字幕。

需要回退时，仅在 source 当前仍等于上述候选 SHA 的前提下恢复 `before/tools/production_memory_presentation.py`（984d），并由唯一设备窗口恢复对应发布绑定。保留此前单次 metadata 投影优化。回退后会恢复原有字幕缺失，因此只用于新故障隔离。
