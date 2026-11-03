# -*- coding: utf-8 -*-
"""KWS 模块测试（人3 · Week A2 · 9/11—9/13）

覆盖：脚本化后端、`KwsRunner → EventBus → FSM` 链路、wav 读取/降采样/声道下混、
真实后端的**降级保护**（缺依赖/缺模型时必须抛 `KwsUnavailable` 而不是崩溃）。

**真实模型解码不进单测**（避免依赖模型文件与网络），由
`examples/run_kws_demo.py --wav ...` 与 `scripts/kws_benchmark.py` 离线验证。
环境标签：PC / SIMULATED。
"""
from __future__ import annotations

import os
import sys
import wave

import numpy as np
import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from board.runtime.audio import (KwsConfig, KwsHit, KwsRunner, KwsUnavailable,   # noqa: E402
                                 ScriptedKeywordSpotter, SherpaKeywordSpotter,
                                 available, read_wav_mono16k)
from board.runtime.audio.kws import (find_kws_model, iter_chunks,                 # noqa: E402
                                     required_model_files)
from board.runtime.event_bus import EventBus, EventEnvelope                      # noqa: E402
from board.runtime.events import EventType                                       # noqa: E402
from board.runtime.fsm import RuntimeFSM                                         # noqa: E402


def _silence(n: int = 1600):
    return np.zeros(n, dtype=np.float32)


def _write_wav(path: str, samples, rate: int = 16000, channels: int = 1,
               width: int = 2) -> str:
    """把 float32 [-1,1] 写成 wav（**测试专用**，验证 read_wav_mono16k）。"""
    data = np.asarray(samples, dtype=np.float32)
    if channels > 1:
        data = np.repeat(data.reshape(-1, 1), channels, axis=1).reshape(-1)
    if width == 2:
        payload = (data * 32767.0).astype("<i2").tobytes()
    elif width == 4:
        payload = (data * 2147483647.0).astype("<i4").tobytes()
    elif width == 1:
        payload = ((data * 127.0) + 128.0).astype(np.uint8).tobytes()
    else:
        payload = b"\x00" * (len(data) * channels * width)
    with wave.open(path, "wb") as fh:
        fh.setnchannels(channels)
        fh.setsampwidth(width)
        fh.setframerate(rate)
        fh.writeframes(payload)
    return path


class TestScriptedBackend:
    """脚本化后端：确定性，用于链路与单测。"""

    def test_hit_only_on_every_n_chunks(self):
        sp = ScriptedKeywordSpotter(every_n_chunks=3)
        assert sp.accept_waveform(_silence()) == []
        assert sp.accept_waveform(_silence()) == []
        assert len(sp.accept_waveform(_silence())) == 1

    def test_keywords_cycle(self):
        sp = ScriptedKeywordSpotter(keywords=("甲", "乙"), every_n_chunks=1)
        got = [sp.accept_waveform(_silence())[0].keyword for _ in range(3)]
        assert got == ["甲", "乙", "甲"]

    def test_timestamp_uses_sample_rate(self):
        sp = ScriptedKeywordSpotter(every_n_chunks=1, sample_rate=16000)
        hit = sp.accept_waveform(_silence(8000))[0]
        assert hit.timestamp_ms == pytest.approx(500.0, rel=1e-6)

    def test_reset_clears_state(self):
        sp = ScriptedKeywordSpotter(every_n_chunks=2)
        sp.accept_waveform(_silence())
        sp.accept_waveform(_silence())
        sp.reset()
        assert sp.accept_waveform(_silence()) == []       # 重新从第 1 块数起

    def test_hit_to_payload_is_jsonable(self):
        payload = KwsHit(keyword="小镜小镜", tokens=["小镜小镜"], timestamp_ms=123.4).to_payload()
        assert payload["keyword"] == "小镜小镜"
        assert payload["engine"] == "sherpa-onnx"
        assert isinstance(payload["timestamp_ms"], float)


