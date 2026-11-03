# -*- coding: utf-8 -*-
"""运行时状态机（Week A1 · 9/3 任务）

状态（人3 任务书 §五 + 2026-09-12 情绪分档 + v2 状态系统重设计）：
  IDLE、PRESENT、LISTENING、THINKING、
  SPEAKING、SPEAKING_NEUTRAL、SPEAKING_LOW、
  AWAKE、PUZZLED、ACK_NOD、DENY_SHAKE、
  CAMERA_LOST、NETWORK_LOST、CANCELLED、ERROR

播报（原 SPEAKING）按回复情绪分三档（v2：在"高/低"之间补上中性档）：
  SPEAKING         情绪高涨 → 素材 `talking_normal`
  SPEAKING_NEUTRAL 中性播报 → 素材 `talking_neutral`（默认档，命中率最高）
  SPEAKING_LOW     情绪低落 → 素材 `talking_low`

一次性动作（v2 新增，播放语义为 burst，见 avatar_assets.BURST_STATES）：
  AWAKE    KWS 唤醒反应（emo_surprised）
  ACK_NOD  命令执行成功的确认点头（ack_nod）

设计：
  事件驱动：handle_event(EventEnvelope) -> Optional[StateChange]
  转换表显式注册；非法转换被拒绝并记录（不抛致命异常）
  CANCELLED 为瞬时状态：进入后自动回迁到 IDLE 或 PRESENT（取决于是否有人在）
  每次状态变更发布 fsm.state_changed 事件到 EventBus

确定性：相同事件序列必得相同状态序列（纯函数 + 显式状态）。
"""
import enum
import typing

from . import avatar_actions
from .event_bus import EventEnvelope
from .events import EventType


class RuntimeState(enum.Enum):
    IDLE = "IDLE"                 # 空闲：无人、无对话
    PRESENT = "PRESENT"           # 有人在（person enter / current target）
    LISTENING = "LISTENING"       # 聆听：VAD/按键录音
    THINKING = "THINKING"         # 思考：ASR 完成，等待回复
    SPEAKING = "SPEAKING"         # 播报·情绪高涨：emotion 命中 HIGH_EMOTIONS
    SPEAKING_NEUTRAL = "SPEAKING_NEUTRAL"  # 播报·中性：emotion 未命中高/低档（v2 新增）
    SPEAKING_LOW = "SPEAKING_LOW"  # 播报·情绪低落：emotion 命中 LOW_EMOTIONS
    AWAKE = "AWAKE"               # 唤醒反应：KWS 命中（一次性 burst，v2 新增）
    PUZZLED = "PUZZLED"           # 困惑不解（从 CAMERA_LOST 解绑、语义归位，v2 新增）
    ACK_NOD = "ACK_NOD"           # 确认点头：命令执行成功（一次性 burst，v2 新增）
    DENY_SHAKE = "DENY_SHAKE"     # 否定摇头：拒绝/不同意（一次性 burst，P1-1 新增）
    CAMERA_LOST = "CAMERA_LOST"   # 摄像头丢失（视觉素材改用 idle_offline）
    NETWORK_LOST = "NETWORK_LOST"  # LAN 断链（本地模式）
    CANCELLED = "CANCELLED"       # 取消（瞬时态）
    ERROR = "ERROR"               # 不可恢复错误

    @property
    def label(self) -> str:
        return self.value


