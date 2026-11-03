"""Retain actual failure numbers only; no photographs, vectors or display names."""
import json,statistics,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
remote=r'''
import hashlib,json,subprocess,urllib.request
from pathlib import Path
get=lambda host,port,path:json.load(urllib.request.urlopen('http://'+host+':'+str(port)+path,timeout=4))
h=get('127.0.0.1',8790,'/health');s=get('127.0.0.1',8790,'/v1/ui/status');u=get('127.0.0.1',8783,'/api/state')
args=Path('/proc/%d/cmdline'%h['pid']).read_bytes().decode().split('\0')
camera_path=Path(args[args.index('--config')+1]);camera=json.loads(camera_path.read_text())
identity=json.loads(Path(camera['identity']['config']).read_text());db=Path(identity['database']).expanduser()
before=hashlib.sha256(db.read_bytes()).hexdigest();item=s['modules']['identity']
p=get('192.168.50.1',8792,'/health')
out={'client_date':'2026-10-19','camera_config':str(camera_path),
 'backend':h['identity']['backend'],'last_inference_ms':h['identity']['last_inference_ms'],
 'camera_error':h['camera_error'],'detector_error':h['detector_error'],'identity_error':h['identity']['error'],
 'sampling_diagnostics':h['identity']['sampling_diagnostics'],
 'identity_state':item['state'],'database_revision':item['db_version'],'registered_count':len(item['people']),
 'database_hash_unchanged_during_inspection':hashlib.sha256(db.read_bytes()).hexdigest()==before,
 'database_mode':oct(db.stat().st_mode&0o777),
 'threshold':identity['threshold'],'ambiguity_margin':identity['ambiguity_margin'],
 'feature_backend':identity.get('feature_backend'),'pc_identity_features':p.get('identity_features'),
 'ui_phase':u['phase'],'automatic_enabled':u['automatic_conversation']['enabled'],
 'recent_identity_codes':[{'generation':t.get('generation'),'audio_complete':t.get('audio_complete'),
   'code':t.get('server_metrics',{}).get('timing',{}).get('llm',{}).get('identity_reply_code')}
   for t in u.get('turns',[])[-8:]],
 'photos_accessed':False,'photos_exported':False,'templates_exported':False,'names_exported':False,
 'production_changed':False,'threshold_changed':False}
print(json.dumps(out))
'''
r=json.loads(ssh('python3 -B -',remote,timeout=30))
f=r['sampling_diagnostics']['last_failure'];assert f and f['metrics']['validation_attempts']>0
m=f['metrics'];scores=[v['score'] for v in m['recent_validation']]
r['failure_summary']={'attempts':m['validation_attempts'],'passes':m['validation_passes'],
 'below_threshold':m['score_rejections'],'margin_rejections_may_overlap':m['margin_rejections'],
 'longest_consecutive_passes':m['best_validation_run'],'required_consecutive_passes':5,
 'quality_skips_across_session':m['quality_skips'],'track_recovery_rejections':m['recovery_rejections'],
 'retained_last_frame_count':len(scores),'last_scores_min':min(scores),'last_scores_median':statistics.median(scores),
 'last_scores_max':max(scores),'failed_candidate_pose_retained':False,'failed_candidate_image_retained':False,
 'only_last_24_scores_retained_not_full_77':True}
(HERE/'actual_failure.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'failure_summary':r['failure_summary'],'database_revision':r['database_revision'],
 'registered_count':r['registered_count'],'backend':r['backend'],'last_inference_ms':r['last_inference_ms']},ensure_ascii=True))
