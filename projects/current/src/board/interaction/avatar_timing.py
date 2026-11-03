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
# 呼吸周期（秒）：2026-10-04 两次放慢 —— 3.7 → 6.0 → **8.0**（≈7.5 次/分，远慢于成人静息 12~16 次/分）。
# 依据（用户实测反馈）：① 3.7s 时"短时间内幅度太大"；② "静止保持 3 秒"太假（画面完全不动、
# 失去光感自然度）⇒ 结论是"**持续缓慢运动**"才对，所以继续放慢周期，而不是让它停顿。
# 放慢**不改变幅度**，只降低每帧变化率（0.185 → 0.086 px @436），观感由急促变安稳。
IDLE_BREATH_PERIOD: float = 8.0
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


def idle_offsets(t: float, *, gain: float = 1.0,
                 period_scale: float = 1.0) -> IdleOffsets:
    """潜动层：全局时间（秒）→ 显示变换（纯解析、无状态、可单测）。

    - `gain`：幅度增益，仅用于**样品对比**（×1 / ×2 / ×4），生产恒 1.0；
    - `period_scale`：**周期倍率**（>1 = 放慢），仅用于样品对比，生产恒 1.0。
      放慢**不改变幅度**，只降低"每帧变化率"（观感由急促变安稳）；
    - `t <= 0` 或 `gain <= 0` → 中性（全 0 / `scale_y = 1.0`），保证"进场不跳"、可一键关闭；
    - 返回的偏移量按 **423×436 显示框**标定；其它尺寸按 `dx * 宽/423` 等比换算即可
      （板端 LVGL 同口径，缩放/位移都取整像素）。
    """
    if t <= 0.0 or gain <= 0.0:
        return IdleOffsets(0.0, 0.0, 1.0, 0.0)
    ps = float(period_scale) if period_scale and period_scale > 0 else 1.0
    breath = IDLE_BREATH_AMP * _rise(t, IDLE_BREATH_PERIOD * ps)
    dx = IDLE_SWAY_AMP_X * math.sin(
        2.0 * math.pi * float(t) / (IDLE_SWAY_PERIODS[0] * ps))
    dy = IDLE_SWAY_AMP_Y * _rise(t, IDLE_SWAY_PERIODS[1] * ps)
    tilt = IDLE_TILT_AMP_DEG * _rise(t, IDLE_TILT_PERIOD * ps)
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


# --------------------------------------------------------------------------- #
# 循环接缝（loop seam）：消除"首末帧同一姿态"造成的循环顿点
# --------------------------------------------------------------------------- #
# 现象（用户实测反馈 2026-10-04）：素材**首末帧姿态基本相同**（i2v 循环素材的常态，
# 生成时 `first_frame = last_frame`），且动作曲线是"起→高潮→收"（末段几乎静止）
# ⇒ 正放循环时"末帧 → 首帧"等于**同一帧连播两次**，观感"顿一下"。
#
# 修法（两层，缺一不可）：
#   ① **裁尾**：把末尾静止段（帧间差 < 阈值的连续若干帧）从循环里去掉 —— 由调用方
#      截短 `frames` 列表实现（见 tools/verify_loop_seam.py 的 N 值），本模块不碰像素；
#   ② **乒乓（折返）**：把推进时间折成"正放 + 倒放"，让动作"做完再收回"，
#      从而不再回到起点重来。**必须去掉折返点的重复帧**，否则 38→38 又是停顿。
PINGPONG_STATES: typing.Tuple[str, ...] = (
    "IDLE", "PRESENT", "LISTENING", "THINKING",
    "CAMERA_LOST", "NETWORK_LOST", "CANCELLED",
)


def pingpong_for_state(runtime_state: typing.Any) -> bool:
    """该状态是否用折返（乒乓）播放。

    待机族（无口型）用折返 → 消除"首末帧同一姿态"的循环顿点；
    **播报族不用**（倒放会让口型反向，观感错）；burst 也不适用（只播一次，见 `frame_time`）。
    """
    return str(runtime_state) in PINGPONG_STATES


