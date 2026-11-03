"""Explicit conversation-scoped commands; ordinary chat never mutates facts."""
import re

ALIASES = {'姓名': '称呼', '名字': '称呼', '称呼': '称呼',
           '项目名': '项目', '项目名称': '项目', '项目': '项目',
           '颜色': '颜色偏好', '喜欢的颜色': '颜色偏好', '颜色偏好': '颜色偏好'}
NUMBER = r'(?:[1-9][0-9]?|[一二三四五六七八九十]|十一|十二)'


def item_number(value):
    if value.isdigit():return int(value)
    return {'一':1,'二':2,'三':3,'四':4,'五':5,'六':6,'七':7,'八':8,'九':9,'十':10,'十一':11,'十二':12}[value]


def key_name(value):
    value = re.sub(r'^(?:我的|关于我的|关于)', '', value.strip()).strip()
    if value in ('我喜欢的颜色', '我最喜欢的颜色'):value='颜色偏好'
    return ALIASES.get(value, value)


def key_terms(key):
    result = {key} | {alias for alias, canonical in ALIASES.items() if canonical == key}
    if key == '称呼':result.update(('我叫','叫我'))
    return result


def parse_command(text):
    if not isinstance(text, str) or len(text) > 200:
        return None
    value = re.sub(r'[。！!？?]+$', '', text.strip())
    value = re.sub(r'^汐蓝[，,\s]*', '', value)
    value = re.sub(r'^(?:请(?:你)?|麻烦你)?(?:帮我)?', '', value).strip()
    if value in ('你记住了什么', '你记住了哪些', '查看记忆', '查看对话记忆', '查看本次对话记忆'):
        return {'operation': 'list'}
    match = re.fullmatch(r'查看第('+NUMBER+r')条记忆', value)
    if match:
        return {'operation': 'view', 'index': item_number(match[1])}
    if value in ('清空本次对话记忆', '清空当前对话记忆', '忘记本次对话的全部记忆'):
        return {'operation': 'clear'}
    if value in ('清空记忆','忘记所有','忘记全部','忘记一切','删除所有记忆'):
        return {'operation': 'scope_help'}
    if value in ('记住','记一下','更正记忆','更正一下'):
        return {'operation': 'help'}
    match = re.fullmatch(r'(?:忘记|删除)(?:第('+NUMBER+r')条记忆|(?:关于)?(.{1,20}?)(?:的记忆)?)', value)
    if match:
        if match[1]:
            return {'operation': 'forget', 'index': item_number(match[1])}
        key = key_name(match[2])
        if not (match[2].startswith(('我的', '关于我的')) or value.endswith('记忆') or key in ALIASES.values()):
            return None
        if re.fullmatch(r'[\w\u4e00-\u9fff]{1,16}', key):
            return {'operation': 'forget', 'key': key}
        return {'operation': 'help'}
    correction = re.fullmatch(r'把我的(.{1,16}?)改(?:为|成)(.{1,64})', value)
    if correction:value='更正记忆：'+correction[1]+'='+correction[2]
    match = re.fullmatch(r'(?:记住|记一下|更正记忆|更正一下)[，,：:]?\s*(.+)', value)
    if match:
        body = match[1].strip()
        pair = re.fullmatch(r'(.{1,20}?)(?:[=＝：:]|等于)\s*(.{1,64})', body)
        if not pair:
            pair = re.fullmatch(r'我的(.{1,16}?)(?:是|叫)(.{1,64})', body)
        if not pair:
            pair = re.fullmatch(r'(.{1,16}?)是(.{1,64})', body)
        if pair:
            key, fact = key_name(pair[1]), pair[2].strip()
        else:
            name = re.fullmatch(r'(?:我叫|叫我)(.{1,20})', body)
            color = re.fullmatch(r'我(?:最)?喜欢(?:的颜色是)?(.{1,20}色)', body)
            if name: key, fact = '称呼', name[1]
            elif color: key, fact = '颜色偏好', color[1]
            else: return {'operation': 'help'}
        if (not re.fullmatch(r'[\w\u4e00-\u9fff]{1,16}', key) or
                not fact or any(c in fact for c in '\r\n\x00') or
                re.search(r'如果|假如|假设|他说|她说|不要记|别记|什么|[？?“”「」『』"]', body)):
            return {'operation': 'help'}
        return {'operation': 'set', 'key': key, 'value': fact}
    return None


class MemoryReplyStream:
    """An actual database result uses the existing TTS/wire, with no LLM guess."""
    def __init__(self, reply):
        self.reply = reply
        self.stopped = False
        self.metrics = {'backend': 'conversation_memory_command'}

    def __iter__(self):
        if self.stopped: return
        yield 'text', self.reply
        if self.stopped: return
        yield 'speech_ready', None
        if self.stopped: return
        yield 'complete', {'reply_text': self.reply, 'emotion': 'friendly', 'avatar_action': ''}

    def cancel(self):
        self.stopped = True