# --------------------------------------------------------------------------- #
# 播报情绪分档（SPEAKING / SPEAKING_NEUTRAL / SPEAKING_LOW）
#
# 依据：`schemas/dialogue_response.schema.json` 的 `emotion` 字段（LAN 主机 LLM 给出，
# 由 policy_validator 按 `allowed_emotions` 白名单校验）。
# v2 把 v1 的"低落 / 非低落"二分改成三档矩阵（原二分的问题：任何没写进低落表的词，
# 包括"neutral / 平静 / 困惑"都会被当成"情绪高涨"去播 talking_normal，动作幅度过火）：
#   命中 LOW_EMOTIONS  → SPEAKING_LOW     → talking_low
#   命中 HIGH_EMOTIONS → SPEAKING         → talking_normal
#   其余（含 neutral） → SPEAKING_NEUTRAL → talking_neutral  ← **默认档**
# 中英双写：emotion 允许中文标签（schema maxLength=32），两种都要认。
# --------------------------------------------------------------------------- #
LOW_EMOTIONS: typing.FrozenSet[str] = frozenset({
    "sad", "low", "down", "depressed", "gloomy", "apologetic", "sorry", "tired",
    "低落", "沮丧", "难过", "伤心", "抱歉", "疲惫",
})

HIGH_EMOTIONS: typing.FrozenSet[str] = frozenset({
    "happy", "joy", "joyful", "excited", "cheerful", "glad", "delighted",
    "enthusiastic", "proud", "surprised", "amused", "playful",
    "开心", "高兴", "兴奋", "愉快", "自豪", "惊喜", "热情",
})

# 默认档：既不高、也不低的一律走中性播报（保守档，动作幅度最小、最不容易违和）
DEFAULT_SPEAKING_STATE = "SPEAKING_NEUTRAL"


def is_low_emotion(emotion: typing.Any) -> bool:
    """情绪标签是否属"低落"档（去空白 + 小写归一；非字符串一律 False）。"""
    if not isinstance(emotion, str):
        return False
    return emotion.strip().lower() in LOW_EMOTIONS


def is_high_emotion(emotion: typing.Any) -> bool:
    """情绪标签是否属"高涨"档（归一规则同 is_low_emotion）。"""
    if not isinstance(emotion, str):
        return False
    return emotion.strip().lower() in HIGH_EMOTIONS


def speaking_state_name(emotion: typing.Any) -> str:
    """回复情绪 → 播报档位名（三档；非字符串/未命中一律返回中性档）。

    返回的是 `RuntimeState` 的**名字**（字符串），避免本纯逻辑模块依赖调用方
    如何构造枚举成员；`SPEAKING` 与 `SPEAKING_LOW` 仍由 `is_low/high_emotion`
    兼容保留。见状态系统重设计 §3「三层触发路由」第 1 层。
    """
    if is_low_emotion(emotion):
        return "SPEAKING_LOW"
    if is_high_emotion(emotion):
        return "SPEAKING"
    return DEFAULT_SPEAKING_STATE


class StateChange:
    """一次状态变更的结果。"""

    __slots__ = ("from_state", "to_state", "trigger_event_type", "is_auto")

    def __init__(self, from_state: RuntimeState, to_state: RuntimeState,
                 trigger_event_type: str, is_auto: bool = False) -> None:
        self.from_state = from_state
        self.to_state = to_state
        self.trigger_event_type = trigger_event_type
        self.is_auto = is_auto

    def to_dict(self) -> typing.Dict:
        return {
            "from": self.from_state.label,
            "to": self.to_state.label,
            "trigger": self.trigger_event_type,
            "auto": self.is_auto,
        }

    def __repr__(self) -> str:  # pragma: no cover
        return "<StateChange %s -> %s @%s%s>" % (
            self.from_state.label, self.to_state.label,
            self.trigger_event_type, " [auto]" if self.is_auto else "")


class InvalidTransition(Exception):
    """非法状态转换（记录而非崩溃，由上层决定降级策略）。"""

    def __init__(self, state: RuntimeState, event_type: str) -> None:
        self.state = state
        self.event_type = event_type
        super().__init__("非法转换: %s + %s" % (state.label, event_type))


