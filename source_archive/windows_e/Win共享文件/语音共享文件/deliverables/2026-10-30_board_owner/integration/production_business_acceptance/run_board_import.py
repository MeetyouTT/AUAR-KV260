"""Run the frozen private board importer; return metadata only to this workspace."""
import argparse
import datetime
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[3]
sys.path.insert(0,str(PROJECT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
SOURCE='/home/root/aura-board-business-20261030/import-source-84f61727a69e7925/aura'
CLI_SHA='e475ac8b4143fdce598195056ca9a0cc867c69e72549c9626c8df528b5003bb8'
REMOTE=r'''
import hashlib,importlib.util,json,os,re,sqlite3,sys
from pathlib import Path
os.environ.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONNOUSERSITE='1',PYTHONDONTWRITEBYTECODE='1')
sys.path[:0]=[SOURCE,'/home/root/aura-board-owner-candidate-20261030/fft-ee19b936d17aa451/deps',
 '/home/root/aura-board-owner-candidate-20261030/asr-1.13.8/deps',
 '/home/root/aura-board-owner-candidate-20261030/webrtcvad-wheels-2.0.14-127741474d07c52f/deps']
path=Path(SOURCE)/'tools/board_production_import.py';raw=path.read_bytes();assert hashlib.sha256(raw).hexdigest()==CLI_SHA
spec=importlib.util.spec_from_file_location('_root_offline_import',str(path));module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
stage=Path(STAGE);legacy=Path('/home/root/.local/share/aura/conversation_selection.json');frozen=stage/'legacy-conversation-selection.json'
selection='no_saved_selection'
if frozen.exists():selection='frozen_anonymous_reference'
elif legacy.is_file():
 assert legacy.resolve()==legacy and not legacy.is_symlink() and legacy.stat().st_size<=4096
 value=json.loads(legacy.read_bytes());assert set(value)=={'version','conversation_id'} and value['version']==1
 db=sqlite3.connect((stage/'conversations.sqlite3').as_uri()+'?mode=ro&immutable=1',uri=True)
 try:
  row=db.execute('SELECT id FROM conversations WHERE id=?',(value['conversation_id'],)).fetchone()
  personal=db.execute('SELECT 1 FROM conversation_profiles WHERE conversation_id=?',(value['conversation_id'],)).fetchone()
 finally:db.close()
 if row and not personal:
  selection='valid_anonymous_reference'
  if ACTION=='execute':
   fd=os.open(str(frozen),os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
   with os.fdopen(fd,'wb') as out:out.write(legacy.read_bytes());out.flush();os.fsync(out.fileno())
 else:selection='saved_scope_not_in_import'
args=['--source-manifest',str(stage/'private-snapshot.json'),'--source-manifest-sha256',MANIFEST_SHA,
 '--speaker-model-id','ecapa-voxceleb-adec041f3ce0cbb809c286a31b1020734e2989fd0e59113786716267b0dda038',
 '--visual-device-id','board-camera','--trusted-utc',TRUSTED_UTC]
if ACTION=='execute':args+=['--execute','--source-writers-stopped']
if frozen.exists():args+=['--selection-source',str(frozen)]
try:
 v=module.main(args)
 result={k:v[k] for k in ('status','execute','receipt_sha256','counts','speaker_files','conversation_selection_verified',
 'source_deleted','retention_started','initial_retention_enabled','profile_grants_issued','business_values_exported') if k in v}
 if ACTION=='preflight':
  c=v.get('source_validation',{}).get('conversation',{});o=v.get('source_validation',{}).get('observation',{})
  result['counts']={k:c[k] for k in ('conversations','turns','profiles') if k in c}
  result['visual_counts']={k:o[k] for k in ('visual_events','imported_visual_events','observations','timeline_events','duplicate_observations') if k in o}
 result['selection_status']=selection
 result['target_created']=Path('/home/root/.local/share/aura-board-business').exists()
except Exception as exc:
 text=str(exc);code=text if re.fullmatch('[a-z][a-z0-9_]{1,100}',text) else 'private_import_failed'
 result=dict(status='REJECTED',error_type=type(exc).__name__,error_code=code,selection_status=selection)
print(json.dumps(result,ensure_ascii=True))
'''

def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=('preflight','execute'));args=p.parse_args()
    plan=json.loads((HERE/'migration_plan.json').read_text(encoding='utf-8'))
    assert plan['status']=='PRIVATE_SNAPSHOTS_STAGED_ON_BOARD_NOT_IMPORTED'
    values=dict(SOURCE=SOURCE,CLI_SHA=CLI_SHA,STAGE=plan['private_stage'],MANIFEST_SHA=plan['private_manifest_sha256'],
        TRUSTED_UTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),ACTION=args.action)
    result=json.loads(ssh('python3 -B -','\n'.join(k+'='+repr(v) for k,v in values.items())+'\n'+REMOTE,timeout=50))
    (HERE/('private_import_'+args.action+'.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=True))
    assert result['status']==('PREFLIGHT_ONLY' if args.action=='preflight' else 'PRIVATE_IMPORT_SEALED')
    if args.action=='execute':
        plan.update(status='PRIVATE_IMPORT_SEALED_NOT_ACTIVE',receipt_sha256=result['receipt_sha256'],real_database_imported=True,
            production_body_cleanup_enabled=False,board_business_ready_claimed=False,updated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
        (HERE/'migration_plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

if __name__=='__main__':main()
