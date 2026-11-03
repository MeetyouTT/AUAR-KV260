# -*- coding: utf-8 -*-
"""玩偶实机演示台（Tk + PIL，零 Qt）—— 本地 LLM 驱动的联动实验台。

为什么是 Tk：本机**没有 PySide6**（板端 `qt_app.py` 跑不了），而 ComfyUI 便携 Python
自带 tkinter 9.0 + PIL ✓。本台**复用生产逻辑层**，只替换渲染层：

    board.runtime.fsm.RuntimeFSM         真状态机（事件驱动、非法转换被拒）
    board.interaction.avatar_assets      真素材解析（14 态映射 / 回退链 / burst 名单）
    board.interaction.avatar_timing      **P0-2 真播放时序**（随机相位 + 按句长变速）
    board.runtime.dialogue_client        真对话合同（Mock / WebSocket 适配器）
    board.runtime.validator              真三层校验（给响应做一次"体检"并显示）

播放回路与 `qt_widgets.AvatarPanel` **同口径**：
状态内相对时间（状态一变归零）→ `_loop_phase`（loop 抽一次随机相位）→
`avatar_timing.frame_time` → `frame_index`。

用法：
    "<PY>" -s tools\\demo_stage.py                          # 不接 LLM（mock 适配器）
    "<PY>" -s tools\\demo_stage.py --host 127.0.0.1 --port 8765   # 接 Ollama 主机
    "<PY>" -s tools\\demo_stage.py --selftest                # 无窗口自检（出 PNG + 指标）
"""
from __future__ import annotations

import argparse
import json
import queue
import sys
import threading
import time
import typing
from pathlib import Path

AURA = Path(__file__).resolve().parents[1]
if str(AURA) not in sys.path:
    sys.path.insert(0, str(AURA))

from PIL import Image, ImageDraw                                   # noqa: E402

from board.interaction import avatar_assets, avatar_timing         # noqa: E402
from board.runtime.audio import tts_style                          # noqa: E402
from board.runtime.audio.tts import TtsConfig, build_player            # noqa: E402
from board.runtime.dialogue_client import MockDialogueAdapter      # noqa: E402
from board.runtime.dialogue_client.adapter import DialogueRequest  # noqa: E402
from board.runtime.event_bus import EventEnvelope                  # noqa: E402
from board.runtime.events import EventType                         # noqa: E402
from board.runtime.fsm import RuntimeFSM                           # noqa: E402

# 控制台可能是 GBK（重定向到文件时尤甚）→ 统一 UTF-8 + 替换，避免 UnicodeEncodeError
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:      # 老解释器 / 特殊 stdout
    pass

STAGE_W, STAGE_H = 320, 360        # 玩偶显示区（素材 464x480 等比缩放）
TICK_MS = 33                       # ≈30Hz 刷新

# 三档句长（与 P0-2 出片同一批文本，便于对照）
LONG_TEXTS = {
    "短句 11 字": "好的，我帮你把灯打开。",
    "中句 29 字": "我看到画面左侧有一位来访者，他正站在门口，手里拿着一封信。",
    "长句 92 字": ("我看到画面左侧有一位来访者，他先在门口停了一会儿，然后向房间里走了两步，"
                   "又把手里那封信举起来晃了晃，像是在确认我有没有注意到他；如果你愿意，"
                   "我也可以先替你打个招呼，再问问他今天来找谁。"),
}

SCENE_ONLINE = {
    "schema_version": "1.0", "scene_seq": 11, "camera_state": "online", "people_count": 1,
    "current_target": {"track_id": 1, "position": "left", "confidence": 0.9},
    "recent_events": [],
}
ALLOWED_EMOTIONS = ["neutral", "friendly", "happy", "excited", "sad", "low"]
ALLOWED_ACTIONS = ["ack_nod", "deny_shake", "emo_surprised", "emo_puzzled"]


