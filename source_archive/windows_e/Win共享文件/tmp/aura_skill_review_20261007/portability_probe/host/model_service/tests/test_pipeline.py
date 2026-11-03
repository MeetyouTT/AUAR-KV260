# -*- coding: utf-8 -*-
"""流水线单测：READY 探针、单轮 ASR→VLM→TTS、取消丢弃、忙时拒绝（§C05/§8.4）。"""
from __future__ import annotations

import threading
import unittest

from model_service.backends import (
    CANDIDATES,
    FixtureAsr,
    FixtureTts,
    FixtureVlm,
    RealBackendPlaceholder,
)
from model_service.pipeline import ModelServicePipeline
from model_service.protocol import (
    AudioFormat,
    AudioRef,
    ErrorCode,
    HostState,
    ImageRef,
    QARequest,
    Stage,
    TargetKey,
    TargetLifecycle,
)

FMT = AudioFormat(rate_hz=16000, channels=1, sample_format="S16_LE")
PCM_0_1S = b"\x01\x00" * 1600          # 1600 样本 = 0.1 s
SAMPLES = 1600


def make_req(**kw) -> QARequest:
    base = dict(boot_id="b1", session_id="s1", request_id=1, generation=1, utterance_id=1,
                board_deadline_ns=10 ** 12,
                audio=AudioRef(audio_epoch=1, first_sample_index=0, sample_count=SAMPLES, fmt=FMT),
                image=ImageRef(frame_id=42, sha256="a" * 64, camera_epoch=1, age_ms=50),
                target=TargetKey(track_id=5, generation=1, lifecycle=TargetLifecycle.CONFIRMED))
    base.update(kw)
    return QARequest(**base)


def make_pipeline(**kw) -> ModelServicePipeline:
    p = ModelServicePipeline(FixtureAsr(), FixtureVlm(), FixtureTts(),
                             max_qa_inflight=kw.pop("max_qa_inflight", 1),
                             request_timeout_ms=kw.pop("request_timeout_ms", 2000), **kw)
    p.startup()
    return p


class TestHealth(unittest.TestCase):
    def test_fixture_pipeline_is_ready_and_flagged(self):
        h = make_pipeline().health()
        self.assertIs(h.state, HostState.READY)
        self.assertTrue(h.is_fixture, "fixture 必须自报模拟，界面据此标注（§17）")
        d = h.to_dict()
        self.assertEqual([m["stage"] for m in d["modules"]], ["ASR", "VLM", "TTS"])
        self.assertEqual(d["protocol_version"], "aura-runtime-1")

    def test_placeholder_backends_are_failed_with_reason(self):
        p = ModelServicePipeline(
            RealBackendPlaceholder(Stage.ASR, "sensevoice-small", "缺权重：未下载"),
            RealBackendPlaceholder(Stage.VLM, "qwen2.5-vl", "缺依赖：未安装 transformers"),
            RealBackendPlaceholder(Stage.TTS, "vits-zh", "缺权重：未下载"))
        h = p.startup()
        self.assertIs(h.state, HostState.FAILED)
        self.assertFalse(h.is_fixture)
        self.assertIn("未下载", h.modules[0].detail)
        self.assertIn("ASR", CANDIDATES)

    def test_stage_failure_degrades_host(self):
        p = ModelServicePipeline(FixtureAsr(), FixtureVlm(ErrorCode.MODEL_NOT_READY),
                                 FixtureTts())
        h = p.startup()
        self.assertIs(h.state, HostState.DEGRADED)
        self.assertIs(h.modules[1].state, HostState.FAILED)


class TestHappyPath(unittest.TestCase):
    def test_full_round_produces_attributed_output(self):
        p = make_pipeline()
        resp = p.handle(make_req(), pcm=PCM_0_1S, image_bytes=b"\x89PNG...")
        self.assertIsNone(resp.error)
        self.assertTrue(resp.complete)
        self.assertEqual(resp.request_id, 1)
        self.assertEqual(resp.session_id, "s1")
        self.assertEqual(resp.generation, 1)
        self.assertEqual([t.stage.value for t in resp.timings], ["ASR", "VLM", "TTS"])
        self.assertEqual([s.segment_index for s in resp.segments], [0, 1])
        self.assertTrue(resp.is_fixture)
        self.assertEqual(p.stats.handled, 1)
        self.assertGreater(resp.segments[0].duration_ms, 0)

    def test_answer_follows_image_binding(self):
        p = make_pipeline()
        a = p.handle(make_req(), pcm=PCM_0_1S)
        b = p.handle(make_req(request_id=2, generation=2,
                              image=ImageRef(frame_id=43, sha256="b" * 64,
                                             camera_epoch=1, age_ms=10)), pcm=PCM_0_1S)
        self.assertIn("aaaaaaaa", a.answer_text)
        self.assertIn("bbbbbbbb", b.answer_text)
        self.assertNotEqual(a.board_deadline_ns, 0)

    def test_text_only_question_path(self):
        p = make_pipeline()
        r = p.handle(make_req(image=None, question_text="现在几点"), pcm=PCM_0_1S)
        self.assertIsNone(r.error)
        self.assertIn("现在几点", r.answer_text)


