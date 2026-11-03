# -*- coding: utf-8 -*-
"""avatar_assets —— 玩偶帧序列素材的路径规范与解析（纯逻辑，无 Qt/渲染依赖）。

素材来源：Seedance 绿幕视频 → 预抠像（透明 PNG 帧序列）。
目录规范：
    assets/avatar/<素材名>/000000.png     透明 PNG 帧序列（RGBA，按文件名排序 = 播放顺序）
    assets/avatar/<素材名>/meta.json      可选：{"fps": 24, "source": "...", "size": [w, h]}

运行时状态（UiState.runtime_state，14 态）与素材目录名通过 STATE_ASSET 映射；
某状态无素材时由渲染层回退到 B2V 矢量主体（见 qt_widgets.AvatarPanel._render_avatar）。
播放语义由 BURST_STATES 区分：名单内为**单次 burst**（末帧即停），其余为无限 loop。

本模块只做「路径/清单/元数据」解析，**不加载像素**；像素加载与缓存由渲染层负责，
因此可脱离 Qt 单测，板端 LVGL 版也可复用同一套路径规范。
"""
from __future__ import annotations

import json
import typing
from pathlib import Path

# 工程根目录：board/interaction/avatar_assets.py -> board/interaction -> board -> wujing-lite
_ROOT = Path(__file__).resolve().parents[2]
AVATAR_DIR = _ROOT / "assets" / "avatar"

# 帧序列文件扩展名（按名称排序即播放顺序）
FRAME_EXTS: typing.Tuple[str, ...] = (".png",)
# 缺省帧率（素材未提供 meta.json 时）
DEFAULT_FPS: float = 24.0

# 运行时状态（14 态）→ 素材目录名。
# 命名沿用「桌宠动作素材生成提示词（Seedance 完整版 v3）」，便于与素材生成规范对接。
# 播报分三档：SPEAKING 高情绪（talking_normal）/ SPEAKING_NEUTRAL 中性（talking_neutral）
# / SPEAKING_LOW 低落（talking_low）；AWAKE、ACK_NOD 为一次性动作（BURST_STATES）。
STATE_ASSET: typing.Dict[str, str] = {
    "IDLE": "idle_normal",
    "PRESENT": "idle_present",
    "LISTENING": "idle_listening",
    "THINKING": "idle_thinking",
    "SPEAKING": "talking_normal",
    "SPEAKING_LOW": "talking_low",
    "SPEAKING_NEUTRAL": "talking_neutral",   # 新增：中性播报（emotion 未命中低落/高情绪）
    "AWAKE": "emo_surprised",                # 新增：KWS 唤醒反应（**burst 单次**）
    "PUZZLED": "emo_puzzled",                # 新增：困惑（从 CAMERA_LOST **解绑**，语义归位）
    "ACK_NOD": "ack_nod",                    # 确认点头（**burst 单次**）
    "DENY_SHAKE": "deny_shake",              # P1-1：否定摇头（**burst 单次**）
    "CAMERA_LOST": "idle_offline",           # 改绑：系统态不该有"情绪表情"（原 emo_puzzled）
    "NETWORK_LOST": "idle_offline",
    "CANCELLED": "idle_normal",
    "ERROR": "emo_sad",
}

# 播放语义名单：**单次 burst**（播到末帧即停、回退上一状态）；未列入者按 loop 无限循环。
# 依据：一次性动作（点头/惊讶）若做成循环会变成"每 1.6 秒重复一次"（见状态系统重设计 §1.1 判据①）。
BURST_STATES: typing.FrozenSet[str] = frozenset({"AWAKE", "ACK_NOD", "DENY_SHAKE"})
# 状态素材缺失时的兜底素材名（再缺失则由渲染层回退 B2V 矢量）
FALLBACK_ASSET: str = "idle_normal"
# 状态专属的**中间兜底**（先于全局 FALLBACK_ASSET 尝试）：语义近似优先，避免掉档太狠。
# 例：低落播报素材未生成时先播"高涨播报"（观感上仍在说话），而不是直接退成"待机"。
FALLBACK_BY_STATE: typing.Dict[str, typing.Tuple[str, ...]] = {
    "SPEAKING_LOW": ("talking_normal",),
    "SPEAKING_NEUTRAL": ("talking_normal",),
    "ACK_NOD": ("talking_normal",),        # 点头素材缺失 → 说话素材（仍在"表达"）
    "DENY_SHAKE": ("talking_normal",),     # P1-1：摇头素材缺失 → 说话素材（仍在"表达"）
    "AWAKE": ("idle_present",),            # 唤醒素材缺失 → 有人时的待机
    "PUZZLED": ("idle_thinking",),         # 困惑素材缺失 → 思考态（语义最近）
}


