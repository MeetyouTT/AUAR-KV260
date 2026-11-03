# -*- coding: utf-8 -*-
"""ASR（唯一 ASR）—— sherpa-onnx 非流式中文识别（`audio/__init__.py` 已约定本模块）。

契约与红线
----------
- 只做「波形 → 文本」；**不做 VAD、不发事件**（VAD 在 `vad.py`；"说完了"由上层发
  `EventType.AUDIO_VAD_END`，不新增事件类型）；
- 依赖可选：未装 `sherpa-onnx` 或模型缺失时本模块**仍可 import**，只有构造真实识别器时
  抛 `AsrUnavailable`（与 `kws.py` 同风格，保证无网/无模型环境的回归不受影响）。

模型
----
默认目录 `aura/models/asr/`（本机已下 `sherpa-onnx-paraformer-zh-2023-09-14`，223 MB）。
定位逻辑支持子目录与 int8/fp32 变体（与 `kws.find_kws_model` 同思路）；
**非量化优先**（精度更好），可用 `AsrConfig.prefer_int8=True` 换速度。
"""
from __future__ import annotations

import dataclasses
import glob
import os
import typing

import numpy as np

#: 默认模型根目录：aura/models/asr（board/runtime/audio/asr.py → 上溯 4 层）
DEFAULT_ASR_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
    "models", "asr")


class AsrUnavailable(RuntimeError):
    """sherpa-onnx 未安装 / 模型文件缺失时抛出（调用方应降级而不是崩溃）。"""


@dataclasses.dataclass
class AsrConfig:
    """ASR 运行时配置（默认对准本机：CPU、2 线程、16kHz 中文）。"""

    model_dir: str = DEFAULT_ASR_DIR
    num_threads: int = 2
    provider: str = "cpu"
    sample_rate: int = 16000
    feature_dim: int = 80
    decoding_method: str = "greedy_search"
    prefer_int8: bool = False


def _candidate_score(name: str, prefer_int8: bool) -> int:
    """模型文件候选打分（越小越优先）。"""
    score = 0
    if ".int8." in name:
        score += -5 if prefer_int8 else 10
    if "fp32" in name:
        score += 1
    return score


def find_asr_model(model_dir: str, prefer_int8: bool = False) -> typing.Dict[str, str]:
    """在模型目录里定位 tokens 与 onnx 模型（支持子目录 / 多变体）。"""
    best: typing.Dict[str, typing.Tuple[int, str]] = {}

    def _consider(key: str, path: str, name: str) -> None:
        score = _candidate_score(name, prefer_int8)
        cur = best.get(key)
        if cur is None or score < cur[0] or (score == cur[0] and path < cur[1]):
            best[key] = (score, path)

    for path in glob.glob(os.path.join(model_dir, "**", "*"), recursive=True):
        if not os.path.isfile(path):
            continue
        name = os.path.basename(path).lower()
        if name == "tokens.txt":
            _consider("tokens", path, name)
        elif name.endswith(".onnx") and ("model" in name):
            _consider("model", path, name)
    return {key: value[1] for key, value in best.items()}


def required_model_files(cfg: AsrConfig) -> typing.List[str]:
    """返回缺失的关键文件（空列表 = 齐备）。"""
    files = find_asr_model(cfg.model_dir, cfg.prefer_int8) if cfg.model_dir else {}
    return [key for key in ("tokens", "model") if key not in files]


class SherpaOfflineRecognizer:
    """非流式识别器：喂整段 utterance → 出文本（配 VAD 使用最自然）。"""

    def __init__(self, cfg: typing.Optional[AsrConfig] = None) -> None:
        self.cfg = cfg or AsrConfig()
        try:
            import sherpa_onnx
        except ImportError as exc:                     # pragma: no cover
            raise AsrUnavailable(
                "未安装 sherpa-onnx：pip install --no-deps sherpa-onnx") from exc

        missing = required_model_files(self.cfg)
        if missing:
            raise AsrUnavailable("模型文件缺失 %s（model_dir=%s）"
                                 % (missing, self.cfg.model_dir or "<未设置>"))
        files = find_asr_model(self.cfg.model_dir, self.cfg.prefer_int8)
        self._sherpa = sherpa_onnx
        self._recognizer = sherpa_onnx.OfflineRecognizer.from_paraformer(
            paraformer=files["model"],
            tokens=files["tokens"],
            num_threads=int(self.cfg.num_threads),
            sample_rate=int(self.cfg.sample_rate),
            feature_dim=int(self.cfg.feature_dim),
            decoding_method=self.cfg.decoding_method,
            provider=self.cfg.provider,
        )
        self.model_path = files["model"]

    def transcribe(self, samples: typing.Any, sample_rate: typing.Optional[int] = None) -> str:
        """整段波形 → 文本（空输入返回空串；异常不抛出，返回空串并打印）。"""
        if samples is None or len(samples) == 0:
            return ""
        audio = np.asarray(samples, dtype=np.float32).reshape(-1)
        stream = self._recognizer.create_stream()
        stream.accept_waveform(int(sample_rate or self.cfg.sample_rate), audio)
        try:
            self._recognizer.decode_stream(stream)
            result = stream.result
        except Exception as exc:                       # pragma: no cover - 运行期异常保护
            print("[asr] 识别失败：%s" % exc, flush=True)
            return ""
        return str(getattr(result, "text", "") or "").strip()

    def stats(self) -> typing.Dict:
        return {"model": os.path.basename(self.model_path),
                "dir": self.cfg.model_dir, "threads": self.cfg.num_threads,
                "provider": self.cfg.provider}


def build_recognizer(cfg: typing.Optional[AsrConfig] = None):
    """按配置构造识别器；不可用返回 None（调用方降级，不让演示中断）。"""
    try:
        return SherpaOfflineRecognizer(cfg)
    except AsrUnavailable as exc:
        print("[asr] 不可用：%s" % exc, flush=True)
        return None
