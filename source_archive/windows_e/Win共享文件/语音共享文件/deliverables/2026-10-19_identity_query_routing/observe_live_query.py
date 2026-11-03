"""Observe the requested fresh test without retaining ordinary speech or identities."""
import json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
previous=json.loads((HERE/'live_query_observation.json').read_text(encoding='utf-8')) if (HERE/'live_query_observation.json').exists() else {}
remote=r'''
import json,time,urllib.request
get=lambda port,path:json.load(urllib.request.urlopen('http://127.0.0.1:'+str(port)+path,timeout=4))
alphabet=set('你好啊呀嗨嘿喂汐蓝西兰溪希夕我是誰谁你知道的吗么嘛认识認得记記还還叫什么名字能出了请问想一下呢小玩偶现在可不以看出来认出有没有怎样')
previous=PREVIOUS
questions=previous.get('question_transcripts',[]);routes=previous.get('route_diagnostics',{})
until=time.monotonic()+40;seen=set(questions);turns={};states={}
while time.monotonic()<until:
 u=get(8783,'/api/state');service=u['local_transcription']['service'];route=service.get('last_voice_route')
 if route:routes[str(route['generation'])]=route
 text=u['local_transcription'].get('text','')
 if text and text not in seen:
  seen.add(text)
  if len(text)<=48 and all(c in alphabet or c in '，,。！!？?：: ' for c in text):questions.append(text)
 for turn in u.get('turns',[]):
  timing=turn.get('server_metrics',{}).get('timing',{}).get('llm',{})
  turns[str(turn['generation'])]={'backend':timing.get('backend'),
   'identity_reply_code':timing.get('identity_reply_code'),'audio_complete':turn.get('audio_complete')}
 i=get(8790,'/v1/ui/status')['modules']['identity'];key=str((i['state'],i.get('face_count')))
 states[key]=states.get(key,0)+1
 if any(t.get('identity_reply_code') and t['audio_complete'] and key in routes
        and routes[key]['direct_identity_question'] for key,t in turns.items()):break
 time.sleep(.15)
print(json.dumps({'question_transcripts':questions,'route_diagnostics':routes,'turn_routes':turns,
 'identity_observations':states,'automatic':u['automatic_conversation'],
 'human_named_answer_proven':any(t['identity_reply_code']=='identity_seen' and t['audio_complete'] for t in turns.values()),
 'ordinary_speech_names_photos_or_templates_exported':False,'production_changed':False}))
'''.replace('PREVIOUS',repr(previous),1)
r=json.loads(ssh('python3 -B -',remote,timeout=55))
(HERE/'live_query_observation.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(r,ensure_ascii=False))
