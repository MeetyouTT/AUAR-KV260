"""Keep the failed live attempt; preserve warm TTS while discarding a cancelled reply."""
import hashlib,json,shutil,sys
from pathlib import Path
H=Path(__file__).resolve().parent;A=H.parents[1]/'aura';C=H/'candidate_source'
assert not (H/'attempt1').exists()
old=json.loads((H/'source_plan.json').read_text())
assert old['candidate_revision']=='voice-turn-handoff-20261029-r5'
attempt=H/'attempt1';attempt.mkdir()
for name in ('source_plan.json','deployment.json','tests.xml','tests_first.log','live_handoff.json'):
 shutil.copy2(H/name,attempt/name)
shutil.copytree(C,attempt/'candidate_source')
for name,row in old['files'].items():
 assert hashlib.sha256((A/name).read_bytes()).hexdigest()==row['candidate']
 target=H/'before_recovery'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((A/name).read_bytes())
p=C/'tools/voice_channel_source.py';s=p.read_text(encoding='utf-8')
a="        while True:\n            check_current()\n            if time.monotonic()>=deadline:raise TimeoutError('Channel synthesis budget expired')"
b="        while True:\n            # OmniVoice cannot abort an in-flight native call without retiring\n            # its owned warm worker. Finish only this bounded call, then discard\n            # its result for a disconnected peer; do not start any new clause.\n            if time.monotonic()>=deadline:raise TimeoutError('Channel synthesis budget expired')"
assert s.count(a)==1;s=s.replace(a,b)
a="        nonlocal segment_id, first_pcm_ms, tts_total_ms, tts_cache_hits, active_tts_id\n"
assert s.count(a)==1;s=s.replace(a,a+'        check_current()\n')
a="        active_tts_id=None\n        tts_cache_hits +="
assert s.count(a)==1;s=s.replace(a,"        active_tts_id=None\n        check_current()\n        tts_cache_hits +=")
p.write_text(s,encoding='utf-8',newline='')
p=C/'common/voice_service_capabilities.py';s=p.read_text(encoding='utf-8').replace('voice-turn-handoff-20261029-r5','voice-turn-handoff-20261029-r6');p.write_text(s,encoding='utf-8',newline='')
sys.path.insert(0,str(A))
from common.voice_service_capabilities import SOURCE_FILES,source_fingerprint
assert source_fingerprint(A)==old['candidate_fingerprint']
plan={**old,'status':'CANDIDATE_RECOVERY','original_r4_fingerprint':old['production_fingerprint'],
 'original_r4_files':old['files'],'production_fingerprint':source_fingerprint(A),
 'source_before':{name:hashlib.sha256((A/name).read_bytes()).hexdigest() for name in SOURCE_FILES},
 'files':{name:{'before':hashlib.sha256((A/name).read_bytes()).hexdigest(),'candidate':hashlib.sha256((C/name).read_bytes()).hexdigest()} for name in old['files']}}
ns={};exec((C/'common/voice_service_capabilities.py').read_text(encoding='utf-8'),ns)
d=hashlib.sha256()
for name in ns['SOURCE_FILES']:
 p=C/name
 if not p.exists():p=A/name
 d.update(name.encode()+b'\0');d.update(hashlib.sha256(p.read_bytes()).digest())
plan.update(candidate_revision=ns['SERVICE_REVISION'],candidate_fingerprint=d.hexdigest(),tests_passed=None)
(H/'source_plan.json').write_text(json.dumps(plan,indent=2),encoding='utf-8')
print(json.dumps({'status':plan['status'],'revision':plan['candidate_revision'],'fingerprint':plan['candidate_fingerprint']}))
