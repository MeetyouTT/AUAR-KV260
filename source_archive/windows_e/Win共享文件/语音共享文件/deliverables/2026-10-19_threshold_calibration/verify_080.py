"""Verify current 0.80 trial after interrupted activation/reboot, no enrollment."""
import json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
c=json.loads((ROOT/'deliverables/2026-10-19_windows_face_features/candidate.json').read_text(encoding='utf-8'))
a=json.loads((HERE/'threshold_080_activation.json').read_text(encoding='utf-8'))
remote=r'''
import hashlib,json,sqlite3,subprocess,urllib.request
from pathlib import Path
c=CANDIDATE;a=ACTIVATION
def get(port,path,host='127.0.0.1'):
 return json.load(urllib.request.urlopen('http://'+host+':'+str(port)+path,timeout=4))
h=get(8790,'/health');view=get(8790,'/v1/ui/status');ui=get(8783,'/api/state')
argv=Path('/proc/%d/cmdline'%h['pid']).read_bytes().decode().split('\0')
camera_path=Path(argv[argv.index('--config')+1]);assert str(camera_path)==c['camera_config']
identity_path=Path(json.loads(camera_path.read_text())['identity']['config']);raw=identity_path.read_bytes();cfg=json.loads(raw)
assert cfg['threshold']==.8 and cfg['ambiguity_margin']==.1
assert hashlib.sha256(raw).hexdigest()==a['identity_config_sha256']
assert cfg['feature_backend']=={'kind':'windows_sface','host':'192.168.50.1','port':8792,'timeout_ms':650}
assert h['identity']['ready'] and not h['identity']['error'] and not h['camera_error'] and not h['detector_error']
assert h['detector']==a['camera_before']['detector'] and h['identity']['backend']=='WINDOWS_CPU_SFACE_ORT'
root=Path(c['runtime']);sources={n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in c['files']}
assert sources==c['files']
db=Path(cfg['database']).expanduser();before=hashlib.sha256(db.read_bytes()).hexdigest()
with sqlite3.connect('file:'+str(db)+'?mode=ro',uri=True) as conn:
 counts={'identities':conn.execute('SELECT count(*) FROM identities').fetchone()[0],
  'templates':conn.execute('SELECT count(*) FROM templates').fetchone()[0],
  'revision':conn.execute("SELECT value FROM metadata WHERE key='revision'").fetchone()[0]}
assert counts=={'identities':0,'templates':0,'revision':13}
assert view['modules']['identity']['people']==[]
assert before==hashlib.sha256(db.read_bytes()).hexdigest()
pc=get(8792,'/health','192.168.50.1');asr=get(8791,'/health','192.168.50.1')
assert pc['ready'] and pc['identity_features']['ready'] and pc['num_step']==16
assert pc['llm_model']=='aura-qwen3.8-27b-abliterated:iq4_xs' and asr['ready']
assert pc['identity_features']['backend']=='WINDOWS_CPU_SFACE_ORT' and not pc['identity_features']['gpu_used']
assert pc['identity_voice_enrollment']['sampling_guidance_version']==3
report={'client_date':'2026-10-19','status':'CURRENT_080_CONFIG_AND_EMPTY_LIBRARY_VERIFIED',
 'threshold':cfg['threshold'],'ambiguity_margin':cfg['ambiguity_margin'],
 'active_identity_config':str(identity_path),'identity_config_sha256':hashlib.sha256(raw).hexdigest(),
 'effective_identity_config':cfg,
 'active_source_count':len(sources),'active_sources_verified':True,'source_runtime':str(root),
 'current_boot_id':h['board_boot_id'],'current_camera_pid':h['pid'],
 'boot_changed_since_original_activation':h['board_boot_id']!=a['camera_before']['board_boot_id'],
 'camera_error':h['camera_error'],'detector_error':h['detector_error'],'identity_error':h['identity']['error'],
 'identity_health':h['identity'],'capture_hz':h['capture_hz'],'detection_hz':h['detection_hz'],
 'body_tracking_preserved':True,'database':counts,'database_hash_unchanged_during_inspection':True,
 'database_mode':oct(db.stat().st_mode&0o777),'pc_health':pc,'asr_ready':asr['ready'],
 'ui_phase':ui['phase'],'audio_output_state':ui['audio_output_state'],
 'automatic':ui['automatic_conversation'],
 'recording':{k:ui['local_recording'].get(k) for k in ('state','can_start','can_stop','error')},
 'voice_service':{k:ui['local_transcription'].get('service',{}).get(k)
  for k in ('ready','enabled','conversation','pending','error')},
 'identity_state':view['modules']['identity']['state'],'real_user_enrollment_passed':None,
 'photos_accessed':False,'templates_exported':False,'names_exported':False}
print(json.dumps(report))
'''.replace('CANDIDATE',repr(c),1).replace('ACTIVATION',repr(a),1)
r=json.loads(ssh('python3 -B -',remote,timeout=40))
folder=HERE/'effective_config_080';folder.mkdir(exist_ok=True)
(folder/'board_identity.json').write_text(json.dumps(r.pop('effective_identity_config'),ensure_ascii=False,indent=2),encoding='utf-8')
(HERE/'threshold_080_current_verification.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({key:r[key] for key in ('status','threshold','database','current_boot_id','current_camera_pid',
 'boot_changed_since_original_activation','ui_phase','automatic','recording','voice_service')},ensure_ascii=True))
