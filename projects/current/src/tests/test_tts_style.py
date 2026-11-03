# -*- coding: utf-8 -*-
"""TTS 语气层单测：`board/runtime/audio/tts_style.py`（LLM 的 emotion → 逐句韵律）。

覆盖：
  ① 三档映射与 `fsm` **同源**（玩偶素材档 == 语音韵律档）；
  ② 未知 / 脏输入一律走中性档（不抛异常）；
  ③ 关键字限幅：非法回落 medium、音高最多 ±1 档、停顿夹取 [0, 2000]；
  ④ SSML 结构：逐段 prosody + 段间 break + XML 转义 + 空文本返回空串；
  ⑤ **一行回退契约**：`TtsPlayer.speak_async(text)` 不传 style → 后端收到 `ssml=None`。
"""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from board.runtime import fsm                                        # noqa: E402
from board.runtime.audio import tts_style                            # noqa: E402
from board.runtime.audio.tts import ScriptedTtsBackend, TtsPlayer    # noqa: E402


def test_tone_table_matches_fsm_single_source():
    """① 分档与 fsm 同源：同一 emotion 在"玩偶素材档"与"语音韵律档"上必须一致。"""
    cases = (("happy", "high"), ("兴奋", "high"), ("surprised", "high"),
             ("sad", "low"), ("难过", "low"), ("apologetic", "low"),
             ("neutral", "neutral"), ("随便聊聊天", "neutral"), ("friendly", "neutral"))
    for emotion, expected in cases:
        name = fsm.speaking_state_name(emotion)          # 玩偶会演哪条 talking_* 素材
        style = tts_style.for_emotion(emotion)           # 语音用什么韵律
        assert style == tts_style.TONE_BY_STATE[name]
        assert style.label == expected


def test_unknown_and_dirty_emotion_fall_back_to_neutral():
    """② 未知 / 非字符串 / 空值 → 中性档（保守默认，不许抛异常）。"""
    neutral = tts_style.TONE_BY_STATE["SPEAKING_NEUTRAL"]
    for dirty in (None, "", "   ", 123, [], {}, "莫名其妙的心情", "Neutral!!!"):
        assert tts_style.for_emotion(dirty) == neutral
    # 大小写 / 空白归一（fsm 的 is_low/high_emotion 已做归一，这里锁住行为）
    assert tts_style.for_emotion("  HAPPY  ").label == "high"


def test_clamp_limits_keywords_pitch_step_and_break():
    """③ 限幅：非法关键字回落 medium、音高最多 ±1 档、停顿夹到 [0, 2000]。"""
    bad = tts_style.TtsStyle(rate="恐怖", pitch="x-high", volume="loud", break_ms=9999)
    fixed = tts_style.clamp_style(bad)
    assert fixed.rate == "medium"        # 非法关键字 → medium
    assert fixed.pitch == "high"         # x-high 越界 1 档 → 收到 high
    assert fixed.volume == "loud"        # 合法且未越界（±2 档内）
    assert fixed.break_ms == 2000
    assert tts_style.clamp_style(tts_style.TtsStyle(break_ms=-50)).break_ms == 0
    assert tts_style.clamp_style(tts_style.TtsStyle(break_ms="abc")).break_ms == 200
    # 极限档 x-low 也只到 1 档（禁止把拼接音压成电音）
    assert tts_style.clamp_style(tts_style.TtsStyle(pitch="x-low")).pitch == "low"


def test_split_segments_keeps_punctuation_and_merges_fragments():
    """④ 切段：标点跟随前段；过短片段被合并（避免"碎句"磕巴）。"""
    segs = tts_style.split_segments("好的，我帮你把灯打开。还有别的吗？")
    assert segs == ["好的，我帮你把灯打开。", "还有别的吗？"]
    assert tts_style.split_segments("嗯，好。") == ["嗯，好。"]
    assert tts_style.split_segments("") == []
    assert tts_style.split_segments("   ") == []
    assert tts_style.split_segments("没有标点的一句话") == ["没有标点的一句话"]


def test_build_ssml_structure_and_escaping():
    """⑤ SSML：逐段 prosody、段间 break、XML 转义、空文本返回空串。"""
    low = tts_style.TONE_BY_STATE["SPEAKING_LOW"]
    ssml = tts_style.build_ssml("我有点难过。不过没关系。", low)
    assert ssml.startswith("<speak") and ssml.endswith("</speak>")
    assert ssml.count("<prosody") == 2 and ssml.count("</prosody>") == 2
    assert ssml.count("<break") == 1
    assert '<break time="330ms"/>' in ssml
    assert 'rate="slow"' in ssml and 'pitch="low"' in ssml
    assert 'xml:lang="zh-CN"' in ssml

    esc = tts_style.build_ssml("A & B <测试>。", tts_style.DEFAULT_STYLE)
    assert "&amp;" in esc and "&lt;测试&gt;" in esc and "<测试>" not in esc
    assert tts_style.build_ssml("   ", tts_style.DEFAULT_STYLE) == ""

    # 单段文本：1 个 prosody、0 个 break
    one = tts_style.build_ssml("一句话而已", tts_style.DEFAULT_STYLE)
    assert one.count("<prosody") == 1 and "<break" not in one


