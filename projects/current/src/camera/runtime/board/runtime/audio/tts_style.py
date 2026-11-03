# -*- coding: utf-8 -*-
"""TTS 语气层：LLM 的 `emotion` → 逐句韵律（SSML）—— 纯逻辑、无依赖、可单测。

为什么有这个模块
----------------
LAN 主机的 LLM 在 `DialogueResponse.emotion` 里已经给出本句情绪（白名单由请求侧
`allowed_emotions` 注入、板端 `policy_validator` 再校验一次）。这条通道此前只被
**玩偶表演**消费（`fsm.speaking_state_name` → 播报三档素材），TTS 语音侧一直是
**恒定语气**（SAPI 固定 Rate/Volume）。本模块补上"最后一跳"：
emotion → 语速/音高/音量/停顿，并以 SSML 交给后端播报。

单一来源（红线）
----------------
分档词表**不在这里重复定义**：直接复用 `board.runtime.fsm.speaking_state_name()`，
把 `SPEAKING / SPEAKING_NEUTRAL / SPEAKING_LOW` 三个档位翻译成韵律。因此
"玩偶演哪条素材"与"语音用什么语气"**永远同档**，不会出现第二套口径。

能力边界（务必知晓）
--------------------
- 现役后端 SAPI 是**拼接式**语音：`pitch` 变调偏生硬 → 本表音高最多偏离 1 档，
  主力手段是**语速 + 停顿**。要"自然的音高起伏"须先换神经 TTS（D5 §14.4 / W12-04 的
  VITS / Kokoro 候选），届时只需改本表取值语义（或新增字段），**调用方一行不动**。
- 只用 SSML **关键字**（x-slow..x-fast / x-low..x-high / x-soft..x-loud），不写
  百分比或 Hz —— 关键字是 SAPI 与 W3C 都保证支持的写法，避免整段 SSML 解析失败。
- 一行回退：`TtsPlayer.speak_async(text)` 不传 `style` 即恢复"恒定语气"旧行为；
  另有 `ENABLE_PITCH=False` 可整体关掉音高（只留语速 + 停顿）。
"""
from __future__ import annotations

import dataclasses
import typing
from xml.sax.saxutils import escape as xml_escape

#: 音高/语速/音量档位（从低到高）。只用关键字，见模块头"能力边界"。
PITCH_STEPS: typing.Tuple[str, ...] = ("x-low", "low", "medium", "high", "x-high")
RATE_STEPS: typing.Tuple[str, ...] = ("x-slow", "slow", "medium", "fast", "x-fast")
VOLUME_STEPS: typing.Tuple[str, ...] = ("x-soft", "soft", "medium", "loud", "x-loud")

#: 相对 `medium` 允许的最大偏离档数（拼接式语音的安全边界）。
PITCH_MAX_STEP: int = 1
RATE_MAX_STEP: int = 2
VOLUME_MAX_STEP: int = 2
#: 置 False → 音高一律 medium（"变调生硬"时的一键降级）。
ENABLE_PITCH: bool = True

#: 段间停顿的夹取范围（毫秒）。
BREAK_MS_MIN: int = 0
BREAK_MS_MAX: int = 2000

SSML_HEAD = ('<speak version="1.0" '
             'xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="zh-CN">')
SSML_TAIL = "</speak>"

#: 断句标点：句末 / 句中（切段用，标点跟随前一段）。
_SENT_END = "。！？!?…"
_CLAUSE = "，,；;、：:"
#: 短于该字数的片段与相邻段合并（否则"碎句"听起来磕巴）。
_MIN_SEG = 6


@dataclasses.dataclass(frozen=True)
class TtsStyle:
    """一句话的韵律档（冻结值表；字段全是 SSML 关键字）。"""

    rate: str = "medium"      # 语速：x-slow / slow / medium / fast / x-fast
    pitch: str = "medium"     # 音高：x-low / low / medium / high / x-high
    volume: str = "medium"    # 音量：x-soft / soft / medium / loud / x-loud
    break_ms: int = 200       # 段间停顿（毫秒）
    label: str = "neutral"    # 档位名（日志 / HUD / 单测用）
    voice: str = ""           # 预留：S2 换神经引擎时按档换音色；空串 = 用 TtsConfig.voice

    def describe(self) -> str:
        """一行可读描述（日志用）。"""
        return "%s(rate=%s pitch=%s vol=%s brk=%dms)" % (
            self.label, self.rate, self.pitch, self.volume, self.break_ms)


#: 播报档位（= `fsm.speaking_state_name` 的返回值）→ 韵律。**三档与玩偶素材同源**。
TONE_BY_STATE: typing.Dict[str, TtsStyle] = {
    # 情绪高涨：略快、略高、略响、句间干脆
    "SPEAKING": TtsStyle("fast", "high", "loud", 110, "high"),
    # 中性（默认档，命中率最高）：不动
    "SPEAKING_NEUTRAL": TtsStyle("medium", "medium", "medium", 200, "neutral"),
    # 情绪低落：放慢、压低、放轻、句间多停
    "SPEAKING_LOW": TtsStyle("slow", "low", "soft", 330, "low"),
}
#: 未知 / 脏输入兜底档（保守默认，绝不抛异常）。
DEFAULT_STYLE: TtsStyle = TONE_BY_STATE["SPEAKING_NEUTRAL"]


