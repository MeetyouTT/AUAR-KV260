"""Inspect only this identity question and route metadata; no name or reply export."""
import json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
remote=r'''
import json,re,subprocess,urllib.request
from pathlib import Path
get=lambda port,path:json.load(urllib.request.urlopen('http://127.0.0.1:'+str(port)+path,timeout=4))
u=get(8783,'/api/state');service=u['local_transcription']['service']
text=u['local_transcription'].get('text','')
# Export only a bounded identity-question character vocabulary, not statements/names.
allowed=set('你好啊呀嗨汐蓝西兰西来西南我是誰谁你知道的吗么嘛认识認得记記还還叫什么名字能出了吗请问想问一下呢小玩偶')
question=''.join(c for c in text if c in allowed or c in '，,。！!？?：: ')
safe=question if text and len(text)<=40 and all(c in allowed or c in '，,。！!？?：: ' for c in text) else '[redacted_non_question_text]'
rows=[]
for t in u.get('turns',[])[-6:]:
 llm=t.get('server_metrics',{}).get('timing',{}).get('llm',{})
 rows.append({'generation':t.get('generation'),'audio_complete':t.get('audio_complete'),
  'backend':llm.get('backend'),'identity_reply_code':llm.get('identity_reply_code')})
pc=json.load(urllib.request.urlopen('http://192.168.50.1:8792/health',timeout=4))
unit=subprocess.check_output(['systemctl','cat','aura-avatar-ui.service'],text=True)
print(json.dumps({'question_transcript':safe,'question_length':len(text),'last_turns':rows,
 'transcription_state':u['local_transcription']['state'],'ui_phase':u['phase'],
 'automatic':u['automatic_conversation'],'service_feedback_ready':service.get('feedback_ready'),
 'identity_flow':service.get('voice_enrollment'),'pc_query_capability':pc['identity_voice_enrollment'],
 'active_ui_startup_config':re.search(r'--config (\S+)',unit).group(1),
 'user_reply_or_registered_name_exported':False}))
'''
r=json.loads(ssh('python3 -B -',remote,timeout=25))
(HERE/'question_route_feedback.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(r,ensure_ascii=False))
