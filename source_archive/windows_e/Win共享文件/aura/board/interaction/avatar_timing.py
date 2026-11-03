# -*- coding: utf-8 -*-
"""玩偶帧序列的**播放时序**纯逻辑（方案 §4.1 P0-2「长句去重复」）。

两个观感问题、两个手段（**只作用于 loop 素材**）：

  ① **入场一致**：`qt_widgets._state_time` 让状态内时间从 0 起 → 每次进 SPEAKING 都是
     同一段入场动作。手段 = **相位随机化**：进入 loop 状态时抽 `phase ∈ [0, duration)`，
     取帧用 `t + phase`。
  ② **循环节一致**：素材 1.625s，长句必然反复回到同一帧。手段 = **轻度变速**：
     按 `reply_text` 字数估句长 → `speed ∈ [0.85, 1.15]`，取帧用 `t * speed`。

为什么单独一个模块（而不是直接写在 qt_widgets 里）：

  · `qt_widgets` 依赖 PySide6，而**本机没有 PySide6** → 验收脚本与 pytest 都拿不到
    取帧口径，"验收测的不是播放层"这个坑会一直存在（见 `.cline-handover.md` 第 28 条）。
    抽到这里后**播放层与验收脚本共用同一份口径**。
  · `frame_index()` 与 `qt_widgets._SpriteSequence.frame_at()` 必须**逐字同口径**，
    故由本模块单点定义，播放层改为调用它。

burst 素材（AWAKE / ACK_NOD / 后续 DENY_SHAKE）**不加相位、不变速**：一次性动作必须
从第 0 帧起播，否则永远停在末帧（`qt_widgets._state_time` docstring 已说明）。
"""
from __future__ import annotations

import math
import random
import typing

# ---- 变速参数（方案 §4.1 P0-2；限幅依据 §8 风险表「speed 越界 → 夹紧」）----
MIN_SPEED: float = 0.85         # 长句：略慢更耐看
MAX_SPEED: float = 1.15         # 短句：略快更利落
CHARS_PER_SECOND: float = 4.5   # 中文口语 ≈ 4~5 字/秒（方案 §2.2 的估算抓手）
FAST_SECONDS: float = 3.0       # 预计句长 ≤ 3s → 取最快
SLOW_SECONDS: float = 9.0       # 预计句长 ≥ 9s → 取最慢

#: 只有播报三档变速（方案：仅在 SPEAKING 档生效），其余状态恒 1.0
SPEAKING_STATES: typing.Tuple[str, ...] = ("SPEAKING", "SPEAKING_NEUTRAL", "SPEAKING_LOW")


def estimate_seconds(text: typing.Any) -> float:
    """回复文本 → 预计口播秒数（`字数 / 4.5`）；非字符串 / 空串 → 0.0。"""
    if not isinstance(text, str):
        return 0.0
    return len(text.strip()) / CHARS_PER_SECOND


def clamp_speed(speed: typing.Any) -> float:
    """速度限幅到 `[MIN_SPEED, MAX_SPEED]`；非法值回落 1.0（方案 §8）。"""
    try:
        value = float(speed)
    except (TypeError, ValueError):
        return 1.0
    return max(MIN_SPEED, min(MAX_SPEED, value))


def speed_for_text(text: typing.Any) -> float:
    """句长 → 播放速度：短句快（→1.15）、长句慢（→0.85），线性插值后限幅。

    映射区间 `[FAST_SECONDS, SLOW_SECONDS]`，超出即夹紧 —— 保证**单调**、可解释；
    无文本（空串 / 非字符串）返回中性 1.0，避免"没拿到回复也乱变速"。
    """
    est = estimate_seconds(text)
    if est <= 0.0:
        return 1.0
    if est <= FAST_SECONDS:
        return MAX_SPEED
    if est >= SLOW_SECONDS:
        return MIN_SPEED
    k = (est - FAST_SECONDS) / (SLOW_SECONDS - FAST_SECONDS)
    return clamp_speed(MAX_SPEED + (MIN_SPEED - MAX_SPEED) * k)


