"""Explicit board-local speaker/anonymous/link business, without a Hub server.

One CPU worker owns the existing SpeakerDevice, progressive matcher and binding
FSMs. The encoder is injected; the board uses the already pinned ECAPA ONNX
export and the original WebRTC 30ms/mode2 gate. No model download, microphone,
network, Windows service, profile grant or device starts on import. Descriptors
contain no vectors but remain private board data and must not enter LLM prompts.
"""
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from contextlib import contextmanager
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import secrets
import sqlite3
import stat
import threading
import time
from types import SimpleNamespace

from common.asr_wire import context
from common.conversation_store import conversation_id as validate_conversation_id
from common.speaker_identity import SpeakerStore, voiced_pcm
from common.speaker_turns import record
from common.speaker_visual import unavailable, validate_visual
from tools.speaker_device import SpeakerDevice
from tools.binding_hub_runtime import BindingHubRuntime
from tools.private_gallery_reference import private_gallery_reference


class SpeakerNotReady(RuntimeError):
    pass


class SpeakerBusy(SpeakerNotReady):
    pass


_OWNER = 'speaker-business-owner.json'
_NAMESPACE = 'speaker-gallery-namespace.json'
_KEY = 'identity-link-receipt.key'
_FILES = ('speakers.sqlite3', 'anonymous-voices.sqlite3', 'identity-links.sqlite3')
_MARKERS = {'speakers.sqlite3':0x41555350, 'anonymous-voices.sqlite3':0x4155414E, 'identity-links.sqlite3':0x41554C4B}
_TABLES = {
    'speakers.sqlite3': {
        'identities':{'id','name'}, 'templates':{'identity_id','model_id','dimension','embedding'},
        'metadata':{'key','value'}},
    'anonymous-voices.sqlite3': {
        'anonymous_meta':{'key','value'}, 'anonymous_labels':{'seq','cluster_id','boot','created','expires','state'},
        'anonymous_anchors':{'cluster_id','anchor'}, 'anonymous_samples':{'cluster_id','capture_id','digest'},
        'anonymous_observations':{'request_id','owner','result','received','cluster_id'}},
    'identity-links.sqlite3': {
        'linked_people':{'person_id','name','name_key','state','created'},
        'modality_links':{'person_id','modality','store_id','identity_id','model_id','revision','fingerprint','state'},
        'binding_attempts':{'attempt_id','origin','name','anonymous_id','face_guard','face_gallery','voice_gallery','state',
                            'expires','confirmed_context','face_receipt','voice_receipt','person_id','error'},
        'anonymous_person_links':{'registry_epoch','anonymous_id','person_id'},
        'binding_invalidations':{'person_id','modality','reason','at'}}}


