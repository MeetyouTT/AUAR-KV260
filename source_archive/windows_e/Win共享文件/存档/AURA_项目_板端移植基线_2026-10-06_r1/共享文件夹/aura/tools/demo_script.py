# -*- coding: utf-8 -*-
"""演示剧本（Cue Sheet）——「跨素材池轮换」观感验收。

一条时间轴，把**时间长短变化**与**情绪三档调度**编排进一次完整演出：

    待机 → 到访 → 唤醒 → 倾听/思考 → 短句(中性) → 长句(中性·看池轮换)
         → 动作+高涨 → 低落 → 高涨长句(中途打断) → 告别

设计意图（对应本次要验收的两件事）
----------------------------------
1. **时间长短变化**：11 字短句 / 29 字中句 / 92 字长句 / 2 字极短句，
   外加"倾听→思考"的**刻意停顿**与"说到一半被打断"。
   ⇒ 检验 `avatar_timing.speed_for_state`（按句长变速）与阶段机 enter/loop/blend/exit。
2. **情绪调度**：`emotion` 经 `fsm.speaking_state_name` 分三档（**单一来源**）
   ⇒ 默认中性两套、高涨两套、低落一套，三档均使用各自的局部复用口型；
   `--assets original` 可看原素材对照。**长句段是主力镜头**：只有它够长（≈23 s），
   能看到中性口型的跨素材交替（`POOL_SWITCH_SECONDS = 6.0`）。

复用真逻辑层，**不重写播放逻辑**
--------------------------------
渲染/播放复用 `tools/demo_stage.StageCore`（真 FSM + 真素材 + P0-2 真时序）；
本脚本只负责"**何时说什么、用什么情绪**"，因此剧本改一行就能试不同节奏。

用法
----
    "<PY>" -s tools\\demo_script.py                  # 虚拟时钟全速 + 打印时间轴
    "<PY>" -s tools\\demo_script.py --window         # 真窗口、真实速度（全剧约 66 s）
    "<PY>" -s tools\\demo_script.py --png            # 额外导出关键帧拼图
    "<PY>" -s tools\\demo_script.py --list           # 只列剧本，不播放
    "<PY>" -s tools\\demo_script.py --quiet          # 只出摘要（不逐行时间轴）
    "<PY>" -s tools\\demo_script.py --assets original # 对照原素材；默认三档说话用复用版

注：采样步长 `--dt`（默认 0.1 s 虚拟时间）越大跑得越快，但**会漏掉 <dt 的瞬态**；
验收素材轮换用默认值即可（切换间隔 ~6.4 s ≫ 0.1 s）。
剧本的 dur/stop 模拟音频忙状态，仅验收播放流程；不调用真实 TTS 或 LLM。
"""
from __future__ import annotations

import argparse
import dataclasses
import sys
import time
import typing
from pathlib import Path

AURA = Path(__file__).resolve().parents[1]
if str(AURA) not in sys.path:
    sys.path.insert(0, str(AURA))

from board.runtime.events import EventType                       # noqa: E402

from tools.demo_stage import LONG_TEXTS, StageCore                # noqa: E402

try:                                                              # 控制台常为 GBK
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


# --------------------------------------------------------------------------- #
# 剧本数据结构
# --------------------------------------------------------------------------- #
#: cue 种类 → 语义
#:   reset   重来（FSM 回 IDLE + 播放时间基归零）
#:   event   发一个真事件（走 FSM，非法转换会被拒并记录）
#:   reply   模拟"主机回复到达"（走 `accept_response`：代次校验 + emotion 分档选素材）
#:   stop    播报结束（`audio.playback_stopped` ⇒ 阶段机 blend → exit）
#:   cancel  打断（代次 +1 作废旧回复 + 平滑收起）
#:   mark    只打标记（不动状态机）
@dataclasses.dataclass(frozen=True)
class Cue:
    """剧本中的一"拍"：在剧本时间 `t`（秒）执行 `kind`。"""

    t: float
    kind: str
    value: typing.Any = None
    note: str = ""
    #: reply 用：计划播报时长（秒）—— 剧本自己计时，到点由外层发 `stop`。
    dur: float = 0.0


def _reply(t: float, text: str, emotion: str, action: str, dur: float,
           note: str = "") -> typing.List[Cue]:
    """一条"回复 + 到点停播"的组合（避免剧本里手写两拍时间对不上）。"""
    return [
        Cue(t, "reply", {"reply_text": text, "emotion": emotion,
                         "avatar_action": action}, note, dur),
        Cue(round(t + dur, 3), "stop", None, ""),
    ]


