# 给父代理的精确集成接点

本交付只在 candidate/ 写入。请合入父侧副本并复核最终源指纹，不要覆盖另一代理已冻结的 11 个基础文件；其中 common/speaker_turns.py、tools/speaker_turns.py 是对基础文件的增量，其余为新模块。SOURCE_MANIFEST.json 同时记录两个基线 SHA；tools/speaker_turns.py 保留最新 mutable PCM job descriptor 的取消清空逻辑。

## 1. 原 Hub 的同一个 CPU worker

现有 `tools/device_hub.py:Hub.__init__.initialize` 在同一 executor 上构造 SpeakerDevice 后接入：

```python
from tools.progressive_speaker_hub import install_anonymous
self.progressive_speaker = install_anonymous(self, anonymous_config)
```

`anonymous_config` 读取新增 config/anonymous_identity.local.json；候选 enabled=true 对应用户已授权的临时记录，不自动修改现役配置。生产 `self.root` 必须是既有私有 AppData 根，不能是源码包、共享目录或模型目录。新库 anonymous-voices.sqlite3 不含 PCM。原 encoder CPU 实例复用，无第二次模型加载；既有 speaker_gate/pool 串行约束保留。普通对话没有人脸前置条件。

私有关联库与 ReceiptAuthority key 也放同一私有根。key 只赋予原登记适配器，不提供任意签名 HTTP/LLM 工具。

```python
from common.identity_links import IdentityLinkRegistry, ReceiptAuthority
from tools.private_gallery_reference import private_gallery_reference

# 此路径/model/dimension 必须来自该服务实际 pinned 配置，不能由请求指定。
self.voice_reference = lambda identity: private_gallery_reference(
    self.root/'speakers.sqlite3', self.speaker.encoder.model_id,
    self.speaker.encoder.dimension, identity_id=identity,
    expected_application_id=self.speaker.store.APPLICATION_ID)
self.identity_links = IdentityLinkRegistry(
    self.root/'identity-links.sqlite3', ReceiptAuthority(private_key),
    anonymous_lookup=self.progressive_speaker.anonymous_store.active,
    anonymous_evidence=self.progressive_speaker.anonymous_store.evidence,
    voice_reference=self.voice_reference)
```

合入后的 tools/speaker_turns.py 会调用可选 progressive_speaker，按同轮分析得到 aN；可选 identity_links/voice_reference 已就绪时，将已标定 voice_proof 或同向量三采集 provisional.proof 交给 resolve，输出严格 v3 identity。人脸可选 `self.face_naming_proof(meta, visual)` 必须使用实际板端只读图库引用调用 tools.identity_resolution.face_proof；没有可信引用就不给视觉姓名，不能按同名猜测。

父侧 common/speaker_turns 的 validate_record 必须合入 v1/v2/v3 增量。原 TimelineConversationStore 和 speaker turn host 会复用它，不需要放宽未知字段校验。所有个人访问布尔值保持 false。

## 2. 统一登记必须位于 device 命令之前

原 `tools/board_model_host.py:ModelHandler` 与 `tools/voice_channel_source.py:serve_channel` 当前先处理 device reply；有 device_reply 后就不再建立 identity_exchange。仅实现索引会导致用户落入互斥流程，不能称完成统一关联。

将 UnifiedBindingRouter 和 SpeakerEnrollmentBridge 放在拥有 SpeakerDevice 的单 CPU worker 内，暴露受 owner/token 限制的统一路由调用；不能跨线程直接使用原 SpeakerStore 的 SQLite connection。ModelHandler 在现有 `device_client.command(meta,text,pcm)` 前读取统一 decision：

```python
decision = binding_route(meta, text, pcm, visual=validated_capture_visual)
if decision['skip_legacy_device_command']:
    device_reply = decision['reply']
else:
    device_reply = device_client.command(meta, text, pcm)

# face_exchange 必须显式选择登记交换，不受 ordinary enrollment_requested 限制。
# 普通 ASR 原文仍用于 transcript；另带受控 board_text 才能规范“记住我”。
if decision['route'] == 'face_exchange':
    identity_exchange = open_binding_exchange(meta, decision['attempt_id'])
elif decision['route'] == 'ordinary_skip_speaker':
    # 照常给聊天模型，但不要再调用旧 standalone 声纹适配器。
    device_reply = None
```

`ordinary_skip_speaker` 是必要接点：关联暂停/无脸时，旧 SpeakerDevice 仍可能 active；若又调旧 command，会把正常聊天误当登记采样。`face_exchange` 的 reply 必须为空或交由 BindingIdentityReplyStream 处理，不能形成 device_reply 抢走人脸路由。

BindingIdentityReplyStream 保留 request/token/sequence/max6/timeout 及原 240 字边界；完成消息与实际朗读文本一致。final transform 调 `router.face_result(meta, pcm, attempt_id, original_result, signed_receipt)`。一次通道/TTS 完成后的 stream.cancel 只关闭当次交换，不撤销跨轮登记；用户明确取消/过期才改变登记状态。