def _fingerprint(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def inspect_speaker_snapshot(path, name, *, model_id):
    """Read-only exact-known-schema gate; returns hashes/counts, no values."""
    path = Path(path).absolute()
    if name not in _TABLES or path.resolve(strict=True) != path or path.is_symlink() or path.stat().st_size > 64*1024*1024:
        raise ValueError('Unsupported speaker snapshot')
    if any(Path(str(path)+suffix).exists() for suffix in ('-wal','-shm','-journal')):
        raise ValueError('Speaker source is not a quiescent snapshot')
    db = sqlite3.connect(path.as_uri()+'?mode=ro&immutable=1',uri=True,timeout=.05)
    try:
        db.execute('PRAGMA query_only=ON'); db.execute('BEGIN')
        if db.execute('PRAGMA application_id').fetchone()[0] != _MARKERS[name]:
            raise ValueError('Speaker application marker mismatch')
        if db.execute('PRAGMA user_version').fetchone()[0] != 0:
            raise ValueError('Unsupported speaker schema version')
        if db.execute('PRAGMA quick_check').fetchone()[0] != 'ok':
            raise ValueError('Speaker snapshot integrity failure')
        schema = db.execute("SELECT type,name,tbl_name,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY type,name").fetchall()
        if any(row[0] in ('trigger','view') for row in schema):
            raise ValueError('Unexpected speaker schema behavior')
        tables = {row[1] for row in schema if row[0] == 'table'}
        required = set(_TABLES[name]) - ({'binding_invalidations'} if name == 'identity-links.sqlite3' else set())
        if not required <= tables <= set(_TABLES[name]):
            raise ValueError('Unsupported speaker schema tables')
        for table in tables:
            info = db.execute('PRAGMA table_info('+table+')').fetchall()
            if {row[1] for row in info} != _TABLES[name][table]:
                raise ValueError('Unsupported speaker schema columns')
            keys = dict(identities=['id'],templates=['identity_id','model_id'],metadata=['key'],
                        anonymous_meta=['key'],anonymous_labels=['seq'],anonymous_anchors=['cluster_id'],
                        anonymous_samples=['cluster_id','capture_id'],anonymous_observations=['request_id'],
                        linked_people=['person_id'],modality_links=['modality','store_id','identity_id','model_id'],
                        binding_attempts=['attempt_id'],anonymous_person_links=['registry_epoch','anonymous_id'],
                        binding_invalidations=[])[table]
            if [row[1] for row in sorted(info,key=lambda row:row[5]) if row[5]] != keys:
                raise ValueError('Unsupported speaker primary keys')
        if name == 'speakers.sqlite3':
            if db.execute('SELECT 1 FROM templates WHERE model_id!=? OR dimension!=192 LIMIT 1',(model_id,)).fetchone():
                raise ValueError('Speaker snapshot model changed')
        elif name == 'anonymous-voices.sqlite3':
            values = dict(db.execute("SELECT key,value FROM anonymous_meta WHERE key IN ('model_id','dimension')"))
            if values != {'model_id':model_id,'dimension':'192'}:
                raise ValueError('Anonymous snapshot model changed')
        return dict(application_id=_MARKERS[name], schema_sha256=hashlib.sha256(json.dumps(schema,sort_keys=True).encode()).hexdigest(),
                    table_count=len(tables), sha256=_fingerprint(path))
    finally:
        db.close()


def _write_json(path, value):
    path = Path(path); temp = path.with_name(path.name+'.partial-'+secrets.token_hex(4))
    fd = os.open(str(temp),os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,'O_NOFOLLOW',0),0o600)
    with os.fdopen(fd,'w',encoding='utf-8') as stream:
        json.dump(value,stream,ensure_ascii=False,separators=(',',':')); stream.flush(); os.fsync(stream.fileno())
    os.replace(temp,path)