# --------------------------------------------------------------------------- #
# 稀疏动作（single-shot + hold）：把"一次性动作"素材当**事件**播，而不是循环
# --------------------------------------------------------------------------- #
# 为什么不用乒乓（**用户实测否决 2026-10-04**）：折返虽然让"速度大小连续"，
# 但**方向反转本身是极强的视觉事件**（"它怎么又倒回去了"）→ 照样"明显看出循环结束"。
# 根因：素材是"起→高潮→收"的**一次性事件型**动作（不是周期性摆动），
# 任何"循环它"的做法都必然产生"又做了一次"的感知。
#
# 正解 = 不循环素材，而把它当成**偶发事件**：
#   动作播一次（duration）→ 停在首帧**保持 hold 秒** → 再播一次。
# 循环点（t = k·(duration+hold)）落在**完全静止的保持段内部**
# ⇒ 循环点两侧所取帧**完全相同**（差 = 0.0）⇒ 结构上不可能被看见；
# 同时"每 hold 秒动一次"恰是活物的自然节奏。持续动感由潜动层（L0）提供
# ⇒ 观感 =「在呼吸的小玩偶，偶尔动一下」。
# ⚠ **已被用户实测否决（2026-10-04）**：完全静止 3 秒会让画面"像卡住"、失去光感自然度
# —— 用户要的是"**持续缓慢运动**"，不是"动一下停住"。下面实现保留供对照，
# 默认路径应改用文件末尾的"匀速化（`warp_time`）+ 整体放慢"（见 warp_time）。
LOOP_HOLD_SECONDS: float = 3.0


def hold_for_state(runtime_state: typing.Any) -> float:
    """该状态"播一次后停住"的时长（秒）；0 表示不启用（照常循环）。

    待机族沿用 `PINGPONG_STATES` 名单（它们正是"一次性动作"素材）；
    **播报族返回 0**（口播必须连续动，不能停）。
    """
    return LOOP_HOLD_SECONDS if pingpong_for_state(runtime_state) else 0.0


def single_shot_time(t: float, duration: float,
                     hold: float = LOOP_HOLD_SECONDS) -> float:
    """稀疏动作：时间 → "播一次 + 静止保持"周期内的等效时间（循环点藏在静止段内）。

    `u = t % (duration + hold)`；输出 `min(u, duration)` —— 超出 `duration` 的部分
    **夹在素材末时刻**（取模后即首帧；素材首末姿态近似相同，故视觉一致），
    于是保持段内每一刻取到的都是同一帧 ⇒ 循环点两侧**逐像素相同**。
    `hold <= 0` 或 `duration <= 0` → 原样返回（退回普通循环）。
    """
    d = float(duration or 0.0)
    h = float(hold or 0.0)
    if d <= 0.0 or h <= 0.0:
        return float(t)
    return min(float(t) % (d + h), d)

def pingpong_time(t: float, duration: float, trim_frames: int = 0,
                  fps: float = 24.0) -> float:
    """推进时间 → 折返后的等效时间（三角波）。

    **有效帧数** `n_eff = round(duration * fps) - trim_frames`（裁掉末尾静止段）；
    **有效时长取"到最后一帧为止"** `eff = (n_eff - 1) / fps` —— 这一点很关键：
    取 `n_eff / fps` 会让折返点正好落在帧边界上，`frame_index` 取模后跳回第 0 帧
    （实测造成 **36 帧**的大跳变）。
    **折返点只出现一次**：周期 `span = 2 * eff` —— 末帧只在折返点被取一次（不会停顿），
    起点帧则必然出现两次（周期的首/尾，这是循环的本质，且帧序前后连续、无跳变）。

    `duration <= 0` 或有效帧数 <= 1 → 原样返回（不做折返，退回旧行为）。
    """
    d = float(duration or 0.0)
    f = float(fps) if fps and fps > 0 else 24.0
    n_eff = int(round(d * f)) - max(0, int(trim_frames))
    if d <= 0.0 or n_eff <= 1:
        return float(t)
    eff = (n_eff - 1) / f               # 到"最后一帧"为止（避免落在帧边界）
    span = 2.0 * eff                    # 一个来回：末帧只在折返点被取一次
    if span <= 0.0:
        return float(t)
    u = float(t) % span
    return u if u <= eff else span - u


