"""Compose an isolated public-source candidate against the recorded production pins."""
import ast
import difflib
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
OUT=HERE.parent
PROJECT=OUT.parents[1]
SOURCE=PROJECT/'deliverables/2026-10-30_board_owner/integration/dialogue_repair/feature_trigger_collaboration/candidate_m03_v90_stage/public_runtime_v90'
observation=OUT/'parallel_platform/gui_startup_review/gui_bootstrap_01.json'
data=json.loads(observation.read_text(encoding='utf-8'))['board_result']
startup=json.loads(data['files']['/home/root/aura-board-business-20261030/production-5259eab11e42af13/startup/config.json']['text'])
assert len(startup['component_sha256'])==380
pins=startup['component_sha256']
current_index=json.loads((OUT/'joint_dialogue_trial_20261101/dialogue_review/source_index.json').read_text(encoding='utf-8'))
assert len(current_index)==16
current={str(Path(row['board_path']).as_posix()).split('/runtime/aura/',1)[1]:row for row in current_index}
assert all(row['current_startup_pinned'] and pins[rel]==row['sha256'] for rel,row in current.items())
root=HERE/'baseline'
assert not root.exists()
root.mkdir()
manifest={};missing=[]
for relative,expected in pins.items():
    if not(relative.endswith('.py') or relative in ('config/character_profile.local.json',
        'config/persona.xuefei.candidate.json','config/yuki_pair.formal.json','config/yuki_accepted_prompt.baseline.txt')):
        continue
    choices=[Path(current[relative]['path'])] if relative in current else []
    choices.extend((PROJECT/'deliverables/2026-10-30_board_owner/integration/dialogue_repair/feature_trigger_collaboration/identity_cooperation_v90/after'/relative,
        SOURCE/relative,PROJECT/'aura'/relative))
    found=next((p for p in choices if p.is_file() and not p.is_symlink()
        and hashlib.sha256(p.read_bytes()).hexdigest()==expected),None)
    if found is None:
        missing.append(relative);continue
    target=root/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(found.read_bytes())
    manifest[relative]={'source':str(found),'sha256':expected,'bytes':target.stat().st_size}
relative='tools/unified_identity_binding.py'
before=(root/relative).read_text(encoding='utf-8')
assert hashlib.sha256((root/relative).read_bytes()).hexdigest()=='f083fe8b618f4b09dce1587b3c32bf47f92510948e728615ce989ef31a1757cf'
old="""        if state=='SAMPLING_VOICE':
            face=json.loads(row['face_receipt'])
"""
new="""        if state=='SAMPLING_VOICE':
            from tools.provisional_voice import query_reply
            if query_reply(text,{'state':'UNKNOWN'}) is not None:
                # A read-only face/voice query is not one of the three voice
                # enrollment samples. The existing hub resolves this ordinary
                # route with current face/voice evidence and its conflict rules.
                return self.decision('ordinary',reason='IDENTITY_QUERY_DURING_VOICE_ENROLLMENT')
            face=json.loads(row['face_receipt'])
"""
assert before.count(old)==1
after=before.replace(old,new)
ast.parse(after)
candidate=HERE/'candidate'/relative;candidate.parent.mkdir(parents=True,exist_ok=True)
candidate.write_text(after,encoding='utf-8',newline='')
(HERE/'CANDIDATE.diff').write_text(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),
    fromfile='production/'+relative,tofile='candidate/'+relative)),encoding='utf-8')
result={'schema':'aura-identity-language-candidate-1','status':'LOCAL_CANDIDATE_TESTS_PENDING',
    'live_startup_sha256':'3fd124287463650f48232cb387c78d01399bad7ddcda483db725163298de4591',
    'recorded_source_startup_sha256':data['startup_sha256'],
    'recorded_source_scope':'same Python pins; subsequent GUI-only binding pin change is separately root-verified',
    'current16_pins_match_recorded380':True,'baseline_files':manifest,'baseline_missing':missing,
    'files':{relative:{'before_sha256':hashlib.sha256((root/relative).read_bytes()).hexdigest(),
        'sha256':hashlib.sha256(candidate.read_bytes()).hexdigest(),'bytes':candidate.stat().st_size}},
    'board_modified':False,'model_or_device_accessed':False,'identity_policy_changed':False}
(HERE/'SOURCE_MANIFEST.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'copied_sources':len(manifest),'missing':missing,'candidate':str(candidate)}))
