# 情绪分档扩展：播报拆「高涨 / 低落」两档（SPEAKING_LOW）· 技术记录

> 日期：2026-09-12 ｜ 工程：`wujing-lite` ｜ 环境标签：PC / SIMULATED
> 触发：`talking_normal` 入库并目检后，确认其演绎为**情绪高涨**（前段双拳举起张嘴、中段右手张开说话、后段握拳，
> 手势丰富）；需求为在既有情绪节点上**再增加一个「情绪低落」的说话状态**。
> 关联文档：`docs/玩偶素材Seedance提示词包_技术记录.md`（§4.8 新提示词 / §11 本次扩展留档）、
> `docs/TALKING素材入库与同代一致性核验_技术记录.md`（上一轮）、`docs/ui_consistency_checklist.md`（V2.1）。

---

## 一、背景与目标

### 1.1 术语澄清（先对齐口径）

本工程里说的「**情绪节点**」**不是**抽象的情绪枚举，而是有明确定义的：
`docs/玩偶素材Seedance提示词包_技术记录.md` §10 写着 ——

> 9 个情绪节点 = 与 `board/runtime/fsm.py` 的 `RuntimeState` **逐字一致**。

即：**情绪节点 ≡ 运行时状态**，一一对应到一张素材、一条提示词、一组玩偶表现。所以"改情绪节点 + 加一个低落说话"
的正确落点是：**在 `RuntimeState` 上新增一个状态**，而不是在 UI 层做临时分支。

### 1.2 目标

| # | 目标 | 判定 |
|---|---|---|
| G1 | 播报按情绪分两档：**高涨**（既有 `talking_normal`）与**低落**（新增） | 两个状态、两张素材、两条表现映射 |
| G2 | 低落档**由真实信号驱动**，不是写死的演示开关 | 由 `dialogue_response.emotion` 决定 |
| G3 | **不改事件合同**（主机/人2 侧零改动） | `board/runtime/events.py` 无新增事件类型 |
| G4 | 向后兼容：旧调用方不传 `emotion` 时行为**与改动前完全一致** | `SPEAKING` 仍指 `talking_normal` |
| G5 | 素材未入库期间**观感不掉档** | 低落播报退 `talking_normal`，而不是退成待机 |

---

## 二、做了什么（改动清单）

| 层 | 文件 | 改动 |
|---|---|---|
| 状态机 | `board/runtime/fsm.py` | 新增枚举 **`RuntimeState.SPEAKING_LOW`**；新增 `LOW_EMOTIONS` 白名单与 `is_low_emotion()`；新增 `RuntimeFSM._route_emotion()` **目标后置路由**；补 `SPEAKING_LOW + AUDIO_PLAYBACK_STOP → IDLE`、把 `SPEAKING_LOW` 纳入取消链（`LISTENING/THINKING/SPEAKING/SPEAKING_LOW`）；故障类 `_add_any` 因遍历 `RuntimeState` 自动覆盖新态 |
| 数据合同 | `ui_spec/ui_state.schema.json` | `runtime_state.enum` 增补 `"SPEAKING_LOW"`（`schema_version` 仍 `1.0`，**加性变更**） |
| 素材层 | `board/ui/avatar_assets.py` | `STATE_ASSET["SPEAKING_LOW"] = "talking_low"`；新增 **`FALLBACK_BY_STATE`** 与 **`fallback_chain()`**，`frames_dir()` 改为沿回退链查找 |
| 表现层 | `board/ui/avatar_fsm.py` | `AVATAR_MAP["SPEAKING_LOW"] = AvatarSpec("speak", "sad", "播报·低落", "accent")`（复用既有 `sad` 几何参数，不新增表情） |
| 演示/证据 | `examples/run_ui.py` | `--all-states` 自动出 **10 张**板图；`--demo` 加第二轮对话（`emotion: sad`）演示分档；文案/帮助文本 9 态 → 10 态 |
| 单测 | `tests/test_fsm.py`、`test_avatar_assets.py`、`test_avatar_fsm.py`、`test_ui_state.py` | 新增 10 个用例（分档路由、兜底链、schema 枚举、表现两档） |

---

## 三、关键决策与踩坑

### 3.1 决策 A：用「目标后置路由」而不是新增事件类型（**事件合同零改动**）

**问题**：转换表是 `dict[(状态, 事件)] = 目标状态`（`board/runtime/fsm.py`），
`THINKING + DIALOGUE_RESPONSE_RECEIVED` **只能注册一个目标**，无法"同一事件、两个目标"。