def _ask(t: float, note: str = "") -> typing.List[Cue]:
    """后续轮通过既有按键入口倾听，再送语音结束事件。

    首轮演完整唤醒；后续轮使用 BOARD_KEY_PRESSED → LISTENING → THINKING，
    避免为了进入思考而反复插入只有 0.2 秒的惊讶动作。
    """
    return [
        Cue(t, "event", EventType.BOARD_KEY_PRESSED,
            note or "└ 开新一轮：按键倾听（→ LISTENING）"),
        Cue(round(t + 0.4, 3), "event", EventType.AUDIO_VAD_END, ""),
    ]


# --------------------------------------------------------------------------- #
# 剧本正文（改这里就能试不同节奏）
# --------------------------------------------------------------------------- #
LONG_TEXT = LONG_TEXTS["长句 92 字"]
MID_TEXT = LONG_TEXTS["中句 29 字"]
SHORT_TEXT = LONG_TEXTS["短句 11 字"]

SCRIPT: typing.List[Cue] = [
    # ---- ① 待机（**对照组**：IDLE 无池 ⇒ 素材恒定，用于证明"轮换只在池内发生"）----
    Cue(0.0, "reset", None, "① 开机待机：IDLE（无池，素材应恒定 idle_normal）"),
    Cue(3.0, "mark", None, "   └ 静止 3 s 后再来人（给足对比时间）"),

    # ---- ② 到访 → PRESENT（有人时的待机，无池）----
    Cue(3.0, "event", EventType.SCENE_PERSON_ENTER, "② 来访者进入 → PRESENT"),

    # ---- ③ 唤醒（**burst 一次性动作**：必须整段播一次，绝不循环）----
    Cue(5.5, "event", EventType.AUDIO_KWS_DETECTED, "③ 关键词唤醒 → AWAKE（burst 惊讶，单次）"),

    # ---- ④ 倾听 → 思考（**刻意停顿**：体现"不急着说"的节奏感）----
    Cue(8.5, "event", EventType.AUDIO_VAD_END, "④ 倾听结束 → 思考（停顿 3 s）"),

    # ---- ⑤ 短句 · 中性档（短句不必轮换，观察起播与收口）----
    # 首轮唤醒播完自动进入 LISTENING，④再到 THINKING；后续轮用 _ask 的倾听入口。
    *_reply(11.5, SHORT_TEXT, "friendly", "", 3.4,
            "⑤b 短句 11 字 · 中性档（friendly 不在高涨表 ⇒ SPEAKING_NEUTRAL）"),

    # ---- ⑥ **主力镜头**：长句 · 中性档 ⇒ 23 s 足够看到口型池交替 ----
    *_ask(15.0, "⑥a 用户说完 → THINKING"),
    *_reply(15.5, LONG_TEXT, "neutral", "", 23.0,
            "⑥b 长句 92 字 · 中性档：观察口型池交替"),

    # ---- ⑦ 动作 + 高涨（ACK_NOD burst 播完自动接进播报 ⇒ 换档 SPEAKING）----
    *_ask(39.0, "⑦a 用户说完 → THINKING"),
    *_reply(39.5, "好的，我这就去办。", "happy", "ack_nod", 4.0,
            "⑦b 点头 + 高涨档：burst 播完接 SPEAKING（池 2 素材）"),

    # ---- ⑧ 低落档（SPEAKING_LOW ⇒ talking_low；素材缺失则回退 talking_normal）----
    *_ask(44.0, "⑧a 用户说完 → THINKING"),
    *_reply(44.5, "抱歉，这件事我帮不上忙，你先别急，我再想想别的办法。", "sad", "", 5.5,
            "⑧b 低落档：SPEAKING_LOW ⇒ talking_low（慢 / 低 / 轻）"),

    # ---- ⑨⑩ 高涨长句，说到一半被打断（验收"无论在哪一帧都能平滑收起"）----
    *_ask(50.5, "⑨a 用户说完 → THINKING"),
    Cue(51.0, "reply", {"reply_text": LONG_TEXT, "emotion": "excited",
                        "avatar_action": ""}, "⑨b 高涨长句起播（8 s 后打断）", 8.0),
    Cue(59.0, "cancel", None, "⑩ 打断：代次作废 + 平滑收起 exit（不该跳帧）"),

    # ---- ⑪ 重来（回到对照组，顺带验证 reset 零残留）----
    Cue(62.0, "reset", None, "⑪ 重来：FSM 回 IDLE + 播放时间基归零"),
    Cue(66.0, "mark", None, "⑫ 剧本结束（全剧 66 s 虚拟时间）"),
]


