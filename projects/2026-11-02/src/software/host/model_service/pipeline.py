# -*- coding: utf-8 -*-
"""C05 单轮流水线：ASR → VLM → TTS，含 READY 功能探针与取消丢弃语义。

依据《03_C负责人手册》：
- §C05.4 单轮内部 ASR→VLM→TTS，空转写/错误直接分支
- §C05.7 VLM 在途数有限；取消不能中止的工作可完成后丢弃输出，该轮不占播放授权
- §C05.8 READY 要求模型已加载且固定输入探针通过
- §8.4 各模块状态 READY/DEGRADED/FAILED 与错误返回
"""
from __future__ import annotations

import copy
import threading
import time
from dataclasses import dataclass, field

from .backends import AsrBackend, BackendError, ProbeResult, TtsBackend, VlmBackend
from .protocol import (
    DOCUMENT_CONTRACT_VERSION,
    PROTOCOL_VERSION,
    ErrorCode,
    ErrorInfo,
    HostState,
    QARequest,
    QAResponse,
    Stage,
    StageTiming,
    validate_request,
)

_BYTES_PER_SAMPLE: dict[str, int] = {"S16_LE": 2, "S32_LE": 4, "F32_LE": 4}


@dataclass
class HealthReport:
    """自检报告；`is_fixture=True` 时界面必须显示"模拟/测试"（§17）。"""

    state: HostState
    modules: list[ProbeResult] = field(default_factory=list)
    note: str = ""

    @property
    def is_fixture(self) -> bool:
        return any(m.is_fixture for m in self.modules)

    def to_dict(self) -> dict:
        return {
            "host_state": self.state.value,
            "is_fixture": self.is_fixture,
            "note": self.note,
            "protocol_version": PROTOCOL_VERSION,
            "document_contract_version": DOCUMENT_CONTRACT_VERSION,
            "modules": [
                {"stage": m.stage.value, "state": m.state.value,
                 "detail": m.detail, "is_fixture": m.is_fixture}
                for m in self.modules
            ],
        }


@dataclass
class ServiceStats:
    handled: int = 0
    replayed: int = 0
    discarded_stale: int = 0
    rejected_busy: int = 0
    stage_ms: dict[str, list[float]] = field(default_factory=dict)

    def summary(self) -> dict:
        out = {"handled": self.handled, "replayed": self.replayed,
               "discarded_stale": self.discarded_stale, "rejected_busy": self.rejected_busy}
        for stage, xs in self.stage_ms.items():
            out[stage + "_ms"] = {"n": len(xs), "last": xs[-1] if xs else None}
        return out


