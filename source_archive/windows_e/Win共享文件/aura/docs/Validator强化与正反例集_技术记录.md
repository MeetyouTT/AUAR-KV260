# Validator 强化与正反例集（173 组）技术记录

> 版本：V1.0 ｜ 日期：2026-09-13 ｜ 作者：人3（运行时 / 对话 / 系统集成）
> 对应计划：A3/A4 ·「9/20 强化 Validator、断链回退和视觉证据」+「9/24 Validator 至少 100 组正反例」
> 环境标签：**PC / SIMULATED**（本机 pytest 与工具执行；不含任何板端实测）
> 关联文档：`docs/runtime_architecture.md` §四、`docs/A1_Gate_Report.md` §五

---

## 一、背景与目标

A1 阶段交付了三层 Validator 骨架（`board/runtime/validator/`），当时只有 14 项单测，且：

1. **Schema 层错误码过于笼统**：所有结构问题都报 `schema.invalid`，上层无法区分「缺字段 / 类型错 / 枚举越界」，
   也不符合 `core.py` 里约定的 `<layer>.<code>` 细粒度风格；
2. **Semantic 层有两处合同未落地**：`ValidationContext.audio_generation_id`（音频代）字段定义了却**从未被使用**，
   而合同明确要求「旧响应不得覆盖新请求（request_id / audio_generation_id 把关）」；场景时间只判了 TTL 过期，
   没有判 `valid_until_ms < captured_at_ms` 这种**脏数据**；
3. **Policy 层缺两类真实幻觉形态**：摄像头已掉线（`camera_state != online`）却声明"看到人"；
   同一条响应里**同时**声明"左边有人、右边有人"（自相矛盾）；
4. **脏输入会抛异常**：`visual_claims: null`、`reply_text: 123`、`current_target: "x"`、`recent_events: "bad"`
   等非法响应会让 Validator 直接 `TypeError`。而 A1 门槛要求「非法响应 → 丢弃并改'不确定'回复」，
   即 Validator 必须**永不因脏数据崩溃**；
5. **用例规模不足**：计划要求 9/24 前达到 **≥100 组正反例**，用于证明「越权与虚构事实被拒」。

本轮目标：**在不改动任何数据合同（`schemas/*.json`）、不改动 `DialogueAdapter` / `DialogueRequest/Response`
接口的前提下**，强化三层判定能力，并把用例集扩到 100 组以上、可一键复现、可出校验报告。

---

## 二、做了什么

| # | 交付物 | 说明 |
|---|---|---|
| 1 | `board/runtime/validator/schema_validator.py`（强化） | `jsonschema` 判定关键字 → 细粒度错误码映射；`required` 错误的路径补全到缺失字段名；排序键类型安全化 |
| 2 | `board/runtime/validator/semantic_validator.py`（强化） | 新增音频代检查、场景时间自洽检查；`scene_seq_used` 类型保护；脏输入加固；抽出 `_check_scene_clock()` |
| 3 | `board/runtime/validator/policy_validator.py`（强化） | 新增 `camera_not_online`、`conflicting_visual_claims`；`reply_text` 类型保护；`current_target` / `recent_events` 脏数据加固；越权条数统计健壮化 |
| 4 | `board/runtime/validator/core.py` | 新增 `ValidationContext.request_audio_generation_id`（可选字段，默认 `None`） |
| 5 | `board/runtime/validator/__init__.py` | 新增 `ValidationChain.validate_response_all()`：三层**全跑不短路**，用于报告与现场诊断 |
| 6 | `tests/data/validator_cases.json`（新增，**173 组**） | 声明式用例集：12 个场景预设 × 19 个上下文预设 + response/request/scene 三类报文 |
| 7 | `tools/validator_cases.py`（新增） | 用例加载器 + 执行器 + 校验报告（`--json evidence_shots/validator_cases_report.json`） |
| 8 | `tests/test_validator_cases.py`（新增） | 173 组参数化单测 + 9 项用例集元检查（数量/唯一性/正反例比例/三层覆盖/红线错误码覆盖） |
| 9 | `docs/runtime_architecture.md` | §四 三层 Validator 表更新（细粒度错误码 + 新增检查项 + 正反例集指引） |

**规模**：173 组用例 = 正例 40 + 反例 133；按 kind 分 response 117 / request 24 / scene 32；
命中 **26 类**错误码（覆盖 Schema 11 类、Semantic 6 类、Policy 9 类）。

---

## 三、关键实现细节与技术决策

### 3.1 Schema 层：细粒度错误码（向后兼容）

`jsonschema` 的错误自带 `validator`（触发关键字）与 `path`，据此映射：

| 关键字 | 错误码 | 关键字 | 错误码 |
|---|---|---|---|
| `required` | `schema.missing_field` | `minimum` / `exclusiveMinimum` | `schema.number_too_small` |
| `additionalProperties` | `schema.unexpected_field` | `maximum` / `exclusiveMaximum` | `schema.number_too_large` |
| `type` | `schema.type_mismatch` | `maxItems` / `minItems` | `schema.array_too_long/short` |
| `enum` / `const` | `schema.enum_violation` / `const_violation` | `uniqueItems` | `schema.duplicate_items` |
| `minLength` / `maxLength` | `schema.string_too_short/long` | `pattern` / `format` | `schema.pattern_mismatch` / `format_mismatch` |

