# -*- coding: utf-8 -*-
"""音频前端（人3 · Week A2）

模块划分：
  - `kws.py`   本地关键词唤醒（sherpa-onnx，依赖可选）→ 发布 `audio.kws_detected`
  - `vad.py`   turn 切分（能量 VAD，零依赖）→ utterance 交给 `asr.py`
  - `asr.py`   唯一 ASR（sherpa-onnx 非流式中文；模型 `models/asr/`，本机已下 223MB 版）
  - `tts.py`   唯一 TTS（Windows SAPI 中文女声）→ **播完发布 `audio.playback_stopped`**

红线：本包只负责**感知与播放**，不做对话编排；事件经由 `board.runtime.event_bus` 流转，
      FSM / UI 均通过既有事件合同消费，不新增事件类型（人3 任务书 §五）。
环境标签：PC / SIMULATED 基线；板端复用同一事件合同。
"""
from .asr import (AsrConfig, AsrUnavailable, SherpaOfflineRecognizer,   # noqa: F401
                  build_recognizer, find_asr_model)
from .kws import (KwsConfig, KwsHit, KwsRunner, KwsUnavailable,      # noqa: F401
                  KeywordSpotterBackend, ScriptedKeywordSpotter,
                  SherpaKeywordSpotter, available, read_wav_mono16k)
from .tts import (SapiTtsBackend, ScriptedTtsBackend, SherpaTtsBackend,  # noqa: F401
                  TtsBackend, TtsConfig, TtsPlayer, TtsUnavailable,
                  ascii_path, build_player, find_tts_model)
from .tts_style import (DEFAULT_STYLE, RATE_MULTIPLIER, TONE_BY_STATE,    # noqa: F401
                        TtsStyle, build_ssml, clamp_style, for_emotion,
                        rate_multiplier, split_segments)
from .vad import EnergyVad, VadConfig, VadEvent                         # noqa: F401