class _WriterLease:
    def __init__(self, root, *, data_origin):
        root = Path(root).absolute()
        if (not root.is_absolute() or root.resolve() != root or data_origin == 'board' and
                any(part.casefold() == 'win共享文件' for part in root.parts)):
            raise ValueError('Speaker storage must be a private regular directory')
        self.fd = None; self.root = root
        if data_origin not in ('board','synthetic'):
            raise ValueError('Explicit speaker data origin required')
        if data_origin == 'board' and os.name != 'posix':
            raise RuntimeError('Real speaker stores require the POSIX board runtime')
        root.mkdir(parents=True,exist_ok=True,mode=0o700)
        if data_origin == 'board':
            info = root.stat()
            if info.st_uid != os.getuid() or info.st_mode & 0o077 or not stat.S_ISDIR(info.st_mode):
                raise PermissionError('Speaker root must be owned by this user and private')
        path = root/'speaker-writer.lock'
        self.fd = os.open(str(path),os.O_RDWR|os.O_CREAT|getattr(os,'O_NOFOLLOW',0),0o600)
        try:
            if data_origin == 'board':
                info = os.fstat(self.fd)
                if info.st_uid != os.getuid() or info.st_mode & 0o077 or not stat.S_ISREG(info.st_mode):
                    raise PermissionError('Speaker writer lease must be private and regular')
            if os.name == 'posix':
                import fcntl
                fcntl.flock(self.fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            else:
                import msvcrt
                if os.fstat(self.fd).st_size == 0:
                    os.write(self.fd,b'0'); os.fsync(self.fd)
                os.lseek(self.fd,0,os.SEEK_SET); msvcrt.locking(self.fd,msvcrt.LK_NBLCK,1)
        except BaseException:
            os.close(self.fd); self.fd = None; raise

    def close(self):
        if self.fd is not None:
            fd,self.fd = self.fd,None
            try:
                if os.name == 'posix':
                    import fcntl
                    fcntl.flock(fd,fcntl.LOCK_UN)
                else:
                    import msvcrt
                    os.lseek(fd,0,os.SEEK_SET); msvcrt.locking(fd,msvcrt.LK_UNLCK,1)
            finally:
                os.close(fd)


class _CheckedEncoder:
    def __init__(self, encoder, current):
        self.encoder,self.current = encoder,current
        self.model_id,self.dimension = encoder.model_id,encoder.dimension
    def encode(self, pcm):
        if not self.current():
            raise InterruptedError('Speaker capture cancelled before embedding')
        value = self.encoder.encode(pcm)
        if not self.current():
            raise InterruptedError('Speaker capture cancelled during embedding')
        return value


class _GuardedStore:
    def __init__(self, store, service):
        self.original,self.service = store,service
    def __getattr__(self,key):
        return getattr(self.original,key)
    def _write(self, method, *args, **kwargs):
        service = self.service
        if not service._current():
            raise InterruptedError('Speaker write has no current capture')
        # Ownership changes serialize with the short original SQLite commit;
        # no lock spans VAD, ECAPA, model requests or spoken playback.
        with service.lock:
            job = getattr(service.local,'job',None)
            if job is None or not service._owns(job) or job['cancelled'].is_set():
                raise InterruptedError('Speaker write belongs to an old capture')
            return getattr(self.original,method)(*args,**kwargs)
    def enroll(self,*args,**kwargs):
        return self._write('enroll',*args,**kwargs)
    def delete(self,*args,**kwargs):
        return self._write('delete',*args,**kwargs)


class BoardSpeakerBusiness:
    """Create explicitly, then use bounded local jobs; one CPU/database owner."""
    @classmethod
    def create(cls, private_root, **kwargs):
        return cls(private_root,create=True,**kwargs)

    def __init__(self, private_root, *, encoder_factory, board_boot_id, quality=None,
                 expected_model_id=None, anonymous_config=None, calibration=None,
                 wall_clock=None, clock=time.monotonic, create=False, data_origin='board',
                 on_evidence=None, startup_timeout=30.):
        if create is not True:
            raise ValueError('Explicit BoardSpeakerBusiness.create is required')
        if not callable(encoder_factory) or not callable(quality) or not callable(wall_clock):
            raise SpeakerNotReady('Pinned encoder, original speech quality gate and board clock are required')
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,96}',board_boot_id or ''):
            raise ValueError('Fresh board boot ID required')
        if data_origin == 'board':
            if quality is not voiced_pcm or importlib.util.find_spec('webrtcvad') is None:
                raise SpeakerNotReady('Original WebRTC mode2 30ms quality dependency is unavailable')
            if not re.fullmatch(r'ecapa-voxceleb-[0-9a-f]{64}',expected_model_id or ''):
                raise ValueError('Pinned original ECAPA model ID required')
        c = dict(calibration or {})
        if (c.get('field_calibrated',False) is not False or c.get('threshold',.8) < .8
                or c.get('margin',.1) < .1 or c.get('consistency',.6) < .6):
            raise ValueError('Keep the original uncalibrated operating policy')
        config = dict(anonymous_config or {'enabled':False})
        if type(config.get('enabled')) is not bool:
            raise ValueError('Anonymous collection requires explicit boolean configuration')
        self.root = Path(private_root).absolute(); self.boot = board_boot_id
        self.clock,self.wall_clock,self.data_origin = clock,wall_clock,data_origin
        self.encoder_factory,self.quality,self.expected_model_id = encoder_factory,quality,expected_model_id
        self.config,self.calibration,self.on_evidence = config,c,on_evidence
        self.lock = threading.RLock(); self.local = threading.local(); self.closing = threading.Event()
        self.jobs = {}; self.latest = OrderedDict(); self.results = OrderedDict()
        self.capacity = threading.BoundedSemaphore(2); self.counts = dict(submitted=0,complete=0,cancelled=0,unavailable=0,evidence_errors=0)
        self.public_state = dict(active=False,speaker_calibrated=False,automatic_profile_access=False,ready=False)
        self.lease = _WriterLease(self.root,data_origin=data_origin)
        self.pool = ThreadPoolExecutor(max_workers=1,thread_name_prefix='board-speaker-cpu')
        try:
            self.pool.submit(self._initialize).result(timeout=startup_timeout)
        except BaseException:
            self.close(timeout=1.); raise

    def _initialize(self):
        self.hub = None
        for name in _FILES+(_OWNER,_NAMESPACE,_KEY):
            if (self.root/name).is_symlink():
                raise ValueError('Speaker files cannot be symbolic links')
        owner_path = self.root/_OWNER
        owner = json.loads(owner_path.read_text(encoding='utf-8')) if owner_path.exists() else None
        if owner is None and any((self.root/name).exists() for name in _FILES):
            raise ValueError('Existing speaker stores require verified migration ownership')
        if owner is not None and (owner.get('version') != 1 or owner.get('data_origin') != self.data_origin):
            raise ValueError('Speaker origin/ownership marker mismatch')
        encoder = self.encoder_factory()
        if encoder.dimension != 192 or not isinstance(encoder.model_id,str) or not encoder.model_id:
            raise ValueError('Original ECAPA dimensions required')
        if self.expected_model_id is not None and encoder.model_id != self.expected_model_id:
            raise ValueError('Speaker encoder changed its original model ID')
        if owner is not None and owner.get('model_id') != encoder.model_id:
            raise ValueError('Speaker store model ownership changed')
        for name in _FILES:
            if (self.root/name).exists():
                inspect_speaker_snapshot(self.root/name,name,model_id=encoder.model_id)
        checked = _CheckedEncoder(encoder,self._current)
        device = SpeakerDevice(checked,self.root/'speakers.sqlite3',calibration=self.calibration,
                               clock=self.clock,quality=self._quality)
        device.store = _GuardedStore(device.store,self)
        hub = SimpleNamespace(root=self.root,speaker=device,progressive_speaker=None,binding=None,identity_links=None,
                              speaker_turns=SimpleNamespace(streaks=OrderedDict(),clock=self.clock,
                                  actor=lambda meta:(meta['board_boot_id'],meta['session_id'])))
        self.hub = hub
        namespace_path = self.root/_NAMESPACE
        if namespace_path.exists():
            namespace = json.loads(namespace_path.read_text(encoding='utf-8'))
            if (namespace.get('version') != 1 or namespace.get('model_id') != encoder.model_id
                    or not re.fullmatch(r'gallery-[0-9a-f]{32}',namespace.get('store_id',''))):
                raise ValueError('Speaker gallery namespace changed')
        elif owner is not None:
            raise ValueError('Missing owned speaker gallery namespace')
        else:
            namespace = dict(version=1,model_id=encoder.model_id,store_id='gallery-'+secrets.token_hex(16),origin='created_local')
            _write_json(namespace_path,namespace)
        def reference(identity):
            value = private_gallery_reference(self.root/'speakers.sqlite3',encoder.model_id,encoder.dimension,
                identity_id=identity,expected_application_id=SpeakerStore.APPLICATION_ID)
            value['store_id'] = namespace['store_id']
            return value
        hub.voice_reference = reference
        if self.config['enabled']:
            hub.binding = BindingHubRuntime(hub,self.config,clock=self.wall_clock,validate_root=lambda root:root,
                                            voice_reference=reference)
            hub.progressive_speaker.quality = self._quality
            hub.progressive_speaker.anonymous_store.clock = self.wall_clock
            hub.progressive_speaker.provisional.clock = self.wall_clock
        owner_value = dict(owner or {})
        owner_value.update(version=1,data_origin=self.data_origin,model_id=encoder.model_id,
                           origin=owner.get('origin') if owner else 'created_local')
        _write_json(owner_path,owner_value)
        self._refresh_public()

    def _quality(self,pcm):
        if not self._current():
            raise InterruptedError('Speaker quality no longer owns the capture')
        result = self.quality(pcm)
        if not self._current():
            raise InterruptedError('Speaker quality capture cancelled')
        return result

    def _owns(self,job):
        meta = job['meta']; actor = meta['board_boot_id'],meta['session_id']
        return self.latest.get(actor) == meta

    def _job_current(self,job):
        with self.lock:
            owned = self._owns(job)
        return (owned and not self.closing.is_set() and not job['cancelled'].is_set()
                and self.clock() < job['deadline'] and job['is_current']())

    def _current(self):
        job = getattr(self.local,'job',None)
        return job is not None and self._job_current(job)

    def _refresh_public(self):
        hub = self.hub
        binding = hub.binding if hub is not None else None
        value = dict(ready=hub is not None,active=bool(hub and (hub.speaker.sessions or binding and
                    (binding.router.active or binding.router.name_waiting))),speaker_calibrated=False,
                    automatic_profile_access=False,pcm_persisted=False,single_cpu_worker=True)
        with self.lock:
            self.public_state = value

    def public(self):
        with self.lock:
            return copy.deepcopy(self.public_state)

    def _submit(self, operation, meta, pcm, *, deadline=None, is_current=lambda:True, cancel_event=None, cid=None, control=True):
        meta = context(meta,pcm)
        if meta['board_boot_id'] != self.boot:
            raise ValueError('Speaker request belongs to another boot')
        if self.closing.is_set():
            raise SpeakerNotReady('Speaker business is closed')
        if not self.capacity.acquire(False):
            raise SpeakerBusy('The sole speaker worker is busy')
        job = dict(meta=meta,pcm=pcm,is_current=is_current,cancelled=cancel_event or threading.Event(),
                   deadline=min(self.clock()+meta['budget_ms']/1000,deadline if deadline is not None else float('inf')),
                   cid=cid,control=control)
        actor = meta['board_boot_id'],meta['session_id']
        try:
            with self.lock:
                previous = self.latest.get(actor)
                if previous is not None and (meta['generation'] < previous['generation'] or
                        meta['generation'] == previous['generation'] and meta != previous):
                    raise ValueError('Stale or reused speaker request ownership')
                self.latest[actor] = meta; self.latest.move_to_end(actor)
                while len(self.latest) > 64:
                    self.latest.popitem(last=False)
                self.jobs[id(job)] = job; self.counts['submitted'] += 1
            future = self.pool.submit(self._run,job,operation)
            job['future'] = future
            def finished(_):
                job['pcm'] = None
                with self.lock:
                    self.jobs.pop(id(job),None)
                self.capacity.release()
            future.add_done_callback(finished)
            return future,job
        except BaseException:
            job['pcm'] = None
            with self.lock:
                self.jobs.pop(id(job),None)
            self.capacity.release(); raise

    def _run(self,job,operation):
        self.local.job = job
        raw,job['pcm'] = job['pcm'],None
        try:
            if not self._current():
                raise InterruptedError('Speaker job cancelled before processing')
            value = operation(raw)
            if not self._current():
                raise InterruptedError('Speaker result no longer owns its capture')
            with self.lock:
                self.counts['complete'] += 1
            return value
        except BaseException:
            if job['control'] and not self._current():
                self._cancel_actor(job['meta'])
            raise
        finally:
            raw = None
            self.local.job = None
            self._refresh_public()

    def _call(self,operation,meta,pcm,**kwargs):
        future,job = self._submit(operation,meta,pcm,**kwargs)
        try:
            while True:
                if not self._job_current(job):
                    job['cancelled'].set(); job['pcm'] = None; future.cancel()
                    raise InterruptedError('Speaker request cancelled or expired')
                try:
                    return future.result(timeout=min(.025,max(.001,job['deadline']-self.clock())))
                except FutureTimeout:
                    if future.done():
                        raise  # An operation's own timeout is not a poll timeout.
        except BaseException:
            job['cancelled'].set(); job['pcm'] = None; raise

    def route(self,meta,text,pcm,*,visual=None,gallery_packet=None,**kwargs):
        visual = validate_visual(visual,meta) if visual is not None else unavailable(meta)
        def work(raw):
            binding = self.hub.binding
            if binding is None:
                raise SpeakerNotReady('Anonymous identity-link workflow was not enabled')
            digest = None
            if gallery_packet is not None:
                from common.face_binding_wire import validate_packet
                packet = validate_packet(gallery_packet,meta)
                digest = binding.ingest_gallery(packet)['packet_sha256']
            return binding.route(meta,text,raw,visual=visual,gallery_digest=digest)
        return self._call(work,meta,pcm,**kwargs)

    def turn(self,meta,text,pcm,**kwargs):
        def work(raw):
            value = self.hub.speaker.turn(meta,text,raw)
            if self.hub.binding is not None:
                self.hub.binding.after_original_voice_turn(meta,text)
            return value
        return self._call(work,meta,pcm,**kwargs)

    def submit_analysis(self,meta,pcm,conversation_id,*,visual=None,on_evidence=None,**kwargs):
        cid = validate_conversation_id(conversation_id); meta = context(meta,pcm)
        visual = validate_visual(visual,meta) if visual is not None else unavailable(meta)
        key = meta['board_boot_id'],meta['session_id'],meta['request_id']
        with self.lock:
            old = self.results.get(key)
            if old is not None:
                if old['meta'] != meta or old['cid'] != cid:
                    raise ValueError('Foreign speaker analysis retry')
                return copy.deepcopy(old['value'])
            analysis_deadline = min(self.clock()+12.,kwargs.get('deadline',float('inf')),self.clock()+meta['budget_ms']/1000)
            self.results[key] = dict(meta=meta,cid=cid,value=record(meta,cid,visual=visual),until=self.clock()+600,
                                     deadline=analysis_deadline,job=None)
            while len(self.results) > 256:
                self.results.popitem(last=False)
        def work(raw):
            binding = self.hub.binding
            value = binding.precomputed_analysis(meta,cid,visual) if binding is not None else None
            if value is None:
                analyzer = self.hub.progressive_speaker
                if analyzer is None:
                    voice,alias = self.hub.speaker.analyze(meta,raw),None
                else:
                    voice,alias = analyzer.analyze(meta,raw,is_current=self._current)
                identity = None
                if binding is not None:
                    proof = analyzer.provisional.proof(meta,store_id=self.hub.voice_reference(None)['store_id'])
                    proofs = [proof] if proof is not None else []
                    face = binding.face_naming_proof(meta,visual)
                    if face is not None:
                        proofs.append(face)
                    identity = binding.registry.resolve(meta,proofs,anonymous=alias)
                value = record(meta,cid,status='COMPLETE',reason='DESCRIPTIVE_EVIDENCE_ONLY',
                               voice=voice,visual=visual,anonymous=alias,identity=identity)
            return value
        try:
            kwargs['deadline'] = analysis_deadline
            future,job = self._submit(work,meta,pcm,cid=cid,control=False,**kwargs)
            with self.lock:
                if key in self.results:
                    self.results[key]['job'] = job
        except SpeakerBusy:
            value = record(meta,cid,status='UNAVAILABLE',reason='SPEAKER_WORKER_BUSY',visual=visual)
            with self.lock:
                self.results[key]['value'] = value; self.counts['unavailable'] += 1
            return copy.deepcopy(value)
        def finished(done):
            try:
                value = done.result()
            except BaseException:
                value = record(meta,cid,status='CANCELLED' if job['cancelled'].is_set() or not self._job_current(job) else 'UNAVAILABLE',
                               reason='SPEAKER_ANALYSIS_NOT_ADOPTED',visual=visual)
            with self.lock:
                row = self.results.get(key)
                if row is not None and row['meta'] == meta and row['value']['status'] == 'PENDING':
                    row['value'] = value
                    row['job'] = None
                elif row is not None:
                    value = row['value']
            callback = on_evidence or self.on_evidence
            if callback is not None and value['status'] == 'COMPLETE':
                try:
                    callback(copy.deepcopy(value))
                except Exception:
                    with self.lock:
                        self.counts['evidence_errors'] += 1
        future.add_done_callback(finished)
        return self.analysis_result(meta,cid)

    def analysis_result(self,meta,conversation_id):
        meta = context(meta); cid = validate_conversation_id(conversation_id)
        key = meta['board_boot_id'],meta['session_id'],meta['request_id']
        with self.lock:
            row = self.results.get(key)
            if row is None or row['meta'] != meta or row['cid'] != cid or self.clock() >= row['until']:
                raise ValueError('Foreign or expired board speaker result')
            job = row['job']
            if row['value']['status'] == 'PENDING' and self.clock() >= row['deadline']:
                if job is not None:
                    job['cancelled'].set(); job['pcm'] = None
                    job.get('future').cancel() if job.get('future') is not None else None
                row['value'] = record(meta,cid,status='EXPIRED',reason='ANALYSIS_DEADLINE',visual=row['value']['visual'])
            return copy.deepcopy(row['value'])

    def analyze(self,meta,pcm,*,conversation_id,visual=None,**kwargs):
        self.submit_analysis(meta,pcm,conversation_id,visual=visual,**kwargs)
        while True:
            value = self.analysis_result(meta,conversation_id)
            if value['status'] != 'PENDING':
                return value
            time.sleep(.01)

    def begin_face_exchange(self,meta,pcm,routed,bridge,capture_snapshot,text,*,is_current=lambda:True,
                            cancel_event=None,deadline=None):
        return LocalFaceExchange(self,meta,pcm,routed,bridge,capture_snapshot,text,
                                 is_current=is_current,cancel_event=cancel_event,deadline=deadline)

    def _cancel_actor(self,meta):
        hub = self.hub; actor = meta['board_boot_id'],meta['session_id']
        hub.speaker.sessions.pop(actor,None)
        if hub.binding is not None:
            binding = hub.binding
            attempt = binding.router.active.pop(actor,None)
            if attempt is not None:
                try:
                    binding.registry.cancel(attempt,meta)
                except (ValueError,sqlite3.Error,TimeoutError):
                    pass
            binding.router.name_waiting.pop(actor,None)
            binding.speaker.sessions.pop(actor,None); binding.speaker.aliases.pop(actor,None)

    def cancel_analysis(self,meta,conversation_id):
        meta = context(meta); cid = validate_conversation_id(conversation_id)
        key = meta['board_boot_id'],meta['session_id'],meta['request_id']
        with self.lock:
            row = self.results.get(key)
            if row is None or row['meta'] != meta or row['cid'] != cid:
                raise ValueError('Foreign speaker cancellation')
            job = row['job']
            if job is not None:
                job['cancelled'].set(); job['pcm'] = None
                job.get('future').cancel() if job.get('future') is not None else None
            row['value'] = record(meta,cid,status='CANCELLED',reason='REQUEST_CANCELLED',visual=row['value']['visual'])
            return copy.deepcopy(row['value'])

    def reset(self):
        with self.lock:
            for job in self.jobs.values():
                job['cancelled'].set(); job['pcm'] = None
        def clear():
            hub = self.hub
            if hub is None:
                return
            if hub.binding is not None:
                binding = hub.binding
                for actor,attempt in tuple(binding.router.active.items()):
                    try:
                        with binding.registry._db() as db:
                            origin = db.execute('SELECT origin FROM binding_attempts WHERE attempt_id=?',(attempt,)).fetchone()
                        if origin is not None:
                            binding.registry.cancel(attempt,json.loads(origin[0]))
                    except (ValueError,sqlite3.Error,TimeoutError):
                        pass
                binding.router.active.clear(); binding.router.name_waiting.clear()
                binding.speaker.sessions.clear(); binding.speaker.aliases.clear()
            hub.speaker.sessions.clear(); self._refresh_public()
        if not self.closing.is_set():
            self.pool.submit(clear)

    def health(self):
        with self.lock:
            state = copy.deepcopy(self.public_state)
            state['ready'] = state['ready'] and not self.closing.is_set()
            return dict(version=1,**state,**self.counts,
                        data_origin=self.data_origin,queued_or_active=len(self.jobs),maximum_job_slots=2,
                        identity_templates_exported=False,profile_grants_issued=False)

    def close(self,*,timeout=2.):
        if not self.closing.is_set():
            self.closing.set()
            with self.lock:
                for job in self.jobs.values():
                    job['cancelled'].set(); job['pcm'] = None
                    if job.get('future') is not None:
                        job['future'].cancel()
            def finish():
                try:
                    hub = getattr(self,'hub',None)
                    if hub is not None:
                        hub.speaker.sessions.clear(); hub.speaker.store.close()
                finally:
                    self.lease.close()
            self.close_future = self.pool.submit(finish)
            self.pool.shutdown(wait=False)
        try:
            self.close_future.result(timeout=timeout)
            return True
        except FutureTimeout:
            return False  # Keep the lease until the native call actually returns.