**关键细节**：`required` 错误的 `path` 指向**父级**，直接输出会出现 `path=""` 无法定位。
因此用正则从消息 `"'reply_text' is a required property"` 中提取字段名并拼到 path 上
（如 `scene_state.camera_state`）。未映射的关键字仍回落 `schema.invalid`，不破坏既有读法；
项目内除本文件外没有代码依赖旧码 `schema.invalid`（已 grep 确认）。

另修一个隐患：原排序键 `key=lambda e: list(e.path)` 在 path 中**混有 int 与 str**（数组下标 + 字段名）时
会抛 `TypeError`。改为 `tuple(str(p) for p in err.path)`，保证多错误时报错顺序稳定且不崩。

### 3.2 Semantic 层：音频代与时间自洽

- **音频代**：新增可选上下文字段 `request_audio_generation_id`。当它与「当前音频代」`audio_generation_id`
  不一致（且非 `None`）时判 `semantic.stale_audio_generation`。**默认 `None` = 不做判定**，
  因此完全不影响既有 A1/A3 链路（`examples/smoke.py`、`ws_adapter` 单测均不传该字段）。
  这条规则正是 A3 判据「TTS 打断后不重播旧响应」在 Validator 侧的落点：请求发出时记录代，响应回来时代已推进 → 丢弃。
- **时间自洽**：抽出 `_check_scene_clock(scene_state, now_ms, result)`，同时判
  `now_ms > valid_until_ms`（`semantic.scene_expired`）与 `valid_until_ms < captured_at_ms`
  （`semantic.scene_ttl_invalid`，脏数据）。`valid_until_ms == 0` 仍视为「未设有效期」跳过，
  保持既有语义（`examples/smoke.py` 的场景就是 0）。
- **类型保护**：`scene_seq_used` 若为字符串，`"125" > 125` 会抛 `TypeError`，故比较前用 `_is_int()`
  严格判断（**排除 `bool`**，因为 `True` 是 `int` 子类，否则 `true` 会被当成 1）。

### 3.3 Policy 层：两类新幻觉

- `policy.camera_not_online`：`camera_state != "online"` 时，任何「看到人」类事实
  （`person_present` / `person_on_*` / `person_recently_*`）一律拒绝；`no_person` / `no_visual_evidence`
  这类「缺证据」声明不受限（摄像头掉线时说"没看到人"是合理表述）。
- `policy.conflicting_visual_claims`：同一响应里出现 ≥2 个不同位置事实即拒绝（LLM 常见幻觉：
  "左边有人…右边也有人"）。注意 `person_present + person_on_left` 属**同位置**组合，不触发。

### 3.4 健壮性加固（永不因脏数据抛异常）

| 脏输入 | 加固方式 |
|---|---|
| `visual_claims: null` / `"abc"` / `[1, "x"]` | 统一走 `_claims()` 过滤：非数组返回空、非对象条目忽略 |
| `reply_text: 123` | 仅当 `isinstance(reply, str)` 才判长度 |
| `current_target: "bad"` | `_as_dict()` 包装，非对象当空对象 |
| `recent_events: "bad"` | `_has_recent_event()` 先判 `isinstance(list)` |
| `fact: {"nested": 1}` | `FACT_RULES.get()` 只在 `isinstance(fact, str)` 时调用（否则 dict 作 key 会 `unhashable`） |
| `control_requests: 5` | 条数统计做容器类型判断 |
| 响应 / 场景非对象 | 各层返回 `.not_object` / `.scene_not_object` |

### 3.5 用例集格式：声明式（避免 173 组重复抄写报文）

若每组用例都写完整报文，JSON 会有数千行且极易出现「基座改了、用例没同步」的漂移。因此设计成
**基座 + 覆盖** 的声明式结构：

```json
{"id": "R-317", "kind": "response", "desc": "同一条响应同时声明左与右",
 "base": "multi_pos", "expect_ok": false, "expect_layer": "policy.response",
 "expect_codes": ["policy.conflicting_visual_claims", "policy.visual_claim_ungrounded"]}
```

- `set` / `del` / `fill`：路径覆盖（前缀 `resp.` / `ctx.` / `scene.`，支持 `a.b[0].c` 形式）；
- **值级引用指令**（`tools/validator_cases.py::expand_refs`）：
  `"$scene.person_left"` 引用预设场景、`{"$repeat": {"char": "很", "times": 501}}` 造超长串、
  `{"$list": {...}}` 造超长数组 —— 让「501 字符」「33 条事件」这类边界用例只需一行；
- `only`：`schema|semantic|policy`，**只跑单层**。用于覆盖被上游层拦截、串联链路走不到的判定
  （如 `people_count` 为负的业务语义码 `semantic.negative_people`、`fact: 123` 的 `policy.unknown_fact`）；
