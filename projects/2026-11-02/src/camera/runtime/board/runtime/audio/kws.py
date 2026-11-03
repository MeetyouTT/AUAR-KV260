# -*- coding: utf-8 -*-
"""本地关键词唤醒（KWS）—— Week A2 任务（人3 · 9/11—9/13）

三条设计原则
------------
1. **合同零改动**：命中只发布既有事件 `EventType.AUDIO_KWS_DETECTED`
   （A1 已定义；FSM 的 `IDLE / PRESENT / NETWORK_LOST → LISTENING` 与 UI 的
   `audio=busy, kws hit` 均已实现并有单测），因此本模块不引入任何新事件类型。
2. **依赖可选**：`sherpa-onnx` 未安装（或没下模型）时本模块**仍可 import**，
   只有构造真实检测器时才抛 `KwsUnavailable` —— 保证无网/无模型环境的回归不受影响。
3. **可测性**：检测后端抽象成 `KeywordSpotterBackend`；单测与无麦克风演示可用
   `ScriptedKeywordSpotter` 注入命中，**不需要模型文件与录音设备**。

环境标签：**PC 基线（CPU）**。板端复用同一事件合同；模型与运行时见
`docs/MODEL_CARD_KWS.md`（含来源/版本/许可/指标）。
"""
from __future__ import annotations

import abc
import dataclasses
import glob
import os
import time
import typing
import wave

import numpy as np


class KwsUnavailable(RuntimeError):
    """sherpa-onnx 不可用 / 模型文件缺失时抛出（调用方应降级而不是崩溃）。"""


@dataclasses.dataclass
class KwsHit:
    """一次唤醒命中。"""

    keyword: str
    tokens: typing.List[str] = dataclasses.field(default_factory=list)
    timestamp_ms: float = 0.0

    def to_payload(self) -> typing.Dict:
        """转成 `audio.kws_detected` 的载荷（JSON 可序列化）。"""
        return {"keyword": self.keyword, "tokens": list(self.tokens),
                "timestamp_ms": round(float(self.timestamp_ms), 1),
                "engine": "sherpa-onnx"}


@dataclasses.dataclass
class KwsConfig:
    """KWS 运行时配置（默认值对齐 sherpa-onnx 官方 KWS 示例）。"""

    model_dir: str = ""
    keywords_file: str = ""
    sample_rate: int = 16000
    threshold: float = 0.25
    score: float = 1.0
    max_active_paths: int = 4
    num_trailing_blanks: int = 1
    provider: str = "cpu"
    num_threads: int = 1

    def resolved(self) -> "KwsConfig":
        """补齐派生字段（keywords_file 缺省 = <model_dir>/keywords.txt）。"""
        cfg = dataclasses.replace(self)
        if not cfg.keywords_file and cfg.model_dir:
            cfg.keywords_file = os.path.join(cfg.model_dir, "keywords.txt")
        return cfg


def _candidate_score(name: str) -> int:
    """模型文件候选打分（越小越优先）。

    官方包同时带 `epoch-12-avg-2` 与 `epoch-99-avg-1`、以及 `.int8.` 量化变体；
    示例与 README 用的是 **非量化 epoch-12-avg-2**，故默认优先它（int8 更快但精度略低）。
    """
    score = 0
    if ".int8." in name:
        score += 10
    if "fp16" in name:
        score += 2
    if "epoch-12-avg-2" in name:
        score -= 5
    return score


def find_kws_model(model_dir: str) -> typing.Dict[str, str]:
    """在模型目录里定位 tokens/encoder/decoder/joiner（支持子目录与多种变体）。

    返回 {'tokens':…, 'encoder':…, 'decoder':…, 'joiner':…, 'keywords':…}；
    缺失的键不会出现，调用方用 `required_model_files()` 校验。
    """
    best: typing.Dict[str, typing.Tuple[int, str]] = {}

    def _consider(key: str, path: str, name: str) -> None:
        score = _candidate_score(name)
        cur = best.get(key)
        if cur is None or score < cur[0] or (score == cur[0] and path < cur[1]):
            best[key] = (score, path)

    for path in glob.glob(os.path.join(model_dir, "**", "*"), recursive=True):
        if not os.path.isfile(path):
            continue
        name = os.path.basename(path).lower()
        if name == "tokens.txt":
            _consider("tokens", path, name)
        elif name.startswith("encoder") and name.endswith(".onnx"):
            _consider("encoder", path, name)
        elif name.startswith("decoder") and name.endswith(".onnx"):
            _consider("decoder", path, name)
        elif name.startswith("joiner") and name.endswith(".onnx"):
            _consider("joiner", path, name)
        elif name == "keywords.txt":
            _consider("keywords", path, name)
    return {key: value[1] for key, value in best.items()}


