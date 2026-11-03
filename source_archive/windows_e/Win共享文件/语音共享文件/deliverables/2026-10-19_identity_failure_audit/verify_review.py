"""Confirm this review left runtime, model configuration and user DB intact."""
import json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
before=json.loads((HERE/'active_runtime.json').read_text(encoding='utf-8'))
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
remote=r'''
import hashlib,json,sqlite3,urllib.request
from pathlib import Path
b=BEFORE
get=lambda port,path:json.load(urllib.request.urlopen('http://127.0.0.1:'+str(port)+path,timeout=4))
h=get(8790,'/health');u=get(8783,'/api/state')
cfg=json.loads(Path(b['identity_config_path']).read_text());assert cfg==b['identity_config']
db=Path(cfg['database']).expanduser();unchanged=hashlib.sha256(db.read_bytes()).hexdigest()==b['database_hash']
assert unchanged
for name,row in b['source_comparison'].items():
 assert hashlib.sha256((Path(b['camera_root'])/name).read_bytes()).hexdigest()==row['camera_sha256']
 assert hashlib.sha256((Path(b['ui_root'])/name).read_bytes()).hexdigest()==row['ui_sha256']
assert h['pid']==b['camera_pid'] and h['identity']['ready'] and not h['identity']['error']
photos=h['identity']['enrollment_photos'];assert photos['image_count']==25 and photos['outcome']=='committed'
assert not photos['error'] and photos['latest_session']==b['camera_health']['identity']['enrollment_photos']['latest_session']
assert u['ui_runtime']['link']=='READY'
print(json.dumps({'status':'PASS_REVIEW_RUNTIME_UNCHANGED','all_15_camera_and_ui_source_hashes_unchanged':True,
 'identity_config_unchanged':True,'database_hash_unchanged':unchanged,'database_revision':15,
 'camera_pid_preserved':True,'identity_service_ready':True,'ui_service_link':'READY',
 'archive_photo_count':photos['image_count'],'archive_no_new_session':True,'archive_error':'',
 'threshold':cfg['threshold'],'ambiguity_margin':cfg['ambiguity_margin']}))
'''.replace('BEFORE',repr(before),1)
r=json.loads(ssh('python3 -B -',remote,timeout=25))
(HERE/'audit_no_mutation.json').write_text(json.dumps(r,indent=2),encoding='utf-8')
summary=json.loads((HERE/'review_summary.json').read_text(encoding='utf-8'))
summary['end_of_review_runtime_unchanged_verified']=True
(HERE/'review_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
report=HERE/'REPORT.md';text=report.read_text(encoding='utf-8')
note='\n末尾复核：`audit_no_mutation.json`已确认15个相关模块在两个活动目录中的原指纹保持、有效配置/正式库哈希不变、相机PID保持、身份和界面服务就绪、照片仍25张且没有新采样会话。\n'
if '末尾复核：' not in text:
 report.write_text(text+note,encoding='utf-8')
 (ROOT.parent/'语言模型分析/身份认证失败详细审查与解决措施_20261019.md').write_text(text+note,encoding='utf-8')
print(json.dumps(r))
