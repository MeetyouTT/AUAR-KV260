"""Separate temporal wording from an actual request to recall stored history."""
import ast,hashlib,json,shutil
from pathlib import Path
H=Path(__file__).resolve().parent;A=H.parents[1]/'aura';C=H/'candidate_source'
plan=json.loads((H/'source_plan.json').read_text(encoding='utf-8'));assert plan['status']=='CANDIDATE'
for name in ('common/timeline.py','tools/voice_channel_source.py','tools/device_client.py'):
 assert hashlib.sha256((A/name).read_bytes()).hexdigest()==plan['source_before'][name]
 for folder in ('before','candidate_source'):
  p=H/folder/name;assert not p.exists();p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((A/name).read_bytes())
 plan['files'][name]={'before':plan['source_before'][name]}
p=C/'common/timeline.py';s=p.read_text(encoding='utf-8')
needle='def query(text,*,now,zone=DEFAULT_ZONE):'
addition=r'''
def recall_requested(text):
    """Voice routing only; date parsing/deletion still uses historical()."""
    if not historical(text):return False
    if re.search(r'(?:不要|不用|不必|无需|别).{0,6}(?:回忆|回顾|查询|查看)',text):return False
    if re.search(r'回忆录|记忆力',text) and not re.search(r'昨天|前天|上次|刚才',text):return False
    if re.search(r'回忆(?!录)|回顾|时间轴|画面记忆|视觉记忆|观察记忆|还记得|你记得|我不记得',text):return True
    if re.search(r'查询|查看|总结|概括|日记|记录|摘录',text):return True
    past_other=re.search(r'刚才|之前|先前|上次|昨天|前天|昨晚|今早|上周|本周|这周|上个月|上月|去年|上星期|最近\d+天|最近看到|\d{4}[-年]\d{1,2}[-月]\d{1,2}',text)
    completed=re.search(r'(?:聊|说|谈|讨论|提)(?:了|过|到)|(?:看|见|发生|经历|做)(?:到|见|了|过)',text)
    # "今天聊什么/今天有点累" is current conversation, not a query of today's archive.
    if not past_other and not completed:return False
    if re.search(r'接着上次|继续上次',text):return True
    question=re.search(r'什么|哪些|哪儿|哪里|到哪|在哪|放哪|谁|多少|几次|吗|有没有|是否',text)
    if not question:return False
    if re.search(r'(?:聊|说|谈|讨论|提|看到|看见|发生|经历|做)',text):return True
    if re.search(r'哪里|在哪|哪儿|放哪|放在|放到',text):return True
    return bool(re.search(r'(?:刚才|之前|先前|上次).{0,6}(?:那|这).{0,4}(?:什么|谁|怎么)',text))

'''
assert s.count(needle)==1;s=s.replace(needle,addition+needle);p.write_text(s,encoding='utf-8',newline='')
p=C/'tools/voice_channel_source.py';s=p.read_text(encoding='utf-8')
assert s.count('from common.timeline import historical')==1 and s.count('if historical(text):')==1
s=s.replace('from common.timeline import historical','from common.timeline import recall_requested').replace('if historical(text):','if recall_requested(text):')
p.write_text(s,encoding='utf-8',newline='')
p=C/'tools/device_client.py';s=p.read_text(encoding='utf-8')
assert s.count('    from common.timeline import historical\n    return historical(text)')==1
s=s.replace('    from common.timeline import historical\n    return historical(text)','    from common.timeline import recall_requested\n    return recall_requested(text)')
p.write_text(s,encoding='utf-8',newline='')
p=C/'common/voice_service_capabilities.py';s=p.read_text(encoding='utf-8')
s=s.replace('voice-chat-json-20261029-r7','voice-chat-context-20261029-r7')
assert s.count("'request_input_fingerprint':1}")==1
s=s.replace("'request_input_fingerprint':1}","'request_input_fingerprint':1,'precise_timeline_voice_intent':1}")
p.write_text(s,encoding='utf-8',newline='')
for name,row in plan['files'].items():
 raw=(C/name).read_bytes();ast.parse(raw.decode('utf-8'));row['candidate']=hashlib.sha256(raw).hexdigest()
ns={};exec((C/'common/voice_service_capabilities.py').read_text(encoding='utf-8'),ns)
d=hashlib.sha256()
for name in ns['SOURCE_FILES']:
 p=C/name
 if not p.exists():p=A/name
 d.update(name.encode()+b'\0');d.update(hashlib.sha256(p.read_bytes()).digest())
plan.update(candidate_revision=ns['SERVICE_REVISION'],candidate_fingerprint=d.hexdigest())
(H/'source_plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
for name in ('tests_final.log','tests.xml'):shutil.copy2(H/name,H/('format_only_'+name))
print(json.dumps({'files':len(plan['files']),'revision':plan['candidate_revision'],'fingerprint':plan['candidate_fingerprint']}))
