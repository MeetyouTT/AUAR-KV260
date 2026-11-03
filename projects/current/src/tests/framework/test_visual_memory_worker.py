"""Board visual-memory assembly with synthetic sources and real loopback HTTP."""
import copy
from contextlib import nullcontext
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import sqlite3
import threading
import time
from types import SimpleNamespace

import pytest

from board.runtime.visual_memory import (CameraHealthError,CameraHealthReader,
    CameraHealthSample,MAX_CAMERA_HEALTH_BYTES,VisualTimelineWorker,_projection)
from common.board_memory import BoardMemoryStore
from common.board_timeline_clock import ClockUnavailable


def health(frame=1,count=1,**changes):
    value = dict(board_boot_id='boot',service_epoch='service',camera_epoch='camera',
        role='DPU_YOLOX_PERSON_PREVIEW',detector={'count_kind':'people','PRIVATE':'private-model-field'},
        observation_frame_id=frame,people_count=count,observation_age_ms=10,capture_age_ms=5,
        camera_error='',detector_error='',timestamp_kind='appsink_dequeue_monotonic',
        identity={'person_id':'PRIVATE_ID','template':'PRIVATE_TEMPLATE'},jpeg_base64='PRIVATE_IMAGE')
    value.update(changes)
    return value


class Mono:
    value = 1.
    def __call__(self):
        return self.value


class Timeline:
    def __init__(self,clock):
        self.boot_id,self.monotonic,self.anchored = 'boot',clock,True
    def event_time(self):
        if not self.anchored:
            raise ClockUnavailable('synthetic_initial_anchor_missing')
        return 10000+self.monotonic()


class FixtureReader:
    source_kind = 'fixture'
    def __init__(self,clock):
        self.clock,self.next,self.calls,self.closed = clock,health(),0,False
    def read(self,**kwargs):
        self.calls += 1
        if isinstance(self.next,Exception):
            raise self.next
        now = self.clock()*1000
        return CameraHealthSample(_projection(self.next),now,now+1,'fixture')
    def close(self):
        self.closed = True


class Store:
    def __init__(self,timeline):
        self.clock,self.saved = timeline.event_time,[]
    def append_event(self,*args,**kwargs):
        self.saved.append((copy.deepcopy(args),copy.deepcopy(kwargs)))


def worker_fixture(store_factory=Store):
    clock = Mono()
    timeline = Timeline(clock)
    reader = FixtureReader(clock)
    store = store_factory(timeline)
    worker = VisualTimelineWorker('boot',store,timeline,reader=reader,
        monotonic=clock,allow_fixture=True)
    return worker,clock,timeline,reader,store


def feed(fixture,frame,stamp,count=1,**changes):
    worker,clock,timeline,reader,store = fixture
    clock.value = stamp
    reader.next = health(frame,count,**changes)
    return worker.step()


def test_construct_does_not_start_poll_or_store_and_missing_anchor_refuses_http():
    worker,clock,timeline,reader,store = worker_fixture()
    assert worker.thread is None and reader.calls == 0 and not store.saved
    timeline.anchored = False
    assert worker.step() == {'status':'unavailable','reason':'clock_unavailable'}
    with pytest.raises(ClockUnavailable):
        worker.start()
    assert worker.thread is None and reader.calls == 0 and not store.saved
    assert worker.close()


def test_stable_visual_events_only_device_scope_and_no_private_fields():
    fixture = worker_fixture()
    worker,clock,timeline,reader,store = fixture
    for frame,stamp in [(1,1.),(2,1.35),(3,1.7),(4,2.05)]:
        feed(fixture,frame,stamp)
    assert len(store.saved) == 1 and 'PRIVATE' not in repr(store.saved)
    args,kwargs = store.saved[0]
    assert args[0] == {'kind':'device','id':'board-camera'} and args[2] == 'camera_observed'
    assert kwargs['metadata']['speaker_known'] is False
    assert kwargs['metadata']['occurred_utc'] > 10000
    public = worker.public()
    assert public['scope_kind'] == 'device' and public['collector']['emitted_events'] == 1
    assert not public['identity_access_granted'] and not public['raw_images_stored']
    assert worker.close()