**备选方案**：

| 方案 | 做法 | 评价 |
|---|---|---|
| ① 新增事件类型（如 `dialogue.response_received_low`） | 主机侧按情绪发不同事件 | ❌ 改**事件合同**，主机/人2 侧要跟着改，成本外溢 |
| ② 转换表值改成 callable 解析器 | `T[(s,e)] = fn(env) -> state` | ⚠️ 动核心数据结构，影响面大 |
| ③ **目标后置路由（采用）** | 保持转换表不变，在 `handle_event` 求出 `target` 后，用 `_route_emotion(envelope, target)` 后置改写 | ✅ 改动局部、语义清晰、**事件合同零改动** |
| ④ UI 层分支 | 状态仍 `SPEAKING`，渲染时看 emotion 选素材 | ❌ 语义藏在渲染层，板端 LVGL 需重实现一遍；且日志/证据里看不到"低落" |

**落地代码**（`fsm.py`）：

```python
    def _route_emotion(self, envelope: EventEnvelope,
                       target: RuntimeState) -> RuntimeState:
        if target is not RuntimeState.SPEAKING:
            return target
        if envelope.event_type != EventType.DIALOGUE_RESPONSE_RECEIVED:
            return target
        payload = envelope.payload if isinstance(envelope.payload, dict) else {}
        return (RuntimeState.SPEAKING_LOW
                if is_low_emotion(payload.get("emotion")) else target)
```

调用点插在"自环短路"之后、"应用变更"之前：

```python
        if target is current:
            return None  # 自环，不产生变更
        target = self._route_emotion(envelope, target)   # 播报情绪分档
        change = self._apply_change(current, target, envelope.event_type, auto=False)
```

> 曾考虑把路由放在"查表前"，但那样会给**所有**状态都套一层判断，且无法区分"目标本来就是 `SPEAKING_LOW`"的情况；
> 后置路由只认 `target is SPEAKING` 一个条件，最不容易误伤。

### 3.2 决策 B：`emotion` 白名单**中英双写**，归一化后匹配

主机（LAN 侧 LLM）返回的 `emotion` 是自由字符串（schema：`maxLength: 32`，**未限定枚举**，
只由 `policy_validator` 按 `allowed_emotions` 白名单把关）。因此：

```python
LOW_EMOTIONS = frozenset({
    "sad", "low", "down", "depressed", "gloomy", "apologetic", "sorry", "tired",
    "低落", "沮丧", "难过", "伤心", "抱歉", "疲惫",
})

def is_low_emotion(emotion: typing.Any) -> bool:
    if not isinstance(emotion, str):
        return False
    return emotion.strip().lower() in LOW_EMOTIONS
```

- **中英双写**：主机可能回中文标签（`"低落"`），只认英文会漏判；
- **归一化**：`" Sad "` 也要命中（单测覆盖）；
- **非字符串一律 False**：`None` / 数字不会误判为低落 → 默认走高涨档（保守方向，观感更安全）。

### 3.3 决策 C：新增 `FALLBACK_BY_STATE`（状态专属中间兜底）

**问题**：素材未入库时，`frames_dir()` 只会退到 `FALLBACK_ASSET = idle_normal`，
于是"低落播报"会变成"**待机**"—— 比"说话"更不搭，观感掉档。

**做法**：把回退链显式化，允许**每状态一条中间兜底**：

```python
FALLBACK_BY_STATE = {"SPEAKING_LOW": ("talking_normal",)}

def fallback_chain(runtime_state: str) -> typing.Tuple[str, ...]:
    chain = []
    candidates = ((asset_name(runtime_state),)
                  + FALLBACK_BY_STATE.get(runtime_state, ())
                  + (FALLBACK_ASSET,))
    for name in candidates:      # 去重保序
        if name not in chain:
            chain.append(name)
    return tuple(chain)
```

- 效果：`SPEAKING_LOW` 回退链 = `talking_low → talking_normal → idle_normal`（最后仍可退 B2V 矢量）；
- **零回归保证**：未定义中间兜底的状态，链就是 `(专属素材, idle_normal)`，与旧实现逐字相同 ——
  单测 `test_fallback_chain_speaking_low` 显式断言了 `THINKING → (idle_thinking, idle_normal)` 与
  `NOT_A_STATE → (idle_normal,)`（去重）两条。

