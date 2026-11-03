# -*- coding: utf-8 -*-
"""VAD（语音活动检测 / turn 切分）—— 板端「turn 切分」（`audio/__init__.py` 已约定本模块）。

契约与红线
----------
- 只做**感知**：把连续采样流切成一个个 utterance（说话段）；**不识别、不编排**；
- 产出的 utterance 交给 `asr.py`；"说完了"由上层发既有事件 `EventType.AUDIO_VAD_END`
  （不新增事件类型）。

历史默认与成熟分类器适配
----------------------
原能量判据保留为现有默认。frame_classifier注入点允许在隔离候选中复用
成熟语音模型，仅替换逐帧是否语音的判定；音频保存、时长和事件契约保持。
此注入点本身不下载模型，也不自动在正式入口开启。

判据（能量 + 静音滞后）
----------------------
- 每 `frame_ms` 一帧，算 RMS；
- 帧有声：`rms >= energy_threshold`；
- 连续有声 ≥ `min_speech_ms` → 进入 utterance（`speech_start`）；
- utterance 内连续静音 ≥ `min_silence_ms` → 收尾（`speech_end`，带整段音频）；
- 超过 `max_utterance_ms` → 强制收尾（防长静音卡死）。
"""
from __future__ import annotations

import dataclasses
import typing

import numpy as np


@dataclasses.dataclass
class VadConfig:
    """VAD 参数（默认对准 16kHz 耳麦 + 演示环境）。"""

    sample_rate: int = 16000
    frame_ms: int = 20
    energy_threshold: float = 0.010      # RMS 门限（实测耳麦底噪 ~0.002）
    min_speech_ms: int = 180             # 连续有声多久算"开始说话"
    min_silence_ms: int = 600            # 静音多久算"说完了"
    max_utterance_ms: int = 15000        # 单句上限（防卡死）

    @property
    def frame_samples(self) -> int:
        return max(1, int(self.sample_rate * self.frame_ms / 1000.0))


@dataclasses.dataclass
class VadEvent:
    """一次 VAD 事件：`speech_start`（仅提示）/ `speech_end`（带整段音频）。"""

    kind: str
    audio: typing.Any = None             # np.ndarray float32，仅 speech_end 带
    duration_ms: float = 0.0

    def to_payload(self) -> typing.Dict:
        return {"kind": self.kind, "duration_ms": round(float(self.duration_ms), 1)}


class EnergyVad:
    """能量 VAD（流式）：反复 `accept(chunk)`，返回本次产生的事件列表。"""

    def __init__(self, config: typing.Optional[VadConfig] = None, *, frame_classifier=None) -> None:
        self.config = config or VadConfig()
        if frame_classifier is not None and (not callable(frame_classifier)
                or self.config.sample_rate != 16000 or self.config.frame_ms != 20):
            raise ValueError('External speech classifier requires 16 kHz/20 ms frames')
        self.frame_classifier = frame_classifier
        self.reset()

    def reset(self) -> None:
        self._pending = np.zeros(0, dtype=np.float32)   # 未凑满一帧的余量
        self._utter: typing.List[typing.Any] = []       # 当前 utterance 的帧
        self._candidate: typing.List[typing.Any] = []   # 尚未达到 min_speech 的候选帧
        self._speech_ms = 0.0                           # 连续有声时长
        self._silence_ms = 0.0                          # 当前 utterance 内连续静音
        self._in_utterance = False

    # ---------------- 内部 ----------------
    @staticmethod
    def _rms(frame: typing.Any) -> float:
        if frame is None or len(frame) == 0:
            return 0.0
        return float(np.sqrt(np.mean(np.square(frame.astype(np.float32, copy=False)))))

    def _finish(self) -> typing.Optional[VadEvent]:
        if not self._in_utterance or not self._utter:
            self.reset_utterance()
            return None
        audio = np.concatenate(self._utter) if len(self._utter) > 1 else self._utter[0]
        event = VadEvent(kind="speech_end", audio=audio,
                         duration_ms=len(audio) * 1000.0 / self.config.sample_rate)
        self.reset_utterance()
        return event

    def reset_utterance(self) -> None:
        self._utter = []
        self._candidate = []
        self._speech_ms = 0.0
        self._silence_ms = 0.0
        self._in_utterance = False

    # ---------------- 外部 ----------------
    def accept(self, samples: typing.Any) -> typing.List[VadEvent]:
        """喂一段 float32 采样（[-1,1]），返回本次产生的事件。"""
        if samples is None or len(samples) == 0:
            return []
        buf = np.concatenate([self._pending, np.asarray(samples, dtype=np.float32)])
        n = self.config.frame_samples
        frame_ms = float(self.config.frame_ms)
        events: typing.List[VadEvent] = []

        start = 0
        while len(buf) - start >= n:
            frame = buf[start:start + n]
            start += n
            loud = (bool(self.frame_classifier(frame)) if self.frame_classifier is not None
                    else self._rms(frame) >= self.config.energy_threshold)

            if loud:
                self._speech_ms += frame_ms
                if self._in_utterance:
                    self._silence_ms = 0.0
                    self._utter.append(frame)
                else:
                    # 先攒候选帧（**含起始音**），攒够 min_speech_ms 才正式进入 utterance
                    self._candidate.append(frame)
                    if self._speech_ms >= self.config.min_speech_ms:
                        self._in_utterance = True
                        self._utter = list(self._candidate)
                        self._candidate = []
                        self._silence_ms = 0.0
                        events.append(VadEvent(kind="speech_start", duration_ms=0.0))
            else:
                self._speech_ms = 0.0
                if self._in_utterance:
                    self._silence_ms += frame_ms
                    self._utter.append(frame)           # 尾巴静音也留下（VAD 收边）
                else:
                    self._candidate = []                # 短噪声：丢弃候选

            if self._in_utterance:
                duration_ms = len(self._utter) * frame_ms
                if self._silence_ms >= self.config.min_silence_ms \
                        or duration_ms >= self.config.max_utterance_ms:
                    done = self._finish()
                    if done is not None:
                        events.append(done)

        self._pending = buf[start:] if start < len(buf) else np.zeros(0, dtype=np.float32)
        return events

    def flush(self) -> typing.Optional[VadEvent]:
        """停止录音时调用：把当前 utterance 直接收尾（不足静音时长的尾巴也交出去）。"""
        self._pending = np.zeros(0, dtype=np.float32)
        return self._finish()