def test_real_shared_store_records_visual_observation_with_timeline_clock(tmp_path):
    clock,timeline = Mono(),None
    timeline = Timeline(clock)
    store = BoardMemoryStore(tmp_path/'synthetic-visual.sqlite3',clock=timeline.event_time)
    reader = FixtureReader(clock)
    worker = VisualTimelineWorker('boot',store,timeline,reader=reader,monotonic=clock,allow_fixture=True)
    fixture = worker,clock,timeline,reader,store
    for frame,stamp in [(1,1.),(2,1.35),(3,1.7)]:
        result = feed(fixture,frame,stamp,2)
    assert result['status'] == 'event_saved'
    rows = store.history({'kind':'device','id':'board-camera'})
    assert len(rows) == 1 and rows[0]['source'] == 'camera_observed'
    assert rows[0]['metadata']['evidence'] == 'visual_observation'
    assert 'PRIVATE' not in repr(rows)
    with sqlite3.connect(store.path) as db:
        assert db.execute('SELECT scope_kind,scope_id FROM bm_events').fetchall() == [('device','board-camera')]
    assert worker.close()


def test_camera_disconnect_is_not_zero_or_departure_and_requires_fresh_stability():
    fixture = worker_fixture()
    worker,clock,timeline,reader,store = fixture
    for frame,stamp in [(1,1.),(2,1.35),(3,1.7)]:
        feed(fixture,frame,stamp)
    reader.next = OSError('PRIVATE camera error')
    assert worker.step()['status'] == 'unavailable'
    assert len(store.saved) == 1 and worker.public()['collector']['current_count'] is None
    for frame,stamp in [(4,2.05),(5,2.4)]:
        feed(fixture,frame,stamp,0)
        assert len(store.saved) == 1
    assert feed(fixture,6,2.75,0)['status'] == 'event_saved'
    assert len(store.saved) == 2 and '离开' not in store.saved[-1][0][3]
    assert 'PRIVATE' not in repr(worker.public())
    assert worker.close()


def test_unavailable_clock_breaks_partial_stability_run():
    fixture = worker_fixture()
    worker,clock,timeline,reader,store = fixture
    feed(fixture,1,1.)
    feed(fixture,2,1.35)
    timeline.anchored = False
    worker.step()
    timeline.anchored = True
    feed(fixture,3,1.7)
    feed(fixture,4,2.05)
    assert not store.saved
    feed(fixture,5,2.4)
    assert len(store.saved) == 1
    assert worker.close()


def test_uncertain_store_write_retries_identical_event_and_occurred_time():
    class Uncertain(Store):
        def append_event(self,*args,**kwargs):
            super().append_event(*args,**kwargs)
            if len(self.saved) == 1:
                raise OSError('Commit acknowledgement lost')
    fixture = worker_fixture(Uncertain)
    worker,clock,timeline,reader,store = fixture
    feed(fixture,1,1.)
    feed(fixture,2,1.35)
    assert feed(fixture,3,1.7)['reason'] == 'visual_store_write_failed'
    assert feed(fixture,4,1.8)['status'] == 'event_saved'
    assert store.saved[0] == store.saved[1]
    assert worker.public()['collector']['emitted_events'] == 1
    assert worker.close()


def test_clock_scope_and_fixture_configuration_fail_closed():
    clock = Mono()
    timeline = Timeline(clock)
    reader = FixtureReader(clock)
    with pytest.raises(ValueError,match='Fixture'):
        VisualTimelineWorker('boot',Store(timeline),timeline,reader=reader,monotonic=clock)
    bad_store = Store(timeline)
    bad_store.clock = time.time
    with pytest.raises(ValueError,match='exact board timeline'):
        VisualTimelineWorker('boot',bad_store,timeline,reader=reader,monotonic=clock,allow_fixture=True)