def script_end() -> float:
    """剧本总时长（最后一拍的 `t`；reply 的 `dur` 已由 `_reply` 展开成独立 `stop`）。"""
    return max(cue.t for cue in SCRIPT)


# --------------------------------------------------------------------------- #
# 回放器（**虚拟时钟**：不真 sleep ⇒ 毫秒级跑完全剧；--realtime 才按真实时间走）
# --------------------------------------------------------------------------- #
class Trace:
    """一次回放的原始记录（供摘要 / 拼图 / 后续单测消费）。"""

    def __init__(self) -> None:
        self.samples: typing.List[typing.Dict] = []                  # 采样点（帧元数据）
        self.switches: typing.List[typing.Dict] = []                 # 素材切换点 ★
        self.states: typing.List[typing.Tuple[float, str]] = []      # 状态变化点
        self.marks: typing.List[typing.Tuple[float, str]] = []       # 剧本标记
        self.events: typing.List[typing.Tuple[float, str]] = []      # 已执行事件
        self.rejected: typing.List[typing.Tuple[float, str]] = []    # 被 FSM 拒绝的事件
        self.errors: typing.List[str] = []                           # 脚本自身错误

    def reset(self) -> None:
        """清空全部记录（重播前调用，避免多轮轨迹串在一起 ⇒ 日志重复刷屏）。"""
        self.samples.clear()
        self.switches.clear()
        self.states.clear()
        self.marks.clear()
        self.events.clear()
        self.rejected.clear()
        self.errors.clear()

    def state_spans(self) -> typing.List[typing.Tuple[str, float, float]]:
        """`[(状态, 起, 止)]`（按状态变化点切段；末段用最后采样点封口）。"""
        if not self.states:
            return []
        end = self.samples[-1]["t"] if self.samples else self.states[-1][0]
        spans: typing.List[typing.Tuple[str, float, float]] = []
        for i, (t0, name) in enumerate(self.states):
            t1 = self.states[i + 1][0] if i + 1 < len(self.states) else end
            if spans and spans[-1][0] == name:
                spans[-1] = (name, spans[-1][1], t1)
            else:
                spans.append((name, t0, t1))
        return spans


