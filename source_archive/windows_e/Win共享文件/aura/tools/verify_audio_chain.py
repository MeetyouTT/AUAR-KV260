# -*- coding: utf-8 -*-
"""音频链路验收：VAD / ASR / TTS（本地；只用 stdlib + numpy + sherpa-onnx）。

检查项
------
  A1 ASR 自检：用模型自带的官方 `test_wavs/*.wav` 识别（模型/引擎是否可用）
  A2 VAD 自检：合成波形（正弦 + 静音）→ 应恰好切出 1 段、时长接近
  A3 TTS→ASR 闭环：用 SAPI 把一句话写成 wav → 重采样到 16k → ASR 识别 → 比对字符重合率
     （这一步同时验证"玩偶说话"与"听懂你说话"两端的打通）

用法（本机无系统 Python，用 ComfyUI 便携解释器）：
    "<PY>" -s tools\\verify_audio_chain.py
输出：控制台 + %TEMP%\\aura_audio_chain.txt
"""
import os
import subprocess
import sys
import time
import wave
from pathlib import Path

import numpy as np

AURA = Path(__file__).resolve().parents[1]
if str(AURA) not in sys.path:
    sys.path.insert(0, str(AURA))

from board.runtime.audio.asr import AsrConfig, SherpaOfflineRecognizer   # noqa: E402
from board.runtime.audio.tts import TtsConfig, build_player              # noqa: E402
from board.runtime.audio.vad import EnergyVad, VadConfig                 # noqa: E402

OUT = Path(os.environ.get("TEMP", ".")) / "aura_audio_chain.txt"
MODEL_DIR = AURA / "models" / "asr"
LOG = []
FAILED = []


def log(s):
    LOG.append(str(s))
    print(s, flush=True)


def check(cond, code, msg):
    log("  [%s] %s" % ("OK " if cond else "FAIL", "%s %s" % (code, msg)))
    if not cond:
        FAILED.append(code)
    return cond


def read_wav(path):
    """读 wav → (float32 mono [-1,1], sample_rate)。"""
    with wave.open(str(path), "rb") as fh:
        sr, ch, sw, n = (fh.getframerate(), fh.getnchannels(),
                         fh.getsampwidth(), fh.getnframes())
        raw = fh.readframes(n)
    if sw == 2:
        data = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    elif sw == 4:
        data = np.frombuffer(raw, dtype=np.int32).astype(np.float32) / 2147483648.0
    else:
        data = np.frombuffer(raw, dtype=np.uint8).astype(np.float32)
        data = (data - 128.0) / 128.0
    if ch > 1:
        data = data.reshape(-1, ch).mean(axis=1)
    return data.astype(np.float32), sr


def resample(x, sr_in, sr_out):
    """线性插值重采样（零依赖；演示足够）。"""
    if sr_in == sr_out or len(x) == 0:
        return np.asarray(x, dtype=np.float32)
    n_out = max(1, int(round(len(x) * float(sr_out) / float(sr_in))))
    idx = np.linspace(0.0, len(x) - 1, n_out)
    return np.interp(idx, np.arange(len(x)), x).astype(np.float32)


def text_overlap(a, b):
    """字符级重合率（去空白/标点后，按较短串计算命中比例）。"""
    keep = lambda s: [c for c in str(s) if c.strip() and c not in "，。！？、,.!?；;：:"]
    aa, bb = keep(a), keep(b)
    if not aa or not bb:
        return 0.0
    hit = sum(1 for c in aa if c in bb)
    return hit / float(len(aa))


# --------------------------------------------------------------------------- #
# A1 ASR 自检（模型自带官方样例）
# --------------------------------------------------------------------------- #
def check_asr():
    log("A1 ASR 自检（官方 test_wavs）")
    try:
        asr = SherpaOfflineRecognizer(AsrConfig(model_dir=str(MODEL_DIR)))
    except Exception as exc:
        check(False, "A1a", "构造识别器失败：%s" % exc)
        return None
    check(True, "A1a", "识别器就绪：%s" % os.path.basename(asr.model_path))
    wav_dir = next(iter(MODEL_DIR.glob("**/test_wavs")), None)
    if wav_dir is None:
        check(False, "A1b", "未找到 test_wavs（模型自带样例）")
        return asr
    ok = total = 0
    for wav in sorted(wav_dir.glob("*.wav"))[:4]:
        samples, sr = read_wav(wav)
        samples = resample(samples, sr, 16000)
        t0 = time.time()
        text = asr.transcribe(samples, 16000)
        total += 1
        ok += 1 if text else 0
        log("    %-12s %.2fs → %s" % (wav.name, time.time() - t0, text[:48]))
    check(ok == total and total > 0, "A1b", "%d/%d 个样例识别出文本" % (ok, total))
    return asr


