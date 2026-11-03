"""Fault-injected handoff tests use fake inference, real local HTTP and no devices."""
import hashlib,http.client,io,json,socket,threading,time,wave
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import patch
import pytest
from common.voice_admission import acquire_turn,disconnected,RequestDiagnostics
from common.asr_wire import encode_context
from tools.asr_server import AsrServer
from tools.board_model_host import ModelHandler
from tools.voice_channel_source import channel_frames
from common.voice_channel import read_frame
PCM=b'\x00\x08'*3200
def meta(name='probe',budget=5000):
 return {'protocol':'aura-asr-1','board_boot_id':'synthetic-handoff','session_id':'synthetic-session',
  'request_id':name,'generation':1,'capture_id':'synthetic-public','sample_count':len(PCM)//2,
  'pcm_sha256':hashlib.sha256(PCM).hexdigest(),'budget_ms':budget}
@contextmanager
def peers():
 a,b=socket.socketpair()
 try:yield a,b
 finally:a.close();b.close()
def test_free_owner_has_no_added_sleep():
 with peers() as (a,b):
  lock=threading.Lock();status,elapsed=acquire_turn(lock,a,time.monotonic()+1)
  assert status=='acquired' and elapsed<50 and lock.locked();lock.release()
def test_replacement_waits_for_cleanup_instead_of_rejection():
 with peers() as (a,b):
  lock=threading.Lock();lock.acquire();timer=threading.Timer(.12,lock.release);timer.start()
  try:
   status,elapsed=acquire_turn(lock,a,time.monotonic()+1)
   assert status=='acquired' and 80<=elapsed<600;lock.release()
  finally:timer.join()
def test_overload_wait_is_bounded_and_does_not_take_owner():
 with peers() as (a,b):
  lock=threading.Lock();lock.acquire()
  status,elapsed=acquire_turn(lock,a,time.monotonic()+1,max_wait=.07)
  assert status=='busy' and 50<=elapsed<400 and lock.locked();lock.release()
def test_original_budget_wins_over_handoff_wait():
 with peers() as (a,b):
  lock=threading.Lock();lock.acquire()
  status,elapsed=acquire_turn(lock,a,time.monotonic()+.06)
  assert status=='expired' and elapsed<300 and lock.locked();lock.release()
def test_disconnected_waiter_never_acquires_or_transcribes():
 with peers() as (a,b):
  lock=threading.Lock();lock.acquire();timer=threading.Timer(.05,b.close);timer.start()
  try:
   status,elapsed=acquire_turn(lock,a,time.monotonic()+1)
   assert status=='cancelled' and elapsed<400 and lock.locked()
  finally:lock.release();timer.join()
def test_already_closed_peer_leaves_available_owner_free():
 with peers() as (a,b):
  b.close();lock=threading.Lock()
  assert acquire_turn(lock,a,time.monotonic()+1)[0]=='cancelled' and not lock.locked()
def test_expired_request_never_takes_available_owner():
 with peers() as (a,b):
  lock=threading.Lock()
  assert acquire_turn(lock,a,time.monotonic()-.1)[0]=='expired' and not lock.locked()
def test_peek_does_not_consume_pipelined_input():
 with peers() as (a,b):
  b.sendall(b'G');assert disconnected(a) is False;assert a.recv(1)==b'G'
def test_diagnostics_are_bounded_and_do_not_copy_speech_or_identity():
 journal=RequestDiagnostics()
 for n in range(100):
  journal.record({**meta(str(n)),'user':'private words','profile':'private name'},'accepted',characters=13,wait_ms=1)
 value=journal.public()
 assert len(value['recent'])==16 and value['counts']['accepted']==100
 assert 'private' not in json.dumps(value) and value['speech_stored'] is False
@contextmanager
def fake_server(serve=None,transcript='汐蓝，你好'):
 calls=[];model=SimpleNamespace(lock=threading.Lock(),request_diagnostics=RequestDiagnostics())
 def transcribe(pcm):calls.append(pcm);return transcript
 server=AsrServer(('127.0.0.1',0),SimpleNamespace(model_id='FAKE_ASR',transcribe=transcribe),handler=ModelHandler)
 server.models=model
 def reply(handler,*args,**kw):handler.send(200,{'ok':True})
 with patch('tools.device_client.command',return_value=None),patch('tools.voice_channel_source.serve_channel',serve or reply):
  thread=threading.Thread(target=server.serve_forever,kwargs={'poll_interval':.02},daemon=True);thread.start()
  try:yield server,model,calls
  finally:server.shutdown();server.server_close();thread.join(2)
def request(server,name='probe',budget=5000,entry=None):
 c=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=6)
 headers={'Content-Type':'application/octet-stream','X-Aura-Asr':encode_context(meta(name,budget))}
 if entry:headers['X-Aura-Entry']=entry
 c.request('POST','/v1/voice/channel',PCM,headers);return c
