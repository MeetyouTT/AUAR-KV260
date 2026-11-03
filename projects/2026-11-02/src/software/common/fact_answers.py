"""Conservative natural questions about explicitly stored facts; no inference."""
import re
from common.memory_commands import key_name

def ordinal(value):
    if value.isdecimal():return int(value)
    digits={'一':1,'二':2,'两':2,'三':3,'四':4,'五':5,'六':6,'七':7,'八':8,'九':9}
    if len(value)==1:return 10 if value=='十' else digits.get(value)
    if value.count('十')!=1:return None
    tens,ones=value.split('十')
    if len(tens)>1 or len(ones)>1 or (tens and tens not in digits) or (ones and ones not in digits):return None
    return (digits.get(tens,1)*10)+digits.get(ones,0)

def question(value):
    if not isinstance(value,str) or len(value)>120:return None
    if re.search(r'如果|假如|假设|比如|他说|她说|扮演|假装|[“”「」『』"\n\x00]',value):return None
    scope=None
    for prefix,label in (('本次对话里','本次对话'),('本次对话中','本次对话'),('这次对话里','本次对话'),
                         ('当前对话里','当前对话'),('我的长期记忆里','我的长期'),('个人记忆里','个人')):
        if value.startswith(prefix):scope=label;value=value[len(prefix):].lstrip('，, ');break
    if value in ('查看记忆历史','查询记忆历史','查看所有记忆历史','查看全部记忆历史'):return {'op':'history_help'}
    indexed=re.fullmatch(r'(?:查看|查询)(本次对话|当前对话|我的长期|个人|我的)?(.{1,18}?)(?:的)?第(\d{1,2}|[一二两三四五六七八九十]{1,3})条(?:记忆历史|更正记录)',value)
    if indexed:
        key=key_name(indexed[2].removesuffix('的'));number=ordinal(indexed[3])
        if not re.fullmatch(r'[\w\u4e00-\u9fff]{1,16}',key) or number is None or not 1<=number<=32:return {'op':'history_help'}
        return {'op':'history','scope':indexed[1] or scope,'key':key,'index':number}
    value=re.sub(r'^(?:你还记得|你记得|还记得)','',value)
    value=re.sub(r'[吗呢]$','',value)
    patterns=[
      ('颜色偏好',r'我(?:最)?喜欢(?:什么|哪种)颜色|我(?:最)?喜欢的颜色是什么|我的颜色偏好是什么'),
      ('称呼',r'我叫什么(?:名字)?|我的(?:名字|称呼)是什么|你应该怎么称呼我'),
      ('项目',r'我的项目(?:叫什么(?:名字)?|是什么)|我的项目名(?:称)?是什么|我的项目名字是什么')]
    for key,pattern in patterns:
        if re.fullmatch(pattern,value):return {'op':'fact','scope':scope,'key':key}
    historic=[('颜色偏好',r'(?:我(?:以前|之前)|(?:以前|之前)我)(?:最)?喜欢(?:什么|哪种)颜色'),
              ('称呼',r'(?:我(?:以前|之前)|(?:以前|之前)我)叫什么(?:名字)?'),
              ('项目',r'我的项目(?:以前|之前)叫什么(?:名字)?')]
    for key,pattern in historic:
        if re.fullmatch(pattern,value):return {'op':'history','scope':scope,'key':key,'previous':True}
    return None

def fact_reply(key,value,personal):
    prefix='当前授权档案' if personal else '这次对话'
    if value is None:return prefix+'还没有明确记住你的'+key+'。'
    if key=='颜色偏好':return prefix+'里，你明确记住的颜色偏好是'+value+'。'
    return prefix+'记住的'+key+'是'+value+'。'

