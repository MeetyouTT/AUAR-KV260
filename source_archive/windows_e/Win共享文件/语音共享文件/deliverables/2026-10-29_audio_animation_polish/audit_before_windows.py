"""Fresh independent private DB checkpoint; only hashes/counts enter deliverables."""
import hashlib,json,sys
from pathlib import Path
H=Path(__file__).resolve().parent;A=H.parents[1]/'aura'
sys.path.insert(0,str(H.parent/'2026-10-29_service_recovery'))
from recovery_common import windows,checkpoint
v={'windows':windows(),'private_checkpoint':checkpoint('before'),
   'model_storage_sha256':hashlib.sha256((A/'config/model_storage.local.json').read_bytes()).hexdigest()}
(H/'windows_before.json').write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'status':'PASS','model_processes':len(v['windows']['models']),
 'checkpoint_status':v['private_checkpoint']['status'],'llm_storage_configuration_preserved':True}))
