# -*- coding: utf-8 -*-
"""玩偶状态 → 表现映射（Week A2 · 9/9）

纯逻辑层（无渲染依赖）：将 RuntimeState（10 态）映射为玩偶表现规格，
PySide6 原型与板端 LVGL 版均复用本映射，保证"状态→表现"一致。

播报分两档（2026-09-12 情绪分档扩展）：
  SPEAKING      情绪高涨 → 素材 `talking_normal`，表情 happy
  SPEAKING_LOW  情绪低落 → 素材 `talking_low`，表情 sad（复用既有 sad 几何参数）
"""
import typing
from dataclasses import dataclass


@dataclass(frozen=True)
class AvatarSpec:
    """一个运行时状态对应的玩偶表现。

    animation   动画标识：breath/attention/listen/think/speak/static
                （参数见 ui/ui_tokens.json -> animations）
    expression  表情：neutral/curious/attentive/thinking/happy/sad
    label       状态文字（显示在玩偶区）
    token_key   主题色令牌键（colors 中的键）
    """
    animation: str
    expression: str
    label: str
    token_key: str = "accent"


# 10 态 → 表现（RuntimeState 名称即 UiState.runtime_state 枚举值）
AVATAR_MAP = {
    "IDLE": AvatarSpec("breath", "neutral", "待机", "accent"),
    "PRESENT": AvatarSpec("attention", "curious", "注视", "accent"),
    "LISTENING": AvatarSpec("listen", "attentive", "聆听", "accent"),
    "THINKING": AvatarSpec("think", "thinking", "思考", "accent"),
    "SPEAKING": AvatarSpec("speak", "happy", "播报", "accent"),
    "SPEAKING_LOW": AvatarSpec("speak", "sad", "播报·低落", "accent"),
    "CAMERA_LOST": AvatarSpec("static", "neutral", "摄像头丢失", "warning"),
    "NETWORK_LOST": AvatarSpec("breath", "neutral", "本地模式", "warning"),
    "CANCELLED": AvatarSpec("breath", "neutral", "已取消", "warning"),
    "ERROR": AvatarSpec("static", "sad", "错误", "error"),
}

# 表情描述（渲染后端参考；保持简单几何绘制）
EXPRESSION_EYES = {
    "neutral": {"eye_dx": 0.16, "eye_dy": -0.05, "eye_r": 0.055, "mouth": "line"},
    "curious": {"eye_dx": 0.16, "eye_dy": -0.06, "eye_r": 0.062, "mouth": "o"},
    "attentive": {"eye_dx": 0.16, "eye_dy": -0.07, "eye_r": 0.060, "mouth": "line"},
    "thinking": {"eye_dx": 0.16, "eye_dy": -0.05, "eye_r": 0.050, "mouth": "line", "look": "up_right"},
    "happy": {"eye_dx": 0.16, "eye_dy": -0.05, "eye_r": 0.058, "mouth": "arc_up"},
    "sad": {"eye_dx": 0.16, "eye_dy": -0.02, "eye_r": 0.052, "mouth": "arc_down"},
}


def avatar_spec(runtime_state: str) -> AvatarSpec:
    """运行时状态 → 玩偶表现（未知状态回退 IDLE）。"""
    return AVATAR_MAP.get(runtime_state, AVATAR_MAP["IDLE"])


def expression_spec(expression: str) -> typing.Dict:
    """表情 → 几何参数（眼睛/嘴），渲染后端使用。"""
    return EXPRESSION_EYES.get(expression, EXPRESSION_EYES["neutral"])


def all_states() -> typing.List[str]:
    return list(AVATAR_MAP.keys())


# --------------------------------------------------------------------------- #
# 方案 C · 映射层：动画帧表（动画名 → 关键帧序列）
#
# 每个关键帧为 (通道, 值)：
#   ("eye", v)    → v 为闭眼程度 0.0(睁) ~ 1.0(闭)
#   ("look_dx", v)→ v 为归一化视线偏移 -1.0(左) ~ 1.0(右)
#   ("scale", v)  → 缩放系数（预留）
# 统一引擎按 UiState.avatar_anim 下发动画名 + 参数（周期/强度）播放帧表。
# TODO(新方案)：帧表可扩展为 sprite 帧名（"eye_open"/"eye_blink"/...）。
# --------------------------------------------------------------------------- #
ANIMATION_FRAMES = {
    "blink": [("eye", 0.0), ("eye", 1.0), ("eye", 0.0)],     # 眨眼：睁→闭→睁
    "look": [("look_dx", -1.0), ("look_dx", 1.0)],            # 左右扫视
    "breathe": [("scale", 1.02)],                             # 呼吸（预留）
    "speak": [("eye", 0.0), ("mouth", 0.6)],                  # 播报（嘴张，预留通道）
}


def animation_frames(name: str) -> typing.List[typing.Tuple[str, float]]:
    """按动画名查帧表（未定义回退空表）。"""
    return list(ANIMATION_FRAMES.get(name, []))
