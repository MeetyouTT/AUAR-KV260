# -*- coding: utf-8 -*-
"""TTS（本地播报）—— 板端**唯一 TTS**（`audio/__init__.py` 已约定 A3 加入本模块）。

契约与红线
----------
- 本模块只负责**播放**，不做对话编排（编排在上层）；
- 播完发布**既有**事件 `EventType.AUDIO_PLAYBACK_STOP`（**不新增事件类型** —— 人3 任务书 §五红线）。
  这条很重要：状态机里 `SPEAKING* / ACK_NOD / PUZZLED → IDLE` 的收尾全靠它，
  以前演示台是"点按钮假装播完"，接上 TTS 后就是**真实语音播完**驱动。

后端（依赖可选，风格与 `kws.py` 一致）
-----------------------------------
- `SapiTtsBackend`：Windows 内置 SAPI（`System.Speech`），**零第三方依赖**，
  经 PowerShell 子进程调用；本机实测有中文女声 `Microsoft Huihui Desktop`。
- `ScriptedTtsBackend`：不出声、只记时间（单测 / 无音频设备环境）。

设计要点
--------
- `speak_async()` 返回句柄，`is_busy()` 判忙，`poll()` 在"刚播完"时发事件；
- **语气层（S1）**：`speak_async(text, style)` 传 `tts_style.TtsStyle` 时改用 SSML（逐段
  rate/pitch/volume + 段间 break），韵律由 **LLM 的 `emotion`** 驱动（见 `tts_style.py`，
  分档词表与 `fsm` 同源）；**不传 `style` = 旧行为**，这就是回退开关；
- 文本转义：PowerShell 单引号字符串里 `'` 需翻倍 —— 中文与常用标点安全；
- 超时保护：`TtsConfig.timeout_s`；异常一律降级（打印 + 视为播完），
  不允许"TTS 挂了把状态机卡在 SPEAKING"。
"""
from __future__ import annotations

import abc
import dataclasses
import os
import pathlib
import shutil
import subprocess
import threading
import time
import typing
import zlib


class TtsUnavailable(RuntimeError):
    """后端不可用（无 PowerShell / 无语音）时抛出（调用方应降级而不是崩溃）。"""


@dataclasses.dataclass
class TtsConfig:
    """TTS 运行时配置（默认值对准本机实测：Huihui 中文女声）。"""

    engine: str = "sapi"                             # sapi | scripted | vits
    voice: str = "Microsoft Huihui Desktop"
    rate: int = 0                                    # -10 ~ 10（0 = 正常语速，仅 sapi）
    volume: int = 100                                # 0 ~ 100（仅 sapi）
    timeout_s: float = 90.0                          # 单句播报上限（防卡死）
    # —— 本地神经 TTS（engine="vits"，sherpa-onnx，见 SherpaTtsBackend）——
    tts_model: str = ""                              # 模型目录名或绝对路径；空 = 在 models/tts 下自动挑
    sid: int = 0                                     # 说话人 ID（多说话人模型，如 aishell3 有 174 个）
    speed: float = 1.0                               # 基础语速（再乘 tts_style 的 rate 档位）
    num_threads: int = 2                             # CPU 线程


class TtsBackend(abc.ABC):
    """播报后端抽象（可替换：SAPI / 未来板端音频设备）。"""

    @abc.abstractmethod
    def speak_async(self, text: str, ssml: typing.Optional[str] = None,
                    style: typing.Any = None) -> typing.Any:
        """开始播报，返回句柄（马上返回，不等播完）。

        - `ssml` 非空 → 后端**应改用 SSML 播报**（韵律由 `tts_style` 生成，SAPI 用）；
        - `style` 是 `tts_style.TtsStyle`（神经 TTS 用它换算语速 `speed`）；
        - 两者都为 None → 纯文本、恒定语气（向后兼容 = 回退路径）。
        """

    @abc.abstractmethod
    def is_busy(self, handle: typing.Any) -> bool:
        """句柄对应播报是否仍在进行。"""


