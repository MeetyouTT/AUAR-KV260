# -*- coding: utf-8 -*-
"""C05 模型后端接口与 fixture 实现（第一版骨架）。

约定（《03_C负责人手册》§8.4）：
- 每个后端必须能被"固定输入功能探针"验证，探针通过才算 READY；
- 缺依赖/缺权重时返回具体 NOT_READY 原因，不允许"端口开着就报 READY"；
- fixture 后端只用于软件开发，必须带 is_fixture=True，界面据此显示"模拟/测试"（§17）。

本模块不导入任何第三方库；真实后端在 backends_real 中实现，依赖缺失时不影响本模块。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from .protocol import (
    AudioFormat,
    AudioSegment,
    ErrorCode,
    ErrorInfo,
    HostState,
    Stage,
)


@dataclass(frozen=True)
class ProbeResult:
    """固定输入功能探针结果（§8.4）。"""

    stage: Stage
    state: HostState
    detail: str
    is_fixture: bool


@dataclass(frozen=True)
class TranscriptionResult:
    text: str
    # 不伪造置信度：模型没有就留 None，有则写明含义（§C05.6）
    quality: float | None = None
    detail: str | None = None


@dataclass(frozen=True)
class VlmResult:
    text: str
    detail: str | None = None


@dataclass(frozen=True)
class TtsResult:
    fmt: AudioFormat
    segments: list[AudioSegment] = field(default_factory=list)


class BackendError(Exception):
    """后端错误；code 直接进 I05 错误枚举。"""

    def __init__(self, code: ErrorCode, detail: str, stage: Stage | None = None) -> None:
        super().__init__(detail)
        self.info = ErrorInfo(code=code, stage=stage or code.stage_hint, detail=detail)


class AsrBackend(ABC):
    """ASR 后端：输入真实 PCM，输出可核验转写。"""

    model_id: str = "unset"
    backend_id: str = "unset"
    is_fixture: bool = False

    @abstractmethod
    def load(self) -> None:
        """常驻加载与预热；失败抛 BackendError(MODEL_NOT_READY)。"""

    @abstractmethod
    def probe(self) -> ProbeResult:
        """固定真实 PCM 探针（§8.4 第 1 行）。"""

    @abstractmethod
    def transcribe(self, pcm: bytes, fmt: AudioFormat) -> TranscriptionResult:
        """真实转写；空输入/格式错误抛 BackendError(BAD_AUDIO/INFERENCE_FAILED)。"""


class VlmBackend(ABC):
    """VLM 后端：固定图＋问题或纯文本，输出图文结果。"""

    model_id: str = "unset"
    backend_id: str = "unset"
    is_fixture: bool = False
    accepts_text_only: bool = True

    @abstractmethod
    def load(self) -> None: ...

    @abstractmethod
    def probe(self) -> ProbeResult: ...

    @abstractmethod
    def answer(self, *, question: str | None, image_sha256: str | None,
               image_bytes: bytes | None, image_age_ms: int | None) -> VlmResult:
        """图文或纯文本问答；图缺失/过期抛 BAD_IMAGE/STALE_IMAGE。"""


class TtsBackend(ABC):
    """TTS 后端：固定中文，输出有格式且可播放的样本。"""

    model_id: str = "unset"
    backend_id: str = "unset"
    is_fixture: bool = False
    output_format: AudioFormat = AudioFormat(rate_hz=48000, channels=1, sample_format="S16_LE")

    @abstractmethod
    def load(self) -> None: ...

    @abstractmethod
    def probe(self) -> ProbeResult: ...

    @abstractmethod
    def synthesize(self, text: str) -> TtsResult:
        """合成；空文本抛 BAD_TEXT，格式不符抛 FORMAT_ERROR。"""


class NotReadyBackend(ABC):
    """真实后端的占位基类：未取得依赖/权重时给出具体 NOT_READY 原因。"""

    model_id: str = "unset"
    backend_id: str = "not_ready"
    is_fixture: bool = False

    def __init__(self, reason: str) -> None:
        self.reason = reason

    def load(self) -> None:
        raise BackendError(ErrorCode.MODEL_NOT_READY, self.reason)

    def probe(self) -> ProbeResult:
        return ProbeResult(self.stage, HostState.FAILED, self.reason, False)

    @property
    @abstractmethod
    def stage(self) -> Stage: ...


FIXTURE_FORMAT = AudioFormat(rate_hz=16000, channels=1, sample_format="S16_LE")


class FixtureAsr(AsrBackend):
    """确定性 ASR：用于协议/取消/超时开发，不作为模型能力证据。"""

    model_id = "fixture-asr-0"
    backend_id = "fixture"
    is_fixture = True

    def __init__(self, text: str = "现在几点", *, fail_with: ErrorCode | None = None) -> None:
        self.text = text
        self.fail_with = fail_with
        self._loaded = False

    def load(self) -> None:
        self._loaded = True

    def probe(self) -> ProbeResult:
        if self.fail_with is not None:
            return ProbeResult(Stage.ASR, HostState.DEGRADED,
                               "fixture 注入错误 %s" % self.fail_with.value, True)
        pcm = _tone(FIXTURE_FORMAT, 0.3)
        try:
            r = self.transcribe(pcm, FIXTURE_FORMAT)
        except BackendError as exc:
            return ProbeResult(Stage.ASR, HostState.FAILED, exc.info.detail, True)
        ok = bool(r.text.strip())
        return ProbeResult(Stage.ASR, HostState.READY if ok else HostState.FAILED,
                           "fixture 转写=%r" % r.text, True)

    def transcribe(self, pcm: bytes, fmt: AudioFormat) -> TranscriptionResult:
        if self.fail_with is not None:
            raise BackendError(self.fail_with, "fixture 注入失败")
        if not pcm or fmt.rate_hz <= 0:
            raise BackendError(ErrorCode.BAD_AUDIO, "空 PCM 或非法采样率")
        return TranscriptionResult(text=self.text, quality=None,
                                   detail="fixture：文本与音频内容无关，仅验证协议通路")


def _tone(fmt: AudioFormat, seconds: float) -> bytes:
    """生成确定性占位 PCM（正弦波及静音交替），无需 numpy。"""
    import math

    n = int(fmt.rate_hz * seconds)
    out = bytearray()
    for i in range(n):
        v = int(6000 * math.sin(2 * math.pi * 440 * i / fmt.rate_hz)) if (i // 400) % 2 == 0 else 0
        out += int(v).to_bytes(2, "little", signed=True)
    return bytes(out)


class FixtureVlm(VlmBackend):
    """确定性 VLM：答案随问题与图 hash 变化，便于验证"换图换答案"（§C06.4）。"""

    model_id = "fixture-vlm-0"
    backend_id = "fixture"
    is_fixture = True

    def __init__(self, fail_with: ErrorCode | None = None) -> None:
        self.fail_with = fail_with
        self._loaded = False

    def load(self) -> None:
        self._loaded = True

    def answer(self, *, question: str | None, image_sha256: str | None,
               image_bytes: bytes | None, image_age_ms: int | None) -> VlmResult:
        if self.fail_with is not None:
            raise BackendError(self.fail_with, "fixture 注入失败")
        if image_sha256 is None and not question:
            raise BackendError(ErrorCode.BAD_IMAGE, "既无图片也无文本问题")
        if image_age_ms is not None and image_age_ms > 2000:
            raise BackendError(ErrorCode.STALE_IMAGE, "帧龄 %d ms 超限" % image_age_ms)
        tag = (image_sha256 or "no-image")[:8]
        q = question or "（未提供文本问题）"
        return VlmResult(text="[模拟] 针对图 %s 的问题「%s」的回答" % (tag, q),
                         detail="fixture：不读取像素，仅验证归属与分支")

    def probe(self) -> ProbeResult:
        try:
            r = self.answer(question="探针问题", image_sha256="0" * 64,
                            image_bytes=None, image_age_ms=0)
        except BackendError as exc:
            return ProbeResult(Stage.VLM, HostState.FAILED, exc.info.detail, True)
        return ProbeResult(Stage.VLM, HostState.READY, "fixture 回答=%r" % r.text[:24], True)


class FixtureTts(TtsBackend):
    """确定性 TTS：按时长分段，验证段号/重复段/缺段拒绝语义。"""

    model_id = "fixture-tts-0"
    backend_id = "fixture"
    is_fixture = True

    def __init__(self, *, segment_count: int = 2, fail_with: ErrorCode | None = None) -> None:
        self.segment_count = segment_count
        self.fail_with = fail_with
        self._loaded = False

    def load(self) -> None:
        self._loaded = True

    def synthesize(self, text: str) -> TtsResult:
        if self.fail_with is not None:
            raise BackendError(self.fail_with, "fixture 注入失败")
        if not text.strip():
            raise BackendError(ErrorCode.BAD_TEXT, "空文本")
        segs: list[AudioSegment] = []
        for i in range(self.segment_count):
            segs.append(AudioSegment(segment_index=i, fmt=self.output_format,
                                     pcm=_tone(self.output_format, 0.2)))
        return TtsResult(fmt=self.output_format, segments=segs)

    def probe(self) -> ProbeResult:
        try:
            r = self.synthesize("探针语音")
        except BackendError as exc:
            return ProbeResult(Stage.TTS, HostState.FAILED, exc.info.detail, True)
        return ProbeResult(Stage.TTS, HostState.READY,
                           "fixture 段数=%d 每段 200 ms" % len(r.segments), True)


class RealBackendPlaceholder(NotReadyBackend):
    """真实后端登记处：在真正接通前一律返回具体 NOT_READY（§C05.3）。

    每项填写候选、权重取得方式与依赖，禁止在未装载时对外报 READY。
    """

    def __init__(self, stage: Stage, model_id: str, install_hint: str) -> None:
        super().__init__(reason=install_hint)
        self._stage = stage
        self.model_id = model_id

    @property
    def stage(self) -> Stage:
        return self._stage


# 候选登记（《当前现状三人分工》与 §C05：候选名字不等于已有通过工件）
CANDIDATES: dict[str, dict[str, str]] = {
    "ASR": {
        "candidate": "SenseVoice-Small / faster-whisper",
        "status": "无权重、无依赖（本机实测未安装 faster-whisper / funasr）",
        "blockers": "需下载权重；torch 当前为 CPU 版，需换 CUDA 版才用得上 RTX 4060",
    },
    "VLM": {
        "candidate": "Qwen2.5-VL（7B 级需评估 8 GB 显存）",
        "status": "无权重、无依赖（未安装 transformers）",
        "blockers": "8 GB 显存需量化或换小模型；首版在途并发 1",
    },
    "TTS": {
        "candidate": "中文 VITS / CosyVoice 系",
        "status": "无权重、无依赖",
        "blockers": "需确认输出采样率与板端播放格式；FORMAT_ERROR 分支要先落地",
    },
}