# --------------------------------------------------------------------------- #
# 匀速化（时间重映射）：让"循环点速度连续" —— 真正看不出"一次循环结束"的办法
# --------------------------------------------------------------------------- #
# 为什么需要（两次实测反馈的结论）：
#   · 素材是"起→高潮→收"，末尾**减速到几乎静止**（末段 0.75 灰阶/帧 vs 首段 3.17，差 4 倍）
#     ⇒ 循环点必然出现"速度突变" = 观众看到的"顿一下"；
#   · 裁尾/乒乓/静止保持三种修法都被实测否决：裁尾治不了速度、乒乓的方向反转本身是强事件、
#     静止保持太假（失去光感自然度）。
# ⇒ 正解：**按累积运动量重参数化时间**（匀速化）—— 低速段被加速通过、高速段被放慢，
#   使"运动量随时间均匀推进"，于是**循环点两侧的速度相等** ⇒ 结构上看不出接缝 ✓；
#   同时可乘 `slowdown` 整体放慢（用户要的"晃动更慢、更自然"）。
# ---- 素材动作的**标准处理**（SOP，用户 2026-10-04 定案）----
# 源素材（i2v 生成，约 5 秒量级，39 帧有效动作）**又快又大**，直接循环播放会出现：
#   ① 循环点**速度突变**（末段 0.75 vs 首段 3.17 灰阶/帧 → 看得出的"顿一下"）；
#   ② 整体节奏**急促**，观感不自然。
# 因此**所有待机族素材统一按下面三条处理**（不做减法、保留表现力）：
#   · **匀速化**：`warp_time()` 按累积运动量重参数化时间 → 循环点速度连续；
#   · **整体放慢** `LOOP_SLOWDOWN` 倍（默认 1.5）→ 节奏舒缓、每帧变化更小；
#   · **潜动层**（呼吸 8.0 s / 重心 / 微摆）另行叠加，提供持续生命感。
# 运行时只需读素材目录下的 `motion.json`（由 `tools/build_motion_table.py` 预计算，零像素开销）。
LOOP_SLOWDOWN: float = 1.5


def cumulative_motion(diffs: typing.Sequence[float]) -> typing.List[float]:
    """帧间差表 → **累积运动量** S（长度 = 帧数；`S[0] = 0`，`S[i] = Σ_{j<i} d[j]`）。"""
    out = [0.0]
    for d in diffs:
        out.append(out[-1] + max(0.0, float(d)))
    return out


def warp_time(t: float, diffs: typing.Sequence[float], fps: float,
              *, slowdown: float = 1.0) -> float:
    """匀速化：播放时间 → 等效"素材时间"（使**运动量**随时间均匀推进）。

    - `diffs`：素材逐帧运动量（人物区平均绝对灰度差，见 `tools/verify_loop_seam.py` 口径）；
    - `slowdown`：整体放慢倍率（>1 = 更慢）；
    - 返回等效时间（秒），可直接喂给 `frame_index()`；
    - `diffs` 为空 / 总运动量为 0 → 原样返回（退回普通循环，绝不抛异常）。
    """
    try:
        f = float(fps) if fps and fps > 0 else 24.0
    except (TypeError, ValueError):
        f = 24.0
    table = cumulative_motion(diffs or ())
    n = len(table)
    total = table[-1]
    if n < 2 or total <= 0.0:
        return float(t)
    try:
        slow = max(1e-6, float(slowdown))
    except (TypeError, ValueError):
        slow = 1.0
    period = (n / f) * slow
    progress = (float(t) % period) / period      # 0..1（循环进度）
    target = progress * total
    i = 0
    while i + 1 < n - 1 and table[i + 1] < target:
        i += 1
    span = table[i + 1] - table[i]
    frac = (target - table[i]) / span if span > 0.0 else 0.0
    return (i + max(0.0, min(1.0, frac))) / f


