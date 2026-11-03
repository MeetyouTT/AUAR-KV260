# -*- coding: utf-8 -*-
"""玩偶状态 → 表现映射（Week A2 · 9/9；2026-10-04 补齐到 **15 态**）

纯逻辑层（无渲染依赖）：将 RuntimeState 映射为玩偶表现规格，
PySide6 原型与板端 LVGL 版均复用本映射，保证"状态→表现"一致。

**本表必须与 `board/runtime/fsm.RuntimeState`（15 态）逐一对齐** —— 少了任何一个，
`avatar_spec()` 就会**静默回退 IDLE**、UI 标签显示成"待机"
（2026-10-04 外部审查实测：`SPEAKING_NEUTRAL` / `PUZZLED` / `ACK_NOD` / `DENY_SHAKE` / `AWAKE` 五个状态标签回落）。
**契约校验见 `tools/verify_state_contract.py`（改动/接手前先跑）**。

播报分三档（v2）：`SPEAKING` 高情绪 / **`SPEAKING_NEUTRAL` 中性（默认档）** / `SPEAKING_LOW` 低落。

`animation` / `expression` 只用于 **B2V 矢量回退路径**（素材缺失时才走）；有帧序列素材时以素材为准。
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


# **15 态** → 表现（RuntimeState 名称即 UiState.runtime_state 的枚举值；与 `fsm.RuntimeState` 一一对应）
AVATAR_MAP = {
    "IDLE": AvatarSpec("breath", "neutral", "待机", "accent"),
    "PRESENT": AvatarSpec("attention", "curious", "注视", "accent"),
    "LISTENING": AvatarSpec("listen", "attentive", "聆听", "accent"),
    "THINKING": AvatarSpec("think", "thinking", "思考", "accent"),
    "SPEAKING": AvatarSpec("speak", "happy", "播报", "accent"),
    # v2 新增：中性播报（**默认档**，命中率最高）
    "SPEAKING_NEUTRAL": AvatarSpec("speak", "neutral", "播报·中性", "accent"),
    "SPEAKING_LOW": AvatarSpec("speak", "sad", "播报·低落", "accent"),
    # v2 新增：唤醒反应（burst，一次性动作）
    "AWAKE": AvatarSpec("attention", "curious", "唤醒", "accent"),
    # v2 新增：困惑（从 CAMERA_LOST 解绑，语义归位）
    "PUZZLED": AvatarSpec("think", "thinking", "困惑", "accent"),
    # v2 新增：点头确认 / 摇头拒绝（均 burst，一次性动作）
    "ACK_NOD": AvatarSpec("attention", "happy", "确认", "accent"),
    "DENY_SHAKE": AvatarSpec("attention", "sad", "拒绝", "accent"),
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