- 判定口径：`expect_ok=true` 的用例**必须零 issue**；`expect_layer` 校验短路层；`expect_codes` 要求全部命中。

**决策：报告与单测共用同一执行器**（`tools/validator_cases.py`）。若测试与报告各写一套加载逻辑，
迟早出现「报告说 100% 通过、单测失败 3 条」的矛盾。现在两者是同一份代码路径。

### 3.6 踩坑记录（本轮真实踩到）

1. **`raw` 用例忽略了 `set` / `del` / `fill`**：`build_target()` 原先在 `if "raw" in case` 时**提前 return**，
   导致所有「引用预设场景 + 局部改坏」的用例（S 系列 25 条）静默变成合法输入、断言全挂（首轮 153/173）。
   修法：`raw` 只决定基座来源，覆盖/删除/填充逻辑统一在之后执行。
2. **上游层会"抢报"**：`R-313`、`R-319` 原本声明 `source_track_id: 7`，而 `no_person_empty` / `camera_lost`
   场景里没有该 track → 被 Semantic 层先用 `semantic.track_not_found` 拦下（短路），Policy 断言永远等不到。
   修法：这两组用例去掉 `source_track_id`，让它走到 Policy 层。**层间短路是设计使然，用例必须按层设计。**
3. **`required` 的 path 指向父级**，不补字段名就无法定位（见 3.1）。
4. **`bool` 是 `int` 子类**：`true` 会被 `isinstance(x, int)` 放行，必须显式排除
   （否则 `scene_seq_used: true` 会被当成 1 参与比较）。
5. **`FACT_RULES.get(fact)` 遇 dict/list 会抛 `unhashable`** —— 脏数据防线不能只靠上层 Schema。

---

## 四、验证方式与结果

### 4.1 用例集执行（一键复现）

```powershell
$w = "D:\share\项目开发\FPGA语音助手开发\wujing-lite"; cd $w
python tools\validator_cases.py --json evidence_shots\validator_cases_report.json
```

实测输出（PC / SIMULATED）：

```
[validator-cases] env=PC / SIMULATED total=173 passed=173 failed=0 (positive 40/40, negative 133/133)
[validator-cases] by_kind={'response': 117, 'request': 24, 'scene': 32}
[validator-cases] code_counts={...26 类错误码...}
```

### 4.2 单测回归

```powershell
python -m pytest tests/ -q     # 全量回归（含 173 组参数化用例 + 9 项用例集元检查）
```

### 4.3 证据

| 证据 | 路径 |
|---|---|
| 校验报告（含逐条明细与错误码分布） | `evidence_shots/validator_cases_report.json` |
| 用例集 | `tests/data/validator_cases.json` |
| 执行器 / 报告工具 | `tools/validator_cases.py` |
| 参数化单测 | `tests/test_validator_cases.py` |

---

## 五、涉及文件清单

| 文件 | 类型 | 说明 |
|---|---|---|
| `board/runtime/validator/schema_validator.py` | 改 | 细粒度错误码映射 + required 路径补全 + 安全排序 |
| `board/runtime/validator/semantic_validator.py` | 改 | 音频代、时间自洽、类型保护、脏数据加固 |
| `board/runtime/validator/policy_validator.py` | 改 | camera_not_online、conflicting_visual_claims、脏数据加固 |
| `board/runtime/validator/core.py` | 改 | 新增 `request_audio_generation_id`（可选） |
| `board/runtime/validator/__init__.py` | 改 | 新增 `validate_response_all()` |
| `tests/data/validator_cases.json` | 新增 | 173 组正反例 |
| `tools/validator_cases.py` | 新增 | 加载 / 执行 / 出报告 |
| `tests/test_validator_cases.py` | 新增 | 参数化单测 + 元检查 |
| `docs/runtime_architecture.md` | 改 | §四 三层 Validator 表更新 |

**未改动（有意为之）**：`schemas/*.json`（数据合同不动）、`dialogue_client/adapter.py` 合同、
`events.py` / `fsm.py` / `ui_state.py`、`examples/smoke.py` 链路。

---

## 六、下一步

1. **A4 · 9/23 故障注入 5 类**（camera / network / ASR / LLM / TTS）：复用 `tools/mock_dialogue_server.py --mode`
   与 `MockBoard` 注入，产出 `docs/故障注入报告.md`；本轮新增的 `semantic.stale_audio_generation`
   正好作为 TTS 打断项的判据。
2. **GA / GB 的 PC 部分报告**（`docs/GA_Gate_Report.md`）：校验报告 `validator_cases_report.json` 直接作为
   「越权与虚构事实被拒」的证据引用（务必标 PC / SIMULATED）。
3. 可选：把 `tools/validator_cases.py --json` 纳入出证据 SOP；板端阶段用 C/C++ 复刻同一份错误码与用例集
   （用例集是 JSON、与语言无关，可直接作为板端移植对照表）。