# --------------------------------------------------------------------------- #
# 三段式（enter / loop / exit）：让"说话很久"不会反复抬手放下
# --------------------------------------------------------------------------- #
# 用户实测指出的**结构性问题**（2026-10-04）：素材是"起→高潮→收"一整段，
# 说话 10 秒时变成"抬手→放下→抬手→放下…"重复 6 次，极不自然；
# 正确结构应是：**[进入：抬手] 播一次 → [保持：手在空中 + 小幅自然动] 循环 N 次 → [退出：放下] 播一次**。
#
# 拆段要求（`tools/split_avatar_segments.py` 自动推荐 + 人工可改）：
#   · `enter`：起始 ~ 高潮（动作建立，播一次）；
#   · `loop` ：**高潮附近的"小幅但非静止"段**，且**首尾姿态相近**（能自然衔接 ⇒ 循环看不出接缝）；
#   · `exit` ：高潮 ~ 结束（收势，播一次）。
# 运行时只读 `assets/avatar/<素材名>/segments.json`；缺省时退回整段循环（不会失效）。
class Segments(typing.NamedTuple):
    """三段帧区间（**闭区间** [起, 止]，单位 = 帧索引）。"""

    enter: typing.Tuple[int, int]
    loop: typing.Tuple[int, int]
    exit: typing.Tuple[int, int]
    #: Historical candidate windows. AvatarPlayer continuous_cursor_v1 uses
    # only `loop`; other windows require pose compatibility before activation.
    # Legacy pure timing helpers can still evaluate these for diagnostics.
    windows: typing.Tuple[typing.Tuple[int, int], ...] = ()

    def frames(self) -> typing.Tuple[int, int, int]:
        """各段帧数（enter, loop, exit）。"""
        return (self.enter[1] - self.enter[0] + 1,
                self.loop[1] - self.loop[0] + 1,
                self.exit[1] - self.exit[0] + 1)

    def loop_at(self, index: int = 0) -> typing.Tuple[int, int]:
        """取第 `index` 个循环窗口（**取模**轮换）；无 `windows` 时返回 `loop`。"""
        if not self.windows:
            return self.loop
        return self.windows[int(index) % len(self.windows)]


def segment_time(t: float, seg: Segments, fps: float,
                 *, loops: int = 6, slowdown: float = LOOP_SLOWDOWN,
                 loop_slowdown: float = 3.0, loop_phase: float = 0.0) -> float:
    """三段式：播放时间 → 等效"素材时间"（enter 一次 → loop 循环 `loops` 次 → exit 一次）。

    - `loops`：保持段循环次数（长句给大值，短应答给 1）—— **由调用方按句长决定**；
    - `slowdown`：整体放慢倍率（与 `LOOP_SLOWDOWN` 同一口径）；
    - 段内为线性映射；`loop` 段内每轮都取模回到段首（该段**首尾姿态相近**才自然，由切段脚本保证）；
    - 帧数非法（任一段 ≤ 0）→ 原样返回（退回整段循环）。
    """
    try:
        f = float(fps) if fps and fps > 0 else 24.0
    except (TypeError, ValueError):
        f = 24.0
    ne, nl, nx = seg.frames()
    if ne <= 0 or nl <= 0 or nx <= 0:
        return float(t)
    try:
        slow = max(1e-6, float(slowdown))
    except (TypeError, ValueError):
        slow = 1.0
    loops = max(1, int(loops))
    try:
        slow_l = max(1e-6, float(loop_slowdown))
    except (TypeError, ValueError):
        slow_l = 1.0
    dur_e, dur_l1, dur_x = ne / f, nl / f, nx / f
    # **保持段单独放慢** `loop_slowdown`：素材的"保持段"往往只有 0.3 秒，
    # 按原速循环会变成"每 0.3 秒抖一下"（实测 10 秒说话=26 次）；放慢到 ≥1 秒/轮才像"自然保持"。
    period = (dur_e + dur_l1 * loops * slow_l + dur_x) * slow
    u = (float(t) % period) / slow
    if u < dur_e:                                   # 进入段
        return (seg.enter[0] + u * f) / f
    u -= dur_e
    if u < dur_l1 * loops * slow_l:                 # 保持段：**来回（乒乓）**循环
        # 为什么必须"来回"而不是单向（用户实测 2026-10-04）：保持段首尾姿态差 9~17 灰阶，
        # 单向循环时"末帧 → 首帧"会**跳回去**，观感 = 手刚抬起来就立刻缩回去、没有过渡；
        # 折返让动作"晃到那头再晃回来"，衔接处天然连续 ⇒ 像"轻微摇晃"，自然。
        # ⚠ 与"整段素材乒乓"（已被用户否决）不同：这里是**小幅保持段内的折返**，是微晃而非"倒带"。
        step = pingpong_time(u / slow_l + float(loop_phase or 0.0), dur_l1, 0, f)
        return (seg.loop[0] + min(step * f, nl - 1)) / f
    u -= dur_l1 * loops * slow_l                    # 退出段
    return (seg.exit[0] + min(u * f, nx - 1)) / f


# ---- 打断（interruption）：阶段独立求值 + 过渡衔接 ----
# 真实交流中"说话时长"**不可能是保持段时长的整数倍**，随时可能被打断（用户插话 / 回复结束 /
# 状态切换）⇒ 不能只提供固定周期的 `segment_time`，必须让播放层**按阶段自由组合、时长不限**。
# 另：从"保持段任意一帧"切到"退出段首帧"会跳变（实测保持段首尾差 9~17 灰阶），
# 故切换处需要一段**交叉淡化**（默认 150 ms，与 `ui_tokens.transitions.state_ms` 同口径）。
SEGMENT_BLEND_MS: float = 150.0