def test_http_new_turn_survives_old_socket_cleanup_and_executes_once():
 entered=threading.Event();cleanup=threading.Event()
 def serve(handler,context,*args,**kw):
  if context['request_id']=='first':
   handler.send_response(200);handler.send_header('Content-Length','0');handler.end_headers();entered.set()
   handler.connection.recv(1);cleanup.set();time.sleep(.2)
  else:handler.send(200,{'ok':True})
 with fake_server(serve) as (server,model,calls):
  first=request(server,'first');first.getresponse().read();assert entered.wait(1);first.close()
  assert cleanup.wait(1)
  second=request(server,'second');response=second.getresponse();assert response.status==200;response.read();second.close()
  assert len(calls)==2
  row=next(r for r in model.request_diagnostics.public()['recent'] if r['request_id']=='second')
  assert row['outcome']=='accepted' and row['admission_wait_ms']>=100
def test_http_busy_returns_explicit_reason_without_extra_inference():
 with fake_server() as (server,model,calls):
  model.lock.acquire()
  try:
   c=request(server,budget=10000);response=c.getresponse();body=json.loads(response.read());c.close()
   assert response.status==503 and body['code']=='voice_busy' and not calls
  finally:model.lock.release()
def test_http_short_budget_expires_without_inference():
 with fake_server() as (server,model,calls):
  model.lock.acquire()
  try:
   c=request(server,budget=500);response=c.getresponse();body=json.loads(response.read());c.close()
   assert response.status==504 and body['code']=='voice_budget_expired' and not calls
  finally:model.lock.release()
def test_http_wake_rejection_stays_distinct_from_service_busy():
 with fake_server(transcript='普通背景说话') as (server,model,calls):
  c=request(server,entry='wake-word-v1');response=c.getresponse();body=json.loads(response.read());c.close()
  assert response.status==422 and body['code']=='entry_rejected' and len(calls)==1
  assert model.request_diagnostics.public()['recent'][-1]['outcome']=='wake_word_not_detected'
def test_http_wake_only_returns_no_llm_and_explicit_diagnostic():
 with fake_server(transcript='汐蓝') as (server,model,calls):
  c=request(server,entry='wake-word-v1');response=c.getresponse();response.read();c.close()
  assert response.status==204 and model.request_diagnostics.public()['recent'][-1]['outcome']=='wake_only'
def test_closed_http_waiter_is_dropped_before_inference():
 with fake_server() as (server,model,calls):
  model.lock.acquire()
  try:
   c=request(server);time.sleep(.04);c.close()
   until=time.monotonic()+1
   while time.monotonic()<until and not model.request_diagnostics.public()['recent']:time.sleep(.01)
   assert model.request_diagnostics.public()['recent'][-1]['outcome']=='cancelled'
   assert not calls
  finally:model.lock.release()
class SlowStream:
 def __init__(self,quiet=False):self.closed=threading.Event();self.quiet=quiet
 def __iter__(self):
  if self.quiet:self.closed.wait(2)
  if not self.closed.is_set():
   yield 'text','这是一段用于检查取消是否及时生效的完整回复。'
   yield 'complete',{'reply_text':'这是一段用于检查取消是否及时生效的完整回复。','emotion':'neutral','avatar_action':''}
 def cancel(self):self.closed.set()
@pytest.mark.parametrize('feedback',[False,True])
def test_disconnect_finishes_only_started_tts_then_discards_it_without_retiring_worker(tmp_path,feedback):
 cancelled=threading.Event();tts_started=threading.Event();calls=[];stream=SlowStream()
 def bounded(text,*,deadline,cancelled,request_id):
  tts_started.set();time.sleep(.15)
  assert not cancelled.is_set(), 'Client disconnect must not retire the warm worker'
  path=tmp_path/'public.wav'
  with wave.open(str(path),'wb') as audio:
   audio.setparams((1,2,24000,0,'NONE','not compressed'));audio.writeframes(b'\x01\x00'*2400)
  return {'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
 voice=SimpleNamespace(generate_bounded=bounded,cancel_request=lambda request:calls.append(request))
 models=SimpleNamespace(histories={},voice=voice)
 def end_peer():
  assert tts_started.wait(1);cancelled.set()
 timer=threading.Thread(target=end_peer);timer.start();began=time.monotonic()
 with patch('tools.voice_channel_source.route',return_value={'mode':'reasoning','reason':'synthetic','feedback_after_ms':50}):
  packets=list(channel_frames(models,meta(),'测试',4,model='fixture',host='fixture',stream_factory=lambda *a,**k:stream,is_cancelled=cancelled.is_set,feedback=feedback))
 timer.join(1)
 kinds=[read_frame(io.BytesIO(p))[0]['kind'] for p in packets]
 assert .1<=time.monotonic()-began<.8 and not calls and stream.closed.is_set()
 assert 'error' in kinds and 'audio' not in kinds and 'end' not in kinds and 'thinking' not in kinds
def test_disconnect_during_silent_llm_releases_stream_promptly():
 cancelled=threading.Event();stream=SlowStream(quiet=True);timer=threading.Timer(.05,cancelled.set)
 models=SimpleNamespace(histories={},voice=SimpleNamespace());timer.start();began=time.monotonic()
 try:packets=list(channel_frames(models,meta(),'测试',4,model='fixture',host='fixture',stream_factory=lambda *a,**k:stream,is_cancelled=cancelled.is_set))
 finally:timer.join()
 assert time.monotonic()-began<.8 and stream.closed.is_set()
 kinds=[read_frame(io.BytesIO(p))[0]['kind'] for p in packets]
 assert 'error' in kinds and 'audio' not in kinds and 'end' not in kinds
