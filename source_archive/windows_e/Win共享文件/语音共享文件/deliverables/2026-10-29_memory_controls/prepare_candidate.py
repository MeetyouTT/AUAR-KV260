"""Freeze source-only baselines for Windows memory improvements; no runtime changes."""
import hashlib,json,shutil,sys
from pathlib import Path
H=Path(__file__).resolve().parent;A=H.parents[1]/'aura';sys.path.insert(0,str(A))
from common.voice_service_capabilities import source_fingerprint
assert not (H/'source_plan.json').exists(),'Inspect existing candidate rather than resetting it'
files=['common/conversation_store.py','common/conversation_context.py','common/timeline_conversations.py',
       'common/voice_service_capabilities.py','tools/board_model_host.py','tools/memory_timeline_host.py']
plan={'status':'CANDIDATE_BUILD','authority':'Windows','board_migration':False,'user_direction':'先完善对话与记忆，迁移后置',
      'production_fingerprint':source_fingerprint(A),'files':{}}
for name in files:
    source=A/name
    for base in ('before','candidate_source'):
        target=H/base/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
    plan['files'][name]={'before':hashlib.sha256(source.read_bytes()).hexdigest()}
for name in ('common/memory_controls.py',):plan['files'][name]={'before':None}
(H/'source_plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
for name in ('bootstrap.py','test_timeline.py','test_summaries.py'):
    shutil.copy2(H.parent/'2026-10-28_timeline_summaries'/name,H/name)
print(json.dumps({'status':'FROZEN_SOURCE_ONLY','files':len(plan['files']),'production_fingerprint':plan['production_fingerprint']}))
