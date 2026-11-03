# Windows 实际接线增量候选

核心 14 文件与其 manifest 保持冻结。此目录新增 5 个候选：仅 tools/device_hub.py 覆盖原声画协作55版 Hub；其余 common/binding_api.py、tools/binding_dispatch.py、tools/binding_hub_runtime.py、tools/binding_model_adapter.py 均为新 helper。父侧合并根为 extras/candidate/，精确 SHA 在 SOURCE_MANIFEST.json。

## 已落地与验证

- 实际 Hub.initialize 在原同一个 CPU executor 上安装匿名分析、私有 identity-links 库、随机持久 HMAC key 与 UnifiedBindingRouter，继续复用原 SpeakerDevice/encoder。生产根限原私有 AppData；测试用假 encoder 和隔离路径注入，不加载真实模型。
- 本地 typed route/state/open/face-result/gallery 仅从 Hub loopback 进入，并使用原 speaker_gate/pool。没有任意 sign HTTP API。登记 face result 必须匹配 request owner、generation、attempt、原流 token 和只在本地持有的私有 capability；再严格验原回执字段/策略，才内部签署给核心索引。
- 实际 ModelAdapter 先于旧 device command 作路由，face_exchange 直接注册原 identity_exchanges，不能被 device_reply 抢走；ordinary_skip_speaker 保留普通对话，避免暂停登记的旧 active 声纹会话吞掉讲话。BoundIdentityExchange 在结束/取消时清掉其可变 PCM holder；原 native 函数的局部输入在函数返回后释放，未宣称能强杀原生调用。
- 原人脸流程完成后自动进入三段声纹和原最终确认；登记/控制采集的 evidence 通过实际 Hub.analysis_submit 复用，不再次编码。普通每轮只由原 Tracker 编码；显式身份问题单次编码后也复用其 v3 evidence，不另开编码器。
- 私有键持久化后可重用；原声纹确认删除、已接受完整人脸 inventory 中不可见身份删除/模板改变，均真实触发派生索引失效。原授权管理器可在同 worker 调 revoke_derived_identity。不会删除原模板、原对话或授予私人记忆。临时超时/IO失败不当作删除。
- 新增实际超时清理：派生登记过期时先清掉它的原声纹 session，再回普通聊天，避免随后旧 legacy 路由继续采样。当前回执仍按原 generation/owner 和容量规则登记。

17 项 extras 专项通过（4.73 秒），包括本机临时 loopback HTTP 与真实 Hub typed API → 原 SpeakerDevice/假 encoder 全流程。extras 覆盖下原 69 项专项和 55 项连续声画/PCM 兼容，共 124 项回归通过（15.79 秒）；不与原交付报告累加为项目总数。初轮测试跨线程读 SQLite 的 fixture 错误、旧 Hub test double 缺新方法的兼容失败日志均保留；没有关闭 SQLite 线程检查或放宽字段门槛。

未修改正式 A 或核心14候选，未读取真实私有模板、现场声音/影像，未部署、开麦、播放、运动或加载新模型。只能认定软件接线候选通过，识别精度、真人登记及整机验收仍待后续。

## 父侧最小调用

```python
from tools.binding_model_adapter import prepare_channel
device_reply, identity_exchange, routed = prepare_channel(
    self.server.models, meta, text, pcm, self.headers, timeout=remaining)
```

这一句替换原 device_client.command 位置。`serve_channel(...,identity_exchange_override=identity_exchange)` 必须在已有 exchange 时跳过旧 enrollment 条件；channel_frames 生成 transcript 时仅在 exchange.binding_request 存在时附加该字段，原 ASR text 不改。父侧在预算用尽或 serve 失败的 finally 同样 cancel exchange。

`ModelHost.accept_identity_result` 方法体用 `return accept_model_result(self,value)`；它兼容原不带回执结果，只允许 BoundIdentityExchange 接收 binding_receipt。

`POST /v1/voice/identity/gallery` 在原受限板端来源、无 Origin 和 JSON 读界限之后调用 `accept_model_gallery(models,body)`，body 必须是 `{context,packet}`。完整 packet 只含最多32项的ID/模板摘要，来自同板实际只读回读；板端先等精确 ACK，再附不超过4096字节的 X-Aura-Face-Gallery。Hub 缓存按同一 context+packet_sha256，未命中不用图库身份。普通没有画面或 metadata 时照常聊天。

图库完整 JSON body 额外硬限24576字节；完整 identity_result 元数据硬限4096，测试的原 COMMITTED 包在界内。超过时拒绝该关联，不扩大原上限、截断内容或伪造完成。单次 Hub typed body 仍沿原900000界限供合法PCM base64使用。

唯一外部候选依赖是另一个代理的 board_bridge/candidate/common/face_binding_wire.py（manifest 记录其 SHA）。板端回执必须由原 command+ACK+last_operation/原 KNOWN 事实构造；本地 HMAC 只保护这条受限适配流程，不能替代该真实板端证据，也未声称对被攻陷的可信板端作远程证明。

## 合并与后续

父侧仍负责把这5文件、核心14、原11基础、板端bridge与ModelHost/Channel小改作最终union；重算源指纹/pins，保护并行机械/显示入口、其他模型与D盘LLM，按现态部署规则操作。原个人授权的撤销回调应在该授权原确认提交后，通过同worker调用 `hub.binding.revoke_derived_identity(person_id)`，没有给任意外部撤销/签名端点。正常模板删除/修改已由上述实际hook处理。
