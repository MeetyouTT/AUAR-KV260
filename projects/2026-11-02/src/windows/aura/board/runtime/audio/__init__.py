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
from importlib import import_module

# Loading a cached WAV or inspecting a device must not load ASR/TTS dependencies.
# Keep the existing public names; import their providers only when requested.
_EXPORT_GROUPS = {
    'asr': ('AsrConfig', 'AsrUnavailable', 'SherpaOfflineRecognizer', 'build_recognizer', 'find_asr_model'),
    'kws': ('KwsConfig', 'KwsHit', 'KwsRunner', 'KwsUnavailable', 'KeywordSpotterBackend',
            'ScriptedKeywordSpotter', 'SherpaKeywordSpotter', 'available', 'read_wav_mono16k'),
    'tts': ('SapiTtsBackend', 'ScriptedTtsBackend', 'SherpaTtsBackend', 'TtsBackend',
            'TtsConfig', 'TtsPlayer', 'TtsUnavailable', 'ascii_path', 'build_player', 'find_tts_model'),
    'tts_style': ('DEFAULT_STYLE', 'RATE_MULTIPLIER', 'TONE_BY_STATE', 'TtsStyle', 'build_ssml',
                  'clamp_style', 'for_emotion', 'rate_multiplier', 'split_segments'),
    'vad': ('EnergyVad', 'VadConfig', 'VadEvent'),
}
_EXPORTS = {name: module for module, names in _EXPORT_GROUPS.items() for name in names}
__all__ = list(_EXPORTS)


def __getattr__(name):
    module = _EXPORTS.get(name)
    if module is None:
        raise AttributeError('module %r has no attribute %r' % (__name__, name))
    value = getattr(import_module('.' + module, __name__), name)
    globals()[name] = value
    return value


def __dir__():
    return sorted(set(globals()) | set(__all__))
