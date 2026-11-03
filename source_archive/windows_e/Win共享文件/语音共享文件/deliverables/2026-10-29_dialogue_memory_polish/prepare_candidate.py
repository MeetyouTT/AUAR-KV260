"""Freeze a Windows-only r4 candidate and regression harness; no live changes."""
import hashlib,json,shutil,sys
from pathlib import Path
H=Path(__file__).resolve().parent;A=H.parents[1]/'aura'
sys.path.insert(0,str(A))
from common.voice_service_capabilities import source_fingerprint,SOURCE_FILES
assert not (H/'source_plan.json').exists(),'Preserve existing work'
files=['common/memory_controls.py','common/voice_service_capabilities.py','tools/voice_channel_source.py']
plan={'status':'BUILDING','user_direction':'继续完善Windows对话记忆并验证优化效果，迁移暂缓',
      'production_fingerprint':source_fingerprint(A),'files':{},
      'source_before':{n:hashlib.sha256((A/n).read_bytes()).hexdigest() for n in SOURCE_FILES},
      'preserved_latency_sha256':hashlib.sha256((A/'config/voice_latency.json').read_bytes()).hexdigest()}
for name in files:
    for base in ('before','candidate_source'):
        target=H/base/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(A/name,target)
    plan['files'][name]={'before':hashlib.sha256((A/name).read_bytes()).hexdigest()}
plan['files']['common/fact_answers.py']={'before':None}
(H/'source_plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
for name in ('test_controls.py','test_timeline.py','test_summaries.py','db_checkpoint.py','start_checkpoint.ps1','synthesize_question.ps1','manage_owned.ps1','verify_private.py'):
    shutil.copy2(H.parent/'2026-10-29_memory_controls'/name,H/name)
p=H/'db_checkpoint.py';p.write_text(p.read_text(encoding='utf-8').replace('controls-20261029-','polish-20261029-'),encoding='utf-8')
(H/'PROGRESS.json').write_text(json.dumps({'status':'BUILDING_WINDOWS_CANDIDATE','complete':False,
    'board_migration':False,'authority':'Windows','production_revision':'voice-memory-controls-20261029-r3',
    'targets':['natural_current_fact_answers','indexed_fact_history_browsing','automatic_unknown_source_protection',
               'same_input_before_after_latency_measurement']},indent=2),encoding='utf-8')
print(json.dumps({'status':plan['status'],'production_fingerprint':plan['production_fingerprint'],'files':4,'board_migration':False}))

