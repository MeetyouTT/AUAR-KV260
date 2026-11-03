import json,re
from zoneinfo import ZoneInfo

def load_config(path):
    value=json.loads(path.read_text(encoding='utf-8-sig'))
    if set(value)!={'version','timezone','device_id','visual_history_days','visual_event_limit'} or value['version']!=1:
        raise ValueError('Invalid timeline config')
    ZoneInfo(value['timezone'])
    if not re.fullmatch('[a-zA-Z0-9_-]{1,64}',value['device_id']):raise ValueError('Invalid device scope')
    for field,low,high in (('visual_history_days',1,366),('visual_event_limit',1,50000)):
        if type(value[field]) is not int or not low<=value[field]<=high:raise ValueError('Invalid timeline retention')
    return value

def visual_forget_command(text):
    if not isinstance(text,str):return None
    value=re.sub(r'[。！!？?]+$','',text.strip())
    match=re.fullmatch(r'(?:请)?(?:删除|清除|忘记)(全部|所有|(?:今天|昨天|前天|\d{4}-\d{1,2}-\d{1,2})(?:上午|下午|晚上|凌晨)?)(?:的)?(?:视觉|画面|观察)(?:记录|记忆)',value)
    if not match:return None
    return '' if match[1] in ('全部','所有') else match[1]
