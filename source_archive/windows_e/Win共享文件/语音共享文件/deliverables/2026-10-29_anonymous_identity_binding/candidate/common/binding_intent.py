"""Pure narrow board translation; preserves the original ASR transcript."""
import re
from common.voice_enrollment import valid_name

def binding_intent(text):
    if not isinstance(text,str) or len(text)>160:return {'kind':'ordinary','name':None}
    value=text.strip(' \t\r\n。！!？?');value=re.sub(r'^(?:汐蓝[，, ]*)','',value)
    for pattern in (r'(?:请)?记住我[，, ]*(?:(?:我叫|我的名字是|叫我)(.+))?',
       r'(?:我叫|我的名字是)(.+?)[，, ]*(?:请)?记住我',
       r'(?:请)?(?:帮我)?(?:登记|关联)(?:我的)?身份[，, ]*(?:我叫|我的名字是)(.+)'):
        match=re.fullmatch(pattern,value)
        if match:
            name=match.group(1);name=name.strip() if name is not None else None
            return {'kind':'remember_self','name':name} if name is None or valid_name(name) else {'kind':'invalid_name','name':None}
    match=re.fullmatch(r'(?:我叫|我的名字是|叫我)(.+)',value)
    if match and valid_name(match.group(1).strip()):return {'kind':'name_hint','name':match.group(1).strip()}
    return {'kind':'ordinary','name':None}

def face_enrollment_text(text,*,active=False):
    """Only inside an authorized identity_request branch, never ordinary chat."""
    intent=binding_intent(text)
    if intent['kind']=='remember_self':
        return '帮我登记身份' if intent['name'] is None else '帮我登记身份，我叫'+intent['name']
    if intent['kind']=='name_hint' and not active:return '帮我登记身份，我叫'+intent['name']
    return text