def test_player_without_style_keeps_plain_text_rollback():
    """⑥ 一行回退契约：不传 style → 后端收到 ssml=None（旧行为逐位不变）。"""
    backend = ScriptedTtsBackend(chars_per_second=1000.0)
    seen = []
    raw = backend.speak_async

    def spy(text, ssml=None, style=None):
        seen.append((text, ssml, style))
        return raw(text, ssml, style)

    backend.speak_async = spy                      # 记录后端实际收到的参数
    player = TtsPlayer(backend=backend)

    player.speak_async("旧行为的一句话")            # 不传 style = 回退路径
    assert seen[-1] == ("旧行为的一句话", None, None)
    assert player.stats()["style"] == "-"

    player.speak_async("新行为的一句话。第二句。", style=tts_style.for_emotion("happy"))
    text, ssml, style_seen = seen[-1]
    assert text == "新行为的一句话。第二句。"
    assert ssml and ssml.startswith("<speak") and 'rate="fast"' in ssml
    assert style_seen.label == "high"              # style 也传给了后端（神经后端要用它算 speed）
    assert player.stats()["style"] == "high"


def test_rate_multiplier_matches_tone_table_direction():
    """S2：韵律档 → 语速乘子，且方向与档位一致（低落<中性<高涨）。"""
    m = tts_style.rate_multiplier
    assert m(tts_style.for_emotion("sad")) < 1.0 < m(tts_style.for_emotion("happy"))
    assert m(tts_style.for_emotion("neutral")) == 1.0
    assert m("x-slow") == 0.80 and m("fast") == 1.12 and m("x-fast") == 1.25
    assert m(None) == 1.0 and m("莫名其妙") == 1.0 and m("") == 1.0


def test_sherpa_speed_for_clamps_and_composes():
    """S2：神经 TTS 的 `speed_for` = 基础 speed × 档位乘子，限幅 [0.5, 2.0]。

    不加载模型：直接 `object.__new__` 造实例只测纯逻辑（模型加载另由真机探针覆盖）。
    """
    from board.runtime.audio.tts import SherpaTtsBackend, TtsConfig

    be = object.__new__(SherpaTtsBackend)
    be.config = TtsConfig(engine="vits", speed=1.0)
    assert round(be.speed_for(tts_style.for_emotion("happy")), 3) == 1.12
    assert round(be.speed_for(tts_style.for_emotion("sad")), 3) == 0.90
    assert be.speed_for(None) == 1.0
    be.config = TtsConfig(engine="vits", speed=5.0)          # 越界 → 夹到上限
    assert be.speed_for(None) == 2.0
    be.config = TtsConfig(engine="vits", speed=0.01)         # 越界 → 夹到下限
    assert be.speed_for(tts_style.for_emotion("sad")) == 0.5


def test_find_tts_model_and_ascii_path(tmp_path, monkeypatch):
    """S2：模型目录定位（VITS 优先、兼容 int8）；非 ASCII 路径 → 返回 ASCII junction。"""
    from board.runtime.audio.tts import (_model_onnx, ascii_path, find_tts_model,
                                         tts_model_root)
    # Keep junctions in the test's temporary area, not persistent user/global folders.
    from board.runtime.audio import tts as tts_module
    monkeypatch.setattr(tts_module, '_ASCII_LINK_ROOT_CANDS', (str(tmp_path / 'tts_links'),))

    assert find_tts_model("这个模型不存在") is None
    root = tts_model_root()
    if root.is_dir() and any(_model_onnx(d) is not None for d in root.iterdir() if d.is_dir()):
        auto = find_tts_model()
        assert auto is not None and auto.is_dir()
        assert _model_onnx(auto) is not None            # onnx 可以是 model.int8.onnx
        names = sorted(d.name for d in root.iterdir()
                       if d.is_dir() and _model_onnx(d) is not None)
        if any(n.startswith("vits") for n in names):
            assert auto.name.startswith("vits")         # 有 vits 时必须挑 vits（D5 口径）

    # 已是 ASCII → 原样返回（不做任何链接）
    plain = tmp_path / "ascii_model"
    plain.mkdir()
    assert ascii_path(plain) == plain.resolve()

    # 非 ASCII → 必须给出纯 ASCII 的可访问路径
    mixed = tmp_path / "中文模型目录"
    mixed.mkdir()
    linked = ascii_path(mixed)
    assert all(ord(c) < 128 for c in str(linked))
    assert linked.is_dir()



def test_style_describe_is_readable():
    """⑦ `describe()` 供 HUD / 日志使用（含档位名与四个参数）。"""
    desc = tts_style.for_emotion("happy").describe()
    assert desc.startswith("high(") and "rate=fast" in desc and "brk=110ms" in desc