def stage_seconds(seg: Segments, fps: float, *, stage: str,
                  loop_slowdown: float = 3.0) -> float:
    """某阶段的时长（秒）：enter / exit = 原速；loop = **一个来回**（往返）的时长。"""
    ne, nl, nx = seg.frames()
    f = float(fps) if fps and fps > 0 else 24.0
    try:
        slow_l = max(1e-6, float(loop_slowdown))
    except (TypeError, ValueError):
        slow_l = 1.0
    if stage == "enter":
        return ne / f
    if stage == "exit":
        return nx / f
    return max(0.0, 2.0 * (nl - 1)) / f * slow_l      # 一个来回


def segment_at(t: float, seg: Segments, fps: float, *, stage: str,
               loop_slowdown: float = 3.0, loop_phase: float = 0.0,
               window_index: int = 0) -> float:
    """**按阶段**求取帧时间（运行时状态机用）—— 各段独立，时长由调用方决定。

    - `stage="enter"`：`t` 从 0 起播进入段（夹在末帧）；
    - `stage="loop"` ：保持段**来回（往返）**播放，`t` 可任意长（自动折返，折返点不重复）；
    - `stage="exit"` ：`t` 从 0 起播退出段（夹在末帧）；
    - 非法 `stage` / 段长度为 0 → 原样返回（退回整段循环，不会失效）。

    用法（播放层状态机）：`enter` 播 `stage_seconds(...)` 秒 → `loop` 一直播到"该走了"
    （被打断 / 回复结束）→ 用 `segment_blend_seconds()` 做淡化 → `exit` 播完。
    """
    ne, nl, nx = seg.frames()
    f = float(fps) if fps and fps > 0 else 24.0
    try:
        slow_l = max(1e-6, float(loop_slowdown))
    except (TypeError, ValueError):
        slow_l = 1.0
    tt = max(0.0, float(t or 0.0))
    if stage == "enter" and ne > 0:
        return (seg.enter[0] + min(tt * f, ne - 1)) / f
    if stage == "loop" and nl > 0:
        a, b = seg.loop_at(window_index)          # 多窗口轮换（无 windows 时 = loop 段）
        wl = max(1, b - a + 1)
        step = pingpong_time(tt / slow_l + float(loop_phase or 0.0), wl / f, 0, f)
        return (a + min(step * f, wl - 1)) / f
    if stage == "exit" and nx > 0:
        return (seg.exit[0] + min(tt * f, nx - 1)) / f
    return float(t)


def segment_blend_seconds() -> float:
    """阶段切换（如"保持段被打断 → 退出段"）的交叉淡化时长（秒）。"""
    return max(0.0, SEGMENT_BLEND_MS / 1000.0)


def loop_window_seconds(seg: Segments, fps: float, *, window_index: int = 0,
                        loop_slowdown: float = 3.0) -> float:
    """第 `window_index` 个循环窗口「**一个来回**」的时长（秒）。

    用途：阶段机按"一个来回"轮换窗口（每个来回结束 → `window_index + 1`），
    所以必须知道**当前窗口**的来回时长（各窗口长度可能不同）。
    """
    a, b = seg.loop_at(window_index)
    f = float(fps) if fps and fps > 0 else 24.0
    try:
        slow_l = max(1e-6, float(loop_slowdown))
    except (TypeError, ValueError):
        slow_l = 1.0
    wl = max(1, b - a + 1)
    return max(0.0, 2.0 * (wl - 1)) / f * slow_l


def segments_from_dict(data: typing.Any) -> typing.Optional[Segments]:
    """`segments.json` → `Segments`；结构非法 → None（调用方退回整段循环）。

    可选字段 `windows`（多个可循环窗口，运行时按"来回"轮换）；缺失 = 只用 `loop` 段（**向后兼容**）。
    """
    if not isinstance(data, dict):
        return None
    try:
        parts = []
        for key in ("enter", "loop", "exit"):
            pair = data[key]
            parts.append((int(pair[0]), int(pair[1])))
    except (KeyError, IndexError, TypeError, ValueError):
        return None
    if any(b < a for a, b in parts):
        return None
    windows = []
    raw = data.get("windows")
    if isinstance(raw, (list, tuple)):
        for pair in raw:
            try:
                wa, wb = int(pair[0]), int(pair[1])
            except (IndexError, TypeError, ValueError):
                continue
            if wb >= wa:
                windows.append((wa, wb))
    return Segments(*parts, windows=tuple(windows))