class TestRunnerPipeline:
    """链路：Runner → EventBus(`audio.kws_detected`) → FSM 进入 LISTENING。"""

    def _make(self, **kw):
        bus = EventBus(max_size=32, dispatch_async=False)
        fsm = RuntimeFSM(bus=bus)
        seen = []
        bus.subscribe(lambda env: seen.append(env), {EventType.AUDIO_KWS_DETECTED})
        runner = KwsRunner(bus, ScriptedKeywordSpotter(every_n_chunks=2), **kw)
        return bus, fsm, runner, seen

    def test_hit_publishes_event_and_fsm_enters_listening(self):
        _bus, fsm, runner, seen = self._make()
        runner.feed(_silence())
        assert seen == [] and fsm.state.label == "IDLE"
        runner.feed(_silence())
        assert len(seen) == 1 and fsm.state.label == "AWAKE"
        # The wake reaction precedes listening; animation completion owns this event.
        _bus.publish(EventEnvelope(EventType.AUDIO_PLAYBACK_STOP, 'avatar', 0))
        assert fsm.state.label == "LISTENING"

    def test_event_source_and_payload(self):
        _bus, _fsm, runner, seen = self._make(source="kws-test")
        runner.feed(_silence())
        runner.feed(_silence())
        env = seen[0]
        assert env.source == "kws-test"
        assert env.payload["keyword"]
        assert env.payload["engine"] == "sherpa-onnx"

    def test_payload_extra_merged(self):
        _bus, _fsm, runner, seen = self._make(payload_extra={"session": "s1"})
        runner.feed(_silence())
        runner.feed(_silence())
        assert seen[0].payload["session"] == "s1"

    def test_stats_and_feed_stream(self):
        _bus, _fsm, runner, _seen = self._make()
        runner.feed_stream(_silence(16000), chunk_size=1600)
        stats = runner.stats()
        assert stats["chunks"] == 10 and stats["hits"] == 5

    def test_no_hit_no_event(self):
        bus = EventBus(max_size=8, dispatch_async=False)
        seen = []
        bus.subscribe(lambda env: seen.append(env))
        runner = KwsRunner(bus, ScriptedKeywordSpotter(every_n_chunks=99))
        runner.feed(_silence())
        assert seen == [] and runner.hits == 0

    def test_clock_is_injectable(self):
        _bus, _fsm, runner, seen = self._make(clock_ms=lambda: 4321)
        runner.feed(_silence())
        runner.feed(_silence())
        assert seen[0].created_at_ms == 4321


class TestWavIO:
    """wav 读取：位宽 / 声道 / 重采样。"""

    def test_read_16bit_mono(self, tmp_path):
        tone = 0.5 * np.sin(2 * np.pi * 440 * np.arange(16000) / 16000.0)
        path = _write_wav(str(tmp_path / "mono.wav"), tone)
        data = read_wav_mono16k(path)
        assert data.dtype == np.float32 and data.ndim == 1
        assert len(data) == 16000
        assert -0.6 <= float(data.min()) and float(data.max()) <= 0.6

    def test_stereo_is_downmixed(self, tmp_path):
        tone = np.full(100, 0.25, dtype=np.float32)
        path = _write_wav(str(tmp_path / "stereo.wav"), tone, channels=2)
        data = read_wav_mono16k(path)
        assert len(data) == 100                              # 下混回单声道长度
        assert float(data[0]) == pytest.approx(0.25, abs=1e-3)

    def test_resample_to_16k_changes_length(self, tmp_path):
        path = _write_wav(str(tmp_path / "8k.wav"), np.zeros(8000, dtype=np.float32), rate=8000)
        data = read_wav_mono16k(path, target_rate=16000)
        assert len(data) == pytest.approx(16000, rel=0.01)

    def test_unsupported_sample_width_raises(self, tmp_path):
        path = _write_wav(str(tmp_path / "w24.wav"), np.zeros(64, dtype=np.float32), width=3)
        with pytest.raises(ValueError):
            read_wav_mono16k(path)

    def test_iter_chunks_splits_and_keeps_tail(self):
        chunks = list(iter_chunks(np.zeros(3500, dtype=np.float32), chunk_size=1600))
        assert [len(c) for c in chunks] == [1600, 1600, 300]


class TestRealBackendGuards:
    """真实后端必须**优雅降级**：缺依赖/缺模型 → KwsUnavailable，绝不崩溃。"""

    def test_available_returns_bool(self):
        assert isinstance(available(), bool)

    def test_missing_model_raises_kws_unavailable(self, tmp_path):
        with pytest.raises(KwsUnavailable):
            SherpaKeywordSpotter(KwsConfig(model_dir=str(tmp_path)))

    def test_find_model_files_on_empty_dir(self, tmp_path):
        assert find_kws_model(str(tmp_path)) == {}

    def test_required_model_files_lists_missing(self, tmp_path):
        missing = required_model_files(KwsConfig(model_dir=str(tmp_path)))
        assert {"tokens", "encoder", "decoder", "joiner"}.issubset(set(missing))

    def test_config_resolved_defaults_keywords_file(self, tmp_path):
        cfg = KwsConfig(model_dir=str(tmp_path)).resolved()
        assert cfg.keywords_file.endswith("keywords.txt")
        assert cfg.sample_rate == 16000 and cfg.threshold == pytest.approx(0.25)

    def test_find_model_files_detects_all_parts(self, tmp_path):
        for name in ("tokens.txt", "encoder-epoch-12.onnx", "decoder-epoch-12.onnx",
                     "joiner-epoch-12.onnx", "keywords.txt"):
            (tmp_path / name).write_bytes(b"x")
        found = find_kws_model(str(tmp_path))
        assert set(found) == {"tokens", "encoder", "decoder", "joiner", "keywords"}
        assert required_model_files(KwsConfig(model_dir=str(tmp_path),
                                              keywords_file=str(tmp_path / "keywords.txt"))) == []
