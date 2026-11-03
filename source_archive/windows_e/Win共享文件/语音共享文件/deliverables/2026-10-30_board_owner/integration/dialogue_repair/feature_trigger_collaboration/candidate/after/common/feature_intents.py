"""Narrow speech-only routing; a match conveys no consent beyond original FSMs.

Quoted, hypothetical and negative requests never become enrollment commands.
The raw transcript and captured PCM stay unchanged in their original owner.
"""
import re

from common.character_profile import strip_character_address
from common.spoken_input import prepare_spoken_input


def speaker_text(text, *, active=False):
    """Return the existing speaker FSM's canonical input, or None.

    Arbitrary utterances during an active enrollment are still handled by the
    original sampler. General cancel/save words are only interpreted there.
    """
    if not isinstance(text, str) or not 1 <= len(text) <= 2000:
        return None
    value = strip_character_address(prepare_spoken_input(text)['text'].strip(' \t\r\n。！!？?'))
    value = value.strip(' \t\r\n，,。！!？?')
    if value in ('取消声纹登记', '停止声纹登记', '不登记声纹了', '不要保存声纹'):
        return '取消声纹登记'
    if value in ('确认保存声纹', '确认删除声纹'):
        return value
    if active and value in ('取消登记', '取消', '不保存'):
        return value
    name = r'([^，,。！？!?\s]{1,20})'
    found = re.fullmatch(r'(?:请)?(?:帮我)?(?:登记我的声纹|记住我的声音|登记声纹)[，, ]*(?:我叫|名字是)'+name, value)
    if found:
        return '登记我的声纹，我叫'+found[1]
    found = re.fullmatch(r'(?:请)?删除声纹[，, ]*(?:名字是|名为)?'+name, value)
    if found:
        return '删除声纹，名字是'+found[1]
    if re.fullmatch(r'(?:请)?(?:帮我)?(?:登记|注册)(?:我的)?声纹', value):
        return '登记我的声纹'
    # Read-only questions use the existing readiness/calibration/match path.
    # Full matches prevent quotations and negation from executing an action.
    question = value
    if question.startswith('请问'):
        question = question[2:]
    question = question.removesuffix('？').removesuffix('?')
    endings = r'[吗呢么啊呀]?'
    patterns = (
        r'(?:现在)?(?:我的)?声纹(?:识别)?(?:现在)?(?:是否|能否)?(?:可用|能用|正常|就绪|有记录|已登记|登记过)'+endings,
        r'(?:我|我的声音|我的声纹)(?:以前|之前)?(?:已经|曾经)?登记过声纹'+endings,
        r'(?:我)?(?:已经)?登记(?:过|了)声纹'+endings,
        r'(?:请)?(?:查询|检查|识别|辨认)(?:一下)?(?:我的)?(?:声纹|声音)'+endings,
        r'(?:你)?(?:现在)?(?:能|可以|会)?(?:识别|辨认|认出|认识)(?:我的)?(?:声纹|声音)'+endings,
        r'(?:你)?(?:听|听听|根据|通过)(?:我的)?声音(?:你)?(?:能|可以)?(?:知道|判断|识别|认出)?(?:我是谁|谁在说话)'+endings,
        r'(?:你)?(?:能|可以)?(?:根据|通过)(?:我的)?声音(?:识别|认出|辨认)(?:我|我是谁)'+endings,
        r'(?:我的)?声纹(?:是否|有没有|有无)(?:登记|记录|保存)'+endings,
        r'(?:现在)?(?:你的)?声纹(?:识别)?(?:功能)?(?:怎么样|状态如何|准备好了吗|能用了吗)',
    )
    if question == '查询我的声纹' or any(re.fullmatch(p, question) for p in patterns):
        return '查询我的声纹'
    return None


def speaker_requested(text):
    return speaker_text(text) is not None