def _clamp_keyword(value: typing.Any, steps: typing.Tuple[str, ...],
                   max_step: int, fallback: str = "medium") -> str:
    """把任意取值收敛到关键字档位，并限制相对 `medium` 的最大偏离档数。"""
    key = str(value or "").strip().lower()
    if key not in steps:
        return fallback
    mid = steps.index("medium")
    lo, hi = max(0, mid - max_step), min(len(steps) - 1, mid + max_step)
    return steps[min(max(steps.index(key), lo), hi)]


def clamp_style(style: TtsStyle) -> TtsStyle:
    """限幅：非法/越界关键字回落 `medium`，音高最多 ±`PITCH_MAX_STEP` 档，停顿夹取。"""
    pitch = "medium" if not ENABLE_PITCH else _clamp_keyword(
        style.pitch, PITCH_STEPS, PITCH_MAX_STEP)
    try:
        break_ms = int(style.break_ms)
    except (TypeError, ValueError):
        break_ms = DEFAULT_STYLE.break_ms
    return dataclasses.replace(
        style,
        rate=_clamp_keyword(style.rate, RATE_STEPS, RATE_MAX_STEP),
        pitch=pitch,
        volume=_clamp_keyword(style.volume, VOLUME_STEPS, VOLUME_MAX_STEP),
        break_ms=max(BREAK_MS_MIN, min(break_ms, BREAK_MS_MAX)),
    )


def style_for_speaking_state(state_name: typing.Any) -> TtsStyle:
    """播报档位名 → 韵律（未知档位走默认中性档）。"""
    return clamp_style(TONE_BY_STATE.get(str(state_name or ""), DEFAULT_STYLE))


#: 韵律档位 → 语速乘子（**神经 TTS** 用：`speed = 基础 speed × 本乘子`）。
#: 与 SAPI 的关键字档一一对应，保证"同一 emotion 在两种引擎上语速同向"。
RATE_MULTIPLIER: typing.Dict[str, float] = {
    "x-slow": 0.80, "slow": 0.90, "medium": 1.00, "fast": 1.12, "x-fast": 1.25,
}


def rate_multiplier(style: typing.Any) -> float:
    """`TtsStyle`（或裸关键字）→ 语速乘子；未知 / 脏输入 → `1.0`。"""
    if isinstance(style, TtsStyle):
        return RATE_MULTIPLIER.get(clamp_style(style).rate, 1.0)
    return RATE_MULTIPLIER.get(str(style or "").strip().lower(), 1.0)


def for_emotion(emotion: typing.Any) -> TtsStyle:
    """LLM 的 `emotion` → 韵律。

    分档判定**委托** `fsm.speaking_state_name()`（延迟导入，避免与 `audio` 包初始化
    顺序纠缠），保证与"玩偶选哪条 `talking_*` 素材"永远同档；未知 / 非字符串 /
    空值一律走中性档。
    """
    from .. import fsm                       # 延迟导入：单一来源，且无循环依赖风险
    try:
        state_name = fsm.speaking_state_name(emotion)
    except Exception:                        # 脏输入不许把播报链路带崩
        return clamp_style(DEFAULT_STYLE)
    return style_for_speaking_state(state_name)


def _merge_short(segs: typing.List[str]) -> typing.List[str]:
    """把过短片段并入相邻段（避免"嗯，"单独成段造成磕巴感）。"""
    merged: typing.List[str] = []
    for seg in segs:
        if merged and len(merged[-1]) < _MIN_SEG:
            merged[-1] += seg
        else:
            merged.append(seg)
    if len(merged) > 1 and len(merged[-1]) < _MIN_SEG:      # 末段太短 → 并回上一段
        tail = merged.pop()                                 # 先取出再赋值：
        merged[-1] += tail                                  # 否则 pop 后 -2 下标越界
    return merged


def split_segments(text: typing.Any) -> typing.List[str]:
    """按标点切段（标点跟随前一段）—— 逐段套韵律才是"起伏"，整句一个参数是平推。"""
    s = str(text or "").strip()
    if not s:
        return []
    out: typing.List[str] = []
    buf = ""
    for ch in s:
        buf += ch
        if ch in _SENT_END or ch in _CLAUSE:
            out.append(buf)
            buf = ""
    if buf:
        out.append(buf)
    return _merge_short(out)


def build_ssml(text: typing.Any, style: TtsStyle) -> str:
    """把一段回复渲染成 SSML：**逐段** prosody + 段间 break。

    - 空文本 → 返回空串（调用方按"不播报"处理）；
    - 文本做 XML 转义（`&` `<` `>`），PowerShell 侧再转义单引号（见 `tts.py`）。
    """
    segs = split_segments(text)
    if not segs:
        return ""
    st = clamp_style(style)
    parts: typing.List[str] = [SSML_HEAD]
    last = len(segs) - 1
    for i, seg in enumerate(segs):
        parts.append('<prosody rate="%s" pitch="%s" volume="%s">%s</prosody>'
                     % (st.rate, st.pitch, st.volume, xml_escape(seg)))
        if i < last:
            parts.append('<break time="%dms"/>' % st.break_ms)
    parts.append(SSML_TAIL)
    return "".join(parts)