class StageCore:
    """播放核心（**纯逻辑、不依赖 Tk**）：真 FSM + 真素材 + P0-2 真时序。"""

    #: 池轮换：单个素材**连播多少秒**后换下一个（`avatar_assets.POOLS` 内交替）。
    #: 取值依据（2026-10-05）：池内素材约 1.6 s/圈，6 s ≈ 4 圈 —— 短于"察觉动作重复"的
    #: 时长，又不至于切换过频（每次切换要走完 blend 150 ms + exit，过频会显得碎片化）。
    POOL_SWITCH_SECONDS: float = 6.0

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
        self._time_key = None              # 时间基键（重来 → 强制下一帧归零）
        self._switch_pending = False
        self._exit_done = False
        self._asset_of.clear()             # 池游标复位 → 下次从池首素材起播
        self._asset_t0.clear()
        self._pool_i.clear()

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
            return self._seq_cache[key]
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
        new_h = max(2, int(round(h * off.scale_y)))
        scaled = image if new_h == h else image.resize((w, new_h), Image.LANCZOS)
        canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        cx = w // 2 + int(round(off.dx))
        bottom = h - int(round(off.dy))
        canvas.alpha_composite(scaled, (max(0, cx - w // 2), max(0, bottom - new_h)))
        if abs(off.tilt_deg) > 1e-6:
            canvas = canvas.rotate(off.tilt_deg, resample=Image.BICUBIC,
                                   center=(cx, min(h, bottom)), fillcolor=(0, 0, 0, 0))
        return canvas

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
        # 时间基 / 阶段机 / 相位统一按 **(状态, 素材名)** 归零：换素材即"新素材从帧 0 起播"
        tkey = (state, asset)
        if tkey != self._time_key:
            self._time_key = tkey
            self._state_t0 = now
            self._phase_key = None          # 状态/素材一变 → 相位必须重抽（不依赖 tick 频率）
        state_time = max(0.0, now - self._state_t0)
        duration = (len(frames) / fps) if fps else len(frames) / 24.0
        # ---- 池轮换时序：播满 N 秒 → 平滑收起（等 exit 播完）→ 换下一个素材 ----
        # 仅当"池里真有 ≥2 个等价素材"时启用；burst 状态**永不参与**（一次性动作不可混播）。
        # 换素材后阶段机键变化 ⇒ 自动 `stage_reset()` ⇒ 新素材从 enter（帧 0）起播。
        if not burst and len(self.pool(state)) > 1:
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
            # #5：**事件驱动阶段机**（enter → loop 往返 → 说完/被打断 → 150ms 淡化 → exit），
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
        if burst and state_time >= duration:
            self._burst_done = True
        image = frames[max(0, idx)]
        if alpha > 0.0 and t_b is not None:    # #5 淡化段：保持段姿态「淡入」退出段
            j = avatar_timing.frame_index(t_b, len(frames), fps, burst)
            other = frames[max(0, j)]
            if other.size == image.size:
                image = Image.blend(image, other, alpha)
        if self.idle_gain > 0.0:               # 潜动层（**全局时间基**，不随状态切换归零）
            image = self._apply_offsets(
                image, avatar_timing.idle_offsets(now, gain=self.idle_gain))
        return {"image": image, "index": idx, "frames": len(frames),
                "stage": self._stage, "alpha": alpha,
                "fps": fps, "burst": burst, "asset": asset, "duration": duration,
                "phase": phase, "speed": speed, "state_time": state_time}

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

    # ---------------- 三段式阶段机（#5：enter → loop → 淡化 → exit）----------------
    # 背景（2026-10-04 外部审查 #5）：原来用固定周期的 `segment_time`（按"预计句长"算循环次数），
    # 但**真实语音时长是随机的** —— 句子短会白等、句子长会提前退，且没有"说完／被打断 → 平滑收起"。
    # 正解 = **事件驱动的阶段机**：
    #     enter（播一次）→ loop（**往返**播，一直播到"该走了"）
    #     → blend（`SEGMENT_BLEND_MS`，默认 150ms **交叉淡化**）→ exit（播一次）→ 停在末帧。
    # 上层在"说完（AUDIO_PLAYBACK_STOP）/ 被打断（状态离开播报）"时调用 `request_exit()`。
    def stage_reset(self) -> None:
        """进入新状态时重置阶段机（回到 enter，窗口计数归零）。"""
        self._stage = "enter"
        self._stage_t0 = 0.0
        self._exit_requested = False
        self._blend_from = 0.0
        self._loop_round = 0          # 多窗口轮换：已完成几个"来回"
        self._exit_done = False       # 新阶段机 → exit 尚未播完（池轮换换素材的前提）

    def request_exit(self) -> None:
        """**该走了**（说完 / 被打断）：标记进入退出流程（下一帧起 blend → exit）。"""
        if self._stage in ("enter", "loop"):
            self._exit_requested = True

    def stage_state(self) -> typing.Tuple[str, bool]:
        """(当前阶段, 是否已请求退出) —— 供 HUD / 测试观察。"""
        return self._stage, self._exit_requested

    def segment_stage_time(self, state: str, seg, fps: float,
                           phase: float, t_stage: float
                           ) -> typing.Tuple[float, float, float]:
        """阶段机求值 → `(t_a, t_b, alpha)`；**`alpha == 0` 表示只画 a**，否则按 alpha 融合 a→b。

        - `t_stage`：**状态内**相对时间（秒），由调用方用 `now - stage_t0` 给出；
        - 阶段推进全在**本方法内**完成（调用方每帧调一次即可，不必自己管阶段）；
        - `blend` 段的 `a` 取自"请求退出那一刻"的 loop 帧（快照），`b` 随 exit 前进 ⇒ 视觉上是
          "保持段的姿态**淡入**到退出段"，因此**无论在哪一帧被打断都不会跳变**。
        """
        blend_s = avatar_timing.segment_blend_seconds()
        enter_s = avatar_timing.stage_seconds(seg, fps, stage="enter")
        exit_s = avatar_timing.stage_seconds(seg, fps, stage="exit")
        # 阶段机键 = **(状态, 素材名)**：换素材即 `stage_reset()` ⇒ 新素材从 enter（帧 0）起播
        sid = self._time_key if self._time_key is not None else state
        if sid != getattr(self, "_stage_key", None):
            self._stage_key = sid
            self.stage_reset()
        if self._stage == "enter":
            if t_stage >= enter_s:
                self._stage, self._stage_t0 = ("blend" if self._exit_requested else "loop"), t_stage
            else:
                t = avatar_timing.segment_at(t_stage, seg, fps, stage="enter")
                return (t, t, 0.0)
        if self._stage == "loop":
            # **多窗口轮换**（用户实测 2026-10-05）：单一窗口往返 ⇒ 长时间说话"同一个动作反复晃"。
            # 每个"来回"结束就换下一个窗口 ⇒ 说话过程有变化；窗口来自 `segments.json` 的 `windows`。
            while True:
                one = avatar_timing.loop_window_seconds(
                    seg, fps, window_index=self._loop_round)
                if one <= 0.0 or (t_stage - self._stage_t0) < one:
                    break
                self._stage_t0 += one            # 推进一格（相位保持连续）
                self._loop_round += 1
            if self._exit_requested:
                self._blend_from = avatar_timing.segment_at(
                    t_stage - self._stage_t0, seg, fps, stage="loop",
                    loop_phase=phase, window_index=self._loop_round)
                self._stage, self._stage_t0 = "blend", t_stage
            else:
                t = avatar_timing.segment_at(t_stage - self._stage_t0, seg, fps,
                                             stage="loop", loop_phase=phase,
                                             window_index=self._loop_round)
                return (t, t, 0.0)
        if self._stage == "blend":
            u = t_stage - self._stage_t0
            if u >= blend_s:
                self._stage, self._stage_t0 = "exit", t_stage
            else:
                b = avatar_timing.segment_at(u, seg, fps, stage="exit")
                alpha = (u / blend_s) if blend_s > 0.0 else 1.0
                return (self._blend_from, b, max(0.0, min(1.0, alpha)))
        if self._stage == "exit":
            u = t_stage - self._stage_t0
            if u >= exit_s:
                self._exit_done = True     # 池轮换：exit 已播完 ⇒ 此刻换素材不会跳变
                u = exit_s                 # 与旧行为等价（原来用 min 夹住）
            t = avatar_timing.segment_at(u, seg, fps, stage="exit")
            return (t, t, 0.0)
        t = avatar_timing.segment_at(t_stage, seg, fps, stage="enter")
        return (t, t, 0.0)


# --------------------------------------------------------------------------- #
# 语音输入（麦克风 → VAD → ASR）：只做"听"这一段，不碰对话编排
# --------------------------------------------------------------------------- #
class VoiceLoop:
    """录音 → 能量 VAD 切分 → sherpa-onnx 识别 → 回调文本。

    线程模型：sounddevice 回调只做"入队"（不能阻塞）；worker 线程做 VAD + ASR（较慢，
    不阻塞 Tk 主线程），结果通过回调交回演示台。
    """

    def __init__(self, on_text: typing.Callable[[str], None],
                 on_status: typing.Callable[[str], None],
                 sample_rate: int = 16000,
                 device: typing.Any = None) -> None:
        self.on_text = on_text
        self.on_status = on_status
        self.sample_rate = int(sample_rate)
        self.device = device
        self._stream: typing.Any = None
        self._queue: typing.Any = None
        self._thread: typing.Any = None
        self._running = False
        self._asr: typing.Any = None
        self._reason = ""
        self.last_text = ""
        self.utterances = 0

    # ---------------- 可用性 ----------------
    def available(self) -> typing.Tuple[bool, str]:
        """(ok, reason)：麦克风库与 ASR 是否都就绪（缺哪个就说哪个，便于降级提示）。"""
        try:
            import sounddevice                     # noqa: F401
        except ImportError:
            return False, "未安装 sounddevice（录音库）"
        if self._asr is None:
            from board.runtime.audio.asr import AsrConfig, build_recognizer
            self._asr = build_recognizer(AsrConfig())
            if self._asr is None:
                return False, "ASR 不可用（sherpa-onnx 或模型缺失）"
        return True, "ok"

    # ---------------- 录音 ----------------
    def start(self) -> bool:
        ok, reason = self.available()
        self._reason = reason
        if not ok:
            self.on_status("语音输入不可用：%s" % reason)
            return False
        if self._running:
            return True
        import sounddevice as sd
        from board.runtime.audio.vad import EnergyVad, VadConfig

        self._vad = EnergyVad(VadConfig(sample_rate=self.sample_rate))
        self._queue = queue.Queue()
        self._running = True

        def _callback(indata, frames, time_info, status):   # noqa: ANN001 - 库回调
            if status:
                pass
            try:
                self._queue.put(indata.copy().reshape(-1))
            except Exception:
                pass

        try:
            self._stream = sd.InputStream(samplerate=self.sample_rate, channels=1,
                                          dtype="float32", device=self.device,
                                          blocksize=int(self.sample_rate * 0.1),
                                          callback=_callback)
            self._stream.start()
        except Exception as exc:
            self._running = False
            self.on_status("麦克风打开失败：%s" % exc)
            return False
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()
        self.on_status("🎤 录音中…（说完停顿 0.6s 自动结束）")
        return True

    def stop(self) -> None:
        """停止录音：关闭流并把没说完的尾巴交给 ASR。"""
        self._running = False
        stream, self._stream = self._stream, None
        if stream is not None:
            try:
                stream.stop()
                stream.close()
            except Exception:
                pass
        tail = None
        if getattr(self, "_vad", None) is not None:
            tail = self._vad.flush()
        if tail is not None and getattr(tail, "audio", None) is not None:
            self._transcribe(tail.audio)

    def is_running(self) -> bool:
        return self._running

    # ---------------- worker ----------------
    def _transcribe(self, samples: typing.Any) -> None:
        if self._asr is None or samples is None or len(samples) == 0:
            return
        t0 = time.time()
        self.on_status("识别中…（%.2fs 音频）" % (len(samples) / float(self.sample_rate)))
        text = self._asr.transcribe(samples, self.sample_rate)
        self.last_text = text
        self.utterances += 1
        self.on_status("ASR %.2fs → %s" % (time.time() - t0, text or "（没听清）"))
        if text:
            self.on_text(text)

    def _worker(self) -> None:
        while self._running or (self._queue is not None and not self._queue.empty()):
            try:
                chunk = self._queue.get(timeout=0.3)
            except queue.Empty:
                continue
            for event in self._vad.accept(chunk):
                if event.kind == "speech_start":
                    self.on_status("听到你说话了…")
                elif event.kind == "speech_end":
                    self.on_status("句尾检测（%.2fs）→ 停止录音"
                                   % (event.duration_ms / 1000.0))
                    self.stop()
                    self._transcribe(event.audio)


# --------------------------------------------------------------------------- #
# Tk 渲染层（替代 qt_widgets；逻辑层全部是生产代码）
# --------------------------------------------------------------------------- #
class StageApp:
    """演示台窗口：左侧玩偶帧显示，右侧对话/事件/日志。"""

    def __init__(self, core: StageCore, adapter, adapter_name: str,
                 tts_enabled: bool = True, tts_engine: str = "sapi",
                 tts_sid: int = 0, tts_model: str = "",
                 voice_enabled: bool = True) -> None:
        import tkinter as tk
        from PIL import ImageTk
        self.tk, self.ImageTk = tk, ImageTk
        self.core = core
        self.adapter = adapter
        self.adapter_name = adapter_name
        # 本地 TTS：玩偶"开口说话"；播完由 _tick 的 poll() 发 AUDIO_PLAYBACK_STOP（真实语音收尾）
        # engine="vits" → 本地神经 TTS（离线 sherpa-onnx，见 SherpaTtsBackend）；
        # 不可用（依赖/模型缺失）时 build_player 会自动降级 sapi → scripted。
        self.tts_enabled = bool(tts_enabled)
        self.tts = (build_player(TtsConfig(engine=tts_engine, sid=tts_sid,
                                           tts_model=tts_model))
                    if self.tts_enabled else None)
        # 语音输入（麦克风 → VAD → ASR）：只做"听"，转写文本回到同一条对话链路
        self._voice_enabled = bool(voice_enabled)
        self.voice = VoiceLoop(on_text=self._voice_text_cb, on_status=self._voice_status_cb)
        self.busy = False
        self._photo = None
        self._last_meta: typing.Optional[typing.Dict] = None
        self.root = tk.Tk()
        self.root.title("AURA · 玩偶演示台（Tk 渲染层；逻辑层为生产代码）")
        self.root.configure(bg="#1b1e24")
        self._build()
        # #4：Esc = 取消当前对话（停 TTS + 作废在途响应）—— 演示时随手可按
        try:
            self.root.bind("<Escape>", lambda _e: self.cancel_talk())
        except Exception:                                  # 极简 / 无窗口环境
            pass
        self.root.after(TICK_MS, self._tick)
        self._log("演示台就绪｜对话通道 = %s" % adapter_name)
        self._log("初始状态 = %s；素材根 = %s"
                  % (self.core.fsm.state.label, avatar_assets.AVATAR_DIR))

    def _build(self) -> None:
        tk = self.tk
        outer = tk.Frame(self.root, bg="#1b1e24")
        outer.pack(fill="both", expand=True, padx=10, pady=10)

        left = tk.Frame(outer, bg="#232830", bd=1, relief="solid")
        left.pack(side="left", anchor="n")
        self.canvas = tk.Canvas(left, width=STAGE_W, height=STAGE_H, bg="#2b2f36",
                                highlightthickness=0)
        self.canvas.pack(padx=6, pady=6)
        self.state_label = tk.Label(left, text="IDLE", fg="#4aa08a", bg="#232830",
                                    font=("Microsoft YaHei", 13, "bold"))
        self.state_label.pack()
        self.hud = tk.Label(left, text="", fg="#93a0ad", bg="#232830", justify="left",
                            font=("Consolas", 9))
        self.hud.pack(padx=8, pady=(4, 8), anchor="w")

        right = tk.Frame(outer, bg="#1b1e24")
        right.pack(side="left", anchor="n", padx=(12, 0))

        tk.Label(right, text="① 对话文本（Enter 直接发送）", fg="#8b96a3", bg="#1b1e24",
                 font=("Microsoft YaHei", 10)).pack(anchor="w")
        row = tk.Frame(right, bg="#1b1e24")
        row.pack(anchor="w", pady=4)
        self.entry = tk.Entry(row, width=46, font=("Microsoft YaHei", 10))
        self.entry.pack(side="left")
        self.entry.insert(0, "你看到我了吗？")
        self.entry.bind("<Return>", lambda _e: self._send_llm())
        tk.Button(row, text="发给 LLM", width=10, command=self._send_llm).pack(side="left", padx=6)

        tk.Label(right, text="② 快捷句长（与 P0-2 出片同一批文本）", fg="#8b96a3",
                 bg="#1b1e24", font=("Microsoft YaHei", 10)).pack(anchor="w", pady=(8, 0))
        row2 = tk.Frame(right, bg="#1b1e24")
        row2.pack(anchor="w", pady=4)
        for label, text in LONG_TEXTS.items():
            tk.Button(row2, text=label, width=14,
                      command=lambda t=text: self._send_text(t)).pack(side="left", padx=3)

        tk.Label(right, text="③ 事件（走真 FSM；非法转换会被拒绝并记日志）", fg="#8b96a3",
                 bg="#1b1e24", font=("Microsoft YaHei", 10)).pack(anchor="w", pady=(8, 0))
        row3 = tk.Frame(right, bg="#1b1e24")
        row3.pack(anchor="w", pady=4)
        for label, evt in (("来访者进入", "scene.person_enter"),
                           ("唤醒 KWS", "audio.kws_detected"),
                           ("说完 VAD", "audio.vad_end"),
                           ("播报结束", "audio.playback_stopped"),
                           ("重来", "")):
            tk.Button(row3, text=label, width=10,
                      command=lambda e=evt: self._send_event(e)).pack(side="left", padx=3)

        tk.Label(right, text="③b 语音输入（按麦说话 → VAD → ASR → 同一条对话链路）",
                 fg="#8b96a3", bg="#1b1e24",
                 font=("Microsoft YaHei", 10)).pack(anchor="w", pady=(8, 0))
        row4 = tk.Frame(right, bg="#1b1e24")
        row4.pack(anchor="w", pady=4)
        self.voice_btn = tk.Button(row4, text="🎤 开始说话", width=14,
                                   command=self._toggle_voice)
        self.voice_btn.pack(side="left", padx=3)
        tk.Label(row4, text="（说完停顿 0.6s 自动结束，识别结果自动发给 LLM）",
                 fg="#6f7a87", bg="#1b1e24", font=("Microsoft YaHei", 9)).pack(side="left")

        tk.Label(right, text="③c 演示动作（绕过 LLM，直接看素材与同步）",
                 fg="#8b96a3", bg="#1b1e24",
                 font=("Microsoft YaHei", 10)).pack(anchor="w", pady=(8, 0))
        row5 = tk.Frame(right, bg="#1b1e24")
        row5.pack(anchor="w", pady=4)
        for label, action, text in (("确认（点头）", "ack_nod", "好的，我这就去办。"),
                                    ("拒绝（摇头）", "deny_shake", "抱歉，这个我没法答应。"),
                                    ("惊讶", "emo_surprised", "啊，原来是这样！"),
                                    ("困惑", "emo_puzzled", "嗯……我没太听懂。")):
            tk.Button(row5, text=label, width=12,
                      command=lambda a=action, t=text: self._local_action(a, t)
                      ).pack(side="left", padx=2)

        tk.Label(right, text="④ 玩偶回复", fg="#8b96a3", bg="#1b1e24",
                 font=("Microsoft YaHei", 10)).pack(anchor="w", pady=(8, 0))
        self._reply_var = tk.StringVar(value="（还没说话）")
        tk.Label(right, textvariable=self._reply_var, wraplength=430, justify="left",
                 fg="#e6e6e6", bg="#232830", padx=8, pady=6,
                 font=("Microsoft YaHei", 11)).pack(anchor="w", fill="x")

        tk.Label(right, text="⑤ 事件日志", fg="#8b96a3", bg="#1b1e24",
                 font=("Microsoft YaHei", 10)).pack(anchor="w", pady=(8, 0))
        self.log = tk.Text(right, width=58, height=12, bg="#15181d", fg="#c9d1d9",
                           font=("Microsoft YaHei", 9), wrap="word")
        self.log.pack(anchor="w")
        self.log.configure(state="disabled")

        # 键盘快捷键：与按钮**同一条路径**（远程控制/鼠标点击到不了本窗口时，只要窗口在前台，
        # 键盘就能操作整台演示台）。用法：Alt+Tab 切到本窗口 → 按 F1~F12。
        hotkeys = (
            ("<F1>", lambda: self._send_event("scene.person_enter")),
            ("<F2>", lambda: self._send_event("audio.kws_detected")),
            ("<F3>", lambda: self._send_event("audio.vad_end")),
            ("<F4>", lambda: self._send_event("audio.playback_stopped")),
            ("<F5>", lambda: self._send_event("")),
            ("<F6>", lambda: self._local_action("ack_nod", "好的，我这就去办。")),
            ("<F7>", lambda: self._local_action("deny_shake", "抱歉，这个我没法答应。")),
            ("<F8>", lambda: self._local_action("emo_surprised", "啊，原来是这样！")),
            ("<F9>", lambda: self._local_action("emo_puzzled", "嗯……我没太听懂。")),
            ("<F10>", lambda: self._send_llm()),
            ("<F11>", lambda: self._toggle_voice()),
            ("<F12>", lambda: self._send_text(list(LONG_TEXTS.values())[0])),
        )
        for seq, fn in hotkeys:
            self.root.bind(seq, lambda _e, f=fn: (f(), "break")[1])
        self._log("快捷键：F1 来访者进入 / F2 唤醒 KWS / F3 说完 VAD / F4 播报结束 / F5 重来 ｜ "
                  "F6 点头 / F7 摇头 / F8 惊讶 / F9 困惑 ｜ F10 发给 LLM / F11 开始说话 / F12 短句")

    # ---------------- 日志 ----------------
    def _log(self, text: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", "%s  %s\n" % (time.strftime("%H:%M:%S"), text))
        self.log.see("end")
        self.log.configure(state="disabled")

    # ---------------- 事件（真 FSM）----------------
    def _send_event(self, name: str) -> None:
        if not name:
            self.core.fsm.reset()
            self.core.reset_playback()
            self.core.reply_text = ""
            self._reply_var.set("（还没说话）")
            self._log("重来 → reset 到 IDLE，相位/时间基归零")
            return
        etype = getattr(EventType, name.strip().upper().replace(".", "_"), None)
        if etype is None:
            self._log("未知事件：%s" % name)
            return
        before = self.core.fsm.rejected_count
        change = self.core.send(etype)
        if self.core.fsm.rejected_count > before:
            self._log("[被拒] %s（%s 下非法转换）" % (name, self.core.fsm.state.label))
        elif change is None:
            self._log("[无变化] %s（自环）" % name)
        else:
            self._log("%s → %s" % (name, self.core.fsm.state.label))

    # ---------------- 语音（麦克风 → VAD → ASR）----------------
    def _voice_status_cb(self, text: str) -> None:
        self.root.after(0, self._log, "[voice] %s" % text)

    def _voice_text_cb(self, text: str) -> None:
        self.root.after(0, self._on_voice_text, text)

    def _on_voice_text(self, text: str) -> None:
        """ASR 结果 → 填进输入框并自动走对话链路（与手打文本完全同一条路）。"""
        self._reset_voice_button()
        self.entry.delete(0, "end")
        self.entry.insert(0, text)
        self._log("语音转写：%s" % text)
        self._send_llm()

    def _reset_voice_button(self) -> None:
        try:
            self.voice_btn.configure(text="🎤 开始说话")
        except Exception:
            pass

    def _toggle_voice(self) -> None:
        if not self._voice_enabled:
            self._log("语音输入已禁用（--no-voice）")
            return
        if self.voice.is_running():
            self.voice.stop()
            self._reset_voice_button()
            self._log("已停止录音")
            return
        # 拿起麦克风 = 一次"唤醒"：演示台用按键替代真机的 KWS 唤醒词
        if self.core.fsm.state.label not in ("LISTENING", "THINKING"):
            self.core.send(EventType.BOARD_KEY_PRESSED)
            self._log("（代按键唤醒）→ %s" % self.core.fsm.state.label)
        if self.voice.start():
            self.voice_btn.configure(text="⏹ 停止录音")

    # ---------------- 对话（真适配器 + 真合同）----------------
    def _local_action(self, action: str, text: str) -> None:
        """绕过 LLM 直接演一个动作（看素材与"动作段→播报段"同步用）。"""
        if self.core.fsm.state.label == "LISTENING":
            self.core.send(EventType.AUDIO_VAD_END)            # 识别 / 输入完成 → THINKING
        elif self.core.fsm.state.label != "THINKING":
            self.core.send(EventType.BOARD_KEY_PRESSED)
            self.core.send(EventType.AUDIO_VAD_END)
        self._reply_var.set(text)
        self.core.apply_response({"emotion": "neutral", "avatar_action": action,
                                  "reply_text": text})
        self._log("演示动作：%s（%s）→ 状态 %s"
                  % (action, text[:12], self.core.fsm.state.label))
        if self.tts is not None:
            self.tts.speak_async(text)
    def _send_text(self, text: str) -> None:
        self.entry.delete(0, "end")
        self.entry.insert(0, text)
        self._send_llm()

    def _send_llm(self) -> None:
        if self.busy:
            self._log("上一条还在等 LLM…")
            return
        transcript = self.entry.get().strip()
        if not transcript:
            return
        # ⚠ #2 修正（2026-10-04 外部审查）：识别完成 = "用户说完" ⇒ **在 LISTENING 时也必须推进到 THINKING**，
        # 否则会出现"回复已显示 / 声音已播，玩偶仍停在聆听"（本轮已实测复现）。
        state_label = self.core.fsm.state.label
        if state_label == "LISTENING":
            self.core.send(EventType.AUDIO_VAD_END)            # → THINKING（等 LLM）
            self._log("（识别完成）→ %s" % self.core.fsm.state.label)
        elif state_label != "THINKING":
            self.core.send(EventType.BOARD_KEY_PRESSED)        # → LISTENING
            self.core.send(EventType.AUDIO_VAD_END)            # → THINKING
            self._log("（演示台代为推进 VAD）→ %s" % self.core.fsm.state.label)
        self.core.new_turn()                    # #4：本轮代次 +1（取消 / 重发都会作废在途响应）
        self.busy = True
        self._log("→ 请求：%s（代次 %d）" % (transcript[:30], self.core.talk_gen))
        threading.Thread(target=self._worker, args=(transcript,), daemon=True).start()

    def _worker(self, transcript: str) -> None:
        gen = self.core.talk_gen            # #4：记住本轮代次，回程时校验（旧代次丢弃）
        request = DialogueRequest(request_id="stage-%d" % int(time.time() * 1000),
                                  audio_generation_id=1, transcript=transcript,
                                  scene_state=dict(SCENE_ONLINE),
                                  allowed_emotions=list(ALLOWED_EMOTIONS),
                                  allowed_avatar_actions=list(ALLOWED_ACTIONS))
        t0 = time.time()
        try:
            data, err = self.adapter.send_request(request, timeout_ms=180000).to_dict(), None
        except Exception as exc:                               # 网络/超时/断链
            data, err = None, exc
        dt = time.time() - t0
        self.root.after(0, lambda: self._on_response(data, err, dt, gen))

    def _on_response(self, data, err, dt: float, gen: typing.Any = None) -> None:
        # ⚠ #4（2026-10-04 外部审查）：**先做代次校验** —— 取消后迟到的旧回复必须丢弃
        # （不设置回复文本、不进状态机、不播放 TTS）。这是"取消完整性"的显示/播放侧。
        if gen is not None and int(gen) != self.core.talk_gen:
            self._log("⛔ 旧回复（代次 %s ≠ %s）已丢弃：取消后不再显示 / 播放"
                      % (gen, self.core.talk_gen))
            return
        self.busy = False
        if err is not None:
            self._log("[LLM 失败] %s（%.1fs）→ 用兜底回复保证演示不断" % (err, dt))
            data = {"reply_text": "网络不太好，我没听清，再说一次好吗？",
                    "emotion": "neutral", "avatar_action": ""}
        self._reply_var.set(data.get("reply_text") or "（空回复）")
        self._log("← %.2fs  emotion=%s  action=%s"
                  % (dt, data.get("emotion"), data.get("avatar_action") or "-"))
        self.core.apply_response(data)
        state = self.core.fsm.state.label
        self._log("状态 → %s（reply %d 字 → speed %.3f）"
                  % (state, len(self.core.reply_text),
                     avatar_timing.speed_for_state(state, self.core.reply_text)))
        if self.tts is not None and self.core.reply_text:
            # S1：LLM 的 emotion 驱动语音韵律（分档词表复用 fsm，与玩偶素材同档）
            style = tts_style.for_emotion(data.get("emotion"))
            self.tts.speak_async(self.core.reply_text, style=style)   # 玩偶"开口"
            self._log("TTS 播报中（%s / %s）· 语气 %s → 播完自动发 audio.playback_stopped"
                      % (self.tts.config.engine, self.tts.config.voice, style.describe()))

    # ---------------- 取消（#4 完整性）----------------
    def cancel_talk(self) -> None:
        """取消当前对话：**停 TTS + 作废在途响应 + 送取消事件**（三件事一起做才算"取消完整"）。

        ⚠ 2026-10-04 外部审查 #4：原来只发 `AUDIO_CANCEL_REQUESTED`（FSM 会瞬时回迁），
        但 **TTS 继续播**、**迟到的旧回复仍被显示并念出**。本方法补齐：
          ① `core.cancel()`   —— 代次 +1 ⇒ 在途响应回程时被判废（见 `_on_response`）；
          ② `tts.stop()`      —— 立即停声；
          ③ `AUDIO_CANCEL_REQUESTED` —— FSM 进 CANCELLED 并按"是否有人在"回迁。
        入口：演示台按 **Esc**（见 `__init__` 的绑定），或由上层 / 测试直接调用。
        """
        self.core.cancel()
        if self.tts is not None:
            try:
                self.tts.stop()
            except Exception as exc:                      # 停播失败不应影响取消语义
                self._log("（TTS 停播异常，忽略）%s" % exc)
        self.busy = False
        self.core.send(EventType.AUDIO_CANCEL_REQUESTED)
        self._log("⛔ 已取消：TTS 停播 + 在途响应作废（代次 %d）→ 状态 %s"
                  % (self.core.talk_gen, self.core.fsm.state.label))

    # ---------------- 播放回路（与播放层同口径）----------------
    def _tick(self) -> None:
        # 真实语音收尾：TTS 刚播完 → 发**既有**事件 AUDIO_PLAYBACK_STOP（状态机自己回 IDLE）
        if self.tts is not None and self.tts.poll():
            # #5：说完 → 先驱动三段式**平滑收起**（blend → exit），再送状态机事件
            self.core.request_exit()
            self.core.send(EventType.AUDIO_PLAYBACK_STOP)
            self._log("TTS 播报结束 → 三段式收尾（blend → exit）｜ audio.playback_stopped（%s）"
                      % self.core.fsm.state.label)
        state = self.core.fsm.state.label
        meta = self.core.frame_at(state, time.monotonic())
        self.state_label.configure(text=state)
        # P0-1：动作段（burst）刚播完 → 语音还在就接进播报档继续演（不再停在末帧）
        if self.core.take_burst_finished():
            if self.tts is not None and self.tts.is_busy():
                self.core.send(EventType.AUDIO_PLAYBACK_START,
                               {"emotion": self.core.emotion})
                self._log("动作段播完 → 接进播报继续演（%s，emotion=%s）"
                          % (self.core.fsm.state.label, self.core.emotion))
            else:
                self._log("动作段播完（语音已停）→ 保持不回迁")
        if meta is None:
            self.canvas.delete("all")
            self.canvas.create_text(STAGE_W // 2, STAGE_H // 2,
                                    text="无素材 → 真机退 B2V 矢量主体", fill="#6f7a87")
            self.hud.configure(text="asset : -（回退链为空）")
        else:
            img = meta["image"].copy()
            img.thumbnail((STAGE_W, STAGE_H), Image.LANCZOS)
            self._photo = self.ImageTk.PhotoImage(img)
            self.canvas.delete("all")
            self.canvas.create_image(STAGE_W // 2, STAGE_H // 2, image=self._photo)
            self.hud.configure(text=(
                "asset : %s (%d 帧 @%.1ffps)\n"
                "frame : %d/%d  %s\n"
                "phase : %.3fs  speed: %.3f\n"
                "state_t: %.2fs"
                % (meta["asset"], meta["frames"], meta["fps"] or 24.0,
                   meta["index"] + 1, meta["frames"],
                   "burst" if meta["burst"] else "loop",
                   meta["phase"], meta["speed"], meta["state_time"])))
        self._last_meta = meta
        self.root.after(TICK_MS, self._tick)

    def run(self) -> None:
        self.root.mainloop()


def build_adapter(args):
    """对话通道：默认 Mock（不依赖网络）；给了 --host 就用真 WebSocket 适配器。"""
    if args.host:
        from board.runtime.dialogue_client.ws_adapter import WebSocketAdapter
        adapter = WebSocketAdapter(host=args.host, port=args.port, path=args.path,
                                   timeout_s=args.timeout)
        adapter.connect()
        return adapter, "WebSocket %s:%d%s" % (args.host, args.port, args.path)
    adapter = MockDialogueAdapter()
    adapter.connect()
    return adapter, "Mock（本地回环；未接 LLM）"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="AURA 玩偶演示台（Tk 渲染层 / 生产逻辑层）")
    parser.add_argument("--host", default="", help="对话主机地址（留空 = 用 Mock）")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--path", default="/dialogue")
    parser.add_argument("--timeout", type=float, default=180.0)
    parser.add_argument("--selftest", action="store_true", help="无窗口自检（导出拼图）")
    parser.add_argument("--backend", default="mock")
    parser.add_argument("--model", default="")
    parser.add_argument("--outdir", default="", help="自检产物目录（默认 docs/demo_stage）")
    parser.add_argument("--no-tts", action="store_true", help="关闭本地 TTS 发声")
    parser.add_argument("--no-voice", action="store_true",
                        help="关闭语音输入（麦克风 + VAD + ASR）")
    parser.add_argument("--tts-engine", default="sapi",
                        choices=("sapi", "scripted", "vits"),
                        help="TTS 后端（sapi=Windows 中文女声；vits=本地离线神经 TTS；"
                             "scripted 只计时不出声）")
    parser.add_argument("--tts-sid", type=int, default=0,
                        help="神经 TTS 的说话人 ID（多说话人模型，如 aishell3 有 174 个）")
    parser.add_argument("--tts-model", default="",
                        help="神经 TTS 模型目录名或绝对路径（留空 = models/tts 下自动挑）")
    args = parser.parse_args(argv)
    if args.selftest:
        outdir = Path(args.outdir) if args.outdir else (AURA / "docs" / "demo_stage")
        return selftest(args.backend, args.model, outdir)
    core = StageCore()
    adapter, name = build_adapter(args)
    StageApp(core, adapter, name, tts_enabled=not args.no_tts,
             tts_engine=args.tts_engine, tts_sid=args.tts_sid,
             tts_model=args.tts_model, voice_enabled=not args.no_voice).run()
    return 0


# 注意：入口 `if __name__ == "__main__"` 必须在**文件末尾**（selftest 定义在其后，
# 入口若提前会 NameError —— 实测踩过）。


# --------------------------------------------------------------------------- #
# 自检（无窗口）：跑剧本 → 导出拼图 + 指标（取证用）
# --------------------------------------------------------------------------- #
def compose(tiles, cols: int = 4, cell=(220, 260), pad: int = 8, bg=(27, 30, 36)):
    """把 [(label, PIL图), ...] 拼成一张图（label 只用 ASCII：状态/素材名）。"""
    from PIL import ImageDraw, ImageFont
    font = ImageFont.load_default()
    rows = (len(tiles) + cols - 1) // cols
    canvas = Image.new("RGB", (cols * cell[0] + (cols + 1) * pad,
                               rows * (cell[1] + 18) + (rows + 1) * pad), bg)
    draw = ImageDraw.Draw(canvas)
    for i, (label, image) in enumerate(tiles):
        r, c = divmod(i, cols)
        x = pad + c * (cell[0] + pad)
        y = pad + r * (cell[1] + 18 + pad)
        tile = Image.new("RGB", cell, (43, 47, 54))
        thumb = image.copy()
        thumb.thumbnail(cell, Image.LANCZOS)
        tile.paste(thumb, ((cell[0] - thumb.width) // 2, (cell[1] - thumb.height) // 2),
                   thumb if thumb.mode == "RGBA" else None)
        canvas.paste(tile, (x, y))
        draw.text((x, y + cell[1] + 4), label, fill=(200, 210, 220), font=font)
    return canvas


def selftest(backend: str, model: str, outdir: Path) -> int:
    """无窗口自检：真 FSM + 真素材 + P0-2 真时序 → 拼图 + 指标。"""
    import random
    core = StageCore(rng=random.Random(20261004))       # 固定种子 → 可复现
    outdir.mkdir(parents=True, exist_ok=True)
    clock = [1000.0]

    def now(step: float = 0.05) -> float:
        clock[0] += step
        return clock[0]

    log = []

    def note(text: str) -> None:
        log.append(text)
        print(text, flush=True)

    tiles = []
    for evt in (EventType.SCENE_PERSON_ENTER, EventType.AUDIO_KWS_DETECTED,
                EventType.AUDIO_VAD_END, EventType.AUDIO_VAD_END):
        core.frame_at(core.fsm.state.label, now(0.01))          # 预热：建立时间基
        core.send(evt)
        meta = core.frame_at(core.fsm.state.label, now(0.3))
        note("[%-16s] asset=%-16s frame=%s/%s %s phase=%.3f speed=%.3f"
             % (core.fsm.state.label, meta["asset"] if meta else "-",
                (meta["index"] + 1) if meta else "-", meta["frames"] if meta else "-",
                "burst" if (meta and meta["burst"]) else "loop",
                meta["phase"] if meta else 0.0, meta["speed"] if meta else 0.0))
        if meta:
            tiles.append(("%s / %s" % (core.fsm.state.label, meta["asset"]), meta["image"]))

    long_text = list(LONG_TEXTS.values())[-1]
    fails = []
    traces = []
    sop_flags = []
    for round_no in (1, 2):
        if core.fsm.state.label not in ("LISTENING", "THINKING"):       # 推进到 THINKING
            core.send(EventType.BOARD_KEY_PRESSED)
            core.send(EventType.AUDIO_VAD_END)
            core.frame_at(core.fsm.state.label, now(0.05))              # 中间态也 tick 一次
        core.apply_response({"emotion": "neutral", "avatar_action": "",
                             "reply_text": long_text})
        state = core.fsm.state.label
        base = now(0.01)
        meta = core.frame_at(state, base)
        diffs, seg, slowdown = core.sop(state)
        sop_flags.append((bool(diffs), seg is not None))
        # ★ 真验收：看**画面**（帧索引序列），不看参数 —— 参数变/不变都不代表画面变/不变
        trace = []
        for k in range(24):                                            # 约 10 秒 @0.4s
            m = core.frame_at(state, base + 0.4 * (k + 1))
            trace.append(m["index"] if m else -1)
        traces.append(trace)
        note("长句 第%d次入场：state=%s asset=%s ｜ 帧序列 %d 点 / 唯一帧 %d "
             "｜ SOP: 匀速化=%s 三段式=%s 放慢=%.1f"
             % (round_no, state, meta["asset"] if meta else "-", len(trace),
                len(set(trace)), "有" if diffs else "无",
                "有" if seg is not None else "无", slowdown))
        for k in range(8):                                            # 播报中 8 个时刻（拼图）
            m = core.frame_at(state, base + 0.4 * (k + 1))
            if m:
                tiles.append(("%s r%d t=%.1fs f%d" % (state, round_no, 0.4 * (k + 1),
                                                      m["index"] + 1), m["image"]))
        core.send(EventType.AUDIO_PLAYBACK_STOP)

    # 判定 1：两次进入的**帧序列**必须不同（这才是"随机相位真的体现在画面上"）
    if traces[0] == traces[1]:
        fails.append("两次入场帧序列完全相同（P0-2 没真正作用于画面）")
        note("帧序列对比：两次相同 → SAME [FAIL]")
    else:
        note("帧序列对比：两次不同 → DIFFERENT [OK]（唯一帧 %d vs %d）"
             % (len(set(traces[0])), len(set(traces[1]))))
    # 判定 2：序列不能恒定（否则说明动画没在动 / 时间映射失效）
    for i, tr in enumerate(traces, 1):
        if len(set(tr)) <= 1:
            fails.append("第 %d 次入场帧序列恒定（动画没动）" % i)
    # 判定 3：SOP 数据必须真被读到（否则静默退回旧口径）
    if not any(flag[0] for flag in sop_flags):
        fails.append("没有任何状态读到 motion.json（匀速化未生效）")
    if not any(flag[1] for flag in sop_flags):
        fails.append("没有任何状态读到 segments.json（三段式未生效）")

    page = outdir / "stage_selftest.png"
    compose(tiles, cols=4).save(str(page))
    note("拼图：%s（%d 格）" % (page, len(tiles)))
    (outdir / "stage_selftest.log").write_text("\n".join(log), encoding="utf-8")
    if fails:
        note("SELFTEST FAIL（%d 项）：%s" % (len(fails), "；".join(fails)))
        return 1
    print("SELFTEST OK", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
