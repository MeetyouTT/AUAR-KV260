"""Narrow speech enrollment intent and bounded board-owned spoken results."""
import re
from common.spoken_input import ALIASES, prepare_spoken_input

PROMPTS = {
 'ask_name':'可以，请正对摄像头。你希望我怎么称呼你？请说，我叫某某。',
 'confirm_name':'称呼是{name}。请说确认登记，或取消登记。',
 'registered':'登记成功啦，以后我会尝试认出你。',
 'cancelled':'好，这次登记已取消。',
 'face_unavailable':'请一个人正对摄像头，等人脸清楚后，再说帮我登记身份。',
 'changed':'画面中的对象变了，这次登记已取消。请重新正对摄像头，再发起登记。',
 'already_known':'当前对象已经登记过了，不需要重复登记。',
 'bad_name':'请只说，我叫某某。也可以说取消登记。',
 'retry_confirm':'请说确认登记，或说取消登记。称呼不对，也可以重新告诉我。',
 'failed':'这次没有确认登记成功，请稍后重试。',
 'expired':'这次登记等待太久，已取消。请重新说帮我登记身份。',
 'sample_front':'请看着镜头，慢慢自然转头。我会自动挑选清晰的人脸。',
 'sample_left':'请轻微向左转头，双眼保持可见。',
 'sample_right':'请轻微向右转头。',
 'sample_validate':'清晰人脸已选好。请自然看向镜头，稍停几秒，我再确认一下。',
 'sample_failed':'这次采样或新画面验证没有通过，尚未保存身份。请调整距离和光线，再重新发起登记。',
 'confirm_update_name':'称呼{name}，要更新原身份，请说确认更新登记；也可取消。',
 'retry_update':'更新原身份需要明确确认。请说确认更新登记，或说取消登记。',
 'prepare_name':'称呼是{name}。请说确认登记，之后看着我慢慢自然转头，我会自动完成并保存。',
 'prepare_update_name':'称呼{name}已经存在。请说确认更新登记，之后看着我，我会自动更新这份人脸登记。',
 'sample_auto':'好的，看着我就行，可以慢慢自然转头。我会自动挑选清晰人脸，完成后告诉你。',
 'identity_seen':'镜头前识别到的是{name}。',
 'identity_unknown':'现在还没有认出镜头前的人，请正对镜头稍停，再问我。',
 'identity_unavailable':'现在没有清晰有效的人脸，请正对摄像头，再问我。',
 'identity_multiple':'镜头前有多个人，请只留一人正对镜头，再问我。',
 'identity_busy':'正在登记人脸，请等这次登记结束后，再问我。',
}

def normalized(text):
    text=prepare_spoken_input(text)['text']
    text=re.sub(r'[\s，,。！!？?：:]','',text)
    return re.sub(r'^(?:(?:你好[啊呀]?|嗨)[啊呀]?)?(?:汐蓝)?','',text)

REQUESTS={'帮我登记身份','请帮我登记身份','我要登记身份','登记身份','帮我登记人脸',
        '记住我的脸','请记住我的脸','我要做身份登记','我要做身份认证','我想登记身份','我想进行身份登记'}

def enrollment_requested(text):
    return normalized(text) in REQUESTS or requested_name(text) is not None

_IDENTITY_QUESTION = re.compile(
    r'(?:(?:你好[啊呀]?|嗨|嘿|喂|早上好|下午好|晚上好)[啊呀]?)?'
    r'(?:(?:'+'|'.join(map(re.escape,('汐蓝',)+ALIASES))+r')[啊呀]?)?'
    r'(?:请问(?:一下)?|问一下|我想问一下)?'
    r'(?:我是谁|我叫什么(?:名字)?|我的名字是什么'
    r'|你(?:还)?(?:知道|记得)(?:我是谁|我叫什么(?:名字)?|我的名字(?:是什么)?)'
    r'|(?:你)?(?:还)?(?:认识|认得|记得)我'
    r'|(?:你)?(?:还)?(?:能|可以)?(?:认出我|认出来我|认得出我)(?:了)?'
    r'|(?:你)?(?:能|可以)?(?:看出|看出来|认出|认出来)我是谁)'
    r'[呢吗么嘛啊呀]?'
)

def identity_query_requested(text):
    """Match the whole direct question, including known character homophones.

    A vocative joined to "我是谁" needs no punctuation. Do not run the general
    spelling/literal-name interpreter here: "我叫什么" is a query, whereas the
    general interpreter deliberately leaves names after "我叫" untouched. Raw
    ASR text, enrollment names, unknown aliases and quoted/negated speech stay
    unchanged; a substring or a model guess never opens this read-only route.
    """
    if not isinstance(text,str) or len(text)>80:return False
    value=re.sub(r'[\s，,。！!？?：:]','',text)
    return _IDENTITY_QUESTION.fullmatch(value) is not None

def requested_name(text):
    value=normalized(text)
    for prefix in sorted(REQUESTS,key=len,reverse=True):
        if value.startswith(prefix):
            match=re.fullmatch(r'(?:我叫|我的名字是|我的称呼是)(.+)',value[len(prefix):])
            if match and valid_name(match.group(1)):return match.group(1)
    return None

def cancelled(text):
    return normalized(text) in {'取消登记','不登记了','先不登记','结束登记','不要登记','停止登记'}

def confirmed(text):
    return normalized(text) in {'确认登记','确认保存','确认登记身份','是的确认登记'}

def update_confirmed(text):
    return normalized(text) in {'确认更新登记','确认更新身份','确认重新登记'}

def valid_name(name):
    return bool(isinstance(name,str) and (re.fullmatch(r'[\u4e00-\u9fff]{2,12}',name)
        or re.fullmatch(r'[A-Za-z][A-Za-z -]{1,23}',name))
        and not re.search(r'你|他|她|什么|怎么|请|登记|取消|确认|忘记|指令|忽略|规则|名字|叫我|然后|并且|顺便|删除|覆盖|全部|所有',name))

def spoken_name(text):
    value=normalized(text)
    match=re.fullmatch(r'(?:不是|不对|改成|更正)?(?:我叫|叫我|我的名字是|我的称呼是|我是)(.+)',value)
    return match.group(1) if match and valid_name(match.group(1)) else None

def result(code,name=''):
    value={'code':code,'name':name};render(value);return value

def render(value):
    if not isinstance(value,dict) or set(value)!={'code','name'} or value['code'] not in PROMPTS:
        raise ValueError('Invalid identity voice result')
    name=value['name']
    if value['code'] in ('confirm_name','confirm_update_name','prepare_name','prepare_update_name','identity_seen'):
        if not valid_name(name):raise ValueError('Invalid identity voice name')
    elif name!='':raise ValueError('Unexpected identity voice name')
    return PROMPTS[value['code']].format(name=name)
