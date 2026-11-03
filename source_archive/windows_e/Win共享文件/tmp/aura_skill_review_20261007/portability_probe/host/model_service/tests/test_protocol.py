# -*- coding: utf-8 -*-
"""协议层单测：字段、单位、拒绝语义（§6.6/§6.7/§6.8）。

运行：在 `aura_fpga/host` 目录执行
    python -m unittest discover -s model_service/tests -t .
"""
from __future__ import annotations

import unittest

from model_service.protocol import (
    PROTOCOL_VERSION,
    AudioFormat,
    AudioRef,
    AudioSegment,
    ErrorCode,
    HostState,
    ImageRef,
    InteractionState,
    QAResponse,
    QARequest,
    SegmentLedger,
    Stage,
    TargetKey,
    TargetLifecycle,
    validate_request,
    validate_response_for_delivery,
)

FMT = AudioFormat(rate_hz=16000, channels=1, sample_format="S16_LE")


def _req(**kw) -> QARequest:
    base = dict(boot_id="b1", session_id="s1", request_id=7, generation=3, utterance_id=2,
                board_deadline_ns=123456789, audio=AudioRef(audio_epoch=1, first_sample_index=0,
                                                            sample_count=16000, fmt=FMT))
    base.update(kw)
    return QARequest(**base)


def _resp(**kw) -> QAResponse:
    base = dict(request_id=7, generation=3, utterance_id=2, session_id="s1", boot_id="b1",
                board_deadline_ns=123456789, transcript="你好", answer_text="你好呀")
    base.update(kw)
    return QAResponse(**base)


class TestEnumsAndUnits(unittest.TestCase):
    def test_protocol_version_frozen(self):
        self.assertEqual(PROTOCOL_VERSION, "aura-runtime-1")

    def test_state_enums_match_manual(self):
        self.assertEqual([s.value for s in InteractionState],
                         ["IDLE", "LISTENING", "PROCESSING", "SPEAKING", "CANCELLED", "ERROR"])
        self.assertEqual([s.value for s in HostState],
                         ["OFFLINE", "CONNECTING", "READY", "DEGRADED", "FAILED"])
        self.assertEqual([s.value for s in TargetLifecycle],
                         ["NONE", "CANDIDATE", "CONFIRMED", "LOST", "AMBIGUOUS"])

    def test_audio_duration_from_sample_count(self):
        ref = AudioRef(audio_epoch=1, first_sample_index=0, sample_count=8000, fmt=FMT)
        self.assertAlmostEqual(ref.duration_s, 0.5, places=6)

    def test_error_stage_hint(self):
        self.assertIs(ErrorCode.BAD_AUDIO.stage_hint, Stage.ASR)
        self.assertIs(ErrorCode.STALE_IMAGE.stage_hint, Stage.VLM)
        self.assertIs(ErrorCode.FORMAT_ERROR.stage_hint, Stage.TTS)
        self.assertIsNone(ErrorCode.EXPIRED.stage_hint)


class TestRequestValidation(unittest.TestCase):
    def test_valid_request_passes(self):
        self.assertEqual(validate_request(_req()), [])

    def test_protocol_mismatch_rejected(self):
        errs = validate_request(_req(protocol_version="aura-runtime-0"))
        self.assertIs(errs[0].code, ErrorCode.PROTOCOL_MISMATCH)

    def test_zero_samples_rejected(self):
        bad = AudioRef(audio_epoch=1, first_sample_index=0, sample_count=0, fmt=FMT)
        errs = validate_request(_req(audio=bad))
        self.assertIs(errs[0].code, ErrorCode.BAD_AUDIO)

    def test_bad_image_rejected(self):
        errs = validate_request(_req(image=ImageRef(frame_id=1, sha256="", camera_epoch=0, age_ms=5)))
        self.assertIs(errs[0].code, ErrorCode.BAD_IMAGE)

    def test_lost_target_rejected(self):
        t = TargetKey(track_id=1, generation=3, lifecycle=TargetLifecycle.LOST)
        errs = validate_request(_req(target=t))
        self.assertIs(errs[0].code, ErrorCode.TARGET_INVALID)


class TestDeliveryValidation(unittest.TestCase):
    def setUp(self):
        self.ctx = dict(boot_id="b1", session_id="s1", request_id=7, generation=3)

    def test_happy_path_returns_none(self):
        self.assertIsNone(validate_response_for_delivery(_resp(), **self.ctx))

    def test_boot_session_request_mismatch(self):
        self.assertIs(validate_response_for_delivery(_resp(boot_id="b0"), **self.ctx).code,
                      ErrorCode.BOOT_MISMATCH)
        self.assertIs(validate_response_for_delivery(_resp(session_id="s0"), **self.ctx).code,
                      ErrorCode.SESSION_MISMATCH)
        self.assertIs(validate_response_for_delivery(_resp(request_id=8), **self.ctx).code,
                      ErrorCode.REQUEST_MISMATCH)

    def test_cancelled_generation_wins(self):
        info = validate_response_for_delivery(_resp(), cancelled_generations=frozenset({3}),
                                              **self.ctx)
        self.assertIs(info.code, ErrorCode.STALE_GENERATION)

    def test_older_generation_rejected(self):
        self.assertIs(validate_response_for_delivery(_resp(generation=2), **self.ctx).code,
                      ErrorCode.STALE_GENERATION)

    def test_target_and_deadline(self):
        self.assertIs(validate_response_for_delivery(_resp(), target_still_valid=False,
                                                     **self.ctx).code, ErrorCode.TARGET_INVALID)
        self.assertIs(validate_response_for_delivery(_resp(), expired=True,
                                                     **self.ctx).code, ErrorCode.EXPIRED)


class TestSegmentLedger(unittest.TestCase):
    def setUp(self):
        self.ledger = SegmentLedger(max_lookahead=2)
        self.ledger.reset(request_id=7, generation=3)

    def _seg(self, idx: int) -> AudioSegment:
        return AudioSegment(segment_index=idx, fmt=FMT, pcm=b"\x00\x00" * 160)

    def test_normal_order_accepted(self):
        resp = _resp()
        self.assertTrue(self.ledger.offer(resp, self._seg(0)))
        self.assertTrue(self.ledger.offer(resp, self._seg(1)))
        self.assertEqual(self.ledger.pending_gap, [])

    def test_duplicate_dropped(self):
        resp = _resp()
        self.assertTrue(self.ledger.offer(resp, self._seg(0)))
        self.assertFalse(self.ledger.offer(resp, self._seg(0)))
        self.assertIs(self.ledger.rejected[-1][1], ErrorCode.REQUEST_MISMATCH)

    def test_far_lookahead_rejected(self):
        resp = _resp()
        self.assertFalse(self.ledger.offer(resp, self._seg(5)))
        self.assertIs(self.ledger.rejected[-1][1], ErrorCode.EXPIRED)

    def test_generation_change_invalidates(self):
        stale = _resp(generation=2)
        self.assertFalse(self.ledger.offer(stale, self._seg(0)))
        self.assertIs(self.ledger.rejected[-1][1], ErrorCode.STALE_GENERATION)

    def test_pending_gap_reports_missing(self):
        resp = _resp()
        self.ledger.offer(resp, self._seg(0))
        self.ledger.offer(resp, self._seg(2))
        self.assertEqual(self.ledger.pending_gap, [1])


if __name__ == "__main__":
    unittest.main()