class ScriptRunner:
    """剧本只调度事件；窗口和虚拟回放共用显示收尾及动作完成流程。"""

    def __init__(self, core: StageCore, dt: float = 0.1,
                 sample_every: float = 0.5) -> None:
        self.core = core
        self.dt = max(0.01, float(dt))
        self.sample_every = max(self.dt, float(sample_every))
        self.trace = Trace()
        self._next_sample = 0.0
        self._last_asset: typing.Optional[str] = None
        self._last_state: typing.Optional[str] = None
        self._last_meta: typing.Optional[typing.Dict] = None
        self._speaking = False       # 剧本模拟音频忙状态；不播放真实声音

    def reset(self) -> None:
        """重播同时清空状态、显示收尾、模拟音频与本轮轨迹。"""
        self.core.fsm.reset()
        self.core.reset_playback()
        self.core.reply_text = ""
        self._speaking = False
        self.trace.reset()
        self._next_sample = 0.0
        self._last_asset = self._last_state = self._last_meta = None

    # ---------------- 单拍执行 ----------------
    def _fire(self, cue: Cue, t: float) -> None:
        core = self.core
        if cue.note:                     # 任何一拍都能带标记（便于时间轴逐拍对齐）
            self.trace.marks.append((t, cue.note))
        if cue.kind == "mark":
            return
        if cue.kind == "reset":
            self._speaking = False
            core.fsm.reset()
            core.reset_playback()
            core.reply_text = ""
            self.trace.events.append((t, "reset → IDLE"))
            return
        if cue.kind == "event":
            before = core.fsm.rejected_count
            core.send(cue.value)
            if core.fsm.rejected_count > before:
                self.trace.rejected.append((t, str(cue.value)))
            else:
                self.trace.events.append((t, "%s → %s" % (cue.value, core.fsm.state.label)))
            return
        if cue.kind == "reply":
            gen = core.new_turn()
            data = dict(cue.value or {})
            ok = core.accept_response(gen, data)
            self._speaking = ok and cue.dur > 0.0
            flag = "" if ok else " [代次作废]"
            self.trace.events.append((
                t, "reply(emotion=%s action=%s) → %s%s"
                   % (data.get("emotion"), data.get("avatar_action") or "-",
                      core.fsm.state.label, flag)))
            return
        if cue.kind == "stop":
            self._speaking = False
            before = core.fsm.rejected_count
            core.send(EventType.AUDIO_PLAYBACK_STOP)
            if core.fsm.rejected_count > before:
                self.trace.rejected.append((t, str(EventType.AUDIO_PLAYBACK_STOP)))
            else:
                self.trace.events.append(
                    (t, "playback_stopped → %s" % core.fsm.state.label))
            return
        if cue.kind == "cancel":
            self._speaking = False
            core.cancel()
            core.send(EventType.AUDIO_CANCEL_REQUESTED)
            self.trace.events.append((t, "cancel → %s" % core.fsm.state.label))
            return
        self.trace.errors.append("未知 cue 种类：%s" % cue.kind)

    # ---------------- 采样 ----------------
    def _sample(self, t: float) -> typing.Optional[typing.Dict]:
        """取实际显示帧，并按正式播放器的策略处理一次性动作完成。"""
        core = self.core
        state = core.fsm.state.label
        if state != self._last_state:
            self.trace.states.append((t, state))
            self._last_state = state
        try:
            meta = core.display_frame(state, t)
        except Exception as exc:                    # 播放层异常不应中断剧本回放
            self.trace.errors.append("display_frame(%.2f) 抛异常：%r" % (t, exc))
            self._last_meta = None
            return
        if core.take_burst_finished():
            completion = core.burst_completion(state, self._speaking, core.emotion)
            if completion is not None:
                before = core.fsm.rejected_count
                core.send(*completion)
                if core.fsm.rejected_count > before:
                    self.trace.rejected.append((t, str(completion[0])))
                else:
                    self.trace.events.append((t, "动作段播完 → %s" % core.fsm.state.label))
        if not isinstance(meta, dict):
            self.trace.samples.append({"t": t, "state": state, "asset": None})
            self._last_meta = None
            return
        asset = str(meta.get("asset") or "")
        display_state = str(meta.get("display_state") or state)
        if self._last_asset is not None and asset != self._last_asset:
            previous_display = (self._last_meta or {}).get("display_state")
            self.trace.switches.append({
                "t": t, "from": self._last_asset, "to": asset, "state": display_state,
                "from_state": previous_display,
                "stage": meta.get("stage"), "index": meta.get("index"),
                "frames": meta.get("frames")})
        self._last_asset = asset
        row = {"t": t, "state": state, "asset": asset,
               "display_state": display_state,
               "transitioning": bool(meta.get("transitioning")),
               "stage": meta.get("stage"), "index": meta.get("index"),
               "frames": meta.get("frames"), "phase": meta.get("phase"),
               "speed": meta.get("speed"), "state_time": meta.get("state_time"),
               "burst": meta.get("burst")}
        self._last_meta = row
        self.trace.samples.append(row)
        return meta

    def _line(self, t: float) -> str:
        """一行时间轴（列：虚拟时刻 / 状态 / 阶段 / 素材 / 帧 / 状态内 t / 速度）。"""
        row = self._last_meta
        state = self._last_state or "-"
        if not row or not row.get("asset"):
            return "%7.2f  %-17s  （无素材 → 真机退 B2V 矢量）" % (t, state)
        return ("%7.2f  %-17s  %-5s  %-20s  %3d/%-3d  [%.2fs]  x%.2f"
                % (t, state, row.get("stage") or "-", row["asset"],
                   int(row.get("index") or 0) + 1, int(row.get("frames") or 0),
                   float(row.get("state_time") or 0.0),
                   float(row.get("speed") or 1.0)))

    # ---------------- 主循环 ----------------
    def run(self, realtime: bool = False, quiet: bool = False) -> Trace:
        """跑完全剧；`realtime=True` 按真实时间走（看它演），否则虚拟时钟全速。"""
        self.reset()
        end = script_end()
        cues = sorted(SCRIPT, key=lambda c: c.t)
        i = 0
        t = 0.0
        wall0 = time.perf_counter()
        if not quiet:
            print("   t(虚拟)  状态               阶段   素材                  帧       状态t    速度")
            print("  " + "-" * 86)
        while t <= end + 1e-9:
            while i < len(cues) and cues[i].t <= t + 1e-9:
                self._fire(cues[i], cues[i].t)
                i += 1
            self._sample(t)
            if t >= self._next_sample - 1e-9:
                self._next_sample = t + self.sample_every
                if not quiet:
                    print(self._line(t))
            if realtime:
                delay = (wall0 + t) - time.perf_counter()
                if delay > 0:
                    time.sleep(delay)
            t = round(t + self.dt, 6)
        self._sample(end)                            # 末帧补采（状态段封口）
        return self.trace