## 3. 板端原人脸流程与真实回执桥

原 `board/runtime/audio/channel_jobs.py` 的 `receive` → identity_request 分支当前直接调用 `identity_flow.handle(header['text'], start_owner, ...)`。仅在这个已授权登记分支对送入流程的文字应用：

```python
from common.binding_intent import face_enrollment_text
board_text = face_enrollment_text(binding_board_text_or_original,
    active=self.identity_flow.public()['active'])
reply = self.identity_flow.handle(board_text, start_owner, is_current=current)
```

不得在每条普通聊天全局改写名字或自动启用登记；“我叫小明”单独出现仍是普通聊天。纯“记住我”先在原流程进入 name 状态，然后同脸短期跟进姓名；相关原始 VoiceEnrollment 测试已覆盖。

当前 identity_result 只有 code/name，**尚不够生成可信 COMMITTED 证据**。需要在原实际 identity_enroll 命令和回读位置收集：原 command、accepted ACK、提交前图库 revision/people、提交后 actual identity.last_operation 与最终 identity ID、原 store/model ID、模板指纹（在拥有节点内计算）。用 face_commit_payload 验证 identity_completion、command_id/action、COMMITTED 与 revision+1；不从朗读“已保存”推断。既有人脸复用走 existing_face_payload，要求 fresh KNOWN 原人脸 ID、同 revision 和明确本次关联确认，state=EXISTING_CONFIRMED。

实际 gallery 路径/model/dimension 从本轮 pinned 源入口解析；可在板端原进程/本地 read-only helper 用 private_gallery_reference 返回小型引用，不导出向量/照片或任意其他人列表，也不重启相机/模型。父侧需要缓存/读取初始图库引用供 router.start；没有引用时目前会 BINDING_PRECONDITION_UNAVAILABLE，不能假造 gallery ID。图库引用含私有路径摘要而不含路径本身。

可选 binding_receipt 元数据沿原 token/owner 的 final registered 或 already_known 返回；接收端先核对原 IdentityReplyStream token 与捕获，再由受限原适配器签署。没有真实原回执，router 不会自动进入声纹。不要提供可签署任意外部 JSON 的接口。

## 4. 原声纹登记自动串联

router.face_result 验过真回执后自动 `SpeakerEnrollmentBridge.start`，内部调用原 `device.turn('登记我的声纹，我叫X')`，不要求用户重新触发声纹登记。原三个样本、VAD、模型、三段一致性与最终保存确认不改。只有处于原 confirm 阶段，才把“确认保存身份关联”映射为原“确认保存声纹”。桥接从原 session 向量数量实际增加确认接受的采集；真实库 revision+1、唯一新增 ID 与原 session 结束共同形成声纹回执，模板指纹私有计算。实际 COMMITTED 完成上下文必须与当前捕获完全相等。

绑定窗口内丢脸/换服务代次/换相机代次、图库修订、换原人脸身份等不会继续采样。没有 ASD，所以登记期间人需在镜头前并按提示说话；不能把单人入镜称为单人发声已验证。原自然人脸恢复轨迹由板端原采样策略负责，不能用几何跟随自动放宽绑定。

两个原库分别提交，最后关联索引再原子激活；任一方中止保留 PARTIAL 并明确提示现状，不自动回滚原用户模板。撤销授权/删除原 face/voice 时须由原确认入口同步 revoke_person；原模板已删或指纹改变，后续 proof 与匿名候选的私有引用检查也会阻止旧名复活。

## 5. 未标定姓名候选与身份问题

原普通 voice evidence 仍 NOT_CALIBRATED，没有 candidate_id。新增 provisional matcher 复用同一 encoder 向量，按原 SpeakerStore.match（且不得低于 0.8/0.1）累计三次不同 PCM/capture，库修订/超30秒重置；proof 仅两秒有效。只有 ACTIVE 关联才解析出姓名，不修改 calibrated 标志，不给私人权限。

`tools.provisional_voice.query_reply(text, identity_evidence)` 只对明确身份问题返回措辞；普通聊天返回 None。未标定时说“声音可能对应 X，尚未标定，不能确认身份”，用户回应名字也不会自动变成认证或开启个人长期记忆。视觉单模态仅说明当前画面可见人脸；冲突不挑一个。aN 当轮读回与原模板存活/指纹检查缺一时不走匿名名称候选。

## 6. 父侧验收与边界

需要父侧继续完成上述实际 wire/model-host/board hooks、原身份删除同步、配置与新源指纹 pin、只读保存前后私有表统计和部署后状态核对。保护并行机械/显示更新、其他模型进程、D盘LLM与既有运行入口；本子代理不部署、不开麦/播放/运动，也未读取真实库。软件候选通过不替代真人统一登记、跨天/重启、相似声纹、多人/电视/画外人及远场的集中验证。
