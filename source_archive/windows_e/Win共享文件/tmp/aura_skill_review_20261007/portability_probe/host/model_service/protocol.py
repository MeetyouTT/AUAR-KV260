# -*- coding: utf-8 -*-
"""I05/I07 主机侧协议定义（第一版骨架，C 线）。

依据《03_C负责人_视听交互主机模型与板端界面执行手册》（AURA-EXEC-20261002-r2）：
- §6.6 一轮问答和音频返回：请求与回复必须携带的归属字段
- §6.7 状态机、时间和单位统一：枚举取值与单位口径
- §6.8 每项数据怎么拒绝：问答返回的拒绝条件
- §8.1 配置合同：`protocol_version: aura-runtime-1`
- §8.4 模型服务的功能探针与错误：错误码枚举

本模块只定义"线上字段与拒绝规则"，不含任何模型实现，也不引用第三方依赖。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

PROTOCOL_VERSION: str = "aura-runtime-1"
DOCUMENT_CONTRACT_VERSION: str = "AURA-EXEC-20261002-r2"


class InteractionState(str, Enum):
    """交互状态机（§6.7）。"""

    IDLE = "IDLE"
    LISTENING = "LISTENING"
    PROCESSING = "PROCESSING"
    SPEAKING = "SPEAKING"
    CANCELLED = "CANCELLED"
    ERROR = "ERROR"


class TargetLifecycle(str, Enum):
    """目标生命周期（§6.7）。"""

    NONE = "NONE"
    CANDIDATE = "CANDIDATE"
    CONFIRMED = "CONFIRMED"
    LOST = "LOST"
    AMBIGUOUS = "AMBIGUOUS"


class IdentityState(str, Enum):
    """身份状态（§6.7）。"""

    UNKNOWN = "UNKNOWN"
    KNOWN = "KNOWN"
    ENROLLING = "ENROLLING"
    DELETED = "DELETED"


class HostState(str, Enum):
    """主机状态；READY 表示模型已加载且功能探针通过（§8.4）。"""

    OFFLINE = "OFFLINE"
    CONNECTING = "CONNECTING"
    READY = "READY"
    DEGRADED = "DEGRADED"
    FAILED = "FAILED"


class Stage(str, Enum):
    """主机三阶段（§6.6）。"""

    ASR = "ASR"
    VLM = "VLM"
    TTS = "TTS"


class ErrorCode(str, Enum):
    """错误码（§8.4 与 §6.8）。"""

    # ASR
    BAD_AUDIO = "BAD_AUDIO"
    # VLM
    BAD_IMAGE = "BAD_IMAGE"
    STALE_IMAGE = "STALE_IMAGE"
    # TTS
    BAD_TEXT = "BAD_TEXT"
    FORMAT_ERROR = "FORMAT_ERROR"
    # 共用
    MODEL_NOT_READY = "MODEL_NOT_READY"
    INFERENCE_FAILED = "INFERENCE_FAILED"
    # 拒绝（§6.8「问答返回」行）
    PROTOCOL_MISMATCH = "PROTOCOL_MISMATCH"
    STALE_GENERATION = "STALE_GENERATION"
    REQUEST_MISMATCH = "REQUEST_MISMATCH"
    SESSION_MISMATCH = "SESSION_MISMATCH"
    BOOT_MISMATCH = "BOOT_MISMATCH"
    TARGET_INVALID = "TARGET_INVALID"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"
    # 板端侧（供 UI/日志统一文案，主机不产生）
    AUDIO_UNAVAILABLE = "AUDIO_UNAVAILABLE"
    XRUN = "XRUN"
    FORMAT_UNSUPPORTED = "FORMAT_UNSUPPORTED"
    DISPLAY_UNAVAILABLE = "DISPLAY_UNAVAILABLE"
    ASSET_MISSING = "ASSET_MISSING"

    @property
    def stage_hint(self) -> Stage | None:
        """错误码所属阶段；None 表示跨阶段或板端错误。"""
        if self in (ErrorCode.BAD_AUDIO,):
            return Stage.ASR
        if self in (ErrorCode.BAD_IMAGE, ErrorCode.STALE_IMAGE):
            return Stage.VLM
        if self in (ErrorCode.BAD_TEXT, ErrorCode.FORMAT_ERROR):
            return Stage.TTS
        return None


USER_MESSAGE_ZH: dict[ErrorCode, str] = {
    ErrorCode.BAD_AUDIO: "录音内容为空或格式不可用",
    ErrorCode.BAD_IMAGE: "本轮画面不可用",
    ErrorCode.STALE_IMAGE: "本轮画面已过期",
    ErrorCode.BAD_TEXT: "回答文本为空，无法合成",
    ErrorCode.FORMAT_ERROR: "合成音频格式与目标设备不匹配",
    ErrorCode.MODEL_NOT_READY: "主机模型未就绪",
    ErrorCode.INFERENCE_FAILED: "模型推理失败",
    ErrorCode.PROTOCOL_MISMATCH: "协议版本不一致",
    ErrorCode.STALE_GENERATION: "该结果属于已取消的旧轮次",
    ErrorCode.REQUEST_MISMATCH: "结果不属于当前请求",
    ErrorCode.SESSION_MISMATCH: "会话不一致",
    ErrorCode.BOOT_MISMATCH: "板端不是同一启动代次",
    ErrorCode.TARGET_INVALID: "目标已离开或已换代",
    ErrorCode.EXPIRED: "结果超期",
    ErrorCode.CANCELLED: "本轮已取消",
    ErrorCode.AUDIO_UNAVAILABLE: "音频设备不可用",
    ErrorCode.XRUN: "音频缓冲溢出或欠载",
    ErrorCode.FORMAT_UNSUPPORTED: "设备不支持该音频格式",
    ErrorCode.DISPLAY_UNAVAILABLE: "显示通路不可用",
    ErrorCode.ASSET_MISSING: "界面资源缺失",
}


@dataclass(frozen=True)
class AudioFormat:
    """音频格式；rate_hz/channels/sample_format 均为实际值，不写"默认"。"""

    rate_hz: int
    channels: int
    sample_format: str


@dataclass(frozen=True)
class AudioRef:
    """音频归属（§6.6/§6.7）：真实样本数决定时长，不由应用读取时刻推断。"""

    audio_epoch: int
    first_sample_index: int
    sample_count: int
    fmt: AudioFormat

    @property
    def duration_s(self) -> float:
        return self.sample_count / float(self.fmt.rate_hz)


@dataclass(frozen=True)
class ImageRef:
    """本轮快照归属（§6.6）；age_ms 由板端用板端时基算出。"""

    frame_id: int
    sha256: str
    camera_epoch: int
    age_ms: int


@dataclass(frozen=True)
class TargetKey:
    track_id: int
    generation: int
    lifecycle: TargetLifecycle


@dataclass(frozen=True)
class QARequest:
    """一轮问答请求（§6.6）。板端期限以板端时基表达，主机不做跨机时钟比较。"""

    boot_id: str
    session_id: str
    request_id: int
    generation: int
    utterance_id: int
    board_deadline_ns: int
    audio: AudioRef
    image: ImageRef | None = None
    target: TargetKey | None = None
    question_text: str | None = None
    protocol_version: str = PROTOCOL_VERSION


@dataclass(frozen=True)
class StageTiming:
    """主机本机阶段耗时（§6.7：Windows 各推理阶段用本机时长）。"""

    stage: Stage
    model_id: str
    backend_id: str
    duration_ms: float
    is_fixture: bool = False


_BYTES_PER_SAMPLE: dict[str, int] = {
    "S16_LE": 2,
    "S32_LE": 4,
    "F32_LE": 4,
}


@dataclass(frozen=True)
class AudioSegment:
    """TTS 回复分段（§6.6：分段序号 + 真实格式）。"""

    segment_index: int
    fmt: AudioFormat
    pcm: bytes

    @property
    def sample_count(self) -> int:
        per = _BYTES_PER_SAMPLE.get(self.fmt.sample_format, 2)
        return len(self.pcm) // max(1, self.fmt.channels * per)

    @property
    def duration_ms(self) -> float:
        return 1000.0 * self.sample_count / float(self.fmt.rate_hz)


@dataclass(frozen=True)
class ErrorInfo:
    code: ErrorCode
    stage: Stage | None
    detail: str

    @property
    def user_message_zh(self) -> str:
        return USER_MESSAGE_ZH.get(self.code, "未知错误")


@dataclass
class QAResponse:
    """主机回复；归属字段原样回传（§6.6）。"""

    request_id: int
    generation: int
    utterance_id: int
    session_id: str
    boot_id: str
    board_deadline_ns: int
    transcript: str | None = None
    answer_text: str | None = None
    segments: list[AudioSegment] = field(default_factory=list)
    timings: list[StageTiming] = field(default_factory=list)
    error: ErrorInfo | None = None
    protocol_version: str = PROTOCOL_VERSION

    @property
    def is_fixture(self) -> bool:
        return any(t.is_fixture for t in self.timings)

    @property
    def complete(self) -> bool:
        return self.error is None and bool(self.answer_text) and bool(self.segments)


def validate_request(req: QARequest) -> list[ErrorInfo]:
    """请求结构校验；返回空列表表示可受理（§6.6/§6.8）。"""
    errs: list[ErrorInfo] = []
    if req.protocol_version != PROTOCOL_VERSION:
        errs.append(ErrorInfo(ErrorCode.PROTOCOL_MISMATCH, None,
                              "请求协议 %s，本机 %s" % (req.protocol_version, PROTOCOL_VERSION)))
    if req.request_id <= 0 or req.utterance_id <= 0 or req.generation < 0:
        errs.append(ErrorInfo(ErrorCode.REQUEST_MISMATCH, None,
                              "request/utterance/generation 取值非法"))
    if req.audio.sample_count <= 0 or req.audio.fmt.rate_hz <= 0 or req.audio.fmt.channels <= 0:
        errs.append(ErrorInfo(ErrorCode.BAD_AUDIO, Stage.ASR, "样本数为 0 或格式字段非法"))
    if req.image is not None and (not req.image.sha256 or req.image.age_ms < 0):
        errs.append(ErrorInfo(ErrorCode.BAD_IMAGE, Stage.VLM, "快照字段非法"))
    if req.target is not None and req.target.lifecycle in (TargetLifecycle.LOST, TargetLifecycle.AMBIGUOUS):
        errs.append(ErrorInfo(ErrorCode.TARGET_INVALID, None,
                              "目标生命周期为 %s" % req.target.lifecycle.value))
    return errs


def validate_response_for_delivery(
    resp: QAResponse,
    *,
    boot_id: str,
    session_id: str,
    request_id: int,
    generation: int,
    cancelled_generations: frozenset[int] | None = None,
    target_still_valid: bool = True,
    expired: bool = False,
) -> ErrorInfo | None:
    """板端播放/显示前的最后一道校验（§6.8「问答返回」行）。

    判定顺序刻意与手册一致：协议 → 启动 → 会话 → 世代/取消 → 请求 → 目标 → 过期。
    返回 None 表示可以播、可以显示。
    """
    cancelled = cancelled_generations or frozenset()
    if resp.protocol_version != PROTOCOL_VERSION:
        return ErrorInfo(ErrorCode.PROTOCOL_MISMATCH, None, "回复协议不一致")
    if resp.boot_id != boot_id:
        return ErrorInfo(ErrorCode.BOOT_MISMATCH, None, "回复来自另一次板端启动")
    if resp.session_id != session_id:
        return ErrorInfo(ErrorCode.SESSION_MISMATCH, None, "回复不属于当前会话")
    if resp.generation in cancelled or resp.generation < generation:
        return ErrorInfo(ErrorCode.STALE_GENERATION, None,
                         "回复世代 %d，当前 %d" % (resp.generation, generation))
    if resp.request_id != request_id:
        return ErrorInfo(ErrorCode.REQUEST_MISMATCH, None,
                         "回复请求 %d，当前 %d" % (resp.request_id, request_id))
    if not target_still_valid:
        return ErrorInfo(ErrorCode.TARGET_INVALID, None, "绑定目标已离开或已换代")
    if expired:
        return ErrorInfo(ErrorCode.EXPIRED, None, "超过板端期限")
    return None


class SegmentLedger:
    """播放分段台账：重复段丢弃、乱序段按有限前视策略处理（§6.6）。

    只接受"当前有效归属"的段；世代切换即整体作废。本类由板端 interaction_service
    持有，放在协议模块里是为了让主机 fixture 测试能复用同一套拒绝语义。
    """

    def __init__(self, *, max_lookahead: int = 4) -> None:
        self.max_lookahead = max_lookahead
        self.request_id: int | None = None
        self.generation: int | None = None
        self._accepted: set[int] = set()
        self._next_index: int = 0
        self.rejected: list[tuple[int, ErrorCode]] = []

    def reset(self, request_id: int, generation: int) -> None:
        self.request_id, self.generation = request_id, generation
        self._accepted.clear()
        self._next_index = 0

    def offer(self, resp: QAResponse, segment: AudioSegment) -> bool:
        """返回 True 表示该段可入播放队列。"""
        if self.request_id != resp.request_id or self.generation != resp.generation:
            self.rejected.append((segment.segment_index, ErrorCode.STALE_GENERATION))
            return False
        if segment.segment_index in self._accepted:
            self.rejected.append((segment.segment_index, ErrorCode.REQUEST_MISMATCH))
            return False
        if segment.segment_index > self._next_index + self.max_lookahead:
            self.rejected.append((segment.segment_index, ErrorCode.EXPIRED))
            return False
        self._accepted.add(segment.segment_index)
        while self._next_index in self._accepted:
            self._next_index += 1
        return True

    @property
    def pending_gap(self) -> list[int]:
        """已越过但仍缺的段号；超时即报缺段错误（§6.6）。

        判据：段号 < 已收到的最大段号，却始终未到——即乱序前视窗口内留下的空洞。
        """
        if not self._accepted:
            return []
        return [i for i in range(max(self._accepted)) if i not in self._accepted]
