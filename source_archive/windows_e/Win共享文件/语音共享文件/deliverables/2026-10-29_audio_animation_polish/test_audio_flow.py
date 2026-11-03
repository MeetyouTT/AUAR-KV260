"""Meaningful IPC backpressure, PCM preservation and interruption safety checks."""
import base64,errno,io,json,time
from types import SimpleNamespace
import pytest
from tools.gstreamer_audio_worker import NonBlockingAudioPublisher
from tools.gstreamer_persistent_engine import PersistentGstAudioEngine
from tests.framework import test_persistent_audio as persistent_fixtures
from tools.barge_in_capture import BargeInCapture
from tests.framework import test_voice_barge_in as barge
def state(n):return dict(kind='state',token=n,clock=n/50,ready=True)
def reference(n,at=0):return dict(kind='reference',sequence=n,at=at,pcm=base64.b64encode(b'\x10\x00'*480).decode())
def rows(raw):return [json.loads(line[6:]) for line in raw.decode().splitlines()]
def test_full_pipe_returns_without_wait_and_retains_only_latest_clock():
 def blocked(*args):raise BlockingIOError(errno.EAGAIN,'controlled full pipe')
 p=NonBlockingAudioPublisher(clock=lambda:0,write=blocked,configure_fd=False)
 p.publish(state(1));p.flush()
 start=time.monotonic()
 for n in range(2,100):
  p.publish(state(n));p.publish(reference(n));p.flush()
 assert time.monotonic()-start<.5 and len(p.references)<=8 and p.state['token']==99
 assert p.blocked_writes>0 and p.coalesced_states>0 and p.dropped_references>0
def test_partial_writes_keep_valid_lines_and_never_splice_different_owners():
 raw=bytearray()
 def write(fd,data):raw.extend(data[:7]);return min(7,len(data))
 p=NonBlockingAudioPublisher(clock=lambda:0,write=write,configure_fd=False)
 p.publish(state(3));p.flush();p.publish(state(4));p.publish(reference(1))
 for _ in range(50):p.flush()
 decoded=rows(raw)
 assert [r['token'] for r in decoded if r['kind']=='state']==[3,4]
 assert [r['sequence'] for r in decoded if r['kind']=='reference']==[1]
def test_fresh_clocks_are_not_starved_by_permanent_echo_reference_stream():
 raw=bytearray()
 def write(fd,data):raw.extend(data);return len(data)
 p=NonBlockingAudioPublisher(clock=lambda:0,write=write,configure_fd=False)
 for n in range(8):p.publish(reference(n))
 p.publish(state(8));p.flush();decoded=rows(raw)
 assert next(i for i,row in enumerate(decoded) if row['kind']=='state')<=2
 assert [r['sequence'] for r in decoded if r['kind']=='reference']==list(range(8))
def test_stale_reference_is_dropped_with_its_sequence_never_relabelled():
 raw=bytearray()
 def write(fd,data):raw.extend(data);return len(data)
 p=NonBlockingAudioPublisher(clock=lambda:.1,write=write,configure_fd=False)
 p.publish(reference(1,0));p.publish(reference(2,.08));p.flush()
 assert [r['sequence'] for r in rows(raw)]==[2] and p.dropped_references==1
def test_peer_disconnect_is_observable_without_blocking_audio_tick():
 def write(*args):raise BrokenPipeError(errno.EPIPE,'controlled closed peer')
 p=NonBlockingAudioPublisher(write=write,configure_fd=False);p.publish(state(1));p.flush()
 assert p.broken and p.snapshot()['broken_pipe']
def test_new_diagnostics_preserve_existing_pcm_and_sink_clock_contract():
 case=persistent_fixtures.PersistentTests();case.setUp()
 try:
  case.play(1);assert case.engine.queued_samples==4800
  case.advance(.4);assert case.engine.done and case.engine.queued_samples==0
  assert b''.join(buffer.pcm for buffer in case.pushes if any(buffer.pcm))==case.pcm
  assert case.engine.position==.2 and case.engine.snapshot()['max_poll_gap_ms']>=0
 finally:case.doCleanups()
def test_late_audio_poll_is_measured_without_skipping_content():
 case=persistent_fixtures.PersistentTests();case.setUp()
 try:
  case.play(1);case.advance(.1)
  case.now+=250000000;case.sink_time=case.now;case.engine.poll();case.advance(.4)
  assert case.engine.snapshot()['max_poll_gap_ms']>=250 and case.engine.turn_late_rebases>=1
  assert b''.join(buffer.pcm for buffer in case.pushes if any(buffer.pcm))==case.pcm
 finally:case.doCleanups()
def test_reference_gap_ends_only_monitor_and_never_authorizes_interruption():
 cap=BargeInCapture(SimpleNamespace(),echo_factory=lambda:None,verifier=None)
 cap._capture_timer();cap.echo=barge.EchoStub();cap.echo.reference_gaps=1
 calls=[];cap.on_speech_start=lambda:calls.append(True)
 try:
  with pytest.raises(RuntimeError,match='reference discontinuity'):
   cap._read_pcm(SimpleNamespace(stdout=io.BytesIO(b'\x00\x00'*320)))
  assert not calls
 finally:cap.close()
def test_full_native_appsrc_retains_pcm_until_real_room_returns():
 case=persistent_fixtures.PersistentTests();case.setUp()
 try:
  case.play(1);case.engine.source.get_property=lambda name:7680
  case.advance(.2);assert case.engine.queued_samples==4800 and not case.engine.ready
  case.engine.source.get_property=lambda name:0
  case.advance(.4)
  assert case.engine.done and b''.join(buffer.pcm for buffer in case.pushes if any(buffer.pcm))==case.pcm
 finally:case.doCleanups()
def test_invalid_native_queue_level_keeps_existing_fail_closed_guard():
 case=persistent_fixtures.PersistentTests();case.setUp()
 try:
  case.engine.source.get_property=lambda name:'invalid'
  case.advance(.1)
  assert not case.engine.device_ready and not case.engine.active and 'queue query failed' in case.engine.error
 finally:case.doCleanups()
