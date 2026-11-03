"""Board-local stable person-count memory from the existing camera owner.

Import/construction starts nothing. One explicitly started worker reads only
127.0.0.1:8790/health and appends small observations to the shared board Store's
device scope. It does not open a camera, read images, identify a person, grant
personal access, call Windows or load a model. HTTP and SQLite never run on a
foreground/UI tick. Camera loss cannot be converted into a departure event.
"""
from dataclasses import dataclass
import copy
import hashlib
import http.client
import io
import json
import math
import select
import threading
import time

from board.runtime.board_dialogue_client import _ConnectionControl
from board.visual_timeline import VisualTimelineCollector
from common.board_timeline_clock import ClockUnavailable


MAX_CAMERA_HEALTH_BYTES = 64*1024


class CameraHealthError(RuntimeError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class CameraHealthSample:
    health: dict
    requested_mono_ms: float
    received_mono_ms: float
    source_kind: str = 'actual'


class _CameraSocketReader(io.RawIOBase):
    """Poll the retained socket, including while waiting for the FIRST byte.

    Shutdown of a blocking socket makefile does not reliably wake an already
    pending silent-header read on every supported Windows/Python combination.
    This layer also checks cancellation itself and cannot wait past its one
    absolute deadline, regardless of how often a peer drips individual bytes.
    """
    def __init__(self,control):
        super().__init__()
        self.control = control

    def readable(self):
        return True

    def readinto(self,buffer):
        control = self.control
        while True:
            control.check()
            readable,_,_ = select.select([control.connected],[],[],
                min(.02,max(.001,control.deadline-control.monotonic())))
            control.check()
            if readable:
                try:
                    count = control.connected.recv_into(buffer)
                except BlockingIOError:
                    continue
                control.check()
                return count


class _CameraResponseSocket:
    def __init__(self,control):
        self.control = control

    def makefile(self,mode):
        if mode != 'rb':
            raise ValueError('Camera response is read only')
        return io.BufferedReader(_CameraSocketReader(self.control))


def _projection(body):
    """Never retain image, identity, face, template, device or extra fields."""
    if not isinstance(body, dict):
        raise CameraHealthError('camera_health_object_rejected')
    result = {name: body.get(name) for name in (
        'board_boot_id','service_epoch','camera_epoch','role','timestamp_kind',
        'observation_frame_id','people_count','observation_age_ms','capture_age_ms')}
    detector = body.get('detector')
    result['detector'] = ({'count_kind': detector.get('count_kind')}
                          if isinstance(detector,dict) else None)
    # The installed owner uses empty strings for successful components. Unknown
    # or malformed error types fail closed without exposing their contents.
    result['camera_error'] = body.get('camera_error') != ''
    result['detector_error'] = body.get('detector_error') != ''
    return result


class CameraHealthReader:
    HOST, PORT, PATH = '127.0.0.1', 8790, '/health'

    def __init__(self, *, clock=time.monotonic,
                 connection_factory=http.client.HTTPConnection, fixture_port=None):
        if fixture_port is not None and (type(fixture_port) is not int or not 1024 <= fixture_port <= 65535):
            raise ValueError('Invalid explicit loopback fixture port')
        self.clock, self.connection_factory = clock, connection_factory
        self.port = self.PORT if fixture_port is None else fixture_port
        self.source_kind = 'actual' if fixture_port is None else 'fixture'
        self.lock = threading.Lock()
        self.active = None
        self.closed = False

    def read(self, *, deadline, cancelled=lambda: False):
        if type(deadline) not in (int,float) or not math.isfinite(deadline):
            raise ValueError('Require original finite camera read deadline')
        remaining = deadline-self.clock()
        if cancelled() or self.closed:
            raise InterruptedError('Camera read cancelled')
        if remaining <= 0:
            raise TimeoutError('Camera read deadline expired')
        connection = self.connection_factory(self.HOST,self.port,timeout=remaining)
        control = _ConnectionControl(connection, deadline=deadline, monotonic=self.clock,
            cancelled=lambda: self.closed or cancelled())
        with self.lock:
            if self.closed:
                connection.close()
                raise InterruptedError('Camera reader closed')
            if self.active is not None:
                connection.close()
                raise CameraHealthError('camera_reader_busy')
            self.active = control
        response = None
        try:
            control.start()
            requested = self.clock()*1000
            control.connect()
            if control.connected is None or control.connected.getpeername() != (self.HOST,self.port):
                raise CameraHealthError('camera_health_peer_rejected')
            connection.request('GET',self.PATH,headers={'Accept':'application/json','Connection':'close'})
            control.check()
            control.connected.setblocking(False)
            response = http.client.HTTPResponse(_CameraResponseSocket(control),method='GET')
            response.begin()
            control.check()
            if response.status != 200:  # HTTPConnection does not follow redirects.
                raise CameraHealthError('camera_health_status_rejected')
            headers = {}
            for name,value in response.getheaders():
                headers.setdefault(name.lower(),[]).append(value)
            lengths,types = headers.get('content-length',[]),headers.get('content-type',[])
            if (len(lengths) != 1 or len(types) != 1
                    or types[0].split(';',1)[0].strip().lower() != 'application/json'
                    or headers.get('transfer-encoding') or headers.get('content-encoding')):
                raise CameraHealthError('camera_health_framing_rejected')
            length = lengths[0].strip()
            if not length.isascii() or not length.isdigit() or not 0 < int(length) <= MAX_CAMERA_HEALTH_BYTES:
                raise CameraHealthError('camera_health_length_rejected')
            raw = response.read(MAX_CAMERA_HEALTH_BYTES+1)
            control.check()
            received = self.clock()*1000
            if len(raw) != int(length):
                raise CameraHealthError('camera_health_length_rejected')
            def unique(pairs):
                value = {}
                for key,item in pairs:
                    if key in value:
                        raise ValueError()
                    value[key] = item
                return value
            try:
                body = json.loads(raw.decode('utf-8'),object_pairs_hook=unique,
                    parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
            except (ValueError,UnicodeError,RecursionError):
                raise CameraHealthError('camera_health_json_rejected') from None
            return CameraHealthSample(_projection(body),requested,received,self.source_kind)
        except (OSError,http.client.HTTPException):
            control.check()
            raise CameraHealthError('camera_health_io_failed') from None
        finally:
            try:
                control.close(response)
            finally:
                with self.lock:
                    if self.active is control:
                        self.active = None

    def close(self):
        with self.lock:
            self.closed = True
            active = self.active
        if active is not None:
            active.interrupt()


class VisualTimelineWorker:
    def __init__(self, boot_id, store, timeline, *, device_id='board-camera',
                 reader=None, poll_interval=.35, request_timeout=.2,
                 monotonic=time.monotonic, allow_fixture=False):
        if (type(poll_interval) not in (int,float) or not .25 <= poll_interval <= .5
                or type(request_timeout) not in (int,float)
                or not .02 <= request_timeout <= min(.5,poll_interval)):
            raise ValueError('Bound visual polling cadence and original HTTP deadline')
        if (not isinstance(device_id,str) or not 1 <= len(device_id) <= 160
                or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-.:' for c in device_id)):
            raise ValueError('Use an explicit stable device scope identifier')
        if (timeline.boot_id != boot_id or timeline.monotonic is not monotonic
                or store.clock != timeline.event_time):
            raise ValueError('Visual memory must share the exact board timeline clock')
        self.reader = reader or CameraHealthReader(clock=monotonic)
        if self.reader.clock is not monotonic:
            raise ValueError('Camera and timeline sampling must share the board monotonic clock')
        if self.reader.source_kind != 'actual' and not allow_fixture:
            raise ValueError('Fixture camera sources require explicit opt-in')
        self.store, self.timeline, self.clock = store,timeline,monotonic
        self.scope = {'kind':'device','id':device_id}
        self.collector = VisualTimelineCollector(boot_id,self._append,self.scope,
            clock_ms=lambda: self.clock()*1000,utc_clock=timeline.event_time,allow_fixture=allow_fixture)
        self.poll_interval,self.request_timeout = poll_interval,request_timeout
        self.condition = threading.Condition()
        self.stop = threading.Event()
        self.thread = None
        self.closed = self.inflight = False
        self.steps = self.errors = 0
        self.last_status,self.last_reason = 'not_started',''
        self._collector_public = self.collector.health()
        self._current_proof = None
        self.query_observation_writes = 0

    def _append(self,*args,**kwargs):
        if self.stop.is_set():
            raise InterruptedError('Visual worker closed before append')
        self.timeline.event_time()  # No initial anchor/system-wall fallback.
        return self.store.append_event(*args,**kwargs)

    def _publish(self,status,reason=''):
        snapshot = self.collector.health()
        with self.condition:
            self.last_status,self.last_reason = status,reason
            self._collector_public = snapshot
            if (self.collector.committed_count is None or self.collector.candidate is None
                    or self.collector.candidate['count'] != self.collector.committed_count):
                self._current_proof = None
        return {'status':status,'reason':reason}

    def _remember_current(self,sample):
        """Cache only an accepted, currently stable source frame, never an ID."""
        count = self.collector.committed_count
        if (self.collector.last_reason or count is None
                or self.collector.candidate is None or self.collector.candidate['count'] != count
                or sample.health.get('people_count') != count):
            return
        h = sample.health
        source_ms = sample.requested_mono_ms-h['observation_age_ms']
        occurred = self.timeline.event_time()-(self.clock()*1000-source_ms)/1000
        identity = (self.collector.boot,h['service_epoch'],h['camera_epoch'],
                    h['observation_frame_id'],sample.source_kind)
        token = hashlib.sha256(json.dumps(identity,separators=(',',':')).encode()).hexdigest()
        text = '摄像头画面取样稳定检测到%d个人体目标。' % count
        if not count:
            text = '摄像头画面取样检测到0个人体目标，未检出人体。'
        proof = dict(count=count,event_id='camera_query:'+token,text=text,
            requested_mono_ms=sample.requested_mono_ms,received_mono_ms=sample.received_mono_ms,
            observation_age_ms=h['observation_age_ms'],capture_age_ms=h['capture_age_ms'],
            metadata=dict(evidence='visual_observation',numbers=[count],speaker_known=False,
                source_id=token,time_basis='board_camera_health_source_bound',occurred_utc=occurred,
                claims=[{'field':'event_kind','value':'person_count_observed' if count else 'no_person_detected'},
                        {'field':'people_count','value':count},
                        {'field':'source_frame_id','value':h['observation_frame_id']},
                        {'field':'source_kind','value':sample.source_kind}]))
        with self.condition:
            self._current_proof = proof

    def current_observation(self):
        """A fresh accepted stable frame, rather than an old timeline count."""
        try:
            self.timeline.event_time()
        except ClockUnavailable:
            return None
        with self.condition:
            if self.closed or self.stop.is_set() or self._current_proof is None:
                return None
            proof = copy.deepcopy(self._current_proof)
        now = self.clock()*1000
        if (now < proof['received_mono_ms']
                or now-proof['requested_mono_ms']+max(proof['observation_age_ms'],proof['capture_age_ms'])
                    >= self.collector.max_age):
            return None
        return proof

    def record_current_observation(self):
        """Give an explicit local query its own same-device source dependency.

        The fixed source-frame event ID and UTC payload remain frozen across
        retries. A forgotten tombstone cannot be recreated as valid. A later
        fresh frame can establish a new observation, without restoring history.
        """
        proof = self.current_observation()
        if proof is None:
            return None
        value = self._append(dict(self.scope),proof['event_id'],'camera_observed',proof['text'],
                             topic='视觉',metadata=proof['metadata'])
        if not isinstance(value,dict) or value.get('state') != 'valid':
            return None
        with self.condition:
            self.query_observation_writes += 1
        return dict(count=proof['count'],event_id=proof['event_id'],revision=value['revision'])

    def step(self):
        with self.condition:
            if self.closed:
                return {'status':'closed','reason':''}
            if self.inflight:
                return {'status':'busy','reason':''}
            self.inflight = True
            self.steps += 1
        stage = 'clock'
        try:
            self.timeline.event_time()
            stage = 'read'
            sample = self.reader.read(deadline=self.clock()+self.request_timeout,cancelled=self.stop.is_set)
            if not isinstance(sample,CameraHealthSample):
                raise CameraHealthError('camera_health_sample_rejected')
            if self.stop.is_set():
                raise InterruptedError()
            self.timeline.event_time()
            stage = 'append'
            event = self.collector.ingest_health(sample.health,
                requested_mono_ms=sample.requested_mono_ms,received_mono_ms=sample.received_mono_ms,
                source_kind=sample.source_kind)
            self._remember_current(sample)
            return self._publish('event_saved' if event is not None else
                'rejected' if self.collector.last_reason else 'observed',self.collector.last_reason)
        except ClockUnavailable:
            self.collector.source_unavailable('clock_unavailable')
            with self.condition:
                self.errors += 1
            return self._publish('unavailable','clock_unavailable')
        except InterruptedError:
            self.collector.source_unavailable('worker_cancelled')
            return self._publish('cancelled','worker_cancelled')
        except Exception as exc:
            if stage != 'append':
                self.collector.source_unavailable()
            with self.condition:
                self.errors += 1
            code = (exc.code if isinstance(exc,CameraHealthError) else
                    'visual_store_write_failed' if stage == 'append' else 'camera_health_unavailable')
            return self._publish('unavailable',code)
        finally:
            with self.condition:
                self.inflight = False
                self.condition.notify_all()

    def start(self):
        self.timeline.event_time()
        with self.condition:
            if self.closed:
                raise RuntimeError('Visual worker is closed')
            if self.thread is not None:
                return False
            self.thread = threading.Thread(target=self._run,name='aura-board-visual-memory',daemon=True)
            self.thread.start()
        return True

    def _run(self):
        while not self.stop.is_set():
            began = self.clock()
            self.step()
            self.stop.wait(max(0.,self.poll_interval-(self.clock()-began)))

    def close(self, *, timeout=1.25):
        if type(timeout) not in (int,float) or not 0 < timeout <= 2:
            raise ValueError('Bound visual worker shutdown wait')
        until = time.monotonic()+timeout
        with self.condition:
            self.closed = True
            self.stop.set()
            thread = self.thread
        self.reader.close()
        if thread is not None and thread is not threading.current_thread():
            thread.join(max(0.,until-time.monotonic()))
        with self.condition:
            while self.inflight and time.monotonic() < until:
                self.condition.wait(max(.001,until-time.monotonic()))
            return not self.inflight and not bool(thread and thread.is_alive())

    def public(self):
        with self.condition:
            return dict(enabled=True,scope_kind='device',source_kind=self.reader.source_kind,
                camera_endpoint='127.0.0.1:'+str(getattr(self.reader,'port',8790))+'/health',
                poll_seconds=self.poll_interval,request_timeout_seconds=self.request_timeout,
                thread_alive=bool(self.thread and self.thread.is_alive()),inflight=self.inflight,
                closed=self.closed,steps=self.steps,errors=self.errors,
                query_observation_writes=self.query_observation_writes,
                last_status=self.last_status,last_reason=self.last_reason,
                collector=dict(self._collector_public),raw_images_stored=False,
                identity_access_granted=False)