### 3.4 决策 D：不新增表情，`SPEAKING_LOW` 复用 `sad`

`avatar_fsm.EXPRESSION_EYES` 只有 6 种几何表情（neutral/curious/attentive/thinking/happy/sad）。
低落播报需要"嘴角下垂"，`sad` 正好是 `mouth: "arc_down"`；而**说话时嘴要动**这件事由
`animation="speak"` 的帧表（`ANIMATION_FRAMES["speak"]`）负责，两者职责不冲突。
结论：**复用 `sad`**，不新增 `sad_speaking`（避免多一份要同步到板端 LVGL 的参数）。

`token_key` 保持 `accent`（不用 `warning`）：低落是**正常对话状态**，不是降级/故障，用 warning 色会误导。

### 3.5 决策 E：既有 `SPEAKING` 语义**不动**（向后兼容）

`SPEAKING` 仍是"情绪高涨"、仍指 `talking_normal`；只有"主机明确说了低落"才切档。
这样：① 老调用方不传 `emotion` → 行为与改动前**逐字一致**；② 演示/回归测试的历史预期不被打翻。

### 3.6 踩坑记录

- **`RuntimeState` 遍历式注册是"免费"的**：`_register_defaults()` 里的
  `_add_any(EventType.CAMERA_LOST, ...)`、`SYSTEM_WORKER_CRASH → ERROR` 等是对 `RuntimeState` 全遍历，
  新增枚举成员后**自动获得故障覆盖**，无需逐条补。反过来说：**新增状态时必须确认这类遍历点在枚举之后执行** ——
  本项目在 `_register_defaults()` 内执行，安全。
- **取消链是"手写元组"**，不是遍历：`for s in (S.LISTENING, S.THINKING, S.SPEAKING)` —— 这种地方**必须手动补**，
  已加 `S.SPEAKING_LOW`；同类手写清单还有 `T[(S.SPEAKING, AUDIO_PLAYBACK_STOP)]`（已并列补 `SPEAKING_LOW`）。
- **单测里 `reset()` 会清在场标志**：`RuntimeFSM.reset()` 内部 `_has_presence = False`，
  所以"低落播报中取消 → 回迁"用例必须走**无人在场**分支（断言 `→ IDLE`），
  否则会写出一个"看起来通过其实走错分支"的用例。
- **`pytest -q` 重定向丢汇总行**（本项目环境老问题）：用 `--junitxml` 读 `<testsuite ...>` 属性取真值
  （本次 `tests=205 failures=0 errors=0 time=5.547`）。
- **证据图不能整张丢进读图工具**（尺寸超限会被省略）：用 PIL 缩到宽 760 + JPEG(q=85) 后读；
  RGBA 素材要先合成到面板底色 `#101820` 再转 RGB，否则半透明边缘会发黑。

---

## 四、验证方式与结果

### 4.1 单测（全量）

```
python -m pytest -q --junitxml=%TEMP%\junit_spklow.xml
→ tests=205 failures=0 errors=0 skipped=0 time=5.547
```

新增/扩写用例（全部通过）：

| 文件 | 用例 | 断言要点 |
|---|---|---|
| `test_fsm.py` | `test_is_low_emotion_normalization` | `" Sad "` / `"低落"` → True；`None` / `3` → False |
| `test_fsm.py` | `test_low_emotion_routes_to_speaking_low` | `emotion ∈ {sad, 沮丧}` → `SPEAKING_LOW`；播报结束 → `IDLE` |
| `test_fsm.py` | `test_missing_or_high_emotion_stays_speaking` | 无 `emotion` / `emotion=happy` → 仍 `SPEAKING`（兼容性） |
| `test_fsm.py` | `test_low_speaking_cancel_resumes_idle` | `SPEAKING_LOW` 中取消 → 瞬时 `CANCELLED` → `IDLE` |
| `test_fsm.py` | `test_low_speaking_state_change_published` | `fsm.state_changed` 的 `to == "SPEAKING_LOW"` |
| `test_fsm.py` | `test_camera_lost_from_any_state`（扩参） | 新增 `SPEAKING_LOW` 也在故障覆盖内 |
| `test_avatar_assets.py` | `test_state_asset_mapping_defaults`（扩断言） | `SPEAKING_LOW → talking_low` |
| `test_avatar_assets.py` | `test_fallback_chain_speaking_low` | 链 = `talking_low → talking_normal → idle_normal`，且旧状态链不变 |
| `test_avatar_assets.py` | `..._prefers_talking_normal_before_idle` / `..._uses_own_asset_when_present` | 有 / 无 `talking_low` 两种落点 |
| `test_avatar_fsm.py` | `test_all_states_defined` / `test_speaking_two_emotion_tiers` | 10 态齐备；`SPEAKING=happy`、`SPEAKING_LOW=speak/sad` |
| `test_ui_state.py` | `test_speaking_low_in_schema_enum` | 枚举内含 `SPEAKING_LOW` 且快照过 JSON Schema 校验 |

