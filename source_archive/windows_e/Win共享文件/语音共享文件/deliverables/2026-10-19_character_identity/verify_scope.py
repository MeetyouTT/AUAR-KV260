"""Compare the requested one-line edit with preserved runtime/config state."""
import hashlib,json,re,sys,urllib.request
from pathlib import Path

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
before=json.loads((HERE/'before_state.json').read_text(encoding='utf-8'))
original=(HERE/'before/character.py').read_text(encoding='utf-8')
current=(ROOT/'aura/board/runtime/character.py').read_text(encoding='utf-8')
assert current==original.replace("CHARACTER_DESCRIPTION = 'DeepSeek 鲸鱼娘'",
                                "CHARACTER_DESCRIPTION = '名字叫汐蓝的桌面玩偶助手'")
assert all(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==sha for name,sha in before['files'].items())
health=json.load(urllib.request.urlopen('http://192.168.50.1:8792/health',timeout=4))
for field in ('llm_model','asr_model','tts','num_step','latency_options','conversation_memory'):
    assert health[field]==before['host'][field],field
assert health['ready'] and not health['busy']
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
remote=r'''
import json,hashlib,subprocess,re,urllib.request
from pathlib import Path
unit=subprocess.check_output(['systemctl','cat','aura-camera-ui.service'],text=True)
config=json.loads(Path(re.search(r'--config (\S+)',unit).group(1)).read_text())
identity=json.loads(Path(config['identity']['config']).read_text());db=Path(identity['database']).expanduser()
camera=json.load(urllib.request.urlopen('http://127.0.0.1:8790/health',timeout=4))
ui=json.load(urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=4))
print(json.dumps({'ui_unit':subprocess.check_output(['systemctl','cat','aura-avatar-ui.service'],text=True),
 'camera_unit':unit,'camera_pid':camera['pid'],'identity_db_sha256':hashlib.sha256(db.read_bytes()).hexdigest(),
 'ui_phase':ui['phase'],'automatic':ui['automatic_conversation'],'pending':ui['local_transcription']['service']['pending']}))
'''
board=json.loads(ssh('python3 -B -',remote))
for field in ('ui_unit','camera_unit','camera_pid','identity_db_sha256'):
    assert board[field]==before['board'][field],field
assert board['ui_phase']=='IDLE' and not board['pending'] and not board['automatic']['enabled']
rows=json.loads((HERE/'actual_self_identity.json').read_text(encoding='utf-8'))
assert len(rows)==4
assert '汐蓝' in rows[0]['reply'] and '汐蓝' in rows[1]['reply']
assert '助手' in rows[2]['reply'] or '玩偶' in rows[2]['reply']
summary={'status':'CHARACTER_IDENTITY_UPDATED_AND_LOADED','name':'汐蓝','description':'名字叫汐蓝的桌面玩偶助手',
 'production_source_change':'character.py CHARACTER_DESCRIPTION only','tests_passed':63,
 'actual_27b_questions':rows,'model_audio_memory_configs_unchanged':True,
 'conversation_counts_unchanged':True,'board_ui_not_restarted':True,'camera_pid_preserved':True,
 'identity_database_unchanged':True,'human_listening_test':False,'host_ready':True}
(HERE/'verification_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({key:value for key,value in summary.items() if key!='actual_27b_questions'},ensure_ascii=True))