def speed_for_state(runtime_state: typing.Any, reply_text: typing.Any = "") -> float:
    """状态 + 回复文本 → 速度倍率；非播报三档恒 1.0（方案：仅 SPEAKING 档生效）。"""
    if str(runtime_state) not in SPEAKING_STATES:
        return 1.0
    return speed_for_text(reply_text)


def random_phase(duration: float, rng: typing.Any = None) -> float:
    """抽一个起始相位 `[0, duration)`；`duration <= 0` → 0.0（无相位可言）。"""
    d = float(duration or 0.0)
    if d <= 0.0:
        return 0.0
    source = rng if rng is not None else random
    return float(source.uniform(0.0, d))


# ---- 长时间循环的"去机械化"（用户反馈：待机/说话久了像机械循环）----
# 为什么需要：loop 素材只有 ~1.6s，长时间停留会**精确重复**（周期恒 = 素材时长）；
# 相位随机化只解决"每次入场同一动作"，不解决"长时间重复"。这里让**等效速度缓慢起伏**，
# 周期随之漂移。做法：两个**不可通约**周期的正弦叠加（5.3s / 7.9s）→ 复合周期 ≈ 42s，
# 肉眼看不到固定节奏；速度起伏 ±0.05（等效速度 ∈ [0.90, 1.10]），比按句长的变速
# （0.85~1.15）更细，观感只是"呼吸节奏偶尔快一点点"，不会显得奇怪。
DRIFT_RATE: float = 0.05
DRIFT_PERIODS: typing.Tuple[float, ...] = (5.3, 7.9)


def drift_time(t: float, rate: float = DRIFT_RATE,
               periods: typing.Sequence[float] = DRIFT_PERIODS) -> float:
    """状态内时间 → **去机械化**后的等效推进时间（纯解析、无状态、可测）。

    `t = 0` 时返回 0（入场仍从第 0 帧起，与相位随机化兼容）；
    对 t 的导数 = `1 + Σ rate·sin(2πt/period)` ∈ `[1-2·rate, 1+2·rate]`。
    """
    out = float(t)
    if rate <= 0.0:
        return out
    for period in periods:
        p = float(period)
        if p <= 0.0:
            continue
        omega = 2.0 * math.pi / p
        out += (rate * p / (2.0 * math.pi)) * (1.0 - math.cos(omega * float(t)))
    return out


def frame_time(state_time: float, *, burst: bool, phase: float = 0.0,
               speed: float = 1.0, drift: bool = True) -> float:
    """状态内相对时间 → 传给取帧的时间参数。

    burst：原样返回（**不加相位、不变速、不漂移** —— 一次性动作必须从第 0 帧起播）；
    loop ：`drift_time(t) * speed + phase`
      · `phase`（P0-2）打破"每次入场都是同一动作"；
      · `speed`（P0-2，仅播报档按句长）让长句略慢、短句略快；
      · `drift_time`（问题 2 修法）让**周期缓慢漂移**，消除"长时间机械循环"。
    """
    t = max(0.0, float(state_time or 0.0))
    if burst:
        return t
    base = drift_time(t) if drift else t
    return base * clamp_speed(speed) + float(phase or 0.0)


def frame_index(t: float, frame_count: int, fps: float, burst: bool) -> int:
    """时间 → 帧索引（与 `_SpriteSequence.frame_at` **逐字同口径**）。

    loop 取模无限循环；burst 夹在末帧停住；fps 非法按 24fps；空素材返回 -1。

    `+ 1e-9` 的作用：`int((i/24)*24)` 在**整数帧边界**上会因浮点下溢取到前一帧
    （实测 `(23/24)*24 = 22.999999999999996` → 22），使"循环节 = 素材时长"
    这一事实在数值上不可测。加一个远小于半帧的 epsilon 让边界稳定落在正确帧，
    观感无差异（原本也是 ±1 帧抖动），但**验收可复现**。
    """
    if frame_count <= 0:
        return -1
    f = float(fps) if fps and fps > 0 else 24.0
    index = int(max(0.0, float(t)) * f + 1e-9)
    if burst:
        return min(index, frame_count - 1)
    return index % frame_count


