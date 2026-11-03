"""Narrow speech enrollment intent and bounded board-owned spoken results."""
import re
from common.spoken_input import prepare_spoken_input

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
 'sample_front':'请正对镜头，采四份正脸。',
 'sample_left':'请轻微向左转头，双眼保持可见。',
 'sample_right':'请轻微向右转头。',
 'sample_validate':'请回正，保持几秒，验证五份新画面。',
 'sample_failed':'这次采样或新画面验证没有通过，尚未保存身份。请调整距离和光线，再重新发起登记。',
 'confirm_update_name':'称呼{name}，要更新原身份，请说确认更新登记；也可取消。',
 'retry_update':'更新原身份需要明确确认。请说确认更新登记，或说取消登记。',
}

def normalized(text):
    text=prepare_spoken_input(text)['text']
    text=re.sub(r'[\s，,。！!？?：:]','',text)
    return re.sub(r'^(?:(?:你好[啊呀]?|嗨)[啊呀]?)?(?:汐蓝)?','',text)

def enrollment_requested(text):
    return normalized(text) in {'帮我登记身份','请帮我登记身份','我要登记身份','登记身份','帮我登记人脸',
        '记住我的脸','请记住我的脸','我要做身份登记','我要做身份认证','我想登记身份','我想进行身份登记'}

def cancelled(text):
    return normalized(text) in {'取消登记','不登记了','先不登记','结束登记','不要登记','停止登记'}

def confirmed(text):
    return normalized(text) in {'确认登记','确认保存','确认登记身份','是的确认登记'}

def update_confirmed(text):
    return normalized(text) in {'确认更新登记','确认更新身份','确认重新登记'}

def valid_name(name):
    return bool(isinstance(name,str) and (re.fullmatch(r'[\u4e00-\u9fff]{2,12}',name)
        or re.fullmatch(r'[A-Za-z][A-Za-z -]{1,23}',name))
        and not re.search(r'你|他|她|什么|怎么|请|登记|取消|确认|忘记|指令|忽略|规则|名字|叫我',name))

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
    if value['code'] in ('confirm_name','confirm_update_name'):
        if not valid_name(name):raise ValueError('Invalid identity voice name')
    elif name!='':raise ValueError('Unexpected identity voice name')
    return PROMPTS[value['code']].format(name=name)