# --------------------------------------------------------------------------- #
# A2 VAD 自检（合成波形）
# --------------------------------------------------------------------------- #
def check_vad():
    log("A2 VAD 自检（合成：0.3s 底噪 + 1.2s 正弦 + 0.9s 底噪）")
    sr = 16000
    rng = np.random.default_rng(7)
    silence = (rng.standard_normal(int(0.3 * sr)) * 0.0005).astype(np.float32)
    tone = (0.25 * np.sin(2 * np.pi * 220 * np.arange(int(1.2 * sr)) / sr)).astype(np.float32)
    tail = (rng.standard_normal(int(0.9 * sr)) * 0.0005).astype(np.float32)
    vad = EnergyVad(VadConfig(sample_rate=sr))
    events = []
    for chunk in np.array_split(np.concatenate([silence, tone, tail]), 12):
        events.extend(vad.accept(chunk))
    flushed = vad.flush()
    if flushed is not None:
        events.append(flushed)
    kinds = [e.kind for e in events]
    ends = [e for e in events if e.kind == "speech_end"]
    log("    事件：%s" % kinds)
    check("speech_start" in kinds, "A2a", "检测到 speech_start")
    check(len(ends) == 1, "A2b", "恰好切出 1 段（实际 %d）" % len(ends))
    if ends:
        dur = ends[0].duration_ms / 1000.0
        log("    切出时长 %.2fs（含 600ms 静音尾巴，期望 ≈1.8s）" % dur)
        check(1.3 <= dur <= 2.4, "A2c", "时长合理：%.2fs" % dur)


# --------------------------------------------------------------------------- #
# A3 TTS → ASR 闭环
# --------------------------------------------------------------------------- #
SENTENCE = "你好，我是桌面玩偶小光。"


def check_tts_closed_loop(asr):
    log("A3 TTS→ASR 闭环（SAPI 写 wav → ASR 识别）")
    player = build_player(TtsConfig())
    spoke = player.speak(SENTENCE)
    log("    TTS：%.2fs（%s / %s）" % (spoke, player.config.engine, player.config.voice))
    check(spoke > 0, "A3a", "TTS 播报成功（%.2fs）" % spoke)

    wav_path = Path(os.environ.get("TEMP", ".")) / "aura_tts_sample.wav"
    script = ("Add-Type -AssemblyName System.Speech; "
              "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
              "try { $s.SelectVoice('%s') } catch { }; "
              "$s.SetOutputToWaveFile('%s'); $s.Speak('%s'); $s.Dispose()"
              % (player.config.voice, str(wav_path), SENTENCE.replace("'", "''")))
    subprocess.run(["powershell", "-NoProfile", "-Command", script], timeout=60, check=False)
    check(wav_path.is_file(), "A3b", "SAPI 写出 wav：%s" % wav_path.name)
    if not wav_path.is_file() or asr is None:
        return
    samples, sr = read_wav(wav_path)
    log("    wav：%.2fs @%dHz → 重采样 16k" % (len(samples) / float(sr), sr))
    t0 = time.time()
    text = asr.transcribe(resample(samples, sr, 16000), 16000)
    log("    识别：%.2fs → %s" % (time.time() - t0, text))
    ratio = text_overlap(SENTENCE, text)
    check(ratio >= 0.6, "A3c", "与原句字符重合率 %.0f%%（≥60%% 视为链路通）" % (ratio * 100))


def main():
    log("=== 音频链路验收（VAD / ASR / TTS）===")
    log("模型目录：%s（存在=%s）" % (MODEL_DIR, MODEL_DIR.is_dir()))
    asr = check_asr()
    check_vad()
    check_tts_closed_loop(asr)
    log("=== RESULT: %s (%d 项失败) ===" % ("FAIL" if FAILED else "OK", len(FAILED)))
    if FAILED:
        log("失败项：%s" % (", ".join(FAILED),))
    OUT.write_text("\n".join(LOG), encoding="utf-8")
    print("log -> %s" % OUT, flush=True)
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
