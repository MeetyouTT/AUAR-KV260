# 运行时架构文档（Runtime Architecture）

> 版本：V0.1 ｜ Week A1（9/1—9/5）｜ 作者：人3（Runtime & Integration）
> 环境标签：**PC（开发主机）**；板卡到货后替换硬件 IO 层，本架构合同不变。

## 一、模块图

```
┌────────────────────────────── board/runtime ──────────────────────────────┐
│  Event Bus (有界队列+策略)  ←── 所有 worker 发布/订阅 EventEnvelope      │
│     │                                                                     │
│     ├── FSM ──────────────── 9 态运行时状态机（发布 fsm.state_changed）   │
│     ├── Validator ────────── Schema → Semantic → Policy 三层              │
│     ├── Dialogue Client ──── Adapter 合同 + Mock（A3 接 WebSocket）        │
│     ├── MockBoard ────────── 外设状态/寄存器/按键（人1 9/6 正式交接）      │
│     └── Logging ──────────── 环形缓冲日志（证据快照）                      │
└───────────────────────────────────────────────────────────────────────────┘
schemas/  ← JSON Schema 数据合同（与语言无关，板端/主机共用）
```

## 二、Event Bus（有界事件总线）

合同：**有界队列；视觉帧丢旧保新；错误/取消/最终状态不静默丢失。**

| 策略 | 行为 | 事件 |
|---|---|---|
| LATEST | 满队列时挤掉最旧**同类型** | `camera.preview_frame`、`detector.frame` |
| LATEST_FINAL | 新状态覆盖旧状态，最新必可读 | `scene.state` |
| CRITICAL | 挤掉最旧非关键事件；全关键则阻塞等待 | 取消/崩溃/隐私/关停/underflow |
| BOUNDED | 满则丢弃并计数 | 心跳等普通事件 |

统计：`published_count`、`dropped_by_type`、`evicted_by_type` 均为证据可读。

## 三、FSM（9 态）

| 状态 | 触发 | 出口 |
|---|---|---|
| IDLE | 初始/无人 | scene.person_enter → PRESENT |
| PRESENT | person enter | kws/key → LISTENING；person_exit → IDLE |
| LISTENING | 唤醒 | vad_end → THINKING；cancel → CANCELLED |
| THINKING | 语音结束 | response → SPEAKING；timeout/error → IDLE |
| SPEAKING | 收到回复 | playback_stop → IDLE；cancel → CANCELLED |
| CAMERA_LOST | 任意状态 + camera.lost | camera.recovered → IDLE |
| NETWORK_LOST | 任意状态 + network_lost | network_restored → IDLE；kws → LISTENING(本地) |
| CANCELLED | 取消（瞬时） | 自动回迁 PRESENT（有人）/ IDLE |
| ERROR | 任意状态 + worker_crash | health_ok → IDLE |

确定性：相同事件序列 → 相同状态序列（纯函数 + 显式转换表）。

## 四、三层 Validator

| 层 | 检查项 | 错误码示例 |
|---|---|---|
| Schema | JSON 结构/类型/枚举/必填（jsonschema） | `schema.missing_field`、`schema.type_mismatch`、`schema.enum_violation`、`schema.number_too_large`、`schema.array_too_long`、`schema.unexpected_field`、`schema.not_object` |
| Semantic | request_id 匹配、scene_seq 不超前、TTL 与时间自洽、track 存在、音频代（打断后旧响应拒绝） | `semantic.request_id_mismatch`、`semantic.scene_seq_ahead`、`semantic.scene_expired`、`semantic.scene_ttl_invalid`、`semantic.track_not_found`、`semantic.stale_audio_generation` |
| Policy | 视觉声明 grounding、emotion/avatar 白名单、回复长度、摄像头在线性、位置声明自洽、越权控制 | `policy.visual_claim_ungrounded`、`policy.unknown_fact`、`policy.camera_not_online`、`policy.conflicting_visual_claims`、`policy.emotion_not_allowed`、`policy.avatar_not_allowed`、`policy.reply_too_long`、`policy.control_denied` |

核心红线：**LLM 视觉声明必须有 SceneState 证据；无证据改输出"不确定"，不允许补造事实。**

> 第 9 轮强化（2026-09-13）：Schema 层由单一 `schema.invalid` 细化为
> 「缺字段 / 类型错 / 枚举越界 / 数值与数组越界 / 未声明字段 / 非对象」等可分类错误码（`jsonschema` 关键字映射，
> 未映射关键字仍回落 `schema.invalid`）；Semantic 层新增**音频代检查**（`ctx.request_audio_generation_id`
> 与当前代不一致 → 旧响应拒绝，支撑 A3「TTS 打断后不重播旧响应」）与**场景时间自洽**检查；
> Policy 层新增**摄像头非 online 时不得声明看到人**与**同一条响应位置声明冲突**检查；
> 三层均对脏输入（`visual_claims: null`、`current_target: "x"` 等）做了不抛异常的加固。
> `ValidationChain.validate_response_all()` 提供「三层全跑不短路」的诊断入口（正式链路仍短路）。

**正反例集（9/24 节点）**：`tests/data/validator_cases.json`（173 组，PC / SIMULATED）+
`tools/validator_cases.py`（执行器 / 出校验报告 `evidence_shots/validator_cases_report.json`）+
`tests/test_validator_cases.py`（参数化单测 + 用例集元检查）。错误码约定 `<layer>.<code>`，
报告与单测共用同一执行器，避免两套判据漂移。

## 五、Adapter 合同（板端 ↔ LAN 主机）

```
DialogueRequest  {protocol_version, request_id, audio_generation_id,
                  transcript, scene_state, allowed_emotions, allowed_avatar_actions}
DialogueResponse {protocol_version, request_id, scene_seq_used, reply_text,
                  emotion, avatar_action, visual_claims}
```

- 必须带超时；超时抛 TimeoutError，断链自动回 CORE_LOCAL。
- 旧响应不得覆盖新请求（request_id / audio_generation_id 把关）。
- A1 用 `MockDialogueAdapter`（本地回环，可注入 latency/fail_mode）；A3 替换为真实 WebSocketAdapter。

## 六、MockBoard

- 模拟外设状态（camera/audio/npu/pl/network）与故障注入。
- 初始寄存器合同（V1.0 §11.2）：IP_ID/CONTROL/FRAME_*/DROP/UNDERFLOW/TIMESTAMP/BOX0-3/ZONE/PRIVACY。
- ⚠️ 环境标签恒为 `SIMULATED`，任何结果不得冒充板端实测（人3 任务书 §九 红线）。

## 七、数据合同引用

| Schema | 文件 |
|---|---|
| DialogueRequest | schemas/dialogue_request.schema.json |
| DialogueResponse | schemas/dialogue_response.schema.json |
| SceneState | schemas/scene_state.schema.json |

## 八、跨角色交接状态

| 流向 | 内容 | 计划 | 状态 |
|---|---|---|---|
| 人1→人3 | MockBoard、寄存器合同、FPGA 状态 | 9/6、9/10 | 待交接（MockBoard 已接口占位） |
| 人2→人3 | Detection/Scene schema、tracker 事件 | 9/4、9/10 | 待交接（scene_state schema 已按 V1.0 §8.4 冻结占位） |
