"""Create a prompt-only chat candidate without changing chunks, models or context limits."""
import hashlib,json,sys
from pathlib import Path
H=Path(__file__).resolve().parent;A=H.parents[1]/'aura';sys.path.insert(0,str(A))
from common.voice_service_capabilities import source_fingerprint
baseline=json.loads((H/'baseline.json').read_text())
assert source_fingerprint(A)==baseline['production_fingerprint']
assert not (H/'source_plan.json').exists()
names=['tools/dialogue_stream.py','common/voice_service_capabilities.py']
plan={**baseline,'status':'CANDIDATE','files':{}}
for name in names:
 raw=(A/name).read_bytes();plan['files'][name]={'before':hashlib.sha256(raw).hexdigest()}
 for folder in ('before','candidate_source'):
  p=H/folder/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
p=H/'candidate_source/tools/dialogue_stream.py';s=p.read_text(encoding='utf-8')
needle="REPLY_FIRST_FIELDS={'a':'reply_text','b':'emotion','c':'avatar_action'}"
hint='只输出紧凑的单行JSON，符号周围不添加空格或换行；台词内容和三个字段要求保持。'
assert s.count(needle)==1;s=s.replace(needle,needle+"\n\nCOMPACT_CHAT_HINT="+repr(hint))
needle='    return body\n\n\ndef wire_history_within_budget'
replacement="""    if reply_first and not think:
        # A formatting hint must never displace history, facts or the user's
        # current question. Omit it when the unmodified request needs the room.
        used=sum(len(row['content'].encode('utf-8')) for row in body['messages'])
        reserve=256+32*len(body['messages'])+body['options']['num_predict']
        if used+reserve+len(COMPACT_CHAT_HINT.encode('utf-8'))<=body['options']['num_ctx']:
            body['messages'][0]['content']+=COMPACT_CHAT_HINT
    return body


def wire_history_within_budget"""
assert s.count(needle)==1;s=s.replace(needle,replacement)
needle="        # Record the exact input/prompt identity without duplicating raw text in"
replacement="""        self.metrics.update(
            request_sha256=hashlib.sha256(json.dumps(body,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')).hexdigest(),
            compact_chat_hint=COMPACT_CHAT_HINT in body['messages'][0]['content'])
        # Record the exact input/prompt identity without duplicating raw text in"""
assert s.count(needle)==1;s=s.replace(needle,replacement)
needle="                    self.raw_reply=decoder.buffer\n"
replacement="""                    self.raw_reply=decoder.buffer
                    inside=False;escaped=False;whitespace=0
                    for char in self.raw_reply:
                        if inside:
                            if escaped:escaped=False
                            elif char=='\\\\':escaped=True
                            elif char=='"':inside=False
                        elif char=='"':inside=True
                        elif char in ' \\t\\r\\n':whitespace+=1
                    self.metrics['json_format_whitespace']=whitespace
"""
# The generated source needs literal escapes inside quoted Python strings.
replacement=replacement.replace("elif char=='\\':","elif char=='\\\\':").replace("elif char in ' \t\r\n':","elif char in ' \\t\\r\\n':")
assert s.count(needle)==1;s=s.replace(needle,replacement)
p.write_text(s,encoding='utf-8',newline='')
p=H/'candidate_source/common/voice_service_capabilities.py';s=p.read_text(encoding='utf-8')
s=s.replace("SERVICE_REVISION = 'voice-turn-handoff-20261029-r6'","SERVICE_REVISION = 'voice-chat-json-20261029-r7'")
needle="'bounded_voice_request_diagnostics':1}"
assert s.count(needle)==1;s=s.replace(needle,"'bounded_voice_request_diagnostics':1,'compact_chat_serialization_hint':1,'request_input_fingerprint':1}")
p.write_text(s,encoding='utf-8',newline='')
for name,row in plan['files'].items():row['candidate']=hashlib.sha256((H/'candidate_source'/name).read_bytes()).hexdigest()
namespace={};exec(s,namespace)
d=hashlib.sha256()
for name in namespace['SOURCE_FILES']:
 p=H/'candidate_source'/name
 if not p.exists():p=A/name
 d.update(name.encode()+b'\0');d.update(hashlib.sha256(p.read_bytes()).digest())
plan.update(candidate_revision=namespace['SERVICE_REVISION'],candidate_fingerprint=d.hexdigest(),
 preserved_latency_sha256=baseline['source_before']['config/voice_latency.json'])
(H/'source_plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'status':plan['status'],'revision':plan['candidate_revision'],'fingerprint':plan['candidate_fingerprint']}))