def asset_name(runtime_state: str) -> str:
    """运行时状态 → 素材目录名（未知状态按 IDLE 处理）。"""
    return STATE_ASSET.get(runtime_state, STATE_ASSET["IDLE"])


def asset_dir(name: str,
              root: typing.Optional[typing.Union[str, Path]] = None) -> Path:
    """素材目录绝对路径（不保证存在）。root 为空时用工程内 AVATAR_DIR（测试可注入）。"""
    base = Path(root) if root is not None else AVATAR_DIR
    return base / name


def list_frames(directory: typing.Union[str, Path]) -> typing.List[Path]:
    """列出目录内帧序列文件（按文件名升序）。目录不存在时返回空表。"""
    d = Path(directory)
    if not d.is_dir():
        return []
    files = [p for p in d.iterdir()
             if p.is_file() and p.suffix.lower() in FRAME_EXTS]
    return sorted(files, key=lambda p: p.name)


def read_meta(directory: typing.Union[str, Path]) -> typing.Dict:
    """读取 meta.json（缺省/非法时返回空字典，绝不抛异常）。"""
    meta_path = Path(directory) / "meta.json"
    if not meta_path.is_file():
        return {}
    try:
        with open(meta_path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def frames_fps(directory: typing.Union[str, Path]) -> float:
    """帧率：优先 meta.json.fps（必须为正数），否则 DEFAULT_FPS。"""
    fps = read_meta(directory).get("fps")
    try:
        value = float(fps)
    except (TypeError, ValueError):
        return DEFAULT_FPS
    return value if value > 0 else DEFAULT_FPS


def fallback_chain(runtime_state: str) -> typing.Tuple[str, ...]:
    """该状态的素材回退链：专属素材 → 状态专属中间兜底 → 全局兜底（去重保序）。

    未定义中间兜底的状态，链与旧行为**完全一致**（专属素材 → `idle_normal`）。
    """
    chain: typing.List[str] = []
    candidates = ((asset_name(runtime_state),)
                  + FALLBACK_BY_STATE.get(runtime_state, ())
                  + (FALLBACK_ASSET,))
    for name in candidates:
        if name not in chain:
            chain.append(name)
    return tuple(chain)


def frames_dir(runtime_state: str,
               root: typing.Optional[typing.Union[str, Path]] = None
               ) -> typing.Optional[Path]:
    """返回该状态实际可用的素材目录（含至少一帧），否则继续沿回退链找。

    回退链见 `fallback_chain()`；全部缺失则返回 None（渲染层回退 B2V 矢量）。
    """
    for name in fallback_chain(runtime_state):
        directory = asset_dir(name, root=root)
        if list_frames(directory):
            return directory
    return None


def has_frames(runtime_state: str,
               root: typing.Optional[typing.Union[str, Path]] = None) -> bool:
    """该状态是否有可用素材帧序列。"""
    return frames_dir(runtime_state, root=root) is not None


def all_asset_names() -> typing.List[str]:
    """全部素材目录名（去重、稳定顺序），供文档/脚本枚举。"""
    names: typing.List[str] = []
    for name in STATE_ASSET.values():
        if name not in names:
            names.append(name)
    if FALLBACK_ASSET not in names:
        names.append(FALLBACK_ASSET)
    return names