def required_model_files(cfg: KwsConfig) -> typing.List[str]:
    """返回缺失的关键文件清单（空列表 = 齐备）。"""
    files = find_kws_model(cfg.model_dir) if cfg.model_dir else {}
    missing = [key for key in ("tokens", "encoder", "decoder", "joiner") if key not in files]
    if cfg.keywords_file and not os.path.isfile(cfg.keywords_file):
        missing.append("keywords")
    return missing


def default_clock_ms() -> int:
    """单调时钟（毫秒）——板端为 64 位单调计数器，PC 基线用 monotonic。"""
    return int(time.monotonic() * 1000)


class KeywordSpotterBackend(abc.ABC):
    """检测后端合同：吃 16kHz 单声道 float32 采样块，吐命中。"""

    def __init__(self, sample_rate: int = 16000) -> None:
        self.sample_rate = int(sample_rate)

    @abc.abstractmethod
    def accept_waveform(self, samples: "np.ndarray") -> typing.List[KwsHit]:
        """喂一段采样（float32，[-1, 1]），返回本块内产生的命中（可能为空）。"""

    def reset(self) -> None:
        """清空内部状态（新的一轮聆听前调用）。"""

    def close(self) -> None:
        """释放资源（默认无操作）。"""

    def __enter__(self) -> "KeywordSpotterBackend":
        return self

    def __exit__(self, *_exc) -> None:
        self.close()


class ScriptedKeywordSpotter(KeywordSpotterBackend):
    """**不依赖模型**的脚本化检测器：每 `every_n_chunks` 块吐一个命中，关键词循环取用。

    用途：① 单测（确定性）；② `--synthetic` 演示；③ 无网络/无模型环境的链路自检。
    """

    def __init__(self, keywords: typing.Sequence[str] = ("小镜小镜",),
                 every_n_chunks: int = 1, sample_rate: int = 16000) -> None:
        super().__init__(sample_rate)
        self._keywords = list(keywords) or ["小镜小镜"]
        self._every = max(1, int(every_n_chunks))
        self._calls = 0
        self._emitted = 0
        self._samples_seen = 0

    def accept_waveform(self, samples: "np.ndarray") -> typing.List[KwsHit]:
        self._calls += 1
        self._samples_seen += int(samples.shape[0]) if samples is not None else 0
        if self._calls % self._every != 0:
            return []
        keyword = self._keywords[self._emitted % len(self._keywords)]
        self._emitted += 1
        return [KwsHit(keyword=keyword,
                       tokens=[keyword],
                       timestamp_ms=self._samples_seen * 1000.0 / self.sample_rate)]

    def reset(self) -> None:
        self._calls = 0
        self._emitted = 0
        self._samples_seen = 0


class SherpaKeywordSpotter(KeywordSpotterBackend):
    """**真实**后端：sherpa-onnx KeywordSpotter（CPU 基线，16kHz 单声道 float32）。

    模型与许可见 `docs/MODEL_CARD_KWS.md`；未装依赖或缺模型时抛 `KwsUnavailable`。
    """

    def __init__(self, config: KwsConfig) -> None:
        cfg = config.resolved()
        super().__init__(cfg.sample_rate)
        self.config = cfg
        try:
            import sherpa_onnx
        except ImportError as exc:                      # pragma: no cover - 环境相关
            raise KwsUnavailable(
                "未安装 sherpa-onnx：pip install sherpa-onnx sounddevice") from exc

        missing = required_model_files(cfg)
        if missing:
            raise KwsUnavailable(
                "模型文件缺失 %s（model_dir=%s）；下载与校验见 docs/MODEL_CARD_KWS.md"
                % (missing, cfg.model_dir or "<未设置>"))

        files = find_kws_model(cfg.model_dir)
        self._sherpa = sherpa_onnx
        self._spotter = sherpa_onnx.KeywordSpotter(
            tokens=files["tokens"],
            encoder=files["encoder"],
            decoder=files["decoder"],
            joiner=files["joiner"],
            num_threads=int(cfg.num_threads),
            max_active_paths=int(cfg.max_active_paths),
            keywords_file=cfg.keywords_file,
            keywords_score=float(cfg.score),
            keywords_threshold=float(cfg.threshold),
            num_trailing_blanks=int(cfg.num_trailing_blanks),
            provider=cfg.provider,
        )
        self._stream = self._spotter.create_stream()
        self._decoded_samples = 0                       # 统计：已解码采样数（算延迟用）

    def _result_keyword(self, stream) -> str:
        """兼容版本差异：`get_result` 可能返回 str，也可能返回带 `.keyword` 的对象。"""
        try:
            res = self._spotter.get_result(stream)
        except Exception:                               # pragma: no cover - 版本差异
            return ""
        if not res:
            return ""
        if isinstance(res, str):
            return res
        return str(getattr(res, "keyword", "") or "")

    def accept_waveform(self, samples: "np.ndarray") -> typing.List[KwsHit]:
        if samples is None or len(samples) == 0:
            return []
        samples = np.asarray(samples, dtype=np.float32)
        self._stream.accept_waveform(self.sample_rate, samples)
        self._decoded_samples += int(samples.shape[0])

        hits: typing.List[KwsHit] = []
        while self._spotter.is_ready(self._stream):
            self._spotter.decode_stream(self._stream)
            keyword = self._result_keyword(self._stream)
            if keyword:
                hits.append(KwsHit(
                    keyword=keyword,
                    tokens=[keyword],
                    timestamp_ms=self._decoded_samples * 1000.0 / self.sample_rate))
                self._spotter.reset_stream(self._stream)   # 命中后重新等下一轮唤醒
        return hits

    def reset(self) -> None:
        self._spotter.reset_stream(self._stream)
        self._decoded_samples = 0

    def close(self) -> None:
        self._stream = None
        self._spotter = None