### 4.2 端到端链路自检（真实 `assets/avatar` 目录）

| emotion | 状态 | 标签 | 表情 | 回退链 | 实际解析 |
|---|---|---|---|---|---|
| `happy` | `SPEAKING` | 播报 | happy | `talking_normal → idle_normal` | `talking_normal` |
| 缺字段 | `SPEAKING` | 播报 | happy | 同上 | `talking_normal` |
| `sad` | **`SPEAKING_LOW`** | **播报·低落** | sad | `talking_low → talking_normal → idle_normal` | `talking_normal`（中间兜底） |
| `低落` | **`SPEAKING_LOW`** | **播报·低落** | sad | 同上 | `talking_normal`（中间兜底） |

> 结论：**FSM 状态 / UiState 快照 / 素材回退链 / 表现映射 四层一致**（校验脚本内联断言 `fsm.state.value == ui.runtime_state`）。

### 4.3 UI 证据（10 张板图）

```
python examples/run_ui.py --all-states
```

出图 10 张：`ui_board_{idle,present,listening,thinking,speaking,`**`speaking_low`**`,camera_lost,network_lost,cancelled,error}.png`
（全部 1024×600）。新增那张目检：右上状态标签 **「播报·低落 [SPEAKING_LOW]」**、
延迟行 `状态 SPEAKING_LOW`、左上对话区显示低沉文案「抱歉，这次我没能帮上忙。」、
玩偶区按回退链播放 `talking_normal`（**仍在"说话"**，不是待机）—— 与 G5 预期一致。

### 4.4 素材进度

```
python tools/prepare_avatar_frames.py --status
→ 5/9 已入库；缺少：emo_puzzled, emo_sad, idle_offline, talking_low
→ 受影响状态：CAMERA_LOST, ERROR, NETWORK_LOST, SPEAKING_LOW
```

> 素材名总数由 **8 → 9**（新增 `talking_low`）；`CANCELLED` 仍复用 `idle_normal`。
> 体积核算：已入库 5 条实测合计 **102.9 MiB**（23.9+8.4+23.6+23.5+23.5），另 4 条按 23.6 MiB 外推 →
> **9 条到齐 ≈197 MiB（PNG）**；板端 RGB565 ≈43.7 MiB/状态 → **10 态 ≈437 MiB**。

---

## 五、涉及文件清单

**代码（生效路径）**

| 文件 | 说明 |
|---|---|
| `board/runtime/fsm.py` | `SPEAKING_LOW` 枚举 + `LOW_EMOTIONS` + `is_low_emotion()` + `_route_emotion()` + 转换补全 |
| `ui_spec/ui_state.schema.json` | `runtime_state.enum` 加 `SPEAKING_LOW` |
| `board/ui/avatar_assets.py` | `STATE_ASSET` 加行 + `FALLBACK_BY_STATE` + `fallback_chain()` + `frames_dir()` 改造 |
| `board/ui/avatar_fsm.py` | `AVATAR_MAP` 加 `SPEAKING_LOW`（speak / sad / 播报·低落） |
| `examples/run_ui.py` | 10 态出图、低落文案、demo 加低落轮、帮助文本 |

**测试**：`tests/test_fsm.py`、`tests/test_avatar_assets.py`、`tests/test_avatar_fsm.py`、`tests/test_ui_state.py`

**文档**：
`docs/玩偶素材Seedance提示词包_技术记录.md`（§3 对照表 / §4.8 新提示词 / §5.1.1 字数 / §11 扩展留档）、
`docs/ui_consistency_checklist.md`（V2.1 / M1 / M9 / §五 证据）、`docs/素材排队应对方案.md`（5/9 + §五.8）、
`assets/avatar/README.md`（映射表 + 兜底链 + 体积核算）、`README.md`（目录树 + 9/12 行）、本文件（+ 同名 `.docx`）。

