"""Prepare a Windows-only handoff fix against exact r4 sources."""
import hashlib,json,shutil,sys
from pathlib import Path
H=Path(__file__).resolve().parent;A=H.parents[1]/'aura';sys.path.insert(0,str(A))
from common.voice_service_capabilities import SOURCE_FILES,source_fingerprint
assert not (H/'source_plan.json').exists()
assert source_fingerprint(A)=='1ed519dc5d287a344019beca4212f588aa9d41dcafebabf867466232346b3de2'
names=['tools/board_model_host.py','tools/voice_channel_source.py','common/voice_service_capabilities.py']
plan={'status':'CANDIDATE','production_fingerprint':source_fingerprint(A),'source_before':{n:hashlib.sha256((A/n).read_bytes()).hexdigest() for n in SOURCE_FILES},'files':{}}
for name in names:
 raw=(A/name).read_bytes();plan['files'][name]={'before':hashlib.sha256(raw).hexdigest()}
 for folder in ('before','candidate_source'):
  target=H/folder/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
(H/'source_plan.json').write_text(json.dumps(plan,indent=2),encoding='utf-8')