class HealthHandler(BaseHTTPRequestHandler):
    def log_message(self,*_):
        pass
    def do_GET(self):
        self.server.paths.append(self.path)
        self.server.entered.set()
        try:
            if self.server.delay in ('drip_headers','drip_body'):
                body = self.server.body
                header = ('HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: '
                    +str(len(body))+'\r\nConnection: close\r\n\r\n').encode()
                self.close_connection = True
                if self.server.delay == 'drip_body':
                    self.wfile.write(header)
                    self.wfile.flush()
                data = header if self.server.delay == 'drip_headers' else body
                for byte in data:
                    self.wfile.write(bytes([byte]))
                    self.wfile.flush()
                    self.server.drips += 1
                    if self.server.release.wait(.015):
                        break
                return
            if self.server.delay == 'headers':
                self.server.release.wait(2)
            raw = self.server.body
            self.send_response(self.server.status_code)
            self.send_header('Content-Type',self.server.content_type)
            self.send_header('Content-Length',str(len(raw)))
            if self.server.status_code == 302:
                self.send_header('Location','http://192.168.50.1:8792/PRIVATE')
            self.end_headers()
            if self.server.delay == 'body':
                self.wfile.write(raw[:1])
                self.wfile.flush()
                self.server.release.wait(2)
                self.wfile.write(raw[1:])
            else:
                self.wfile.write(raw)
        except (OSError,ValueError):
            pass


@pytest.fixture
def health_server():
    server = ThreadingHTTPServer(('127.0.0.1',0),HealthHandler)
    server.daemon_threads = False
    server.body = json.dumps(health()).encode()
    server.content_type,server.status_code,server.delay = 'application/json',200,None
    server.entered,server.release = threading.Event(),threading.Event()
    server.paths = []
    server.drips = 0
    thread = threading.Thread(target=server.serve_forever,kwargs={'poll_interval':.01})
    thread.start()
    try:
        yield server
    finally:
        server.release.set()
        server.shutdown()
        server.server_close()
        thread.join(2)
        assert not thread.is_alive()


def test_actual_reader_filters_private_health_and_uses_only_fixed_health_path(health_server):
    connections = []
    class Observed(http.client.HTTPConnection):
        def connect(self):
            super().connect()
            self.actual_socket = self.sock
    def connection(*args,**kwargs):
        result = Observed(*args,**kwargs)
        connections.append(result)
        return result
    reader = CameraHealthReader(fixture_port=health_server.server_port,connection_factory=connection)
    try:
        sample = reader.read(deadline=time.monotonic()+1)
        assert sample.source_kind == 'fixture' and 'PRIVATE' not in repr(sample.health)
        assert sample.health['detector'] == {'count_kind':'people'}
        assert sample.requested_mono_ms <= sample.received_mono_ms
        assert health_server.paths == ['/health']
        assert reader.active is None
        assert connections[0].actual_socket.fileno() == -1
    finally:
        reader.close()


@pytest.mark.parametrize('case', ['redirect','length','content_type','duplicate','nonfinite'])
def test_reader_rejects_redirect_malformed_and_over_bound_responses(health_server,case):
    if case == 'redirect':
        health_server.status_code = 302
    elif case == 'length':
        health_server.body = b'X'*(MAX_CAMERA_HEALTH_BYTES+1)
    elif case == 'content_type':
        health_server.content_type = 'text/plain'
    elif case == 'duplicate':
        health_server.body = b'{"people_count":1,"people_count":2}'
    elif case == 'nonfinite':
        health_server.body = b'{"people_count":NaN}'
    reader = CameraHealthReader(fixture_port=health_server.server_port)
    try:
        with pytest.raises(CameraHealthError):
            reader.read(deadline=time.monotonic()+1)
        assert health_server.paths == ['/health']
    finally:
        reader.close()


