"""Portrait ownership, wire bounds, cancellation, freshness and unique delivery."""
import json
import socket
import struct
import threading
import time
from types import SimpleNamespace
import pytest
from common import portrait_wire as wire
from board.runtime.portrait_offload import PortraitOffload
from tools.portrait_host import PortraitServer

def request(**changes):
    value=dict(protocol=wire.PROTOCOL,kind='render',session='test-session',generation=1,sequence=1,
        state='SPEAKING_NEUTRAL',clock=1.,gain=.5,level=.5,idle_gain=1.,emotion='neutral',characters=10,
        audio_sample=24000,track='answer',width=8,height=8,revision='test-revision')
    return dict(value,**changes)

def response(plan):
    value={k:plan[k] for k in ('session','generation','sequence','state','clock','audio_sample','track','revision','width','height')}
    value.update(protocol=wire.PROTOCOL,kind='frame',asset='idle_normal',index=1,display_state=plan['state'],
        transitioning=False,mouth_level=.5,speech_gain=.5,burst_finished=False,render_ms=1.)
    return value,b'\x11\x22\x33'*(plan['width']*plan['height'])

def until(predicate,seconds=2):
    end=time.monotonic()+seconds
    while time.monotonic()<end:
        if predicate():return
        time.sleep(.003)
    raise AssertionError('Portrait operation did not settle')

@pytest.mark.parametrize('change',[
    {'generation':True},{'clock':float('nan')},{'gain':1.01},{'level':-.1},{'idle_gain':3},
    {'characters':8001},{'audio_sample':-1},{'track':'other'},{'width':0},{'height':601},
    {'state':'EXECUTE'},{'session':'../private'},{'revision':''},{'sequence':0},{'filename':'private'},
])
def test_invalid_plan_is_rejected(change):
    with pytest.raises(ValueError):wire.plan(request(**change))

def test_rgb_round_trip_has_bounded_metadata_and_exact_payload():
    a,b=socket.socketpair()
    try:
        value,pixels=response(request());wire.send(a,value,pixels);header,body=wire.receive(b,192)
        assert wire.frame(header,body,request())==value and body==pixels
    finally:a.close();b.close()

@pytest.mark.parametrize('field,value',[
    ('generation',2),('session','old-session'),('state','IDLE'),('track','feedback'),
    ('sequence',2),('clock',0.),('width',9),('revision','old-revision'),('audio_sample',1),
])
def test_old_or_mismatched_frame_owner_is_rejected(field,value):
    header,pixels=response(request());header[field]=value
    with pytest.raises(ValueError):wire.frame(header,pixels,request())

@pytest.mark.parametrize('raw',[
    struct.pack('!I',wire.MAX_HEADER+1),
    struct.pack('!I',0),
])
def test_oversized_header_rejected_before_body_allocation(raw):
    a,b=socket.socketpair()
    try:
        a.sendall(raw)
        with pytest.raises(ValueError):wire.receive(b)
    finally:a.close();b.close()

def test_crc_and_duplicate_json_fields_are_rejected():
    for header,body in ((b'{"payload_bytes":1,"crc32":"00000000"}',b'x'),
                        (b'{"payload_bytes":0,"payload_bytes":0,"crc32":"00000000"}',b'')):
        a,b=socket.socketpair()
        try:
            a.sendall(struct.pack('!I',len(header))+header+body)
            with pytest.raises(ValueError):wire.receive(b)
        finally:a.close();b.close()

class Renderer:
    revision='test-revision';size=(8,8)
    def __init__(self):self.delay=0.;self.entered=threading.Event()
    def render(self,plan):
        self.entered.set()
        if self.delay:time.sleep(self.delay)
        return response(plan)

@pytest.fixture
def rig():
    renderer=Renderer();server=PortraitServer(('127.0.0.1',0),renderer)
    thread=threading.Thread(target=server.serve_forever,kwargs={'poll_interval':.01},daemon=True);thread.start()
    client=PortraitOffload({'host':'192.168.50.1','port':8796,'revision':'test-revision','max_age_ms':100},(8,8),
        connect=lambda address,timeout:socket.create_connection(server.server_address,timeout=timeout))
    core=SimpleNamespace(talk_gen=1,fsm=SimpleNamespace(state=SimpleNamespace(label='SPEAKING_NEUTRAL')),
                         idle_gain=1.,emotion='neutral',reply_text='test')
    yield client,renderer,server,core
    client.close();server.shutdown();server.server_close();thread.join(1)

def offer(client,core,sample=24000,track='answer'):
    return client.offer(core,1.,.5,.5,sample,track)

def test_async_result_is_consumed_once_and_wait_never_repeats_pixels(rig):
    client,renderer,server,core=rig
    assert offer(client,core) is None
    until(lambda:client.status()['accepted']>0)
    frame=offer(client,core);assert len(frame['_portrait_rgb'])==192
    # Hold the condition so the receiver cannot publish the next response.
    with client.condition:assert offer(client,core)=={'_portrait_wait':True}

def test_state_generation_and_track_changes_clear_previous_pixels(rig):
    client,renderer,server,core=rig
    offer(client,core);until(lambda:client.status()['accepted']>0)
    assert '_portrait_rgb' in offer(client,core)
    renderer.delay=.2
    core.talk_gen=2
    assert offer(client,core) is None
    core.fsm.state.label='IDLE'
    assert offer(client,core) is None
    assert offer(client,core,track='feedback') is None