class LocalFaceExchange:
    """Same scoped original face transaction/receipt, entirely on the board."""
    def __init__(self,business,meta,pcm,routed,bridge,capture_snapshot,text,*,is_current,cancel_event,deadline):
        self.business,self.meta,self.pcm = business,context(meta,pcm),pcm
        self.bridge,self.cancel_event = bridge,cancel_event or threading.Event()
        self.is_current,self.deadline = is_current,deadline or business.clock()+min(110,meta['budget_ms']/1000)
        self.attempt = routed['decision']['attempt_id']; self.token = secrets.token_hex(24); self.closed = False
        self.options = dict(is_current=is_current,cancel_event=self.cancel_event,deadline=self.deadline)
        def work(raw):
            return business.hub.binding.open_exchange(meta,self.attempt,self.token,min(110,max(.001,self.deadline-business.clock())))
        self.capability = business._call(work,meta,pcm,**self.options)['capability']
        self.exchange = bridge.exchange(meta,routed['binding_request'],capture_snapshot,text,self.current)

    def current(self):
        return not self.closed and not self.cancel_event.is_set() and self.business.clock()<self.deadline and self.is_current()

    @contextmanager
    def scope(self):
        if not self.current():
            raise InterruptedError('Local face exchange is no longer current')
        with self.bridge.scope(self.exchange):
            yield self

    def transform(self,value,final=True):
        if not self.current():
            raise InterruptedError('Local face result is no longer current')
        receipt = self.exchange.receipt(value,self.bridge.original_snapshot) if final else None
        raw = self.pcm
        def work(pcm):
            return self.business.hub.binding.face_result(self.meta,pcm,self.attempt,self.token,self.capability,value,
                                                        binding_receipt=receipt,final=final)
        result = self.business._call(work,self.meta,raw,**self.options)
        if final:
            self.closed = True; self.pcm = None
        return result['reply']

    def cancel(self):
        self.closed = True; self.pcm = None