**证据**：`evidence_shots/ui_board_speaking_low.png`（新增）、`evidence_shots/ui_board_*.png`（其余 9 张重出）、
`evidence_shots/ui_board_speaking{,_low}_view.jpg`、`evidence_shots/compare_speaking_vs_low_view.jpg`（目检缩图）。

---

## 六、下一步

1. **生成新素材**：按提示词包 **§4.8** 出 `talking_low.mp4`（9:16 / 首尾帧同一锚点图 / 低动态）
   → 步骤 7 关键帧核验（**与 `talking_normal` 首帧互比**，不要拿旧锚点图当基准）
   → 入库 `--framing waist-up --max-side 480 --budget-mb 35` → `--verify` / `--status`（目标 6/9）。
2. **待确认项（沿用，未变）**：① `--ref` 基准是否统一换新代首帧；② `idle_normal` 是否 `--force` 重生成
   waist-up（当前循环缝 mean 19.90 FAIL）；③ 是否做 alpha 包围盒归一化（≈半天）。
3. **剩余素材队列（4 条）**：**`talking_low`（本轮新增，§4.8）** → `emo_puzzled`（§4.5）
   → `idle_offline`（§4.6）→ `emo_sad`（§4.7）。
4. **板端口径**：`ui_state.schema.json` 的 `schema_version` 仍 `1.0`（加性、向后兼容），
   但 LVGL 侧需同步"10 态"清单 —— 已写入 `docs/ui_consistency_checklist.md` 的 V2.1 与 M1/M9 行。

---

## 七、情绪节点口径拆分：表达性 6 + 系统·故障 4（2026-09-12 追加 · **纯文档**）

**决策**：此前「情绪节点 ≡ `RuntimeState` 全量」的口径把「摄像头丢失 / 网络丢失 / 已取消 / 错误」
也当作"情绪"讨论与评审，口径含糊。经与需求方确认，采用**零风险方案**：**只在文档层分组，代码/合同/单测不动**。

| 组 | 数量 | 节点 | 验收标准 |
|---|---|---|---|
| ① **表达性节点** | **6** | IDLE 待机 / PRESENT 探头·注视 / LISTENING 倾听 / THINKING 思考 / SPEAKING 说话·**高涨** / SPEAKING_LOW 说话·**低落** | **逐条**目检：动作与表情是否达预期（需专门生成素材） |
| ② **系统·故障态** | **4** | CAMERA_LOST 摄像头丢失 / NETWORK_LOST 网络丢失（本地模式） / CANCELLED 已取消 / ERROR 错误 | **不白屏 + 语义正确**（允许复用兜底或"降级表演"） |

**红线（逐项核对过，全部零改动）**：`board/runtime/fsm.py`（`RuntimeState` 成员与转换表）、
`ui_spec/ui_state.schema.json`（`runtime_state.enum`）、`board/ui/avatar_assets.py`（`STATE_ASSET` /
`FALLBACK_BY_STATE` / `fallback_chain`）、`board/ui/avatar_fsm.py`（`AVATAR_MAP`）、`tests/*`（单测）
—— `pytest` 仍 **205 passed**，`--all-states` 仍出 **10 张**板图。

**文档落点（4 处口径统一）**：

| # | 文件 | 改动 |
|---|---|---|
| 1 | `docs/玩偶素材Seedance提示词包_技术记录.md` | §3 拆为 **3.1 表达性节点（6）/ 3.2 系统·故障态（4）**，加"中文"列；新增 **§12** 记录口径、理由与"§10 复核记录按新口径如何理解" |
| 2 | `assets/avatar/README.md` | §二 拆为 **2.1 / 2.2** 两张表，加"中文"列（待机 / 探头·注视 / 倾听 / …） |
| 3 | `docs/ui_consistency_checklist.md` | V2.1 变更块增补分组口径，**明示"仅为文档口径、非代码变更"** |
| 4 | `docs/素材排队应对方案.md` | 头部现状块加一行交叉引用 |

**取舍说明（为什么"只拆不删"）**：`CANCELLED` 是**瞬时态**（FSM 依赖它做自动回迁）、
`CAMERA_LOST / NETWORK_LOST / ERROR` 由人2/人3 事件直接驱动、已被板端三区实现与单测消费；
删除等于改数据合同并波及 10+ 处文档与板端实现，而"分组"已完全满足
「清单可枚举、验收可判定、评审不串味」三个诉求 —— 故取零风险路线。