class ScriptedTtsBackend(TtsBackend):
    """不出声的假后端：按 `chars / chars_per_second` 估算播报时长（可测性）。"""

    def __init__(self, chars_per_second: float = 4.5) -> None:
        self.chars_per_second = float(chars_per_second)
        self.spoken: typing.List[str] = []

    def speak_async(self, text: str, ssml: typing.Optional[str] = None,
                    style: typing.Any = None) -> typing.Dict:
        # SSML 只是韵律包装，时长仍按**纯文本**字数估算（含标点，与旧行为一致）
        seconds = len(str(text)) / (self.chars_per_second or 4.5)
        handle = {"text": str(text), "until": time.monotonic() + seconds,
                  "ssml": bool(ssml)}
        self.spoken.append(str(text))
        return handle

    def is_busy(self, handle: typing.Any) -> bool:
        if not handle:
            return False
        return time.monotonic() < handle.get("until", 0.0)


class SapiTtsBackend(TtsBackend):
    """Windows SAPI 播报后端（PowerShell 子进程，**零 Python 依赖**）。"""

    def __init__(self, config: typing.Optional[TtsConfig] = None) -> None:
        self.config = config or TtsConfig()
        self._powershell = shutil.which("powershell") or shutil.which("pwsh")
        if not self._powershell:
            raise TtsUnavailable("找不到 powershell.exe，无法使用 SAPI 播报")

    def _script(self, text: str, ssml: typing.Optional[str] = None) -> str:
        """构造脚本：选声音（失败则用默认）+ 设语速/音量 + 同步 Speak / SpeakSsml。

        `ssml` 非空 → 走 `SpeakSsml`（逐段韵律，见 `tts_style`）；否则走旧的 `Speak`。
        PowerShell 单引号字符串里 `'` 需翻倍；SSML 里的 `"` 在单引号内无需处理。
        """
        cfg = self.config
        safe_voice = str(cfg.voice).replace("'", "''")
        head = ("Add-Type -AssemblyName System.Speech; "
                "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
                "try { $s.SelectVoice('%s') } catch { }; "
                "$s.Rate = %d; $s.Volume = %d; "
                % (safe_voice, int(cfg.rate), int(cfg.volume)))
        if ssml:
            safe_ssml = str(ssml).replace("'", "''")
            return head + "$s.SpeakSsml('%s'); $s.Dispose()" % safe_ssml
        safe_text = str(text).replace("'", "''")
        return head + "$s.Speak('%s'); $s.Dispose()" % safe_text

    def speak_async(self, text: str, ssml: typing.Optional[str] = None,
                    style: typing.Any = None):
        return subprocess.Popen(
            [self._powershell, "-NoProfile", "-Command", self._script(text, ssml)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def is_busy(self, handle: typing.Any) -> bool:
        return handle is not None and handle.poll() is None


# --------------------------------------------------------------------------- #
# 本地神经 TTS（sherpa-onnx · VITS 中文，CPU）—— S2 新增；依赖可选、惰性导入
#
# 依据：D5 §14.4 / W12-04「中文 TTS：已验证中文 VITS，不满意再比 Kokoro」。
# 音色 = `TtsConfig.sid`（多说话人模型），语速 = `TtsConfig.speed` × `tts_style` 档位。
# --------------------------------------------------------------------------- #

#: ASCII 链接根的**候选链**（`kaldifst` 只能打开窄字符路径，必须整条路径都是 ASCII）。
_ASCII_LINK_ROOT_CANDS: typing.Tuple[str, ...] = (
    os.path.expandvars(r"%LOCALAPPDATA%\aura_tts_links"),
    r"C:\ProgramData\aura_tts_links",
    r"C:\aura_tts_links",
)


def _ascii_link_root() -> typing.Optional[pathlib.Path]:
    """挑一个**纯 ASCII 且可写**的链接根；都不行则返回 None（调用方退回原路径）。"""
    for raw in _ASCII_LINK_ROOT_CANDS:
        cand = pathlib.Path(raw)
        if not all(ord(c) < 128 for c in str(cand)):
            continue
        try:
            cand.mkdir(parents=True, exist_ok=True)
        except OSError:
            continue
        return cand
    return None


def _safe_link_name(path: pathlib.Path) -> str:
    """链接名必须纯 ASCII：只保留 ASCII 字母数字与 `._-`，再拼目标路径哈希。"""
    keep = "".join(ch for ch in path.name
                   if ord(ch) < 128 and (ch.isalnum() or ch in "._-"))
    tag = zlib.crc32(str(path).encode("utf-8")) & 0xFFFFFFFF
    return ("%s_%08x" % (keep, tag)) if keep else ("link_%08x" % tag)


def tts_model_root() -> pathlib.Path:
    """`models/tts`（board/runtime/audio/tts.py → 上溯 3 级到工程根）。"""
    return pathlib.Path(__file__).resolve().parents[3] / "models" / "tts"


def ascii_path(path: typing.Any) -> pathlib.Path:
    """把可能含非 ASCII 的模型目录换成 **ASCII junction** 再返回。

    根因：sherpa-onnx 依赖的 **kaldifst 用窄字符路径**打开 `.fst`，遇到本工程路径里的
    `、`/中文会直接 `Error opening input stream`（实测 2026-10-04）。用
    `mklink /J`（免管理员）建一个 ASCII 链接即可绕开；已是 ASCII 则原样返回。
    """
    p = pathlib.Path(path).resolve()
    if all(ord(c) < 128 for c in str(p)):
        return p
    root = _ascii_link_root()
    if root is None:
        return p
    # 链接名 = ASCII 安全前缀 + 目标哈希：同一目录恒定复用，换路径也不会误指旧目标
    link = root / _safe_link_name(p)
    if not link.exists():
        subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(p)],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return link if link.exists() else p


def _model_onnx(d: pathlib.Path) -> typing.Optional[pathlib.Path]:
    """模型目录里的 onnx：`model.onnx` 优先，其次 int8 量化版 `model.int8.onnx`。"""
    for name in ("model.onnx", "model.int8.onnx"):
        if (d / name).is_file():
            return d / name
    return None


def find_tts_model(name_or_path: typing.Any = "") -> typing.Optional[pathlib.Path]:
    """定位 TTS 模型目录：显式路径/目录名优先；否则在 `models/tts` 下自动挑第一个可用模型。"""
    if name_or_path:
        p = pathlib.Path(str(name_or_path))
        for cand in ((p,) if p.is_absolute() else (p, tts_model_root() / p)):
            if cand.is_dir():
                return cand
        return None
    root = tts_model_root()
    if not root.is_dir():
        return None
    # 自动挑选顺序：**VITS 优先**（D5 §14.4「先试现成中文 VITS，不满意再比 Kokoro」），
    # 同族内按目录名排序，保证结果稳定可复现。
    dirs = sorted((d for d in root.iterdir()
                   if d.is_dir() and _model_onnx(d) is not None),
                  key=lambda d: (0 if d.name.startswith("vits") else 1, d.name))
    return dirs[0] if dirs else None


class _SherpaHandle:
    """神经 TTS 句柄：合成线程 + sounddevice 播放控制。

    `kill()` 与 `TtsPlayer.stop()` 的调用约定对齐（`stop()` 会调 `handle.kill()`）：
    停声 = 置停止标志 + `sd.stop()`（满足 T19「停声要快」）。
    """

    def __init__(self, sd: typing.Any) -> None:
        self._sd = sd
        self.thread: typing.Optional[threading.Thread] = None
        self.stop_requested = False
        self.error: typing.Any = None

    def kill(self) -> None:
        self.stop_requested = True
        try:
            self._sd.stop()
        except Exception:
            pass


class SherpaTtsBackend(TtsBackend):
    """离线神经 TTS（sherpa-onnx VITS 中文，CPU 合成 + sounddevice 播放）。

    与 `SapiTtsBackend` 的差别：**能自然表达语气**（`speed` 与 prosody 由模型韵律承担），
    且完全离线、可冻结；代价是首次加载模型（实测 0.6 s）与音色由模型决定。
    """

    def __init__(self, config: typing.Optional[TtsConfig] = None) -> None:
        self.config = config or TtsConfig()
        try:
            import numpy          # noqa: F401  —— 只确认依赖存在（波形重采样要用）
            import sherpa_onnx
            import sounddevice as sd
        except Exception as exc:
            raise TtsUnavailable("本地神经 TTS 依赖缺失（sherpa-onnx / sounddevice / numpy）：%s" % exc)
        self._sherpa = sherpa_onnx
        self._sd = sd
        found = find_tts_model(self.config.tts_model)
        if found is None:
            raise TtsUnavailable("未找到 TTS 模型目录（models/tts/*，需含 model.onnx）")
        self.model_dir = ascii_path(found)
        self._tts = self._build_tts()
        try:
            self.sample_rate = int(self._tts.sample_rate)
            self.num_speakers = int(self._tts.num_speakers)
        except Exception:
            self.sample_rate, self.num_speakers = 0, 0
        try:
            self.device_rate = int(sd.query_devices(kind="output")["default_samplerate"])
        except Exception:
            self.device_rate = 0

    def _build_tts(self) -> typing.Any:
        """按模型目录内容构造 `OfflineTts`：**Kokoro**（有 `voices.bin`）/ **VITS** 两分支。"""
        d = self.model_dir
        onnx = _model_onnx(d)
        if onnx is None or not (d / "tokens.txt").is_file():
            raise TtsUnavailable("模型目录不完整（需 onnx + tokens.txt）：%s" % d)
        # 规则 fst：两个包命名不同（VITS `phone/date/number.fst`；Kokoro `*-zh.fst`），
        # 统一按前缀挑，避免各写一份分支。
        fsts = [str(p) for p in sorted(d.glob("*.fst"))
                if p.name.split(".")[0].split("-")[0] in ("phone", "date", "number")]
        num_threads = int(self.config.num_threads)

        if (d / "voices.bin").is_file():                 # ── Kokoro（多语，必须给 lexicon）
            lexicons = [str(d / n) for n in
                        ("lexicon-zh.txt", "lexicon-us-en.txt", "lexicon-gb-en.txt")
                        if (d / n).is_file()]
            kokoro = self._sherpa.OfflineTtsKokoroModelConfig(
                model=str(onnx), voices=str(d / "voices.bin"),
                tokens=str(d / "tokens.txt"), lexicon=",".join(lexicons),
                data_dir=str(d / "espeak-ng-data") if (d / "espeak-ng-data").is_dir() else "",
                dict_dir=str(d / "dict") if (d / "dict").is_dir() else "")
            self.kind = "kokoro"
            model = self._sherpa.OfflineTtsModelConfig(kokoro=kokoro,
                                                       num_threads=num_threads)
        else:                                            # ── VITS（icefall / HF 系列）
            lex = d / "lexicon.txt"
            vits = self._sherpa.OfflineTtsVitsModelConfig(
                model=str(onnx), lexicon=str(lex) if lex.is_file() else "",
                tokens=str(d / "tokens.txt"))
            self.kind = "vits"
            model = self._sherpa.OfflineTtsModelConfig(vits=vits,
                                                       num_threads=num_threads)

        cfg = self._sherpa.OfflineTtsConfig(
            model=model, rule_fsts=",".join(fsts), max_num_sentences=1)
        return self._sherpa.OfflineTts(cfg)

    def speed_for(self, style: typing.Any = None) -> float:
        """语速 = 基础 `speed` × 韵律档位乘子，限幅 `[0.5, 2.0]`（防越界到听不懂）。

        乘子来自 `tts_style.rate_multiplier()` —— 与 SAPI 的关键字档**同源**：
        同一句 `emotion` 在 SAPI 上体现为 `rate=slow/fast`，在这里体现为 `speed=0.9/1.12`。
        """
        base = float(self.config.speed or 1.0)
        if style is None:
            return max(0.5, min(base, 2.0))
        from .tts_style import rate_multiplier
        return max(0.5, min(base * rate_multiplier(style), 2.0))

    def _play(self, samples: typing.Any, sample_rate: int) -> None:
        """播放波形；**采样率与声卡不一致时做线性重采样**（如 8 kHz 模型）。

        sounddevice 的采样率上限/下限因设备而异，直接 `play(8k)` 会报
        `Invalid sample rate`，故统一重采样到本机默认输出率。
        """
        import numpy as np
        data = np.asarray(samples, dtype="float32")
        rate = int(sample_rate or 0)
        target = int(self.device_rate or 0)
        if rate and target and rate != target:
            n = max(1, int(round(len(data) * target / float(rate))))
            idx = np.linspace(0.0, len(data) - 1.0, n)
            data = np.interp(idx, np.arange(len(data)), data).astype("float32")
            rate = target
        self._sd.play(data, rate or None)

    def speak_async(self, text: str, ssml: typing.Optional[str] = None,
                    style: typing.Any = None) -> _SherpaHandle:
        """合成 + **异步播放**（线程内），立即返回句柄。

        SSML 对本后端无意义（韵律由模型承担）→ 只用纯文本；语气通过 `style` 换成 `speed`。
        """
        handle = _SherpaHandle(self._sd)
        speed = self.speed_for(style)
        sid = int(self.config.sid)
        tts, plain = self._tts, str(text)

        def run() -> None:
            try:
                audio = tts.generate(plain, sid=sid, speed=speed)
                if handle.stop_requested:
                    return
                self._play(audio.samples, audio.sample_rate)
            except Exception as exc:                       # 合成失败不许静默
                handle.error = exc
                print("[tts] 神经 TTS 合成失败：%s" % exc, flush=True)

        thread = threading.Thread(target=run, daemon=True)
        handle.thread = thread
        thread.start()
        return handle

    def is_busy(self, handle: typing.Any) -> bool:
        """忙 = 还在合成，或声卡仍在放。"""
        if handle is None:
            return False
        if handle.thread is not None and handle.thread.is_alive():
            return True
        try:
            stream = self._sd.get_stream()
            return bool(stream is not None and getattr(stream, "active", False))
        except Exception:
            return False


class TtsPlayer:
    """对外门面：一句话播报 + 「播完发事件」。

    典型用法：
        player.speak_async(reply_text)      # 玩偶"开口"
        ...每帧...
        if player.poll():                   # 刚播完 → 已在总线发 AUDIO_PLAYBACK_STOP
            ...
    """

    def __init__(self, config: typing.Optional[TtsConfig] = None, bus: typing.Any = None,
                 backend: typing.Any = None, source: str = "tts") -> None:
        self.config = config or TtsConfig()
        self.bus = bus
        self.source = source
        if backend is not None:
            self.backend = backend
        elif self.config.engine == "scripted":
            self.backend = ScriptedTtsBackend()
        elif self.config.engine in ("vits", "sherpa"):
            # 本地神经 TTS（离线、可冻结；依赖缺失/模型缺失会抛 TtsUnavailable → 上层降级）
            self.backend = SherpaTtsBackend(self.config)
        else:
            self.backend = SapiTtsBackend(self.config)
        self._handle: typing.Any = None
        self._started_at = 0.0
        self._last_text = ""
        self._last_style = ""                       # 本次播报的韵律档名（未知/中性档为空串）
        self._timeout_fired = False
        self.spoken_count = 0

    # ---------------- 播报 ----------------
    def speak_async(self, text: str, style: typing.Any = None) -> bool:
        """开始播报（先停上一句，避免叠音）；返回是否成功启动。

        `style` 传 `tts_style.TtsStyle` 时：SAPI 后端走 SSML（rate/pitch/volume/break），
        神经后端折算成 `speed`（见 `SherpaTtsBackend.speed_for`）。
        不传（默认 None）→ 与旧行为**逐位一致**（纯文本、恒定语气）。这就是回退开关。
        """
        self.stop()
        text = str(text or "").strip()
        if not text:
            return False
        ssml = None
        if style is not None:
            from .tts_style import build_ssml       # 延迟导入：不用语气层时零开销
            ssml = build_ssml(text, style) or None
        try:
            self._handle = self.backend.speak_async(text, ssml, style)
        except Exception as exc:                    # 后端异常 → 降级：视为立刻播完
            print("[tts] 播报失败，按已播完处理：%s" % exc, flush=True)
            self._handle = False
        self._last_text = text
        self._last_style = getattr(style, "label", "") or ""
        self._started_at = time.monotonic()
        self._timeout_fired = False
        self.spoken_count += 1
        return True

    def speak(self, text: str, style: typing.Any = None) -> float:
        """阻塞版：播完返回实际耗时（秒）—— 用来校准"字数/4.5"的估算。"""
        if not self.speak_async(text, style):
            return 0.0
        while self.is_busy():
            time.sleep(0.02)
        return time.monotonic() - self._started_at

    def is_busy(self) -> bool:
        if self._handle is None or self._handle is False:
            return False
        if time.monotonic() - self._started_at > self.config.timeout_s:
            self._timeout_fired = True                # 超时保护：不许卡在 SPEAKING
            self.stop()
            return False
        try:
            return bool(self.backend.is_busy(self._handle))
        except Exception:
            return False

    def stop(self) -> None:
        handle, self._handle = self._handle, None
        if handle and handle is not False:
            try:
                handle.kill()
            except Exception:
                pass

    # ---------------- 事件 ----------------
    def poll(self) -> bool:
        """「刚播完」返回 True，并在有总线时代发 `AUDIO_PLAYBACK_STOP`。"""
        if self._handle is None:
            return False
        if self.is_busy():
            return False
        finished_text = self._last_text
        self._handle = None
        self.publish_playback_stop(finished_text)
        return True

    def publish_playback_stop(self, text: str = "") -> None:
        if self.bus is None:
            return
        from ..event_bus import EventEnvelope
        from ..events import EventType
        now_ms = self.bus._now_ms() if hasattr(self.bus, "_now_ms") else int(time.time() * 1000)
        self.bus.publish(EventEnvelope(
            event_type=EventType.AUDIO_PLAYBACK_STOP, source=self.source,
            created_at_ms=now_ms,
            payload={"reason": "tts_finished", "text": str(text)[:40]}))

    def stats(self) -> typing.Dict:
        return {"engine": self.config.engine, "voice": self.config.voice,
                "spoken": self.spoken_count, "busy": self.is_busy(),
                "last_text": self._last_text[:40], "timeout_fired": self._timeout_fired,
                "style": self._last_style or "-"}


def build_player(config: typing.Optional[TtsConfig] = None,
                 bus: typing.Any = None) -> TtsPlayer:
    """按配置构造播放器，**逐级降级**（不让演示中断）。

    引擎不可用时按 `vits（本地神经）→ sapi（系统语音）→ scripted（不出声计时）` 回退；
    `scripted` 恒可用，故必然返回一个可用播放器。
    """
    cfg = config or TtsConfig()
    order = [cfg.engine] + [e for e in ("vits", "sapi", "scripted") if e != cfg.engine]
    last: typing.Optional[Exception] = None
    for engine in order:
        cfg.engine = engine
        try:
            return TtsPlayer(cfg, bus=bus)
        except TtsUnavailable as exc:
            last = exc
            print("[tts] %s 后端不可用，尝试降级：%s" % (engine, exc), flush=True)
    cfg.engine = "scripted"                       # 兜底（理论上到不了这里）
    print("[tts] 全部后端不可用（%s），最后降级 scripted" % last, flush=True)
    return TtsPlayer(cfg, bus=bus)
