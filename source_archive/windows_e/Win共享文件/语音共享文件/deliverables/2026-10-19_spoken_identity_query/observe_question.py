"""Short read-only observation; export only identity-question vocabulary and route codes."""
import json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh

remote = r'''
import json,re,time,urllib.request
get=lambda port,path:json.load(urllib.request.urlopen('http://127.0.0.1:'+str(port)+path,timeout=3))
alphabet=set('你好啊呀嗨嘿喂汐蓝西兰溪希夕我是誰谁你知道的吗么嘛认识認得记記还還叫什么名字能出了请问想一下呢小玩偶现在可不以看出来认出有没有怎样')
seen=set();rows=[];routes={};states={};until=time.monotonic()+35
while time.monotonic()<until:
 u=get(8783,'/api/state');t=u['local_transcription'];text=t.get('text','')
 identity=get(8790,'/v1/ui/status')['modules']['identity']
 key=(identity['state'],identity.get('face_count'),bool(identity.get('source_frame_id')))
 states[str(key)]=states.get(str(key),0)+1
 if text and text not in seen:
  seen.add(text)
  allowed=len(text)<=48 and all(c in alphabet or c in '，,。！!？?：: ' for c in text)
  rows.append({'question':text if allowed else '[redacted_non_question_text]',
   'characters':len(text),'transcription_state':t['state'],
   'face_count':identity.get('face_count'),'identity_state':identity['state']})
 for turn in u.get('turns',[]):
  llm=turn.get('server_metrics',{}).get('timing',{}).get('llm',{})
  routes[str(turn.get('generation'))]={'backend':llm.get('backend'),
   'identity_reply_code':llm.get('identity_reply_code'),'audio_complete':turn.get('audio_complete')}
 time.sleep(.15)
print(json.dumps({'questions':rows,'routes':routes,'camera_states':states,
 'final_automatic':u['automatic_conversation'],'names_or_photos_exported':False,'production_changed':False}))
'''
r = json.loads(ssh('python3 -B -', remote, timeout=55))
(HERE/'question_observation.json').write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(r, ensure_ascii=False))