# --------------------------------------------------------------------------- #
# 摘要报告
# --------------------------------------------------------------------------- #
def report(trace: Trace, core: StageCore) -> None:
    """打印演出摘要：标记 → 事件 → 状态段 → **素材切换点** → 结论。"""
    bar = "=" * 88
    print("\n" + bar)
    print("=== 剧本标记 ===")
    for t, note in trace.marks:
        print("  %6.2fs  %s" % (t, note))

    print("\n=== 事件（已执行）===")
    for t, text in trace.events:
        print("  %6.2fs  %s" % (t, text))
    for t, text in trace.rejected:
        print("  %6.2fs  [被拒] %s（该状态下非法转换 —— 调整剧本时间点即可）" % (t, text))

    print("\n=== 状态段时长 ===")
    total = 0.0
    for name, t0, t1 in trace.state_spans():
        total += t1 - t0
        print("  %-18s %6.2f → %6.2f s   时长 %.2f s" % (name, t0, t1, t1 - t0))
    print("  %-18s 合计 %.2f s" % ("", total))

    print("\n=== ★ 素材切换点（跨素材池轮换的直接证据）===")
    if not trace.switches:
        print("  （无切换）")
    by_state: typing.Dict[str, typing.List[typing.Dict]] = {}
    for sw in trace.switches:
        by_state.setdefault(str(sw["state"]), []).append(sw)
    for state, items in by_state.items():
        print("  状态 %s   池 = %s" % (state, list(core.pool(state))))
        for i, sw in enumerate(items):
            gap = "" if i == 0 else "   +%.2fs" % (sw["t"] - items[i - 1]["t"])
            print("    %6.2fs  %-20s → %-20s  (idx=%s, stage=%s)%s"
                  % (sw["t"], sw["from"], sw["to"], sw.get("index"),
                     sw.get("stage"), gap))

    print("\n=== 池使用总览 ===")
    used: typing.Dict[str, typing.Set[str]] = {}
    for row in trace.samples:
        if row.get("asset"):
            used.setdefault(str(row.get("display_state") or row["state"]), set()).add(str(row["asset"]))
    for state in sorted(used):
        pool = list(core.pool(state))
        got = sorted(used[state])
        mark = "轮换" if len(got) > 1 else "恒定"
        print("  %-18s %s  用到 %d 个：%s（池 %d 个）"
              % (state, mark, len(got), got, len(pool)))

    if trace.errors:
        print("\n=== 脚本错误 ===")
        for err in trace.errors:
            print("  ! %s" % err)

    rotated = [s for s, a in used.items() if len(a) > 1 and len(core.pool(s)) > 1]
    # 只统计同一显示状态的池内轮换，排除开始说话与收尾后的跨状态切换。
    pool_sw = [sw for sw in trace.switches
               if sw.get("from_state") == sw["state"]
               and len(core.pool(str(sw["state"]))) > 1
               and sw["from"] in core.pool(str(sw["state"]))
               and sw["to"] in core.pool(str(sw["state"]))]
    print("\n=== 结论 ===")
    print("  有池且发生轮换的状态：%s" % (rotated or "（无）"))
    all_enter = all(sw.get("index") == 0
                    for sw in pool_sw)
    print("  池内换素材（共 %d 次）每次都从首帧起播：%s"
          % (len(pool_sw), "是" if all_enter else "否！"))
    print(bar)