class ModelServicePipeline:
    """主机模型服务核心；不绑定具体传输层（HTTP 层另行包装）。"""

    def __init__(
        self,
        asr: AsrBackend,
        vlm: VlmBackend,
        tts: TtsBackend,
        *,
        max_qa_inflight: int = 1,
        request_timeout_ms: int = 15000,
        clock=time.monotonic,
    ) -> None:
        self.asr, self.vlm, self.tts = asr, vlm, tts
        self.max_qa_inflight = max(1, max_qa_inflight)
        self.request_timeout_ms = int(request_timeout_ms)
        self._clock = clock
        self._sem = threading.BoundedSemaphore(max(1, max_qa_inflight))
        self._lock = threading.Lock()
        self._cancelled: set[int] = set()
        self._latest_generation: int = -1
        self._loaded = False
        # 重试保持请求语义：同一 (session, request, generation) 不重复推理（§C04/C07）
        self._cache: dict[tuple[str, int, int], QAResponse] = {}
        self._cache_order: list[tuple[str, int, int]] = []
        self._cache_max = 16
        self.stats = ServiceStats()

    # ---- 生命周期与自检 -------------------------------------------------

    def startup(self) -> HealthReport:
        """加载并预热三个后端；失败只记录，不伪装 READY（§C05.3）。"""
        for be in (self.asr, self.vlm, self.tts):
            try:
                be.load()
            except BackendError:
                pass
        self._loaded = True
        return self.health()

    def health(self) -> HealthReport:
        mods = [self.asr.probe(), self.vlm.probe(), self.tts.probe()]
        if not self._loaded:
            return HealthReport(HostState.CONNECTING, mods, "尚未执行 startup/load")
        if all(m.state is HostState.READY for m in mods):
            state, note = HostState.READY, "全部探针通过"
        elif any(m.state is HostState.READY for m in mods):
            state, note = HostState.DEGRADED, "部分模块未通过探针"
        else:
            state, note = HostState.FAILED, "全部模块未通过探针"
        return HealthReport(state, mods, note)

    # ---- 世代与取消 -----------------------------------------------------

    def note_generation(self, generation: int) -> None:
        with self._lock:
            self._latest_generation = max(self._latest_generation, generation)

    def cancel(self, generation: int) -> None:
        """本地取消优先：先推进世代失效，再异步通知主机（§C07.1）。"""
        with self._lock:
            self._cancelled.add(generation)
            self._latest_generation = max(self._latest_generation, generation)

    def is_stale(self, generation: int) -> bool:
        with self._lock:
            return generation in self._cancelled or generation < self._latest_generation

    # ---- 单轮流水线 -----------------------------------------------------

    def handle(self, req: QARequest, *, pcm: bytes, image_bytes: bytes | None = None) -> QAResponse:
        """执行一轮 ASR→VLM→TTS；所有预期错误都通过返回值表达，不抛异常。

        `pcm` 由传输层按板端真实格式注入（媒体走二进制载荷，不塞进大 JSON，见 §C04）。
        """
        resp = QAResponse(request_id=req.request_id, generation=req.generation,
                          utterance_id=req.utterance_id, session_id=req.session_id,
                          boot_id=req.boot_id, board_deadline_ns=req.board_deadline_ns)
        errs = validate_request(req)
        if errs:
            resp.error = errs[0]
            return resp
        payload_err = _check_payload(req, pcm)
        if payload_err is not None:
            resp.error = payload_err
            return resp
        if self.is_stale(req.generation):
            resp.error = ErrorInfo(ErrorCode.CANCELLED, None, "世代已取消或已被更新世代取代")
            return resp

        cached = self._cache.get((req.session_id, req.request_id, req.generation))
        if cached is not None:
            self.stats.replayed += 1
            return copy.deepcopy(cached)
        self.note_generation(req.generation)

        budget_s = self.request_timeout_ms / 1000.0
        if not self._sem.acquire(timeout=budget_s):
            self.stats.rejected_busy += 1
            resp.error = ErrorInfo(ErrorCode.EXPIRED, Stage.VLM,
                                   "在途已达上限 %d，本机预算 %d ms 内未取得执行权"
                                   % (self.max_qa_inflight, self.request_timeout_ms))
            return resp
        try:
            return self._run(req, resp, pcm=pcm, image_bytes=image_bytes)
        finally:
            self._sem.release()

    def _run(self, req: QARequest, resp: QAResponse, *, pcm: bytes,
             image_bytes: bytes | None) -> QAResponse:
        try:
            t0 = self._clock()
            tr = self.asr.transcribe(pcm, req.audio.fmt)
            self._record(resp, Stage.ASR, self.asr.model_id, self.asr.backend_id,
                         self.asr.is_fixture, t0)
        except BackendError as exc:
            resp.error = exc.info
            return resp
        if not tr.text.strip():
            resp.error = ErrorInfo(ErrorCode.INFERENCE_FAILED, Stage.ASR, "转写为空")
            return resp
        resp.transcript = tr.text
        if self.is_stale(req.generation):
            return self._discard(resp, "ASR 完成后世代已切换")

        question = req.question_text or tr.text
        try:
            t0 = self._clock()
            vr = self.vlm.answer(question=question,
                                 image_sha256=(req.image.sha256 if req.image else None),
                                 image_bytes=image_bytes,
                                 image_age_ms=(req.image.age_ms if req.image else None))
            self._record(resp, Stage.VLM, self.vlm.model_id, self.vlm.backend_id,
                         self.vlm.is_fixture, t0)
        except BackendError as exc:
            resp.error = exc.info
            return resp
        resp.answer_text = vr.text
        if self.is_stale(req.generation):
            return self._discard(resp, "VLM 完成后世代已切换")

        try:
            t0 = self._clock()
            tt = self.tts.synthesize(vr.text)
            self._record(resp, Stage.TTS, self.tts.model_id, self.tts.backend_id,
                         self.tts.is_fixture, t0)
        except BackendError as exc:
            resp.error = exc.info
            return resp
        resp.segments = list(tt.segments)
        if self.is_stale(req.generation):
            return self._discard(resp, "TTS 完成后世代已切换")
        self._remember(req, resp)
        self.stats.handled += 1
        return resp

    def _remember(self, req: QARequest, resp: QAResponse) -> None:
        """只缓存成功结果；失败重试允许重新执行。"""
        key = (req.session_id, req.request_id, req.generation)
        if key not in self._cache:
            self._cache_order.append(key)
            if len(self._cache_order) > self._cache_max:
                self._cache.pop(self._cache_order.pop(0), None)
        self._cache[key] = copy.deepcopy(resp)

    def _record(self, resp: QAResponse, stage: Stage, model_id: str, backend_id: str,
                is_fixture: bool, t0: float) -> None:
        ms = (self._clock() - t0) * 1000.0
        resp.timings.append(StageTiming(stage=stage, model_id=model_id, backend_id=backend_id,
                                        duration_ms=ms, is_fixture=is_fixture))
        self.stats.stage_ms.setdefault(stage.value, []).append(ms)

    def _discard(self, resp: QAResponse, detail: str) -> QAResponse:
        """丢弃已完成但已失效的输出：清空可播放内容，避免旧轮复活（§C05.7）。"""
        self.stats.discarded_stale += 1
        resp.segments = []
        resp.error = ErrorInfo(ErrorCode.CANCELLED, None, detail)
        return resp


def _check_payload(req: QARequest, pcm: bytes) -> ErrorInfo | None:
    """字节数与声明样本数必须对应（§4.6 验收：音频格式/时长/样本数对应）。"""
    per = _BYTES_PER_SAMPLE.get(req.audio.fmt.sample_format)
    if per is None:
        return ErrorInfo(ErrorCode.FORMAT_UNSUPPORTED, Stage.ASR,
                         "未知采样格式 %s" % req.audio.fmt.sample_format)
    expect = req.audio.sample_count * req.audio.fmt.channels * per
    if len(pcm) != expect:
        return ErrorInfo(ErrorCode.BAD_AUDIO, Stage.ASR,
                         "PCM 字节 %d，声明 %d 样本×%d 声道×%d 字节应为 %d"
                         % (len(pcm), req.audio.sample_count, req.audio.fmt.channels, per, expect))
    return None
