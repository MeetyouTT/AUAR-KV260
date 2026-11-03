# -*- coding: utf-8 -*-
"""Shared avatar playback core for Tk and Qt; independent of both UI toolkits."""
from __future__ import annotations
import typing
import math
from PIL import Image
from . import avatar_assets, avatar_timing
from board.runtime.event_bus import EventEnvelope
from board.runtime.events import EventType
from board.runtime.fsm import RuntimeFSM

class AvatarPlayer:
    """播放核心（**纯逻辑、不依赖 Tk**）：真 FSM + 真素材 + P0-2 真时序。"""

    #: 池轮换：单个素材**连播多少秒**后换下一个（`avatar_assets.POOLS` 内交替）。
    #: Six seconds triggers recovery; actual rotation waits for its completion.
    POOL_SWITCH_SECONDS: float = 6.0
    MAX_CACHED_SEQUENCES: int = 3

    def __init__(self, sprite_root: typing.Any = None, rng: typing.Any = None) -> None:
        self.fsm = RuntimeFSM(publish_state_changes=False)
        self.sprite_root = sprite_root
        self.rng = rng
        self.reply_text = ""
        self.last_action = ""
        self.emotion = "neutral"          # 最近一次回复的情绪（P0-1 续播按它分档）
        self.talk_gen = 0                 # 对话代次（#4：取消后旧回复必须作废）
        self.cancelled = False
        self._stage = "enter"             # #5：三段式阶段机（enter/loop/blend/exit）
        self._stage_t0 = 0.0
        self._stage_key = None
        self._exit_requested = False
        self._blend_from = 0.0
        # 缓存键 = (状态, 素材名)：池轮换下**每个素材各有一套**帧序列 / SOP 数据
        self._seq_cache: typing.Dict[typing.Tuple[str, str], typing.Any] = {}
        self._sop_cache: typing.Dict[typing.Tuple[str, str], typing.Any] = {}
        # ---- 跨素材池轮换（用户 2026-10-05：说话不够自然 → 同语义素材交替）----
        # `_pool_names`：状态 → 可轮换素材名（`avatar_assets.pool_assets`，池内未生成自动忽略）
        # `_asset_of` ：状态 → **当前生效素材名**（池游标所指；无池 = 主素材 == 旧行为）
        # `_asset_t0` ：状态 → 当前素材起播时刻（决定"播满 N 秒换素材"）
        self._pool_names: typing.Dict[str, typing.Tuple[str, ...]] = {}
        self._asset_of: typing.Dict[str, str] = {}
        self._pool_i: typing.Dict[str, int] = {}
        self._asset_t0: typing.Dict[str, float] = {}
        self._time_key: typing.Any = None   # (状态, 素材名)：时间基归零键（见 frame_at）
        # 池轮换时序：`_switch_pending` = 已决定"该换素材了"（在等当前素材的 exit 播完）；
        # `_exit_done` = 当前素材的 exit 段已播完（由 `segment_stage_time` 置位）
        self._switch_pending = False
        self._exit_done = False
        self._burst_done = False
        self.idle_gain = 1.0               # 潜动层幅度增益（生产恒 1.0；仅做幅度对比时调大）
        self.reset_playback()

    # ---------------- 状态机 ----------------
    def send(self, event_type, payload: typing.Optional[dict] = None):
        return self.fsm.handle_event(EventEnvelope(
            event_type=event_type, source="demo_stage", created_at_ms=0,
            payload=payload or {}))

    def reset_playback(self) -> None:
        """时间基/相位归零（重来时调用）。"""
        self._state_key: typing.Optional[str] = None
        self._state_t0 = 0.0
        self._phase_key: typing.Any = None
        self._phase = 0.0
        self._burst_done = False           # burst 素材是否刚播完（供 P0-1 上报用）
        self._burst_reported = False
        self._display_state = None
        self._display_target = None
        self._display_exiting = False
        self._stage_key = None
        self.stage_reset()
        self._time_key = None              # 时间基键（重来 → 强制下一帧归零）
        self._switch_pending = False
        self._exit_done = False
        self._asset_of.clear()             # 池游标复位 → 下次从池首素材起播
        self._asset_t0.clear()
        self._pool_i.clear()

    def display_frame(self, state: str, now: float) -> typing.Optional[typing.Dict]:
        """Render the previous speaking asset through its exit before showing the new state.

        The business FSM may already be IDLE; display transitions deliberately have
        their own lifetime. Emergency/error states interrupt immediately.
        """
        self._display_target = state
        if self._display_state is None:
            self._display_state = state
        old = self._display_state
        if state in ('ERROR', 'CAMERA_LOST', 'NETWORK_LOST'):
            self._display_exiting = False
            self._display_state = state
        elif old != state and not self._display_exiting:
            seq = self.sequence(old)
            seg = self.sop(old)[1] if seq is not None else None
            if old in avatar_timing.SPEAKING_STATES and seg is not None:
                self._display_exiting = True
                self._switch_pending = False
                self.request_exit()
            else:
                self._display_state = state
        if self._display_exiting and self._exit_done:
            self._display_exiting = False
            self._display_state = state
            self._time_key = None
            self._stage_key = None
            self._asset_t0[state] = now
        meta = self.frame_at(self._display_state, now)
        if meta is not None:
            meta.update(display_state=self._display_state, target_state=state,
                        transitioning=self._display_exiting)
        return meta

    @staticmethod
    def burst_completion(state: str, speaking: bool,
                         emotion: str = 'neutral') -> typing.Optional[typing.Tuple]:
        """The single event policy consumed by Tk and Qt after a one-shot action."""
        if speaking:
            return (EventType.AUDIO_PLAYBACK_START, {'emotion': emotion})
        if state == 'AWAKE':
            return (EventType.AUDIO_PLAYBACK_STOP, {'reason': 'wake_animation_finished'})
        return None

    # ---------------- 素材池（跨素材轮换的取材层）----------------
    def pool(self, state: str) -> typing.Tuple[str, ...]:
        """state → **可轮换素材名**（只保留真有帧的；无池 = `(主素材,)` ⇒ 旧行为）。

        直接复用 `avatar_assets.pool_assets`（池内素材**未生成时自动忽略** ⇒ 可先写池、
        后补素材）；池只影响**素材选择**，不影响状态合同（`ui/ui_state.schema.json` 仍 15 态）。
        """
        if state not in self._pool_names:
            self._pool_names[state] = avatar_assets.pool_assets(
                state, root=self.sprite_root)
        return self._pool_names[state]

    def asset_of(self, state: str) -> str:
        """状态 → **当前生效素材名**（池游标所指）；未初始化 / 已失效时取池首。"""
        names = self.pool(state)
        name = self._asset_of.get(state)
        if name not in names:
            name = names[0]
            self._asset_of[state] = name
        return name

    def advance_asset(self, state: str, now: float) -> str:
        """池游标前进一格（换素材）：**新素材必须从 enter（帧 0）起播**。

        数值依据（`%TEMP%\\zz_link.py`，2026-10-05）：跨素材"上素材末帧 → 下素材首帧"
        灰阶差 1.18~1.56，**低于素材内部 loop 接缝**（自环 1.21~1.31）⇒ 池内混用安全；
        为肉眼零跳变，切换仍走完当前素材的 `exit`（见 `frame_at`）。
        """
        names = self.pool(state)
        if len(names) <= 1:
            return names[0] if names else ""
        i = (self._pool_i.get(state, 0) + 1) % len(names)
        self._pool_i[state] = i
        name = names[i]
        self._asset_of[state] = name
        self._asset_t0[state] = now
        return name

    def sequence(self, state: str, asset: typing.Optional[str] = None):
        """state → (frames, fps, burst, asset) 或 None（真机上退 B2V 矢量）。

        `asset` 省略时用 `asset_of(state)`（池轮换当前素材）；该素材目录若**缺帧**，回退
        原状态回退链（`frames_dir`）—— 池配置写错也不会把画面弄丢（零回归）。
        """
        name = asset or self.asset_of(state)
        key = (state, name)
        if key in self._seq_cache:
            cached = self._seq_cache.pop(key)
            self._seq_cache[key] = cached
            return cached
        out = None
        directory = avatar_assets.asset_dir(name, root=self.sprite_root)
        if not avatar_assets.list_frames(directory):
            directory = avatar_assets.frames_dir(state, root=self.sprite_root)
        if directory is not None:
            frames = []
            for path in avatar_assets.list_frames(directory):
                try:
                    frames.append(Image.open(path).convert("RGBA"))
                except OSError:
                    continue
            if frames:
                out = (frames, avatar_assets.frames_fps(directory),
                       state in avatar_assets.BURST_STATES, directory.name)
        self._seq_cache[key] = out
        while len(self._seq_cache) > self.MAX_CACHED_SEQUENCES:
            del self._seq_cache[next(iter(self._seq_cache))]
        return out

    # ---------------- SOP 运行时数据（匀速化 / 三段式）----------------
    def sop(self, state: str, asset: typing.Optional[str] = None):
        """state → (diffs, seg, slowdown)：SOP 运行时数据（缺失则 None / 默认放慢倍率）。

        数据由 `tools/build_motion_table.py --write` 与 `split_avatar_segments.py --write`
        预计算并落盘，运行时**零像素开销**（只读 JSON）。
        `asset` 省略时用 `asset_of(state)`（池轮换当前素材 ⇒ **每素材各一套**运动表 / 切段）。
        """
        name = asset or self.asset_of(state)
        key = (state, name)
        if key not in self._sop_cache:
            diffs: typing.Any = None
            seg: typing.Any = None
            slowdown: float = avatar_timing.LOOP_SLOWDOWN
            directory = avatar_assets.asset_dir(name, root=self.sprite_root)
            if not avatar_assets.list_frames(directory):
                directory = avatar_assets.frames_dir(state, root=self.sprite_root)
            if directory is not None:
                diffs = avatar_assets.read_motion(directory)
                # ⚠ burst 状态（点头 / 摇头 / 惊讶）**必须整段播一次**，绝不用三段式 ——
                # 即便素材目录里残留了 segments.json 也要忽略（双保险，不靠调用顺序）。
                if state not in avatar_assets.BURST_STATES:
                    seg_data = avatar_assets.read_segments(directory)
                    if seg_data:
                        seg = avatar_timing.segments_from_dict(seg_data)
                got = avatar_assets.read_slowdown(directory)
                if got:
                    slowdown = float(got)
            self._sop_cache[key] = (diffs, seg, slowdown)
        return self._sop_cache[key]

    @staticmethod
    def _apply_offsets(image, off):
        """潜动层（呼吸/重心/微摆）→ 显示变换（**底边中心锚定**，与出片脚本同口径）。

        画布尺寸保持不变（不留白）：偏移量本身只有 ±1.2 px / 0.35°，
        加上分量小，越界部分可忽略 → UI 侧无需改动即可直接显示。
        """
        w, h = image.size
        # One inverse affine transform keeps fractional offsets continuous. The
        # previous integer rounding made breathing step by one whole pixel and
        # required separate resize/composite/rotate passes on every UI tick.
        angle = math.radians(off.tilt_deg)
        c, s = math.cos(angle), math.sin(angle)
        sy = max(1e-6, off.scale_y)
        cx, cy = w / 2.0 + off.dx, h - off.dy
        return image.transform((w, h), getattr(Image, "Transform", Image).AFFINE,
            (c, -s, w / 2.0 - c * cx + s * cy,
             s / sy, c / sy, h - (s * cx + c * cy) / sy),
            resample=getattr(Image, "Resampling", Image).BILINEAR, fillcolor=(0, 0, 0, 0))

    # ---------------- 播放（与播放层同口径）----------------
    def frame_at(self, state: str, now: float) -> typing.Optional[typing.Dict]:
        # ---- 跨素材池轮换（用户 2026-10-05）----
        # 池只在**非 burst** 状态生效（burst 是一次性动作，绝不能与其他素材混播）；
        # `_asset_t0` = "当前素材起播时刻"，换素材时一并归零 ⇒ 阶段机回到 enter（帧 0）。
        if state not in avatar_assets.BURST_STATES:
            self._asset_t0.setdefault(state, now)
        seq = self.sequence(state)
        if seq is None:
            return None
        frames, fps, burst, asset = seq
        if state != self._state_key:
            self._state_key = state
            self._switch_pending = False    # 换状态 ⇒ 丢弃上一状态遗留的"待换素材"标记
            self._asset_t0[state] = now
        # 时间基 / 阶段机 / 相位统一按 **(状态, 素材名)** 归零：换素材即"新素材从帧 0 起播"
        tkey = (state, asset)
        if tkey != self._time_key:
            self._time_key = tkey
            self._state_t0 = now
            self._phase_key = None          # 状态/素材一变 → 相位必须重抽（不依赖 tick 频率）
            self._burst_done = False
            self._burst_reported = False
        state_time = max(0.0, now - self._state_t0)
        duration = (len(frames) / fps) if fps else len(frames) / 24.0
        # ---- 池轮换时序：播满 N 秒 → 平滑收起（等 exit 播完）→ 换下一个素材 ----
        # 仅当"池里真有 ≥2 个等价素材"时启用；burst 状态**永不参与**（一次性动作不可混播）。
        # 换素材后阶段机键变化 ⇒ 自动 `stage_reset()` ⇒ 新素材从 enter（帧 0）起播。
        if not burst and not self._display_exiting and len(self.pool(state)) > 1:
            _, seg_now, _ = self.sop(state)
            if self._switch_pending and (seg_now is None
                                         or (self._stage == "exit" and self._exit_done)):
                self._switch_pending = False
                self.advance_asset(state, now)
                seq = self.sequence(state)
                if seq is None:
                    return None
                frames, fps, burst, asset = seq
                self._time_key = (state, asset)
                self._state_t0 = now
                self._phase_key = None
                state_time = 0.0
                duration = (len(frames) / fps) if fps else len(frames) / 24.0
            elif (not self._switch_pending) and self._stage in ("enter", "loop") \
                    and (now - self._asset_t0.get(state, now)) >= self.POOL_SWITCH_SECONDS:
                self._switch_pending = True
                if seg_now is not None:
                    # 有切段数据 → 先把当前素材**平滑收起**（blend 150ms + exit），播完再换；
                    # 无切段数据 → 没有 exit 可等，直接换（跨素材差异本就小于素材内部 loop 接缝）
                    self.request_exit()
        phase = 0.0
        if not burst:
            key = (state, round(duration, 4))
            if key != self._phase_key:
                self._phase_key = key
                self._phase = avatar_timing.random_phase(duration, self.rng)
            phase = self._phase
        speed = avatar_timing.speed_for_state(state, self.reply_text)
        # ★ SOP 播放口径（与 qt_widgets 共用同一份 avatar_timing）★
        #   burst → 原样起播；有 segments.json → 三段式（按句长定循环次数）；
        #   否则 → 匀速化 + 整体放慢（循环点速度连续，看不出一次循环结束）。
        diffs, seg, slowdown = self.sop(state)
        t_b = None
        alpha = 0.0
        if burst:
            t = avatar_timing.frame_time(state_time, burst=True, phase=0.0, speed=1.0)
        elif seg is not None:
            # Event-driven continuous cursor; "blend" now means velocity ramp.
            # 不再用"固定周期 + 按预计句长估循环次数"（真实语音时长随机，估不准）。
            t, t_b, alpha = self.segment_stage_time(state, seg, fps, phase, state_time)
            if alpha >= 1.0:                     # 淡化已完成 → 本次按纯 exit 帧处理
                t_b, alpha = None, 0.0
        else:
            t = avatar_timing.playback_time(state_time, state=state, diffs=diffs,
                                            fps=fps, duration=duration, burst=False,
                                            slowdown=slowdown)
        idx = avatar_timing.frame_index(t, len(frames), fps, burst)
        # P0-1：burst 素材播完（此时已夹在末帧）→ 记一次，供上层"接进播报段"
        if burst and state_time >= duration and not self._burst_reported:
            self._burst_done = True
            self._burst_reported = True
        image = frames[max(0, idx)]
        source_position = max(0.0, min(t * fps, len(frames) - 1.0))
        interpolation = 0.0
        if seg is not None and not burst:
            # Only interpolate neighbouring ORIGINAL frames. No crossfade
            # between unrelated gestures or windows (which creates ghost hands).
            left = int(math.floor(source_position))
            interpolation = source_position - left
            idx = left
            image = frames[left]
            if interpolation > 1e-6 and left + 1 < len(frames):
                image = Image.blend(image, frames[left + 1], interpolation)
        if alpha > 0.0 and t_b is not None:    # #5 淡化段：保持段姿态「淡入」退出段
            j = avatar_timing.frame_index(t_b, len(frames), fps, burst)
            other = frames[max(0, j)]
            if other.size == image.size:
                image = Image.blend(image, other, alpha)
        if self.idle_gain > 0.0 and not getattr(self, "defer_portrait_offsets", False):               # 潜动层（**全局时间基**，不随状态切换归零）
            image = self._apply_offsets(
                image, avatar_timing.idle_offsets(now, gain=self.idle_gain))
        return {"image": image, "index": idx, "frames": len(frames),
                "stage": self._stage, "alpha": alpha,
                "fps": fps, "burst": burst, "asset": asset, "duration": duration,
                "phase": 0.0 if seg is not None else phase,
                "speed": 1.0 if seg is not None else speed,
                "requested_speed": speed, "state_time": state_time,
                "source_position": source_position, "interpolation": interpolation}

    # ---------------- 对话 ----------------
    def apply_response(self, response_dict: typing.Dict) -> None:
        """主机响应 → 状态机（走真实事件通道）+ 记录回复文本/动作/情绪。"""
        self.reply_text = str(response_dict.get("reply_text") or "")
        self.last_action = str(response_dict.get("avatar_action") or "")
        self.emotion = str(response_dict.get("emotion") or "neutral")
        self.send(EventType.DIALOGUE_RESPONSE_RECEIVED, response_dict)

    def take_burst_finished(self) -> bool:
        """burst 素材刚播完（**只上报一次**）—— 供上层发 AUDIO_PLAYBACK_START（P0-1）。"""
        if self._burst_done:
            self._burst_done = False
            return True
        return False

    # ---------------- 对话代次（#4：取消后旧回复必须作废）----------------
    # 背景（2026-10-04 外部审查 #4）：取消**只改状态**，没有停 TTS；取消后迟到的旧回复
    # 仍会被显示并念出来。根因是"请求 → 响应"之间**没有身份校验**。
    # 方案：给每一轮对话一个**代次**（`talk_gen`）；取消 / 重新发起都会令其递增，
    # 于是"旧代次"的响应到达时可直接判废（**不显示、不播放**）—— 与 FSM 层解耦、可单测。
    def new_turn(self) -> int:
        """发起新一轮对话：递增代次并返回（调用方持有该值，回程时校验）。"""
        self.talk_gen += 1
        self.cancelled = False
        return self.talk_gen

    def cancel(self) -> None:
        """取消当前轮：代次递增 ⇒ 在途响应一律作废（停播由调用方执行 `tts.stop()`）。"""
        self.talk_gen += 1
        self.cancelled = True
        self._burst_done = False

    def accept_response(self, gen: typing.Any, response_dict: typing.Dict) -> bool:
        """代次校验 + 应用响应；**旧代次返回 False**（调用方应丢弃：不显示、不播放）。"""
        try:
            if int(gen) != self.talk_gen:
                return False
        except (TypeError, ValueError):
            return False
        self.apply_response(response_dict)
        return True

    # Event-driven stages: enter -> primary loop -> velocity ramp -> recovery.
    # The historical name "blend" is kept for HUD/trace compatibility; it no
    # longer means blending a held pose with unrelated exit-start frames.
    def stage_reset(self) -> None:
        """进入新状态时重置阶段机（回到 enter，窗口计数归零）。"""
        self._stage = "enter"
        self._stage_t0 = 0.0
        self._exit_requested = False
        self._blend_from = 0.0
        self._loop_round = 0          # 多窗口轮换：已完成几个"来回"
        self._exit_done = False       # 新阶段机 → exit 尚未播完（池轮换换素材的前提）
        self._source_position = 0.0
        self._exit_target = 0.0

    def request_exit(self) -> None:
        """Request native forward recovery; the blend stage now eases velocity."""
        if self._stage in ("enter", "loop"):
            self._exit_requested = True

    def stage_state(self) -> typing.Tuple[str, bool]:
        """(当前阶段, 是否已请求退出) —— 供 HUD / 测试观察。"""
        return self._stage, self._exit_requested

    def segment_stage_time(self, state: str, seg, fps: float,
                           phase: float, t_stage: float
                           ) -> typing.Tuple[float, float, float]:
        """Continuous source cursor, independent of the UI sampling frequency.

        Use the primary window only: other windows have not passed cross-pose
        compatibility checks. Enter reaches its start without a random phase.
        A cosine round trip eases both reversals. Stop/cancel takes the shorter
        original-frame route to a recovery endpoint. `blend` is retained
        as a diagnostic stage name for the 150 ms velocity ramp, not a pose fade.
        The tuple API remains compatible; alpha is zero (no distant-pose blend).
        """
        f = fps if fps and fps > 0 else 24.0
        a, b = seg.loop
        ramp = avatar_timing.segment_blend_seconds()
        sid = self._time_key if self._time_key is not None else state
        if sid != self._stage_key:
            self._stage_key = sid
            self.stage_reset()
        if self._stage in ('enter', 'loop'):
            enter_end = max(0.0, (a - seg.enter[0]) / f)
            if t_stage < enter_end:
                self._stage = 'enter'
                position = seg.enter[0] + max(0.0, t_stage) * f
            else:
                self._stage = 'loop'
                period = max(0.0, 2.0 * (b - a) / f * 3.0)
                elapsed = max(0.0, t_stage - enter_end)
                self._loop_round = int(elapsed / period) if period else 0
                u = (elapsed % period) / period if period else 0.0
                position = a + (b - a) * (1.0 - math.cos(2.0 * math.pi * u)) / 2.0
            if self._exit_requested:
                # Both clip endpoints are recovery anchors. Interruptions take
                # the shorter original-frame route (avoids performing the whole
                # gesture after a very short utterance); pool rotation uses end.
                self._blend_from = position
                self._exit_target = float(seg.exit[1])
                if not self._switch_pending and position - seg.enter[0] < seg.exit[1] - position:
                    self._exit_target = float(seg.enter[0])
                self._stage, self._stage_t0 = 'blend', t_stage
        if self._stage in ('blend', 'exit'):
            elapsed = max(0.0, t_stage - self._stage_t0)
            if ramp > 0.0 and elapsed < ramp:
                advance = f * elapsed * elapsed / (2.0 * ramp)
            else:
                # Same time origin across the stage boundary: no restart.
                self._stage = 'exit'
                advance = f * max(0.0, elapsed - ramp / 2.0)
            direction = 1.0 if self._exit_target >= self._blend_from else -1.0
            distance = abs(self._exit_target - self._blend_from)
            position = self._blend_from + direction * min(distance, advance)
            self._exit_done = advance >= distance
            if self._exit_done:
                self._stage = 'exit'
        self._source_position = position
        return position / f, position / f, 0.0


