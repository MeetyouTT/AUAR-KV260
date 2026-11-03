"""Small, conservative preferences retained beyond the four-round window.

Only a direct first-person color assertion is accepted. Questions, quotations,
other people's preferences and arbitrary instructions cannot become facts.
The host calls this only after a matching complete-playback acknowledgement.
"""
import re

COLORS = ('绿色','红色','蓝色','黄色','紫色','橙色','粉色','白色','黑色','灰色','棕色','青色',
          '浅绿色','深绿色','薄荷绿','墨绿色','浅蓝色','深蓝色','天蓝色','宝蓝色','粉红色')
_COLOR = '(?:'+'|'.join(sorted(map(re.escape,COLORS),key=len,reverse=True))+')'
_PREFIX = r'(?:(?:你好[啊呀]?|嗨|嘿)[，,！!。]?)?(?:(?:请)?(?:记住|记一下|记得)[，,：:]?)?'
_SET = re.compile(_PREFIX+r'(?:我(?:最)?喜欢(?:的颜色)?(?:是|为)?|我最爱的颜色是)('+_COLOR+r')(?:了|呀|啊|呢)?[。！!]*')
_REMOVE = re.compile(r'我(?:不再喜欢|不喜欢)('+_COLOR+r')(?:了)?[。！!]*')
_FORGET = re.compile(r'(?:请)?(?:忘记|删除|清除)(?:我的|我喜欢的)(?:颜色偏好|颜色|颜色记忆)[。！!]*')


def color_update(text):
    if not isinstance(text,str) or len(text)>64:return None
    text=re.sub(r'\s+','',text)
    if _FORGET.fullmatch(text):return {'operation':'forget'}
    match=_REMOVE.fullmatch(text)
    if match:return {'operation':'remove','color':match.group(1)}
    match=_SET.fullmatch(text)
    if match:return {'operation':'set','color':match.group(1)}
    return None