def iter_chunks(samples: "np.ndarray",
                chunk_size: int = 1600) -> typing.Iterator["np.ndarray"]:
    """把长音频切成固定长度块（默认 1600 采样 = 100ms @16kHz），模拟实时流。"""
    step = max(1, int(chunk_size))
    for start in range(0, len(samples), step):
        yield samples[start:start + step]


class KwsRunner:
    """把「检测后端」接到「事件总线」：命中即发布 `audio.kws_detected`。

    只做搬运、不做状态判断 —— 状态迁移由 FSM 负责（合同解耦）。
    """

    def __init__(self, bus: typing.Any, backend: KeywordSpotterBackend,
                 source: str = "kws",
                 clock_ms: typing.Callable[[], int] = default_clock_ms,
                 payload_extra: typing.Optional[typing.Dict] = None) -> None:
        self.bus = bus
        self.backend = backend
        self.source = source
        self.clock_ms = clock_ms
        self.payload_extra = dict(payload_extra or {})
        self.chunks = 0                                 # 喂入块数
        self.hits = 0                                   # 累计命中数（证据/统计）

    def feed(self, samples: "np.ndarray") -> typing.List[KwsHit]:
        """喂一块采样；命中则发事件；返回本次命中列表。"""
        from ..event_bus import EventEnvelope           # 延迟导入，避免包初始化顺序问题
        from ..events import EventType

        self.chunks += 1
        hits = self.backend.accept_waveform(samples)
        for hit in hits:
            payload = hit.to_payload()
            payload.update(self.payload_extra)
            self.bus.publish(EventEnvelope(event_type=EventType.AUDIO_KWS_DETECTED,
                                           source=self.source,
                                           created_at_ms=self.clock_ms(),
                                           payload=payload))
            self.hits += 1
        return hits

    def feed_stream(self, samples: "np.ndarray",
                    chunk_size: int = 1600) -> typing.List[KwsHit]:
        """按块喂完整段音频 → 返回全部命中（离线验证 / benchmark 用）。"""
        out: typing.List[KwsHit] = []
        for chunk in iter_chunks(samples, chunk_size):
            out.extend(self.feed(chunk))
        return out

    def reset(self) -> None:
        self.backend.reset()

    def close(self) -> None:
        self.backend.close()

    def stats(self) -> typing.Dict:
        return {"chunks": self.chunks, "hits": self.hits, "source": self.source,
                "payload_extra": dict(self.payload_extra)}


def read_wav_mono16k(path: str, target_rate: int = 16000) -> "np.ndarray":
    """读 wav → **单声道 float32**（[-1,1]），必要时线性重采样到 target_rate。

    ⚠️ 线性重采样只为「能喂进模型」，音质与官方重采样不具可比性；
       正式 benchmark 请用 16kHz 素材或用 ffmpeg 预转换。
    """
    with wave.open(path, "rb") as fh:
        n_ch = fh.getnchannels()
        width = fh.getsampwidth()
        rate = fh.getframerate()
        raw = fh.readframes(fh.getnframes())

    if width == 2:
        data = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
    elif width == 4:
        data = np.frombuffer(raw, dtype="<i4").astype(np.float32) / 2147483648.0
    elif width == 1:
        data = (np.frombuffer(raw, dtype=np.uint8).astype(np.float32) - 128.0) / 128.0
    else:
        raise ValueError("不支持的采样位宽：%d 字节" % width)

    if n_ch > 1:                                        # 多声道 → 取均值（够用即可）
        data = data.reshape(-1, n_ch).mean(axis=1)
    if target_rate > 0 and rate != target_rate and len(data) > 1:
        n_out = int(round(len(data) * target_rate / float(rate)))
        idx = np.linspace(0.0, len(data) - 1.0, num=max(1, n_out))
        data = np.interp(idx, np.arange(len(data)), data).astype(np.float32)
    return np.ascontiguousarray(data, dtype=np.float32)


def available() -> bool:
    """sherpa-onnx 是否可导入（**不校验模型文件**）。"""
    try:
        import sherpa_onnx                                # noqa: F401
        return True
    except ImportError:
        return False
