"""One public board-Ethernet fixed27B -> RAM OmniVoice case, no Store/devices."""
import hashlib
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[3]
sys.path[:0]=[str(HERE),str(PROJECT/'deliverables/2026-10-18_board_dialogue')]
from board_ssh import ssh
import manage
from production_runtime import write_json,utc

REMOTE=r'''
import hashlib,http.client,json,signal,sys,threading,time,uuid
from pathlib import Path
signal.alarm(75)
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
assert boot=='8100a7fd-0c6a-46c4-82b8-f874988a1521'
code=Path('/home/root/aura-board-owner-candidate-20261030/resume-730de9634b8daa07/code')
pins={
 'board/__init__.py':'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
 'board/runtime/__init__.py':'e872d26327cffcd548d40793547880be7ed91b97c93b361fdcff3709f8f3f695',
 'common/__init__.py':'9194622c40cccdf5c8db07fd11f4c472fcba36cfb935e5ab04396fe51b818cfe',
 'common/model_inference_wire.py':'0786eb20e13b88c59572cde507532d760cd7d2eb24434e904845e73be99d7255',
 'board/runtime/board_dialogue_client.py':'38220eb34939e63b3ebcff4ccef4d8b3ddefb22ce74c98f9224244894dad44f6',
 'common/board_timeline_clock.py':'93b65ec3d9ca393b32499845297c78a2f1f71bc19e069b2ce3dc6f69e795af02'}
for relative,expected in pins.items():assert hashlib.sha256((code/relative).read_bytes()).hexdigest()==expected
sys.path.insert(0,str(code))
from board.runtime.board_dialogue_client import InferenceHttpClient
from common.model_inference_wire import Owner,decode_audio
profile_path=Path('/home/root/aura-character-xuefei-20261030/f94fca2c94288acb/runtime/aura/config/character_profile.local.json')
raw_profile=profile_path.read_bytes()
assert hashlib.sha256(raw_profile).hexdigest()=='5dcac93339a56c549ef176e260b4ed7f01fdc3307059c53aa3784b7a382f09c3'
profile=json.loads(raw_profile);prompt=profile['persona_full_prompt']
assert profile['profile_version']=='xuefei-yuki-board-v1-candidate'
assert len(prompt.encode())==978 and hashlib.sha256(prompt.encode()).hexdigest()=='11b1b4d04c55ac110969fd5dd7ffb37f29b29bbc26d9c7906e454d4f69af654e'

def health():
 c=http.client.HTTPConnection('192.168.50.1',8797,timeout=2)
 try:
  c.connect();assert c.sock.getpeername()==('192.168.50.1',8797)
  c.request('GET','/health',headers={'Connection':'close'})
  r=c.getresponse();raw=r.read(65537)
  assert r.status==200 and len(raw)<=65536 and r.getheader('Content-Type','').split(';')[0]=='application/json'
  v=json.loads(raw)
  assert v['protocol_version']==1 and v['ok'] is True and v['role']=='model_inference_only'
  assert v['backend']['model']=='aura-qwen3.8-27b-abliterated:iq4_xs'
  assert v['backend']['tts']=='omnivoice' and v['backend']['num_step']==16 and v['backend']['tts_ready'] is True
  assert v['backend']['gpu_coordination']['enforcing'] is True
  return v
 finally:c.close()

before=health()
assert before['active'] is False and before['pending']==0,'Another production request is active; no inference sent'
client=InferenceHttpClient('192.168.50.1',8797)
session='public-name-'+uuid.uuid4().hex
def body(kind):
 v=dict(protocol_version=1,request_id=uuid.uuid4().hex,board_boot_id=boot,session_id=session,generation=1,budget_ms=60000)
 if kind=='llm':v.update(task='dialogue',messages=[dict(role='system',content=prompt),dict(role='user',content='你叫什么名字？')],options=dict(think=False,num_predict=120))
 return v
deadline=time.monotonic()+60.
llm=body('llm');llm_owner=Owner.from_dict(llm)
response=client.request('llm',llm,deadline=deadline)
assert response['ok'] is True
reply=json.loads(response['result']['text'])
assert set(reply)=={'reply_text','emotion','avatar_action'}
text=reply['reply_text']
assert isinstance(text,str) and 1<=len(text.strip())<=48 and all(ord(c)>=32 for c in text)
assert '雪妃' in text and '汐蓝' not in text and '<think' not in text.lower() and text.strip()!='你叫什么名字？'
assert reply['emotion'] in ('neutral','friendly','happy','sad') and reply['avatar_action']==''
tts=body('tts');tts['text']=text.strip();tts_owner=Owner.from_dict(tts)
response=client.request('tts',tts,deadline=deadline)
assert response['ok'] is True
audio=response['result']['audio'];pcm,rate=decode_audio(audio)
assert rate==24000 and audio['encoding']=='pcm_s16le' and audio['channels']==1
assert len(pcm)==audio['samples']*2 and audio['samples']>0
assert hashlib.sha256(pcm).hexdigest()==audio['sha256']
audio_sha,audio_samples=audio['sha256'],audio['samples']
# Completed owner cancellation is explicit and idempotent. It never adopts an
# old result. No playing-plan, audio device or Store was created in this case.
cancellations=[]
for owner in (llm_owner,tts_owner):
 cancelled=client.cancel(owner)
 assert cancelled and cancelled['ok'] is True and cancelled['result']==dict(cancelled=False,state='completed')
 cancellations.append(dict(request_id=owner.request_id,state=cancelled['result']['state']))
# The same tested client must reject a pre-cancelled transport before any new
# connection/inference; this is not an additional model case or generation.
def forbidden_connection(*args,**kwargs):raise AssertionError('Cancelled request must not connect')
blocked=InferenceHttpClient('192.168.50.1',8797,connection_factory=forbidden_connection)
try:blocked.request('tts',tts,deadline=deadline,cancelled=lambda:True)
except InterruptedError:pre_cancelled=True
else:raise AssertionError('Pre-cancelled request was sent')
assert not client._connections and not blocked._connections
response.clear();audio.clear();pcm=None
after=health()
assert after['active'] is False and after['pending']==0 and after['backend']['tts_ready'] is True
assert after['counts'].get('accepted_llm',0)-before['counts'].get('accepted_llm',0)==1
assert after['counts'].get('accepted_tts',0)-before['counts'].get('accepted_tts',0)==1
signal.alarm(0)
print(json.dumps(dict(status='PASS_ONE_PUBLIC_BOARD_ETHERNET_27B_RAM_TTS_CHAIN',public_reply=text.strip(),
 reply_emotion=reply['emotion'],reply_action=reply['avatar_action'],pcm_sha256=audio_sha,pcm_samples=audio_samples,
 sample_rate=rate,channels=1,encoding='pcm_s16le',stream_owner=dict(board_boot_id=boot,session_id=session,generation=1,
 llm_request_id=llm_owner.request_id,tts_request_id=tts_owner.request_id),
 completed_request_cancellation=cancellations,pre_cancelled_request_not_sent=pre_cancelled,
 cancellation_scope='completed-owner idempotent cleanup plus pre-send cancellation; no active GPU interruption claimed',
 profile_version=profile['profile_version'],prompt_bytes=978,prompt_sha256=profile['persona_prompt_sha256'],
 fixed_model=after['backend']['model'],tts='omnivoice',num_step=after['backend']['num_step'],
 gpu_enforcing=True,scheduler_idle_after=True,model_inference_requests=2,private_store_accessed=False,
 asr_called=False,board_model_loaded=False,audio_device_opened=False,audio_played=False,pcm_archived=False,
 services_restarted=False,performance_benchmark=False),ensure_ascii=True))
'''


def main():
    record,state=manage.latest()
    assert record and state['status']=='READY' and manage.same_owner(record)
    bound=dict(host_session_id=record['session_id'],launcher=record['owner'],main_pid=state['pid'],
        tts_pid=state['same_unique_tts_pid'],fixed_daemon_pid=state['fixed_daemon_pid'])
    remote=json.loads(ssh('python3 -B -',REMOTE,timeout=90))
    after,after_state=manage.latest()
    assert after==record and manage.same_owner(record)
    assert after_state['same_unique_tts_pid']==bound['tts_pid'] and after_state['pid']==bound['main_pid']
    result=dict(recorded_utc=utc(),model_owner_binding=bound,**remote)
    write_json(HERE/'actual_public_board_name_chain.json',result)
    print(json.dumps(dict(output=str(HERE/'actual_public_board_name_chain.json'),**result),ensure_ascii=True))


if __name__=='__main__':main()
