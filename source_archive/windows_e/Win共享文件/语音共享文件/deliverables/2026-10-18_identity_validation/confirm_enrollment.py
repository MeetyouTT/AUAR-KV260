"""Audit successful spoken enrollment without exporting names or templates."""
import json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
remote=r'''
import hashlib,json,urllib.request
get=lambda port,path:json.load(urllib.request.urlopen('http://127.0.0.1:'+str(port)+path,timeout=4))
ui=get(8783,'/api/state');cam=get(8790,'/v1/ui/status');health=get(8790,'/health')
identity=cam['modules'].get('identity',{});op=identity.get('last_operation',{})
turns=[]
for index,turn in enumerate(ui.get('turns',[])):
 metrics=turn.get('server_metrics',{});timing=metrics.get('timing',{});llm=timing.get('llm',{})
 if llm.get('backend')!='board_identity_workflow':continue
 turns.append({'index':index,'generation':turn.get('generation'),'reply_code':llm.get('identity_reply_code'),
  'audio_complete':turn.get('audio_complete'),'first_pcm_ms':metrics.get('first_pcm_ms'),
  'tts_cache_hits':metrics.get('tts_cache_hits'),'software_request_to_answer_seconds':turn.get('request_to_answer_seconds')})
value={'camera_health':health,'identity_state':identity.get('state'),
 'identity_detail':identity.get('detail') if identity.get('state')!='KNOWN' else 'KNOWN_NAME_REDACTED',
 'enrolled_count':len(identity.get('people',[])),
 'person_hashes':[hashlib.sha256(p['person_id'].encode()).hexdigest()[:16] for p in identity.get('people',[])],
 'current_person_hash':hashlib.sha256(identity.get('person_id','').encode()).hexdigest()[:16] if identity.get('person_id') else '',
 'operation':{k:op.get(k) for k in ('command_id','action','state','db_version')} if op else None,
 'identity_turns':turns,'latest_playback_ack':ui['local_transcription']['service'].get('last_playback_ack'),
 'automatic':ui['automatic_conversation'],'ui_phase':ui['phase'],
 'names_redacted':True,'templates_exported':False,'photos_saved':False}
print(json.dumps(value))
'''
r=json.loads(ssh('python3 -',remote,timeout=25))
(HERE/'confirmed_enrollment_audit.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(r,ensure_ascii=True))