class RuntimeFSM:
    """运行时状态机。

    使用：
      fsm = RuntimeFSM()
      change = fsm.handle_event(env)   # 返回 StateChange 或 None
      fsm.state                          # 当前状态
    """

    _ANY = "*"  # 通配事件类型（异常/恢复类转换用）

    def __init__(self, bus: typing.Optional["EventBus"] = None,
                 publish_state_changes: bool = True) -> None:
        self._state = RuntimeState.IDLE
        self._bus = bus
        self._publish_changes = publish_state_changes
        self._has_presence = False
        self._prev_normal_state = RuntimeState.IDLE  # 断链/丢失前状态，用于恢复
        self._transitions = {}
        self._guards = {}  # {(from, event): callable() -> bool}
        self._rejected = 0
        self._history = []  # 最近状态变更（诊断/证据）
        self._subscription = None
        self._register_defaults()
        if bus is not None:
            self.bind_bus(bus)

    def bind_bus(self, bus: "EventBus") -> "RuntimeFSM":
        """订阅 EventBus 中 FSM 关心的事件，自动驱动状态转换。

        只订阅转换表里出现的事件类型（含通配 *_ANY 的全部事件），
        避免无关事件造成 rejected 噪声。
        """
        self._bus = bus
        interested = set(et for (_s, et) in self._transitions if et != self._ANY)
        # 通配事件（*_ANY）需要订阅全部事件
        if any(et == self._ANY for (_s, et) in self._transitions):
            interested = None  # 全部
        self._subscription = bus.subscribe(self._on_event, interested)
        return self

    def unbind_bus(self) -> None:
        if self._subscription is not None:
            self._subscription.unsubscribe()
            self._subscription = None

    def _on_event(self, envelope: EventEnvelope) -> None:
        if envelope.event_type == EventType.FSM_STATE_CHANGED:
            return  # 防自触发（状态变更事件不回灌给 FSM）
        self.handle_event(envelope)

    # ------------------------------------------------------------------ #
    # 属性
    # ------------------------------------------------------------------ #
    @property
    def state(self) -> RuntimeState:
        return self._state

    @property
    def has_presence(self) -> bool:
        return self._has_presence

    @property
    def rejected_count(self) -> int:
        return self._rejected

    def history(self, limit: int = 20) -> typing.List[typing.Dict]:
        return list(self._history[-limit:])

    # ------------------------------------------------------------------ #
    # 注册
    # ------------------------------------------------------------------ #
    def add_transition(self, from_state: RuntimeState, event_type: str,
                       to_state: RuntimeState,
                       guard: typing.Optional[typing.Callable[[EventEnvelope], bool]] = None) -> None:
        self._transitions[(from_state, event_type)] = to_state
        if guard is not None:
            self._guards[(from_state, event_type)] = guard

    def _add_any(self, event_type: str, to_state: RuntimeState) -> None:
        """任何状态遇指定事件 → to_state（异常恢复类）。"""
        for s in RuntimeState:
            self._transitions[(s, event_type)] = to_state

    # ------------------------------------------------------------------ #
    # 默认转换表（人3 任务书 §五 + 主计划 §7.3 玩偶状态一致性）
    # ------------------------------------------------------------------ #
    def _register_defaults(self) -> None:
        T = self._transitions
        S = RuntimeState

        # 在场/离场
        T[(S.IDLE, EventType.SCENE_PERSON_ENTER)] = S.PRESENT
        T[(S.IDLE, EventType.SCENE_TARGET_UPDATE)] = S.PRESENT
        T[(S.PRESENT, EventType.SCENE_PERSON_EXIT)] = S.IDLE

        # 唤醒 → 反应（v2：先播 AWAKE 一次性反应）
        # ⚠ 2026-10-04 修正（外部审查 #1）：原来 `AWAKE + AUDIO_VAD_END → LISTENING` 会**吃掉"说完"**，
        # 于是真实语音里"唤醒 → 一次句尾 → 收到回复"会停在**聆听**、**回复事件被拒**
        # （要连发两次句尾才进思考）。正确语义：
        #   · `AWAKE + AUDIO_VAD_END`          → **THINKING**（用户已经说完，直接进思考）；
        #   · `AWAKE + AUDIO_PLAYBACK_STOP`    → **LISTENING**（唤醒反应播完 → 开始聆听，这才是"聆听"的正规入口）；
        #   · `AWAKE + DIALOGUE_RESPONSE_RECEIVED` → 播报（快路径兜底：回复早于反应播完）。
        T[(S.IDLE, EventType.AUDIO_KWS_DETECTED)] = S.AWAKE
        T[(S.PRESENT, EventType.AUDIO_KWS_DETECTED)] = S.AWAKE
        T[(S.AWAKE, EventType.AUDIO_VAD_END)] = S.THINKING
        T[(S.AWAKE, EventType.AUDIO_PLAYBACK_STOP)] = S.LISTENING
        T[(S.AWAKE, EventType.DIALOGUE_RESPONSE_RECEIVED)] = S.SPEAKING
        T[(S.AWAKE, EventType.AUDIO_KWS_DETECTED)] = S.LISTENING
        T[(S.AWAKE, EventType.DIALOGUE_TIMEOUT)] = S.LISTENING
        # 实体按键不播反应（用户手上已在操作，反应动画只会显得卡顿）→ 直接聆听
        T[(S.IDLE, EventType.BOARD_KEY_PRESSED)] = S.LISTENING
        T[(S.PRESENT, EventType.BOARD_KEY_PRESSED)] = S.LISTENING

        # 聆听 → 思考 / 超时
        T[(S.LISTENING, EventType.AUDIO_VAD_END)] = S.THINKING
        # ⚠ 2026-10-04 新增（外部审查 #1 兜底）：聆听中**直接收到回复**（快路径 / VAD 事件缺失）
        # 也应当进播报 —— 否则任何时序偏差都会把玩偶**卡在聆听**（实测：回复被拒，画面停在聆听）。
        T[(S.LISTENING, EventType.DIALOGUE_RESPONSE_RECEIVED)] = S.SPEAKING
        T[(S.LISTENING, EventType.DIALOGUE_TIMEOUT)] = S.IDLE
        T[(S.LISTENING, EventType.DIALOGUE_ERROR)] = S.IDLE

        # 思考 → 播报 / 失败
        T[(S.THINKING, EventType.DIALOGUE_RESPONSE_RECEIVED)] = S.SPEAKING
        T[(S.THINKING, EventType.DIALOGUE_TIMEOUT)] = S.IDLE
        T[(S.THINKING, EventType.DIALOGUE_ERROR)] = S.IDLE

        # Validated stream cues can arrive during an already audible answer.
        for speaking in (S.SPEAKING, S.SPEAKING_NEUTRAL, S.SPEAKING_LOW):
            T[(speaking, EventType.DIALOGUE_RESPONSE_RECEIVED)] = S.SPEAKING

        # 播报结束（三档共用同一事件）
        T[(S.SPEAKING, EventType.AUDIO_PLAYBACK_STOP)] = S.IDLE
        T[(S.SPEAKING_NEUTRAL, EventType.AUDIO_PLAYBACK_STOP)] = S.IDLE
        T[(S.SPEAKING_LOW, EventType.AUDIO_PLAYBACK_STOP)] = S.IDLE

        # 一次性动作（v2）收尾：ACK_NOD / PUZZLED 由 burst 素材播完或超时回迁空闲
        T[(S.ACK_NOD, EventType.AUDIO_PLAYBACK_STOP)] = S.IDLE
        T[(S.ACK_NOD, EventType.DIALOGUE_TIMEOUT)] = S.IDLE
        T[(S.PUZZLED, EventType.AUDIO_PLAYBACK_STOP)] = S.IDLE
        T[(S.PUZZLED, EventType.DIALOGUE_TIMEOUT)] = S.IDLE
        # P1-1：否定摇头（burst）收尾与 ACK_NOD 同规格
        T[(S.DENY_SHAKE, EventType.AUDIO_PLAYBACK_STOP)] = S.IDLE
        T[(S.DENY_SHAKE, EventType.DIALOGUE_TIMEOUT)] = S.IDLE

        # P0-1（方案 §4.1）解耦「一次性动作」与「说话」：动作段播完**不直接回 IDLE**，
        # 而是接进按 emotion 分档的播报档，直到 AUDIO_PLAYBACK_STOP（"语音还在就继续演"）。
        # 触发事件复用合同里早已存在、此前从未被使用的 AUDIO_PLAYBACK_START（语义 = 播报开始），
        # 因此**不新增事件类型**；目标档位再由 `_route_emotion` 按 payload.emotion 分档。
        for _s in (S.ACK_NOD, S.AWAKE, S.PUZZLED, S.DENY_SHAKE):
            T[(_s, EventType.AUDIO_PLAYBACK_START)] = S.SPEAKING

        # 取消（进入瞬时 CANCELLED，再自动回迁）
        for s in (S.LISTENING, S.THINKING, S.SPEAKING, S.SPEAKING_NEUTRAL,
                  S.SPEAKING_LOW, S.AWAKE, S.ACK_NOD, S.PUZZLED, S.DENY_SHAKE):
            T[(s, EventType.AUDIO_CANCEL_REQUESTED)] = S.CANCELLED
            T[(s, EventType.BOARD_KEY_PRESSED)] = S.CANCELLED  # 实体取消键

        # 摄像头丢失/恢复
        self._add_any(EventType.CAMERA_LOST, S.CAMERA_LOST)
        T[(S.CAMERA_LOST, EventType.CAMERA_RECOVERED)] = S.IDLE

        # 网络断链/恢复（NETWORK_LOST 覆盖正常对话态）
        self._add_any(EventType.DIALOGUE_NETWORK_LOST, S.NETWORK_LOST)
        # 网络恢复：任意状态均可回到正常模式（含本地聆听中被恢复）
        self._add_any(EventType.DIALOGUE_NETWORK_RESTORED, S.IDLE)
        # NETWORK_LOST 下本地 KWS 可继续（本地模式）
        T[(S.NETWORK_LOST, EventType.AUDIO_KWS_DETECTED)] = S.LISTENING

        # 崩溃/健康恢复
        self._add_any(EventType.SYSTEM_WORKER_CRASH, S.ERROR)
        T[(S.ERROR, EventType.SYSTEM_HEALTH_OK)] = S.IDLE

        # CANCELLED 瞬时：按是否有人在回迁
        self.add_transition(S.CANCELLED, self._ANY, S.PRESENT,
                            guard=lambda _e: self._has_presence)
        self.add_transition(S.CANCELLED, self._ANY, S.IDLE,
                            guard=lambda _e: not self._has_presence)


    # ------------------------------------------------------------------ #
    # 核心：处理事件
    # ------------------------------------------------------------------ #
    def handle_event(self, envelope: EventEnvelope) -> typing.Optional[StateChange]:
        """处理一个事件，返回状态变更（无变更返回 None）。"""

        # 维护在场记忆
        if envelope.event_type == EventType.SCENE_PERSON_ENTER:
            self._has_presence = True
        elif envelope.event_type == EventType.SCENE_PERSON_EXIT:
            self._has_presence = False

        current = self._state
        target = self._transitions.get((current, envelope.event_type))
        if target is None:
            target = self._transitions.get((current, self._ANY))

        if target is None:
            self._rejected += 1
            return None  # 非法/未定义转换：记录不崩溃

        # guard 检查
        guard = self._guards.get((current, envelope.event_type)) or self._guards.get((current, self._ANY))
        if guard is not None and not guard(envelope):
            self._rejected += 1
            return None

        if target is current:
            return None  # 自环，不产生变更

        # 播报情绪分档：同一事件两档目标（见 _route_emotion）
        target = self._route_emotion(envelope, target)

        change = self._apply_change(current, target, envelope.event_type, auto=False)

        # CANCELLED 瞬时态：立即自动回迁
        if target == RuntimeState.CANCELLED:
            self._auto_resume_from_cancelled()
        return change

    def _route_emotion(self, envelope: EventEnvelope,
                       target: RuntimeState) -> RuntimeState:
        """播报分档路由（v2 三档）：emotion → SPEAKING / SPEAKING_NEUTRAL / SPEAKING_LOW。

        设计取舍：转换表按 (状态, 事件) 键控，同一事件无法注册两个目标，
        故采用"目标后置路由"而不是新增事件类型 —— **事件合同（主机/人2 侧）零改动**，
        只把 `dialogue_response.schema.json` 里早已存在的 `emotion` 字段用起来。

        v2 变化：v1 只在"低 / 非低"之间二分，于是 neutral / 平静 / 困惑 这类词都会落到
        "高情绪"档去播 talking_normal（幅度过火、与语义不符）；现在未命中高/低表的
        一律走**中性档**（保守默认），判定见 fsm.speaking_state_name。
        """
        if target is not RuntimeState.SPEAKING:
            return target
        payload = envelope.payload if isinstance(envelope.payload, dict) else {}
        if envelope.event_type == EventType.AUDIO_PLAYBACK_START:
            # P0-1：一次性动作播完 → 接进播报段（按 emotion 分档），直到语音播完
            return RuntimeState[speaking_state_name(payload.get("emotion"))]
        if envelope.event_type != EventType.DIALOGUE_RESPONSE_RECEIVED:
            return target
        # 第 3 层触发路由：`avatar_action` 通道（响应协议里早已存在的字段，
        # v2 才接到播放层）。取值集合**单一来源** = board/runtime/avatar_actions.py，
        # 白名单 / mock / fsm 三处不再各写一份字面量（方案 §4.1 P0-4 一致性收口）；
        # 名单内但板端尚无对应状态的动作按「未知动作」忽略，其余取值一律忽略
        action = payload.get("avatar_action")
        state_name = avatar_actions.state_for(action)
        if state_name is not None:
            state = RuntimeState.__members__.get(state_name)
            if state is not None:
                return state
            # 白名单内但板端还没有该状态（如 deny_shake，待 P1-1 补素材与状态）→
            # 不落状态，等价于原「未知动作不改状态」的脏数据保护。
        return RuntimeState[speaking_state_name(payload.get("emotion"))]

    def _apply_change(self, from_state: RuntimeState, to_state: RuntimeState,
                      trigger: str, auto: bool) -> StateChange:
        self._state = to_state
        change = StateChange(from_state, to_state, trigger, auto)
        self._history.append(change.to_dict())
        if self._bus is not None and self._publish_changes:
            self._bus.publish(EventEnvelope(
                event_type=EventType.FSM_STATE_CHANGED,
                source="fsm",
                created_at_ms=self._now_ms(),
                payload=change.to_dict(),
            ))
        return change

    def _auto_resume_from_cancelled(self) -> None:
        resume = RuntimeState.PRESENT if self._has_presence else RuntimeState.IDLE
        self._apply_change(RuntimeState.CANCELLED, resume, "auto", auto=True)

    def _now_ms(self) -> int:
        if self._bus is not None:
            return self._bus._now_ms()
        import time
        return int(time.time() * 1000)

    # ------------------------------------------------------------------ #
    # 强制状态（启动/恢复时用，产生 state_changed 事件）
    # ------------------------------------------------------------------ #
    def reset(self, state: RuntimeState = RuntimeState.IDLE) -> StateChange:
        old = self._state
        self._has_presence = False
        return self._apply_change(old, state, "reset", auto=True)