def loops_for_duration(duration_seconds: float, seg: Segments, fps: float,
                       *, min_loops: int = 1, max_loops: int = 60,
                       loop_slowdown: float = 3.0) -> int:
    """按**时长**估算保持段循环次数：让 enter + loop×N + exit 覆盖 `duration_seconds`。

    `N = clamp(round((duration - enter 时长 - exit 时长) / (保持段单轮时长 × loop_slowdown)), min, max)`
    —— 长句自动多循环几次，短应答只循环 1 次（等于只播 enter + exit）。
    ⚠ 单轮时长必须按 `loop_slowdown` 换算（与 `segment_time` 同口径），否则会低估轮长、循环过密。
    """
    ne, nl, nx = seg.frames()
    f = float(fps) if fps and fps > 0 else 24.0
    try:
        slow_l = max(1e-6, float(loop_slowdown))
    except (TypeError, ValueError):
        slow_l = 1.0
    one = nl / f * slow_l
    if one <= 0.0:
        return max(1, int(min_loops))
    fixed = (ne + nx) / f
    n = int(round((float(duration_seconds or 0.0) - fixed) / one))
    return max(max(1, int(min_loops)), min(int(max_loops), n))

def playback_time(state_time: float, *, state: typing.Any, diffs,
                  fps: float, duration: float, burst: bool,
                  slowdown: float = LOOP_SLOWDOWN) -> float:
    """**标准播放入口（SOP）**：状态内时间 → 取帧时间。

    这是"素材按标准处理"的**单一入口** —— 播放层只调它，不要各自拼
    `frame_time`/`warp_time`：
      · burst（一次性动作）→ **原样返回**（必须从第 0 帧起播）；
      · loop → **匀速化 + 放慢**（`warp_time`，循环点速度连续，看不出一次循环结束）；
      · `diffs` 为空（素材还没跑过 `tools/build_motion_table.py`）→ 自动退回
        `frame_time()`（普通循环），**不会失效**，只是又会出现顿点。
    """
    t = max(0.0, float(state_time or 0.0))
    if burst:
        return t
    if diffs:
        return warp_time(t, diffs, fps, slowdown=slowdown)
    return frame_time(t, burst=False)


def cycle_speed_ratio(diffs: typing.Sequence[float], fps: float,
                      warp: bool = False, slowdown: float = 1.0) -> float:
    """循环点的**速度突变比**（末段 ÷ 首段）——验收用。

    ⚠ 度量必须是**画面运动量**（累积帧间差），**不能**用"帧索引差"：
    后者恒为 1（采样步长决定），什么都测不出（第一版就栽在这）。

    每个采样间隔的"画面运动量" = `S[idx_next] - S[idx_now]`（`S` = 累积运动量表）；
    比值 ≈ 1 ⇒ 速度连续（看不出循环）；≫1 或 ≪1 ⇒ 有"顿"。
    """
    f = float(fps) if fps and fps > 0 else 24.0
    table = cumulative_motion(diffs or ())
    n = len(table)
    if n < 4 or table[-1] <= 0.0:
        return 1.0
    step = 1.0 / f
    if warp:
        slow = max(1e-6, float(slowdown))
        count = int(round((n / f) * slow * f))
        samples = [warp_time(i * step, diffs, f, slowdown=slow) for i in range(count + 1)]
        idx = [int(s * f + 1e-9) for s in samples]
    else:
        samples = [i * step for i in range(n + 1)]
        idx = [int(s * f + 1e-9) % n for s in samples]
    idx = [min(max(0, i), n - 1) for i in idx]
    motion = [table[b] - table[a] for a, b in zip(idx, idx[1:])]
    motion = [m for m in motion if m > 0.0]      # 剔除"同一帧重复"的空间隔
    if len(motion) < 8:
        return 1.0
    # 用**前/后 1/4 窗口均值**：比"前 3 个间隔"稳健得多（单点取整抖动不会污染结论）
    k = max(3, len(motion) // 4)
    head = sum(motion[:k]) / float(k)
    tail = sum(motion[-k:]) / float(k)
    if head <= 0.0:
        return 1.0
    return tail / head