def test_actual_socket_peer_mismatch_is_rejected_before_get(health_server):
    reader = CameraHealthReader(connection_factory=lambda host,port,timeout:
        http.client.HTTPConnection(host,health_server.server_port,timeout=timeout))
    try:
        with pytest.raises(CameraHealthError,match='camera_health_peer_rejected'):
            reader.read(deadline=time.monotonic()+1)
        assert not health_server.paths
    finally:
        reader.close()


@pytest.mark.parametrize('stage', ['headers','body'])
@pytest.mark.parametrize('stop', ['deadline','cancel','close'])
def test_real_loopback_total_deadline_cancel_and_close_interrupt_same_socket(health_server,stage,stop):
    health_server.delay = stage
    reader = CameraHealthReader(fixture_port=health_server.server_port)
    cancelled,errors = threading.Event(),[]
    until = time.monotonic()+(.08 if stop == 'deadline' else 1)
    def read():
        try:
            reader.read(deadline=until,cancelled=cancelled.is_set)
        except BaseException as exc:
            errors.append(exc)
    thread = threading.Thread(target=read)
    began = time.monotonic()
    thread.start()
    assert health_server.entered.wait(1)
    if stop == 'cancel':
        cancelled.set()
    elif stop == 'close':
        reader.close()
    thread.join(.5)
    assert not thread.is_alive() and len(errors) == 1
    assert isinstance(errors[0],TimeoutError if stop == 'deadline' else InterruptedError)
    assert time.monotonic()-began < .7 and reader.active is None
    reader.close()


def test_worker_public_and_close_do_not_wait_for_http_or_hold_shared_lock(health_server):
    health_server.delay = 'body'
    timeline = Timeline(time.monotonic)
    store = Store(timeline)
    reader = CameraHealthReader(fixture_port=health_server.server_port)
    worker = VisualTimelineWorker('boot',store,timeline,reader=reader,allow_fixture=True)
    assert worker.start()
    assert health_server.entered.wait(1)
    began = time.monotonic()
    assert worker.public()['inflight']
    assert worker.step()['status'] == 'busy'
    assert time.monotonic()-began < .1
    assert worker.close(timeout=1)
    assert not worker.public()['thread_alive'] and not worker.public()['inflight']
    assert not store.saved


@pytest.mark.parametrize('stage',['drip_headers','drip_body'])
@pytest.mark.parametrize('cancel',[False,True])
def test_dripping_peer_cannot_extend_original_deadline_or_cancel(health_server,stage,cancel):
    health_server.delay = stage
    reader = CameraHealthReader(fixture_port=health_server.server_port)
    stopped,errors = threading.Event(),[]
    began = time.monotonic()
    def read():
        try:
            reader.read(deadline=began+(.8 if cancel else .1),cancelled=stopped.is_set)
        except BaseException as exc:
            errors.append(exc)
    thread = threading.Thread(target=read)
    thread.start()
    until = time.monotonic()+1
    while health_server.drips<2 and time.monotonic()<until:
        time.sleep(.002)
    assert health_server.drips>=2
    if cancel:
        stopped.set()
    thread.join(.4)
    assert not thread.is_alive() and len(errors) == 1
    assert isinstance(errors[0],InterruptedError if cancel else TimeoutError)
    assert time.monotonic()-began < .5 and reader.active is None
    reader.close()


def test_busy_store_does_not_block_public_and_close_reports_inflight_writer():
    entered,release = threading.Event(),threading.Event()
    class Blocked(Store):
        def append_event(self,*args,**kwargs):
            entered.set()
            release.wait(2)
            super().append_event(*args,**kwargs)
    fixture = worker_fixture(Blocked)
    worker,clock,timeline,reader,store = fixture
    feed(fixture,1,1.)
    feed(fixture,2,1.35)
    results = []
    thread = threading.Thread(target=lambda:results.append(feed(fixture,3,1.7)))
    thread.start()
    assert entered.wait(1)
    try:
        began = time.monotonic()
        assert worker.public()['inflight']
        assert not worker.close(timeout=.05)
        assert time.monotonic()-began < .2
    finally:
        release.set()
        thread.join(1)
    assert not thread.is_alive() and worker.close()
    assert worker.step()['status'] == 'closed'