# --------------------------------------------------------------------------- #
# 关键帧拼图（可选；只作留档样例，**不能替代真窗口验收**）
# --------------------------------------------------------------------------- #
def _font(size: int = 13):
    """中文字体（与 Tk 版同款 Microsoft YaHei）；找不到则退默认位图字体。"""
    from PIL import ImageFont
    for name in ("msyh.ttc", "simhei.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            continue
    return ImageFont.load_default()


def export_png(trace: Trace, core: StageCore, outdir) -> Path:
    """把**每个 (状态, 素材) 首次出现**时的代表帧拼成一张对比图。

    取材走 `core.sequence(state, asset)`（真素材目录，缺帧自动回退），
    因此这里展示的就是**播放层实际会画的素材**；帧号取采样时的 `index`。

    ⚠ 静态图看不出"交替感"，仅用于确认"池里每个素材都真的长得出来"。
    """
    from PIL import Image, ImageDraw
    picks: typing.List[typing.Tuple[float, str, str, int]] = []
    seen: typing.Set[typing.Tuple[str, str]] = set()
    for row in trace.samples:
        asset = row.get("asset")
        if not asset:
            continue
        display_state = str(row.get("display_state") or row["state"])
        key = (display_state, str(asset))
        if key in seen:
            continue
        seen.add(key)
        picks.append((float(row["t"]), display_state, str(asset),
                      int(row.get("index") or 0)))

    tiles: typing.List[typing.Tuple[typing.Any, str]] = []
    for t, state, asset, idx in picks:
        got = core.sequence(state, asset)          # (frames, fps, burst, 实际素材名)
        if not got:
            continue
        frames = got[0]
        image = frames[max(0, min(idx, len(frames) - 1))].copy()
        image.thumbnail((232, 240), Image.LANCZOS)
        tiles.append((image, "%5.1fs %s\n%s  #%d/%d"
                      % (t, state, asset, idx + 1, len(frames))))

    if not tiles:
        raise RuntimeError("没有任何可导出帧（素材缺失？）")

    cols = 4
    rows = (len(tiles) + cols - 1) // cols
    cw, ch = 244, 272                        # 单元格（含标签区）
    canvas = Image.new("RGBA", (cw * cols, ch * rows), (28, 32, 38, 255))
    draw = ImageDraw.Draw(canvas)
    font = _font(13)
    for i, (img, label) in enumerate(tiles):
        cx, cy = (i % cols) * cw, (i // cols) * ch
        canvas.alpha_composite(img, (cx + 6, cy + 6))
        draw.multiline_text((cx + 6, cy + 6 + img.height + 4), label,
                            fill=(210, 218, 226, 255), font=font)

    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / "demo_script_assets.png"
    canvas.convert("RGB").save(path)
    return path

# --------------------------------------------------------------------------- #
# 真窗口演出（可选；`--window`）—— 把剧本**画出来**，用于肉眼验收观感
# --------------------------------------------------------------------------- #
def run_window(core: StageCore, tick_ms: int = 33) -> Trace:
    """按剧本时间轴驱动真窗口演出（渲染口径与 `demo_stage.StageApp` 一致）。

    与 `ScriptRunner` **共用同一套 `_fire`**（不复制剧本逻辑），差别只在时钟：
    这里用 `time.monotonic()` 真实时间推进（`tick_ms` 只是重排间隔，实测 ≈12 fps），把每帧画到 Tk 画布上，
    并把剧本标记 / 已执行事件逐条落到右侧日志，便于**边看边核对**。

    ⚠ 为什么不直接开 `demo_stage.py`：那条路的 LLM 是 Mock（`mock_adapter.py`
    固定 `emotion="friendly"`）⇒ 窗口里**永远演不到** `happy/excited`（`SPEAKING`）
    与 `sad/low`（`SPEAKING_LOW`）两档；本函数直接按剧本注入 emotion，三档齐全。

    返回本次回放的 `Trace`（演出结束后可继续 `report()` / `export_png()`）。
    """
    import tkinter as tk
    from PIL import Image, ImageTk        # Image 用于 thumbnail 的重采样常量（漏导入会首帧就 NameError）

    cues = sorted(SCRIPT, key=lambda c: c.t)
    end = script_end()
    stage_w, stage_h = 320, 360                       # 与 demo_stage.STAGE_W/H 同口径
    runner = ScriptRunner(core, dt=tick_ms / 1000.0)
    runner.reset()
    trace = runner.trace

    root = tk.Tk()
    root.title("AURA 演示剧本演出（%d 拍 / 全剧 %.0f s）" % (len(cues), end))
    root.configure(bg="#1b1e24")

    canvas = tk.Canvas(root, width=stage_w, height=stage_h, bg="#101318",
                       highlightthickness=0)
    canvas.pack(side="left", padx=(10, 6), pady=10)

    right = tk.Frame(root, bg="#1b1e24")
    right.pack(side="left", fill="both", expand=True, padx=(0, 10), pady=10)
    state_lbl = tk.Label(right, text="IDLE", fg="#7ee787", bg="#1b1e24",
                         font=("Microsoft YaHei", 16, "bold"), anchor="w")
    state_lbl.pack(anchor="w")
    hud = tk.Label(right, text="", fg="#c9d1d9", bg="#1b1e24", justify="left",
                   anchor="w", font=("Consolas", 10))
    hud.pack(anchor="w", pady=(6, 0))
    log = tk.Text(right, width=48, height=20, bg="#15181d", fg="#c9d1d9",
                  font=("Microsoft YaHei", 9), wrap="word")
    log.pack(anchor="w", fill="both", expand=True, pady=(6, 0))
    log.configure(state="disabled")

    wall = [time.monotonic()]

    def log_add(text: str) -> None:
        log.configure(state="normal")
        log.insert("end", "%6.2fs  %s\n" % (time.monotonic() - wall[0], text))
        log.see("end")
        log.configure(state="disabled")

    cursor = [0]                                      # 下一拍待触发的下标
    seen_mk = [0]                                     # 已落日志的标记 / 事件计数
    seen_ev = [0]
    photo = [None]                                    # 必须持引用，否则被 GC
    done = [False]
    scheduled = [False]                               # tick 链是否已排进 after 队列（防重播排出第二条链）

    def tick() -> None:
        tick_started = time.monotonic()
        scheduled[0] = False
        t = time.monotonic() - wall[0]
        while cursor[0] < len(cues) and cues[cursor[0]].t <= t + 1e-9:
            runner._fire(cues[cursor[0]], cues[cursor[0]].t)
            cursor[0] += 1
        meta = runner._sample(t)                    # 与无窗口回放共用同一条完整播放回路
        for _t0, text in trace.marks[seen_mk[0]:]:
            log_add(text)
        seen_mk[0] = len(trace.marks)
        for _t0, text in trace.events[seen_ev[0]:]:
            log_add("· %s" % text)
        seen_ev[0] = len(trace.events)

        state = core.fsm.state.label
        display_state = str((meta or {}).get("display_state") or state)
        state_lbl.configure(text=state if display_state == state else
                            "%s（显示 %s）" % (state, display_state))
        if meta is None:
            canvas.delete("all")
            canvas.create_text(stage_w // 2, stage_h // 2,
                               text="无素材 → 真机退 B2V 矢量主体", fill="#6f7a87")
            hud.configure(text="asset : -（回退链为空）")
        else:
            img = meta["image"].copy()
            img.thumbnail((stage_w, stage_h), Image.LANCZOS)
            photo[0] = ImageTk.PhotoImage(img)
            canvas.delete("all")
            canvas.create_image(stage_w // 2, stage_h // 2, image=photo[0])
            hud.configure(text=(
                "asset  : %s   （池 %d 个）\n"
                "frame  : %d/%d  %s\n"
                "phase  : %.3fs   speed: %.3f\n"
                "state_t: %.2fs   stage: %s\n"
                "虚时   : %.2fs / %.0fs"
                % (meta["asset"], len(core.pool(display_state)),
                   int(meta.get("index") or 0) + 1, int(meta.get("frames") or 0),
                   "burst" if meta.get("burst") else "loop",
                   float(meta.get("phase") or 0.0), float(meta.get("speed") or 1.0),
                   float(meta.get("state_time") or 0.0), meta.get("stage") or "-",
                   min(t, end), end)))
        if t < end + 0.4:
            scheduled[0] = True
            root.after(max(1, tick_ms - int((time.monotonic() - tick_started) * 1000)), tick)
        elif not done[0]:                           # 演出结束 ⇒ 自然停链（重播时由 replay 重新起链）
            done[0] = True
            log_add("—— 演出结束（全剧 %.0f s）——" % end)

    def replay(_event=None) -> None:
        """F5 重播：FSM 回 IDLE + 播放时间基归零（与剧本 ⑪ 同口径，零残留）。"""
        runner.reset()
        cursor[0], seen_mk[0], seen_ev[0], done[0] = 0, 0, 0, False
        wall[0] = time.monotonic()
        log_add("—— 重播（F5）——")
        if not scheduled[0]:                          # ★ 演出结束后 tick 链已停 ⇒ 必须重新起链，否则"点了没反应"
            scheduled[0] = True
            root.after(tick_ms, tick)

    tk.Label(right, text="F5 = 重播全剧；直接关窗即退出", fg="#6f7a87",
             bg="#1b1e24", font=("Microsoft YaHei", 9)).pack(anchor="w", pady=(6, 0))
    tk.Button(right, text="重播（F5）", width=14, command=replay).pack(
        anchor="w", pady=(4, 0))
    root.bind("<F5>", replay)
    scheduled[0] = True                               # 首轮起链（与 replay 里的补链互斥）
    root.after(tick_ms, tick)
    root.mainloop()
    return trace


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def _cue_brief(value: typing.Any) -> str:
    """`--list` 用：把 cue 的 value 压成一行短描述。"""
    if isinstance(value, dict):
        return "%s / %s / %s" % (value.get("emotion"),
                                 value.get("avatar_action") or "-",
                                 str(value.get("reply_text"))[:16] + "…")
    return "" if value is None else str(value)


def create_demo_core(assets: str = "reuse") -> StageCore:
    """Select preview assets for this temporary script, without changing production pools."""
    if assets == "original":
        return StageCore()
    if assets != "reuse":
        raise ValueError("Unknown demo asset selection: " + assets)
    delivery = AURA.parent / "deliverables" / "2026-10-06_avatar_reuse"
    if not (delivery / "preview_script.py").is_file():
        raise FileNotFoundError("复用交付目录缺失，请保留共享目录结构，或用 --assets original 查看原版")
    if str(delivery) not in sys.path:
        sys.path.insert(0, str(delivery))
    from preview_script import ReusePreviewPlayer
    return ReusePreviewPlayer()


def main(argv: typing.Optional[typing.Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="AURA 演示剧本（跨素材池轮换观感验收；复用 demo_stage.StageCore）")
    parser.add_argument("--dt", type=float, default=0.1, help="虚拟时钟步长（秒）")
    parser.add_argument("--sample-every", type=float, default=0.5,
                        help="时间轴打印间隔（秒）")
    parser.add_argument("--realtime", action="store_true",
                        help="按真实时间回放（全剧约 66 s；用于看着它演一遍）")
    parser.add_argument("--quiet", action="store_true",
                        help="不打印逐行时间轴，只出摘要")
    parser.add_argument("--png", action="store_true", help="额外导出关键帧拼图")
    parser.add_argument("--outdir", default="", help="拼图输出目录（默认 docs/demo_stage）")
    parser.add_argument("--list", action="store_true", help="只列剧本，不回放")
    parser.add_argument("--window", action="store_true",
                        help="开真窗口按剧本演出（约 66 s；肉眼验收观感）")
    parser.add_argument("--qt-window", action="store_true", help="使用 Qt 窗口演出")
    parser.add_argument("--assets", choices=("reuse", "original"), default="reuse",
                        help="临时剧本使用的素材：reuse 为新口型复用版，original 为原版对照")
    args = parser.parse_args(argv)

    if args.list:
        print("=== 演示剧本（%d 拍 / 全剧 %.0f s）===" % (len(SCRIPT), script_end()))
        for cue in sorted(SCRIPT, key=lambda c: c.t):
            print("  %6.2fs  %-6s %s"
                  % (cue.t, cue.kind, cue.note or _cue_brief(cue.value)))
        return 0

    print("=== 演示剧本：跨素材池轮换观感验收 ===")
    print("全剧 %.0f s ｜ 步长 %.2f s ｜ 模式 %s"
          % (script_end(), args.dt,
             "真窗口按真实时间演出" if (args.window or args.qt_window) else
             ("按真实时间" if args.realtime else "虚拟时钟全速")))
    core = create_demo_core(args.assets)
    print("中性说话素材：%s" % " / ".join(core.pool("SPEAKING_NEUTRAL")))
    if args.qt_window:
        delivery = AURA.parent / "deliverables" / "2026-10-06_avatar_reuse"
        if str(delivery) not in sys.path:
            sys.path.insert(0, str(delivery))
        from preview_window_qt import run_window as run_qt_window
        trace = run_qt_window(core)
        return 1 if trace.errors or trace.rejected else 0
    if args.window:                      # 真窗口演出（肉眼验收；过程日志已在窗口里逐条显示）
        return 1 if run_window(core).errors else 0
    runner = ScriptRunner(core, dt=args.dt, sample_every=args.sample_every)
    trace = runner.run(realtime=args.realtime, quiet=args.quiet)
    report(trace, core)
    if args.png:
        outdir = args.outdir or (AURA / "docs" / "demo_stage")
        try:
            print("拼图 → %s" % export_png(trace, core, outdir))
        except Exception as exc:                # 拼图失败不该影响剧本结论
            print("[拼图失败] %r（不影响剧本结论）" % exc)
    return 1 if trace.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())