class TestRejections(unittest.TestCase):
    def test_payload_size_mismatch_rejected(self):
        p = make_pipeline()
        r = p.handle(make_req(), pcm=b"\x01\x00" * 100)
        self.assertIs(r.error.code, ErrorCode.BAD_AUDIO)
        self.assertEqual(r.timings, [])

    def test_unknown_sample_format_rejected(self):
        fmt = AudioFormat(rate_hz=16000, channels=1, sample_format="S24_3LE")
        ref = AudioRef(audio_epoch=1, first_sample_index=0, sample_count=10, fmt=fmt)
        p = make_pipeline()
        r = p.handle(make_req(audio=ref), pcm=b"\x00" * 30)
        self.assertIs(r.error.code, ErrorCode.FORMAT_UNSUPPORTED)

    def test_empty_transcript_branches(self):
        p = ModelServicePipeline(FixtureAsr(text="   "), FixtureVlm(), FixtureTts())
        p.startup()
        r = p.handle(make_req(), pcm=PCM_0_1S)
        self.assertIs(r.error.code, ErrorCode.INFERENCE_FAILED)
        self.assertEqual([t.stage.value for t in r.timings], ["ASR"])

    def test_asr_failure_propagates(self):
        p = ModelServicePipeline(FixtureAsr(fail_with=ErrorCode.BAD_AUDIO), FixtureVlm(),
                                 FixtureTts())
        p.startup()
        r = p.handle(make_req(), pcm=PCM_0_1S)
        self.assertIs(r.error.code, ErrorCode.BAD_AUDIO)
        self.assertEqual(p.stats.handled, 0)

    def test_stale_image_rejected_by_vlm(self):
        img = ImageRef(frame_id=1, sha256="c" * 64, camera_epoch=1, age_ms=9999)
        p = make_pipeline()
        r = p.handle(make_req(image=img), pcm=PCM_0_1S)
        self.assertIs(r.error.code, ErrorCode.STALE_IMAGE)
        self.assertEqual(r.segments, [])


class CancellingVlm(FixtureVlm):
    """在真实请求的 VLM 阶段触发本地取消，验证"完成后丢弃输出"（§C05.7）。

    注意：`probe()` 也会调用 answer()，因此用 `armed` 显式武装，
    只对携带请求图指纹的那一次调用生效（探针不得污染服务状态）。
    """

    def __init__(self, generation: int, sha: str) -> None:
        super().__init__()
        self.pipeline = None
        self.generation = generation
        self.sha = sha
        self.armed = False

    def answer(self, **kw):
        r = super().answer(**kw)
        if self.armed and kw.get("image_sha256") == self.sha:
            assert self.pipeline is not None
            self.pipeline.cancel(self.generation)
        return r


class TestCancelAndRetry(unittest.TestCase):
    def _pipeline_with_cancelling_vlm(self):
        vlm = CancellingVlm(generation=1, sha="a" * 64)
        p = ModelServicePipeline(FixtureAsr(), vlm, FixtureTts())
        vlm.pipeline = p
        p.startup()
        vlm.armed = True
        return p

    def test_cancel_before_start_is_refused(self):
        p = make_pipeline()
        p.cancel(1)
        r = p.handle(make_req(), pcm=PCM_0_1S)
        self.assertIs(r.error.code, ErrorCode.CANCELLED)
        self.assertEqual(r.timings, [])

    def test_cancel_during_vlm_discards_audio(self):
        p = self._pipeline_with_cancelling_vlm()
        r = p.handle(make_req(), pcm=PCM_0_1S)
        self.assertIs(r.error.code, ErrorCode.CANCELLED)
        self.assertEqual(r.segments, [], "旧轮不得留下可播放音频")
        self.assertEqual(p.stats.discarded_stale, 1)
        self.assertEqual(p.stats.handled, 0)

    def test_new_generation_supersedes_old(self):
        p = make_pipeline()
        self.assertIsNone(p.handle(make_req(), pcm=PCM_0_1S).error)
        old = p.handle(make_req(), pcm=PCM_0_1S)      # 同一世代重复提交
        self.assertIsNone(old.error)
        self.assertEqual(p.stats.replayed, 1)
        self.assertEqual(p.stats.handled, 1)
        p.cancel(1)
        p.note_generation(2)
        stale = p.handle(make_req(request_id=3, generation=1), pcm=PCM_0_1S)
        self.assertIs(stale.error.code, ErrorCode.CANCELLED)

    def test_busy_rejected_within_local_budget(self):
        p = make_pipeline(request_timeout_ms=50)
        self.assertTrue(p._sem.acquire())
        try:
            r = p.handle(make_req(), pcm=PCM_0_1S)
        finally:
            p._sem.release()
        self.assertIs(r.error.code, ErrorCode.EXPIRED)
        self.assertIs(r.error.stage, Stage.VLM)
        self.assertEqual(p.stats.rejected_busy, 1)


class TestPayloadThreading(unittest.TestCase):
    def test_concurrent_handle_is_serialized(self):
        p = make_pipeline(max_qa_inflight=1)
        results = []

        def run(rid: int) -> None:
            results.append(p.handle(make_req(request_id=rid, generation=1),
                                    pcm=PCM_0_1S).error)

        threads = [threading.Thread(target=run, args=(i,)) for i in (11, 12, 13)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(p.stats.handled + p.stats.replayed, 3)
        self.assertTrue(all(e is None for e in results))


if __name__ == "__main__":
    unittest.main()