def sample_frame_indices(frame_count: int, fps: float, burst: bool, seconds: float,
                         *, phase: float = 0.0, speed: float = 1.0,
                         out_fps: float = 24.0, drift: bool = True) -> typing.List[int]:
    """按**播放层时间基**采样帧索引序列（播放层 / 验收脚本共用口径）。

    `out_fps` 取与素材相同的 24 时，未变速（`speed=1.0`）的序列其精确周期恰为
    `frame_count` 个采样点（= 素材时长），这正是 G1「循环节 = 素材时长」的量化基线；
    变速后该周期消失/改变 —— 验收脚本据此断言"峰值间隔不再固定"。
    """
    step = 1.0 / float(out_fps) if out_fps and out_fps > 0 else 1.0 / 24.0
    steps = max(1, int(round(float(seconds) / step)))
    out = []  # type: typing.List[int]
    for i in range(steps):
        t = frame_time(i * step, burst=burst, phase=phase, speed=speed, drift=drift)
        out.append(frame_index(t, frame_count, fps, burst))
    return out


def exact_period(seq: typing.Sequence[int], min_lag: int = 2) -> typing.Optional[int]:
    """序列的**精确周期**（单位：采样点）＝使 `seq[i] == seq[i+lag]` 对全部 i 成立的最小 lag。

    找不到（< 2 * min_lag 长度内无精确重复）→ None，即"循环节已被打散"。
    """
    n = len(seq)
    for lag in range(max(1, int(min_lag)), n // 2 + 1):
        if all(seq[i] == seq[i + lag] for i in range(n - lag)):
            return lag
    return None


# --------------------------------------------------------------------------- #
# 潜动层（L0）：程序化「活着」的微动（呼吸 / 重心 / 微摆）
# --------------------------------------------------------------------------- #
# 为什么需要（2026-10-04 运动量体检结论，见 docs/玩偶素材运动量与可辨识度_数值体检_技术记录.md）：
#   · 素材是 39 帧 @24fps = **1.625s 做一次明显动作**，且 `amp_p90` 33~57（门槛 3.0 的 11~19 倍）
#     → 循环节太短 + 幅度过大，观感是"做操"而不是"在场"；
#   · 素材**没有整体位移**（体检 v3 实测帧间 `shift = 0,0`；仅 AWAKE/ACK_NOD/ERROR 为 `0,1`）
#     → 在**播放层**叠加整体微动不会与素材自身的局部动作打架，这正是本模块成立的前提；
#   · "活物"的底噪 = 长周期、低幅度、**永不精确重复**的微动（呼吸/重心/微摆）——
#     它是"生命感"里最大的乘数，且**不需要任何新素材**。
#
# 设计口径（PC 与板端共用同一份；播放层只做坐标变换，不重复实现数学）：
#   · 四个通道周期**互质**（3.7 / 5.3 / 7.9 / 6.7 s）→ 复合周期 > 200s，肉眼看不到重复；
#   · `t <= 0` 时**全部回到中性位**（位移 0 / 缩放 1.0）→ 进场不跳变、可随时开关；
#   · 呼吸与微摆**单向**（只隆起 / 只偏一侧，`(1-cos)/2` ∈ [0,1]）→ 像呼吸而不是"抖"；
#     重心用 `sin` 双向 ±1.2px → 给"站不稳的活物感"；
#   · 时间基必须是**全局单调时间**（如 `time.monotonic()`），**不是** `_state_time` 状态内时间
#     —— 否则每次状态切换都会"重新吸一口气"，观感割裂。
#   · **锚点 = 显示框底边中心**：素材按 waist-up 入库且底部对齐（423×436），
#     以底边为不动点做纵向缩放 → 观感是"胸腔起伏"，而不是人物整体上浮（那会像"飘"）。
IDLE_BREATH_PERIOD: float = 3.7        # 呼吸周期（秒）≈ 16 次/分，接近成人静息呼吸
IDLE_BREATH_AMP: float = 0.006         # 纵向缩放半幅：1.000 → 1.006（±0.6%）
IDLE_SWAY_PERIODS: typing.Tuple[float, ...] = (5.3, 7.9)   # 重心漂移的两个互质周期
IDLE_SWAY_AMP_X: float = 1.2           # 水平漂移幅度（像素，按 423 宽显示框标定）
IDLE_SWAY_AMP_Y: float = 0.5           # 垂直漂移幅度（像素，仅"轻微下沉"）
IDLE_TILT_PERIOD: float = 6.7          # 微摆周期（秒）
IDLE_TILT_AMP_DEG: float = 0.35        # 微摆幅度（度）


class IdleOffsets(typing.NamedTuple):
    """潜动层一次采样的结果（显示坐标系；锚点 = 显示框底边中心）。"""

    dx: float          # 水平位移（像素，+ 向右）
    dy: float          # 垂直位移（像素，+ 向下）
    scale_y: float     # 纵向缩放（1.0 = 原样；> 1 为呼吸隆起）
    tilt_deg: float    # 旋转（度，+ 顺时针）


def _rise(t: float, period: float) -> float:
    """单向起伏基函数：周期非法 → 0；否则 `(1 - cos(2πt/T)) / 2` ∈ [0, 1]（t=0 → 0）。"""
    p = float(period)
    if p <= 0.0:
        return 0.0
    return 0.5 * (1.0 - math.cos(2.0 * math.pi * float(t) / p))


def idle_offsets(t: float, *, gain: float = 1.0) -> IdleOffsets:
    """潜动层：全局时间（秒）→ 显示变换（纯解析、无状态、可单测）。

    - `gain`：幅度增益，仅用于**样品对比**（×1 / ×2 / ×4），生产恒 1.0；
    - `t <= 0` 或 `gain <= 0` → 中性（全 0 / `scale_y = 1.0`），保证"进场不跳"、可一键关闭；
    - 返回的偏移量按 **423×436 显示框**标定；其它尺寸按 `dx * 宽/423` 等比换算即可
      （板端 LVGL 同口径，缩放/位移都取整像素）。
    """
    if t <= 0.0 or gain <= 0.0:
        return IdleOffsets(0.0, 0.0, 1.0, 0.0)
    breath = IDLE_BREATH_AMP * _rise(t, IDLE_BREATH_PERIOD)
    dx = IDLE_SWAY_AMP_X * math.sin(2.0 * math.pi * float(t) / IDLE_SWAY_PERIODS[0])
    dy = IDLE_SWAY_AMP_Y * _rise(t, IDLE_SWAY_PERIODS[1])
    tilt = IDLE_TILT_AMP_DEG * _rise(t, IDLE_TILT_PERIOD)
    return IdleOffsets(gain * dx, gain * dy, 1.0 + gain * breath, gain * tilt)


def idle_composite_period(tolerance: float = 0.5) -> float:
    """潜动层诸通道的**复合周期**（秒）：各周期两两之比取有理逼近后求最小公倍。

    用途：验收断言"底噪在长时间尺度上不重复"。实现取每个周期到 `tolerance` 秒的
    整数倍近似（3.7→37/10、5.3→53/10、7.9→79/10、6.7→67/10），再对整数倍求 LCM。
    """
    periods = [IDLE_BREATH_PERIOD, IDLE_TILT_PERIOD] + list(IDLE_SWAY_PERIODS)
    units = []
    for period in periods:
        p = float(period)
        if p <= 0.0:
            continue
        units.append(int(round(p / max(1e-6, float(tolerance)))))
    value = 1
    for unit in units:
        value = value * unit // math.gcd(value, unit)
    return float(value) * float(tolerance)
