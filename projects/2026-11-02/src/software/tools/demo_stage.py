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


from board.interaction.avatar_player import AvatarPlayer as StageCore


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
        gen = self.core.new_turn()              # Capture before starting the worker: cancellation can race its startup.
        self.busy = True
        self._log("→ 请求：%s（代次 %d）" % (transcript[:30], self.core.talk_gen))
        threading.Thread(target=self._worker, args=(transcript, gen), daemon=True).start()

    def _worker(self, transcript: str, gen: int) -> None:
        request = DialogueRequest(request_id="stage-%d" % int(time.time() * 1000),
                                  audio_generation_id=gen, transcript=transcript,
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
        tick_started = time.monotonic()
        # 真实语音收尾：TTS 刚播完 → 发**既有**事件 AUDIO_PLAYBACK_STOP（状态机自己回 IDLE）
        if self.tts is not None and self.tts.poll():
            # #5：说完 → 先驱动三段式**平滑收起**（blend → exit），再送状态机事件
            self.core.send(EventType.AUDIO_PLAYBACK_STOP)
            self._log("TTS 播报结束 → 显示层保留播报素材完成收尾｜ audio.playback_stopped（%s）"
                      % self.core.fsm.state.label)
        state = self.core.fsm.state.label
        meta = self.core.display_frame(state, time.monotonic())
        self.state_label.configure(text=state)
        # P0-1：动作段（burst）刚播完 → 语音还在就接进播报档继续演（不再停在末帧）
        if self.core.take_burst_finished():
            completion = self.core.burst_completion(
                state, self.tts is not None and self.tts.is_busy(), self.core.emotion)
            if completion is not None:
                self.core.send(*completion)
                self._log("动作段播完 → %s" % self.core.fsm.state.label)
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
        self.root.after(max(1, TICK_MS - int((time.monotonic() - tick_started) * 1000)), self._tick)

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
        sampled = []
        for k in range(24):                                            # 约 10 秒 @0.4s
            m = core.frame_at(state, base + 0.4 * (k + 1))
            trace.append(m["index"] if m else -1)
            sampled.append(m)
        traces.append(trace)
        note("长句 第%d次入场：state=%s asset=%s ｜ 帧序列 %d 点 / 唯一帧 %d "
             "｜ SOP: 匀速化=%s 三段式=%s 放慢=%.1f"
             % (round_no, state, meta["asset"] if meta else "-", len(trace),
                len(set(trace)), "有" if diffs else "无",
                "有" if seg is not None else "无", slowdown))
        for k, m in enumerate(sampled[:8]):                           # Reuse the frames actually sampled in time order.
            if m:
                tiles.append(("%s r%d t=%.1fs f%d" % (state, round_no, 0.4 * (k + 1),
                                                      m["index"] + 1), m["image"]))
        now(9.6)                                                     # Keep subsequent states on a monotonic clock.
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
