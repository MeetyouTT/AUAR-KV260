"""Root-only public synthetic TTS fixtures, stored/resampled on the board."""
import hashlib
import json
from pathlib import Path
import sys
import uuid

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[4]
sys.path.insert(0, str(PROJECT / 'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
TEXT_SHA = 'e41dc194e00e3b76c40bdf4ee96cadf364e088a9c2c1f180ff872d6e77f72ede'

REMOTE = r'''
import argparse,audioop,hashlib,importlib.util,json,pathlib,subprocess,sys,time,uuid,wave
root=pathlib.Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
guard_path=pathlib.Path('/home/root/aura-public-asr-thread-abba-20261031/210925ca35fb5acd/probe_asr_abba.py')
assert hashlib.sha256(guard_path.read_bytes()).hexdigest()=='210925ca35fb5acdf90e96c08f9fe4713042637dd777d707c8ccb4134cdecf69'
spec=importlib.util.spec_from_file_location('_public_asr_guard',guard_path)
guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard)
boot=pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip()
ui=int(subprocess.check_output(['/bin/systemctl','show','aura-avatar-ui.service','-p','MainPID','--value'],text=True))
camera=guard.get('127.0.0.1',8790,'/health')['pid']
args=argparse.Namespace(runtime_root=str(root),startup_sha256=EXPECTED,boot_id=boot,
 ui_pid=ui,ui_birth=guard.proc(ui)['birth'],camera_pid=camera,camera_birth=guard.proc(camera)['birth'],min_available_mib=512)
guard_deadline=time.monotonic()+20
while True:
 try:
  before=guard.metadata(args)
  break
 except guard.ProbeRefused as exc:
  if exc.code not in ('pause_and_idle_required','model_or_background_summary_active') or time.monotonic()>=guard_deadline:raise
  time.sleep(.25)
startup=json.loads((root/'startup/config.json').read_bytes());code=root/'runtime/aura'
for relative in ('board/runtime/board_dialogue_client.py','common/model_inference_wire.py','common/board_timeline_clock.py'):
 assert hashlib.sha256((code/relative).read_bytes()).hexdigest()==startup['component_sha256'][relative]
sys.path.insert(0,str(code))
from board.runtime.board_dialogue_client import InferenceHttpClient
from common.model_inference_wire import Owner,decode_audio
health=guard.get('192.168.50.1',8797,'/health')
assert health['backend']['tts']=='omnivoice' and health['backend']['num_step']==16 and health['backend']['tts_ready'] is True
assert health['backend']['gpu_coordination']['enforcing'] is True
directory=pathlib.Path('/home/root/aura-public-streaming-validation-20261031')/('synthetic-'+RUN_ID)
assert not directory.parent.is_symlink();directory.mkdir(mode=0o700,parents=True,exist_ok=False)
client=InferenceHttpClient('192.168.50.1',8797)
session='public-asr-quality-'+RUN_ID
rows=[];total_deadline=time.monotonic()+120
for row in CASES:
 assert row['id'] in ('S01','S02','S03','S04','S05','S06','S07','S08')
 assert 1<=len(row['text'])<=60
 guard.metadata(args,allow_background=True)
 remaining=min(20000,int((total_deadline-time.monotonic())*1000));assert remaining>2000
 request=dict(protocol_version=1,request_id=uuid.uuid4().hex,board_boot_id=boot,
  session_id=session,generation=1,budget_ms=remaining,text=row['text'])
 owner=Owner.from_dict(request)
 try:
  response=client.request('tts',request,deadline=time.monotonic()+remaining/1000,cancelled=lambda:False)
  assert response['ok'] is True
  pcm,rate=decode_audio(response['result']['audio']);assert rate==24000
  pcm16,_=audioop.ratecv(pcm,2,1,24000,16000,None)
  assert 0<len(pcm16)<=20*16000*2 and len(pcm16)%2==0
  path=directory/(row['id']+'.wav')
  with path.open('xb') as out:
   with wave.open(out,'wb') as writer:
    writer.setnchannels(1);writer.setsampwidth(2);writer.setframerate(16000);writer.writeframes(pcm16)
  rows.append(dict(id=row['id'],reference_text=row['text'],wav_path=str(path),
   sha256=hashlib.sha256(path.read_bytes()).hexdigest(),samples=len(pcm16)//2,rate=16000,
   critical_spans=row['critical_spans'],intended_not_human_verified=True))
 finally:
  client.cancel(owner)
manifest=dict(schema_version=1,public_synthetic=True,intended_not_human_verified=True,
 source_texts_sha256=TEXT_SHA,tts='omnivoice',num_step=16,resampling='audioop.ratecv 24000 to 16000 mono PCM16 on board',
 microphone_opened=False,audio_played=False,production_store_accessed=False,execute_recognized_commands=False,cases=rows)
raw=(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
manifest_path=directory/'manifest.json'
with manifest_path.open('xb') as out:out.write(raw)
after=guard.metadata(args,allow_background=True)
assert before['ui']==after['ui'] and before['camera']==after['camera']
print(json.dumps(dict(status='PUBLIC_SYNTHETIC_FIXTURES_CREATED',board_manifest_path=str(manifest_path),
 board_manifest_sha256=hashlib.sha256(raw).hexdigest(),manifest=manifest,before=before,after=after,
 production_configuration_changed=False,model_weights_changed=False)))
'''

if __name__ == '__main__':
    source = HERE / 'quality/synthetic_acceptance_texts.json'
    raw = source.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == TEXT_SHA
    cases = json.loads(raw)['cases']
    spec = json.loads((HERE.parent.parent / 'production_business_acceptance/spec.json').read_text(encoding='utf-8'))
    run_id = uuid.uuid4().hex[:16]
    header = 'EXPECTED=' + repr(spec['startup_sha256']) + '\nTEXT_SHA=' + repr(TEXT_SHA) + '\nRUN_ID=' + repr(run_id) + '\nCASES=' + repr(cases) + '\n'
    value = json.loads(ssh('python3 -B -', header + REMOTE, timeout=150))
    output = HERE / ('actual_fixture_generation_' + run_id + '.json')
    with output.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print(json.dumps(dict(status=value['status'],board_manifest_path=value['board_manifest_path'],board_manifest_sha256=value['board_manifest_sha256'],
                         cases=[dict(id=row['id'],samples=row['samples']) for row in value['manifest']['cases']],output=str(output))))
