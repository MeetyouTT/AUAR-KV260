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
# **burst 素材名集合**（由 `STATE_ASSET` 反查）：这些素材必须**整段播一次**（末帧停住），
# **不得**做循环 / 三段式「取中间帧」处理 —— 点头、摇头、惊讶都是一次性完整动作，
# 从中间帧起播或循环播放都会破坏语义（用户 2026-10-04 明确指出）。
BURST_ASSETS: typing.FrozenSet[str] = frozenset(
    STATE_ASSET[state] for state in BURST_STATES if state in STATE_ASSET)
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


# **跨素材池**（用户 2026-10-05 反馈："说话不够自然 → 多生成一些素材交替"）：
# 某些状态允许多个**语义等价**素材，播放层按「一个素材播满 N 秒」轮换使用；
# 单素材即便做了多窗口轮换，长时间说话仍会看出重复。
# ⚠ 池内素材必须**语义等价**（都属"中性播报"），否则情绪会串味（低落时不该出现高涨动作）；
# ⚠ 池只影响**素材选择**，不影响状态合同（`ui/ui_state.schema.json` 仍是 15 态）；
# ⚠ 池内素材**未生成时自动忽略**（见 `pool_assets`）⇒ 可以先写池、后补素材。
POOLS: typing.Dict[str, typing.Tuple[str, ...]] = {
    "SPEAKING_NEUTRAL": ("talking_neutral", "talking_neutral_b", "talking_neutral_c"),
    "SPEAKING": ("talking_normal", "talking_normal_b"),
}


def pool_assets(runtime_state: str,
                root: typing.Optional[typing.Union[str, Path]] = None
                ) -> typing.Tuple[str, ...]:
    """该状态的**候选素材名**（只保留目录里真有帧的）；无池 → 只有主素材（**旧行为**）。

    与 `fallback_chain()` 的分工：回退链回答"主素材缺失时**退哪去**"（允许退化语义）；
    本函数回答"有哪些**等价**素材可轮换"（**严格同语义**，绝不把别的情绪素材混进来）。
    返回顺序即轮换顺序，第一个通常是主素材（也即 `STATE_ASSET` 指定的那个）。
    """
    names = POOLS.get(runtime_state)
    primary = asset_name(runtime_state)
    if not names:
        return (primary,)
    usable = [n for n in names
              if isinstance(n, str) and n and list_frames(asset_dir(n, root=root))]
    return tuple(usable) if usable else (primary,)


def asset_name(runtime_state: str) -> str:
    """运行时状态 → 素材目录名（未知状态按 IDLE 处理）。"""
    return STATE_ASSET.get(runtime_state, STATE_ASSET["IDLE"])


def is_burst_asset(name: str) -> bool:
    """该**素材名**是否属于一次性动作（burst）—— 用于"不做三段式 / 不循环"的判定。

    例：`ack_nod` / `deny_shake` / `emo_surprised` 为 True；`idle_*` / `talking_*` 为 False。
    """
    return str(name) in BURST_ASSETS


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
    """全部素材目录名（去重、稳定顺序），供文档/脚本枚举。

    ⚠ 必须包含 **`POOLS` 池内素材**（跨素材交替用的变体）：它们虽不是任何状态的
    **主素材**，但同样需要 `motion.json` / `segments.json` 等预计算产物 ——
    否则 `split_avatar_segments.py` 会漏掉它们，新素材无切段 ⇒ 多窗口轮换失效
    （2026-10-05 实测：只列 `STATE_ASSET` 时 `talking_neutral_b` 不出现）。
    顺序：先 `STATE_ASSET` 的值（**保持旧顺序 ⇒ 旧脚本输出零变化**），再追加池内素材。
    """
    names: typing.List[str] = []
    pooled = [n for pool in POOLS.values() for n in pool]
    for name in list(STATE_ASSET.values()) + pooled:
        if name not in names:
            names.append(name)
    if FALLBACK_ASSET not in names:
        names.append(FALLBACK_ASSET)
    return names


# --------------------------------------------------------------------------- #
# SOP 运行时数据（由 tools/ 预计算，播放层只读）
# --------------------------------------------------------------------------- #
def _read_json(directory: typing.Union[str, Path],
               name: str) -> typing.Any:
    """读素材目录下的 JSON；缺失/非法 → None（绝不抛异常）。"""
    path = Path(directory) / name
    if not path.is_file():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def read_motion(directory: typing.Union[str, Path]
                ) -> typing.Optional[typing.List[float]]:
    """素材**逐帧运动量表**（`motion.json` 的 `diffs`）；缺失/非法 → None。

    由 `tools/build_motion_table.py --write` 生成；播放层用它做**匀速化**
    （`avatar_timing.warp_time` / `playback_time`），使循环点速度连续。
    """
    data = _read_json(directory, "motion.json")
    diffs = data.get("diffs") if isinstance(data, dict) else None
    if not isinstance(diffs, list) or not diffs:
        return None
    try:
        return [float(d) for d in diffs]
    except (TypeError, ValueError):
        return None


def read_slowdown(directory: typing.Union[str, Path],
                  default: typing.Optional[float] = None
                  ) -> typing.Optional[float]:
    """素材规格里的**放慢倍率**（`motion.json.slowdown`）；缺失 → default。"""
    data = _read_json(directory, "motion.json")
    value = data.get("slowdown") if isinstance(data, dict) else None
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def read_segments(directory: typing.Union[str, Path]) -> typing.Any:
    """素材**三段区间**（`segments.json`）→ dict（喂给 `avatar_timing.segments_from_dict`）；缺失 → None。

    由 `tools/split_avatar_segments.py --write` 生成：enter / loop / exit 三个闭区间帧号。
    """
    data = _read_json(directory, "segments.json")
    return data if isinstance(data, dict) else None