def test_board_business_factory_explicitly_starts_and_closes_shared_visual_worker(tmp_path,monkeypatch):
    import board.runtime.visual_memory as visual
    from board.runtime.board_business import BoardBusinessConfig,BoardBusinessRuntime
    from common.conversation_selection import ConversationSelection
    timeline = Timeline(time.monotonic)
    timeline.safe_for_compaction = lambda: False
    timeline.compaction_guard = nullcontext
    timeline.quality_snapshot = lambda: {'anchored':timeline.anchored}
    reader = FixtureReader(time.monotonic)
    original_read = reader.read
    def next_frame(**kwargs):
        reader.next = health(reader.calls+1)
        return original_read(**kwargs)
    reader.read = next_frame
    real_worker = VisualTimelineWorker
    created = []
    def create(*args,**kwargs):
        value = real_worker(*args,**kwargs,reader=reader,allow_fixture=True)
        created.append(value)
        return value
    monkeypatch.setattr(visual,'VisualTimelineWorker',create)
    class Memory:
        thread = None
        def __init__(self,*args,**kwargs):
            self.started = False
        def start(self):
            self.started = True
        def close(self):
            self.started = False
        def health(self):
            return {'started':self.started}
    runtime = BoardBusinessRuntime(BoardBusinessConfig(str(tmp_path/'private'),(9000.,1e10),
        visual_device_id='test-device-camera'),'boot',asr=lambda *args,**kwargs: '',
        system_prompt='只输出原三字段JSON。',conversation_selection=ConversationSelection(tmp_path/'conversation.json'),
        timeline=timeline,client=SimpleNamespace(host='192.168.50.1',port=8797),worker_factory=Memory,
        capture_idle=lambda:True)
    try:
        assert runtime.visual_memory is created[0] and reader.calls == 0
        assert runtime.public()['visual_timeline']['enabled']
        timeline.anchored = False
        with pytest.raises(ClockUnavailable):
            runtime.start()
        assert reader.calls == 0 and runtime.jobs.thread is None
        timeline.anchored = True
        runtime.start()
        until = time.monotonic()+1.5
        while created[0].public()['collector']['emitted_events'] == 0 and time.monotonic()<until:
            time.sleep(.01)
        rows = runtime.store.history({'kind':'device','id':'test-device-camera'})
        assert len(rows) == 1 and rows[0]['source'] == 'camera_observed'
        assert 'PRIVATE' not in repr(rows)
    finally:
        runtime.close()
    assert runtime.close_complete and reader.closed and not created[0].public()['thread_alive']


def test_board_runtime_retains_writer_until_visual_close_reports_finished(tmp_path):
    from board.runtime.board_business import BoardBusinessConfig,BoardBusinessRuntime
    from common.conversation_selection import ConversationSelection
    timeline = Timeline(time.monotonic)
    timeline.safe_for_compaction = lambda: False
    timeline.compaction_guard = nullcontext
    timeline.quality_snapshot = lambda: {'anchored':True}
    runtime = BoardBusinessRuntime(BoardBusinessConfig(str(tmp_path/'private'),(9000.,1e10)),
        'boot',asr=lambda *args,**kwargs: '',system_prompt='只输出原三字段JSON。',
        conversation_selection=ConversationSelection(tmp_path/'conversation.json'),timeline=timeline,
        client=SimpleNamespace(host='192.168.50.1',port=8797),capture_idle=lambda:True)
    released,finished = [],[]
    runtime.writer_lock = SimpleNamespace(close=lambda:released.append(True))
    runtime.visual_memory = SimpleNamespace(close=lambda:bool(finished))
    with pytest.raises(RuntimeError,match='writer lock retained'):
        runtime.close()
    assert not released and not runtime.close_complete
    finished.append(True)
    runtime.close()
    assert released == [True] and runtime.close_complete