def migrate_speaker_snapshots(source_root,target_root,*,expected_sha256,expected_model_id,
                              single_writer_stopped=False,data_origin='board'):
    """Import four frozen private files, preserving registry epochs and key.

    The caller first stops the sole old business writer and transfers a coherent
    snapshot directly to private board storage. This helper performs no network
    operation or live backup. It never overwrites a populated destination. The
    old namespace is derived from verified actual voice-link rows, not a name or
    caller-provided gallery string. A final private marker gates future opening.
    Returned evidence contains counts/flags only, never IDs, keys or templates.
    """
    if single_writer_stopped is not True:
        raise ValueError('A frozen single-writer handoff is required')
    names = _FILES+(_KEY,)
    if (not isinstance(expected_sha256,dict) or set(expected_sha256) != set(names)
            or any(not re.fullmatch(r'[0-9a-f]{64}',value or '') for value in expected_sha256.values())):
        raise ValueError('Every private source file requires an exact fingerprint')
    source = Path(source_root).absolute(); target = Path(target_root).absolute()
    if source.resolve() != source or source == target:
        raise ValueError('Separate regular private snapshot/destination required')
    if data_origin == 'board':
        if os.name != 'posix' or any(part.casefold() == 'win共享文件' for part in source.parts):
            raise ValueError('Source snapshots must stay in board-private storage')
        info = source.stat()
        if info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise PermissionError('Snapshot directory is not private')
    for name in names:
        path = source/name
        if path.is_symlink() or not path.is_file() or _fingerprint(path) != expected_sha256[name]:
            raise ValueError('Speaker source fingerprint mismatch')
    for name in _FILES:
        inspect_speaker_snapshot(source/name,name,model_id=expected_model_id)
    if (source/_KEY).stat().st_size != 32:
        raise ValueError('Original private receipt key is invalid')
    db = sqlite3.connect((source/'identity-links.sqlite3').as_uri()+'?mode=ro&immutable=1',uri=True,timeout=.05)
    try:
        db.execute('PRAGMA query_only=ON')
        namespaces = db.execute("SELECT DISTINCT store_id,model_id FROM modality_links WHERE modality='voice' AND state='ACTIVE'").fetchall()
    finally:
        db.close()
    if len(namespaces) > 1 or namespaces and (namespaces[0][1] != expected_model_id or
            not re.fullmatch(r'gallery-[0-9a-f]{32}',namespaces[0][0] or '')):
        raise ValueError('Active original speaker gallery namespaces disagree')
    namespace = namespaces[0][0] if namespaces else 'gallery-'+secrets.token_hex(16)
    lease = _WriterLease(target,data_origin=data_origin)
    try:
        owner_path = target/_OWNER
        if owner_path.exists():
            owner = json.loads(owner_path.read_text(encoding='utf-8'))
            if (owner.get('origin') == 'imported_snapshot' and owner.get('source_sha256') == expected_sha256
                    and owner.get('model_id') == expected_model_id and owner.get('data_origin') == data_origin):
                return dict(imported=False,idempotent=True,files=4,automatic_profile_access=False)
            raise ValueError('Speaker destination is not empty')
        if any(path.name != 'speaker-writer.lock' for path in target.iterdir()):
            raise ValueError('Speaker destination is not empty')
        for name in names:
            path = target/name; temporary = target/(name+'.partial')
            fd = os.open(str(temporary),os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,'O_NOFOLLOW',0),0o600)
            with os.fdopen(fd,'wb') as destination,(source/name).open('rb') as original:
                for chunk in iter(lambda:original.read(1024*1024),b''):
                    destination.write(chunk)
                destination.flush(); os.fsync(destination.fileno())
            if _fingerprint(temporary) != expected_sha256[name] or _fingerprint(source/name) != expected_sha256[name]:
                raise ValueError('Speaker snapshot changed during handoff')
            os.replace(temporary,path)
        _write_json(target/_NAMESPACE,dict(version=1,model_id=expected_model_id,store_id=namespace,
                                          origin='verified_active_voice_links' if namespaces else 'new_unlinked_namespace'))
        _write_json(owner_path,dict(version=1,data_origin=data_origin,model_id=expected_model_id,
                                   origin='imported_snapshot',source_sha256=expected_sha256))
        return dict(imported=True,idempotent=False,files=4,application_markers_preserved=True,
                    original_receipt_key_preserved=True,registry_epoch_preserved=True,
                    active_namespace_preserved=bool(namespaces),automatic_profile_access=False)
    finally:
        lease.close()

