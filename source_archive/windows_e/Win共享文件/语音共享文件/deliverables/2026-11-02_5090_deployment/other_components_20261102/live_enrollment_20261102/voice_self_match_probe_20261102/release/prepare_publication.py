"""Prepare reviewed source publication; this script never contacts the board."""
import ast
import base64
import hashlib
import json
from pathlib import Path

RELEASE=Path(__file__).resolve().parent
ENROLL=RELEASE.parents[1]
OLD=ENROLL/'lifecycle_review/no_speech_fix'
TRACE=ENROLL/'voice_entry_name_fix_20261102/release'
BASE='21c1dbcd454d50875d4fd61c970e269666257dd236c87103c12b1058965de51e'
OLD_BASE='9a9a709a7b2e898879bac595758f9b7ece6f2ff2e75a4c9f42ed9c38e043072a'
TX='voice-self-match-probe-v1'
BEFORE={'board/runtime/board_speaker_business.py':'6904267bd016a10a1508b26f372f0db54a71d78eed2eb15b043026218b1b7816'}
manifest=json.loads((RELEASE.parent/'SOURCE_MANIFEST.json').read_text('utf-8'))
assert set(manifest['files'])==set(BEFORE)
payload={'base_startup_sha256':BASE,'files':{}}
after={}
for key,before in BEFORE.items():
    info=manifest['files'][key]
    data=(RELEASE.parent/'candidate_runtime'/key).read_bytes()
    digest=hashlib.sha256(data).hexdigest()
    assert info['before_sha256']==before and info['after_sha256']==digest
    compile(data,key,'exec')
    after[key]=digest
    payload['files'][key]=dict(before_sha256=before,candidate_sha256=digest,payload_base64=base64.b64encode(data).decode())
old_worker=(ENROLL/'voice_entry_name_fix_20261102/candidate_runtime/board/runtime/board_speaker_business.py').read_bytes()
new_worker=(RELEASE.parent/'candidate_runtime/board/runtime/board_speaker_business.py').read_bytes()
for helper_class in ('_WriterLease','_CheckedEncoder','_GuardedStore'):
    def helper_ast(data):
        return ast.dump(next(n for n in ast.parse(data).body if isinstance(n,ast.ClassDef) and n.name==helper_class),include_attributes=False)
    assert helper_ast(old_worker)==helper_ast(new_worker),'Original store/encoder owner guard changed'

def changed(text,replacements):
    for old,new in replacements:
        assert old in text,old
        text=text.replace(old,new)
    return text
stop=(OLD/'stop_gui_for_no_speech_fix.py').read_text('utf-8')
stop=changed(stop,[(OLD_BASE,BASE),('no-speech-enrollment-v1',TX),('no-speech-enrollment','voice-self-match-probe'),
 ("'2142'","'144958'"),('/proc/2142/','/proc/144958/'),("'76636'","'1211899'"),
 ('/proc/2151/','/proc/145002/'),("'76768'","'1215213'")])
stop=stop.replace('TX.mkdir(mode=0o700)',"""assert hashlib.sha256(Path('/proc/144958/cmdline').read_bytes()).hexdigest() == '48a28efa32b2050901e73e85a80a30a90dcfbce0b7249bde5d6d90902740631d'
assert hashlib.sha256(Path('/proc/145002/cmdline').read_bytes()).hexdigest() == '1bbdc657f20f2f0cbb64c1ccfd4016c7c59430ee585c84c0890b86d36d51e712'
assert (ui.get('manual_pan') or {}).get('automatic_following') is False
TX.mkdir(mode=0o700)""")

apply=(OLD/'apply_no_speech_fix.template.py').read_text('utf-8')
apply=changed(apply,[(OLD_BASE,BASE),('no-speech-enrollment-v1',TX),
 ("{'board/runtime/audio/board_asr.py', 'board/runtime/audio/board_dialogue_jobs.py'}",repr(set(BEFORE))),
 ('/proc/2142','/proc/144958'),('/proc/2151','/proc/145002'),('no-speech-','voice-entry-name-fix-'),
 ('NO_SPEECH_FIX_APPLIED_GUI_STOPPED','VOICE_SELF_MATCH_PROBE_APPLIED_GUI_STOPPED'),
 ("'other_component_pins_preserved': 378","'other_component_pins_preserved': 379")])