def test_pcm_position_going_back_cannot_use_future_pixels(rig):
    client,renderer,server,core=rig
    offer(client,core);until(lambda:client.status()['accepted']>0)
    assert offer(client,core,sample=0) is None

def test_total_rpc_timeout_falls_back_and_closes_worker(rig):
    client,renderer,server,core=rig;renderer.delay=.3
    began=time.perf_counter();offer(client,core)
    until(lambda:client.status()['failures']>0)
    assert time.perf_counter()-began<.5 and client.status()['mode']=='local'
    assert offer(client,core) is None

def test_disable_and_cancel_drop_inflight_response_without_waiting(rig):
    client,renderer,server,core=rig;renderer.delay=.2
    offer(client,core);assert renderer.entered.wait(1)
    old=client.session;began=time.perf_counter();client.set_enabled(False)
    assert time.perf_counter()-began<.05 and client.session!=old
    assert offer(client,core) is None and client.status()['mode']=='disabled'
    client.set_enabled(True);assert offer(client,core) is None

def test_host_health_does_not_acquire_or_replace_renderer(rig):
    client,renderer,server,core=rig
    with socket.create_connection(server.server_address,timeout=1) as connection:
        wire.send(connection,{'protocol':wire.PROTOCOL,'kind':'health'});header,payload=wire.receive(connection,0)
    assert header['ready'] and not payload and server.frames==0

def test_cancelled_rpc_is_not_counted_as_network_failure(rig):
    client,renderer,server,core=rig;renderer.delay=.2
    offer(client,core);assert renderer.entered.wait(1)
    client.set_enabled(False)
    until(lambda:client.connection is None)
    assert client.status()['failures']==0

def test_only_supported_frame_rates_are_accepted(rig):
    client,renderer,server,core=rig
    for value in (True,0,10,25,24.):
        with pytest.raises(ValueError):client.set_fps(value)
    assert client.set_fps(16)=={'fps':16} and client.target_fps==16

def test_repeated_failures_do_not_restart_the_local_animation_clock(rig):
    client,renderer,server,core=rig;renderer.delay=.3;resets=[]
    core.reset_playback=lambda:resets.append(True)
    offer(client,core)
    client.reset_local_if_needed(core);assert len(resets)==1
    def failed_twice():
        offer(client,core);client.reset_local_if_needed(core)
        return client.status()['failures']>=2
    until(failed_twice)
    client.reset_local_if_needed(core);assert len(resets)==1

def test_new_frames_do_not_bypass_network_retry_backoff(rig):
    client,renderer,server,core=rig;attempts=[]
    def offline(address,timeout):
        attempts.append(time.monotonic());raise ConnectionRefusedError('test outage')
    client.connect=offline;began=time.monotonic()
    while time.monotonic()-began<.25:
        offer(client,core);time.sleep(.004)
    assert len(attempts)==1

def test_held_frame_is_dropped_after_internal_audio_generation_change():
    from tools.board_avatar_worker import FramePresenter
    class Sink:
        def __init__(self):self.calls=[]
        def push(self,*args):self.calls.append(args)
    sink=Sink();generation=[(1,1,'first')];guard=threading.Condition()
    presenter=FramePresenter(sink,lambda:generation[0],guard)
    try:
        presenter.offer(b'old',1,generation[0],time.monotonic()+.05)
        with guard:generation[0]=(1,2,'second')
        until(lambda:presenter.read()['dropped']==1)
        assert not sink.calls
    finally:presenter.close()

def test_remote_frame_cannot_expire_while_waiting_for_native_handoff():
    from tools.board_avatar_worker import FramePresenter
    calls=[]
    sink=SimpleNamespace(push=lambda *args:calls.append(args));guard=threading.Condition()
    presenter=FramePresenter(sink,lambda:1,guard)
    try:
        presenter.offer(b'expiring',1,1,time.monotonic()+.05,expires=time.monotonic()+.02)
        until(lambda:presenter.read()['expired']==1)
        assert not calls and presenter.read()['dropped']==1
    finally:presenter.close()

def test_remote_pixels_do_not_receive_a_second_local_render_hold():
    from tools.board_avatar_worker import AvatarRenderWorker
    class Controller:
        phase='IDLE';last_error=''
        def __init__(self):
            self.sequence=0;self.core=SimpleNamespace(talk_gen=1,fsm=SimpleNamespace(state=SimpleNamespace(label='IDLE')))
            self.portrait_offload=SimpleNamespace(target_fps=12,session='test',status=lambda:{'mode':'remote'},close=lambda:None)
        def tick(self):
            self.sequence+=1
            return {'_portrait_rgb':b'\x11\x22\x33'*64,'_portrait_sequence':self.sequence,'_portrait_expires':time.monotonic()+.04}
        def public(self):return {'phase':'IDLE','error':self.last_error}
        def cancel(self):pass
    calls=[];controller=Controller();sink=SimpleNamespace(push=lambda *args:calls.append(time.monotonic()))
    worker=AvatarRenderWorker(controller,'white',(8,8),1/24,native_video=sink,visual_fps=12)
    try:
        until(lambda:len(calls)>=3)
        assert not controller.last_error and worker.presenter.read()['expired']==0
    finally:worker.close()
