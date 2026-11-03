"""Pure narrow board translation; preserves the original ASR transcript."""
import re
from common.voice_enrollment import valid_name
from common.character_profile import strip_character_address

def binding_intent(text):
    if not isinstance(text,str) or len(text)>160:return {'kind':'ordinary','name':None}
    value=strip_character_address(text.strip(' \t\r\n。！!？?'))
    # Explicit standalone commands are not combined enrollment consent.
    found=re.fullmatch(r'(?:请)?(?:帮我)?登记(?:我的)?人脸[，, ]*(?:(?:我叫|我的名字是|叫我)(.+))?',value)
    if found:
        name=found.group(1);name=name.strip() if name is not None else None
        return {'kind':'face_only','name':name} if name is None or valid_name(name) else {'kind':'invalid_name','name':None}
    from common.feature_intents import speaker_text
    voice=speaker_text(text)
    if voice=='登记我的声纹':return {'kind':'voice_only','name':None}
    prefix='登记我的声纹，我叫'
    if isinstance(voice,str) and voice.startswith(prefix):return {'kind':'voice_only','name':voice[len(prefix):]}
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
    if intent['kind'] in ('remember_self','face_only'):
        return '帮我登记身份' if intent['name'] is None else '帮我登记身份，我叫'+intent['name']
    if intent['kind']=='name_hint' and not active:return '帮我登记身份，我叫'+intent['name']
    return text