apply=apply.replace("assert startup['component_sha256']['board/identity/voice_enrollment.py']", """assert startup['component_sha256']['board/runtime/board_business.py'] == 'bf185a86dfd1f94924759c194b0246b51e64cb0a09654c935e8e1310f7bbea51'
assert startup['component_sha256']['common/feature_intents.py'] == '2ad13c7a5a175a85dfb412182fca44a79229962ff742b18691a7b72ea75f15f2'
assert startup['component_sha256']['tools/yuki_jobs_candidate.py'] == 'd7bade70cf15cd5c7dd9bb17be702f86c5f2d1a32ad5c5809dddffde7a71d200'
assert startup['component_sha256']['board/runtime/audio/board_dialogue_jobs.py'] == '580b2cf796275104cf15f2295afa2de29f82f32eabdd783a4b3aff858840a464'
assert startup['component_sha256']['board/runtime/audio/board_asr.py'] == 'c51488ac6bd3563bc3dc42934b321e98e26cb2b58d700318765a60ca4908ef60'
assert startup['component_sha256']['common/binding_intent.py'] == '8048cd5bd4f3f80cd872f373e1eed149820f37d2ec40042390c17cfb4cd94df1'
assert startup['component_sha256']['board/interaction/ui_services.py'] == 'e4dedf9b3d56d22d9eb93de1e96ad1a69870d553ea50f7dd5082b21e19f381c9'
assert startup['component_sha256']['tools/board_camera_preview.py'] == '67d6c0f2b24ea97e20fdcc7b3383b6444269a6e26f5deb566f2b88746b7daf9b'
assert sha(aura / 'config/yuki_pair.formal.json') == '998710fc12bf442d6baea501bab0234665b666caa29f4be8f685741d50d82099'
pair_pins = json.loads(raw(aura / 'config/yuki_pair.formal.json'))['runtime_pins']
assert len(pair_pins) == 10 and not (set(pair_pins) & KEYS)
assert all(sha(aura / k) == v for k,v in pair_pins.items())
assert startup['component_sha256']['board/identity/voice_enrollment.py']""")
apply='PAYLOAD = '+repr(payload)+'\n'+apply

start=(OLD/'start_gui_after_no_speech_fix.py').read_text('utf-8')
start=changed(start,[('no-speech-enrollment-v1',TX),('no-speech-enrollment','voice-self-match-probe'),
 ('no-speech-fix','voice-self-match-probe'),('NO_SPEECH_FIX_APPLIED_GUI_STOPPED','VOICE_SELF_MATCH_PROBE_APPLIED_GUI_STOPPED')])
tree=ast.parse(start)
node=next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='TARGETS' for t in n.targets))
lines=start.splitlines(keepends=True);lines[node.lineno-1:node.end_lineno]=['TARGETS = '+repr(after)+'\n'];start=''.join(lines)

startup_raw=(TRACE/'startup.after.predicted.json').read_bytes()
assert hashlib.sha256(startup_raw).hexdigest()==BASE
startup=json.loads(startup_raw)
for key,digest in after.items():
    assert startup['component_sha256'][key]==BEFORE[key]
    startup['component_sha256'][key]=digest
predicted=(json.dumps(startup,sort_keys=True,indent=2)+'\n').encode()
records={}
for filename,data in [('stop_gui_once.py',stop.encode()),('apply_fix_once.py',apply.encode()),('start_gui_once.py',start.encode()),('startup.after.predicted.json',predicted)]:
    target=RELEASE/filename
    assert not target.exists()
    if filename.endswith('.py'):compile(data,str(target),'exec')
    target.write_bytes(data);records[filename]=hashlib.sha256(data).hexdigest()
final=dict(base_startup_sha256=BASE,predicted_startup_after_sha256=hashlib.sha256(predicted).hexdigest(),source_before=BEFORE,source_after=after,generated_files=records,device_actions=False)
(RELEASE/'RELEASE_MANIFEST.json').write_text(json.dumps(final,indent=2)+'\n','utf-8')
print(json.dumps(final))
