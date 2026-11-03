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
import math
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

# Added only by the explicit migration bootstrap publisher, never by ordinary
# speaker construction. This origin survives later registrations/deletions.
for _schema_tables in _TABLES.values():
    _schema_tables['bm_production_origin'] = {'slot','database_uuid','bundle_id','sources_sha256','migration_manifest_sha256'}


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
        required = set(_TABLES[name]) - {'bm_production_origin'} - ({'binding_invalidations'} if name == 'identity-links.sqlite3' else set())
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
                        binding_invalidations=[],bm_production_origin=['slot'])[table]
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
        if (c.get('field_calibrated',False) is not False or
                any(type(c.get(key,default)) not in (int,float) or not math.isfinite(c.get(key,default))
                    or not floor <= c.get(key,default) <= 1 for key,default,floor in
                    (('threshold',.8,.35),('margin',.1,.1),('consistency',.6,.6)))):
            raise ValueError('Keep the configured uncalibrated operating policy')
        config = dict(anonymous_config or {'enabled':False})
        if (set(config)-{'enabled','threshold','margin','retention_seconds','max_clusters'}
                or type(config.get('enabled')) is not bool):
            raise ValueError('Anonymous collection requires explicit boolean configuration')
        if config['enabled']:
            from common.anonymous_voice import AnonymousPolicy
            AnonymousPolicy(threshold=config.get('threshold',.90),margin=config.get('margin',.10),
                            ttl_seconds=config.get('retention_seconds',86400),max_clusters=config.get('max_clusters',32))
        self.root = Path(private_root).absolute(); self.boot = board_boot_id
        self.clock,self.wall_clock,self.data_origin = clock,wall_clock,data_origin
        self.encoder_factory,self.quality,self.expected_model_id = encoder_factory,quality,expected_model_id
        self.config,self.calibration,self.on_evidence = config,c,on_evidence
        self.lock = threading.RLock(); self.local = threading.local(); self.closing = threading.Event()
        self.jobs = {}; self.latest = OrderedDict(); self.results = OrderedDict()
        self.last_evidence_error = None
        self.capacity = threading.BoundedSemaphore(2); self.counts = dict(submitted=0,complete=0,cancelled=0,unavailable=0,evidence_errors=0)
        self._probe_cache = OrderedDict(); self._probe_versions = OrderedDict()
        self._probe_captures = OrderedDict()
        self._probe_completed = 0
        self._probe_owner = None; self._probe_until = 0.; self._probe_wall_bounds = None
        self._probe_view = self._probe_metadata('IDLE',0)
        self._address_pending = OrderedDict(); self._address_leases = OrderedDict()
        self._address_token = None; self._address_epoch = 0
        self._address_view = dict(version=1,phase='WAITING',required_captures=1,
            matched_captures=0,session_cached=False,field_calibrated=False,
            identity_verified=False,personal_memory_allowed=False)
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
        token = self._probe_gallery() if hub is not None else None
        now = self.clock()
        with self.lock:
            self._address_token = token
            for key,row in tuple(self._address_leases.items()):
                if row['token'] != token or now >= row['until']:
                    self._address_leases.pop(key,None)
            for key,row in tuple(self._address_pending.items()):
                if now >= row['until']:
                    self._address_pending.pop(key,None)
            address = copy.deepcopy(self._address_view)
            address['session_cached'] = bool(self._address_leases)
        value = dict(ready=hub is not None,active=bool(hub and (hub.speaker.sessions or binding and
                    (binding.router.active or binding.router.name_waiting))),speaker_calibrated=False,
                    automatic_profile_access=False,pcm_persisted=False,single_cpu_worker=True,
                    identity_match_threshold=hub.speaker.threshold if hub is not None else None,
                    identity_ambiguity_margin=hub.speaker.margin if hub is not None else None,
                    enrollment_consistency=hub.speaker.consistency if hub is not None else None,
                    conversation_address=address,
                    self_match_probe=copy.deepcopy(self._probe_view))
        with self.lock:
            self.public_state = value

    def public(self):
        with self.lock:
            value = copy.deepcopy(self.public_state)
            limits = self._probe_until,self._probe_wall_bounds,self._probe_completed
        return self._probe_project(value,limits)

    def _probe_project(self,value,limits):
        probe = value.get('self_match_probe')
        if probe is None or probe['phase'] not in ('CANDIDATE','COLLECTING'):return value
        until,bounds,completed = limits
        try:
            expired = self.clock() >= until
            if bounds is not None:expired = expired or not bounds[0] <= self.wall_clock() < bounds[1]
        except Exception:
            # UI observation fails closed without hiding the worker's own clock
            # faults. Never call timeline time while holding the service lock.
            expired = True
        if expired:value['self_match_probe'] = self._probe_metadata('EXPIRED',0,completed=completed)
        return value

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
            if job['control']:
                self._clear_status_receipt(job['meta'])
                if not self._current():
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
                    value=future.result(timeout=min(.025,max(.001,job['deadline']-self.clock())))
                    if not self._job_current(job):
                        raise InterruptedError('Speaker result cancelled before adoption')
                    value=self._adopt_self_match(job,value)
                    if not self._job_current(job):
                        raise InterruptedError('Speaker result cancelled during adoption')
                    return value
                except FutureTimeout:
                    if future.done():
                        raise  # An operation's own timeout is not a poll timeout.
        except BaseException:
            job['cancelled'].set(); job['pcm'] = None
            if job['control']:
                # A cancellation may win after _run's final ownership check.
                # Serialize metadata invalidation after the original work, on
                # its sole worker; never undo an already committed identity.
                try:self.pool.submit(self._clear_status_receipt,job['meta'])
                except RuntimeError:pass  # Closing service cannot admit a later query.
                try:self.pool.submit(self._clear_self_match,job['meta'])
                except RuntimeError:pass
            raise

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
            if self._explicit_self_match(text):
                device = self.hub.speaker
                actor = meta['board_boot_id'],meta['session_id']
                if value is None:
                    self._probe_publish(meta,'UNAVAILABLE',0)
                elif not device.calibrated and actor not in device.sessions:
                    return self._self_match_query(meta,raw,value)
            return value
        return self._call(work,meta,pcm,**kwargs)

    @staticmethod
    def _explicit_self_match(text):
        from common.character_profile import strip_character_address
        from common.feature_intents import speaker_text
        from common.spoken_input import prepare_spoken_input
        if speaker_text(text) != '查询我的声纹':return False
        value = strip_character_address(prepare_spoken_input(text)['text']).strip(' ，,。！!？?')
        patterns = (
            r'(?:请)?(?:识别|辨认|辨别)(?:一下)?(?:我的)?(?:声纹|声音)[吗呢么啊呀]?',
            r'(?:你)?(?:现在)?(?:能|可以|会)?(?:识别|辨认|认出|认识|辨别)(?:我的)?(?:声纹|声音)[吗呢么啊呀]?',
            r'(?:你)?(?:听|听听|根据|通过)(?:我的)?声音(?:你)?(?:能|可以)?(?:知道|判断|识别|认出|辨别)?(?:我是谁|谁在说话)[吗呢么啊呀]?',
            r'(?:你)?(?:能|可以)?(?:根据|通过)(?:我的)?声音(?:识别|认出|辨认|辨别)(?:我|我是谁)[吗呢么啊呀]?',
        )
        return any(re.fullmatch(pattern,value) for pattern in patterns)

    @staticmethod
    def _probe_metadata(phase,count,*,completed=0):
        return dict(version=1,phase=phase,distinct_captures=max(0,min(3,count)),required_captures=3,
                    candidate_completed=max(0,min(65535,completed)),completed_is_historical=True,
                    field_calibrated=False,identity_verified=False,personal_memory_allowed=False)

    def _probe_publish(self,meta,phase,count,*,until=0.,wall_bounds=None):
        with self.lock:
            old = self._probe_owner
            if (old is not None and (old['board_boot_id'],old['session_id']) == (meta['board_boot_id'],meta['session_id'])
                    and old['generation'] > meta['generation']):return
            self._probe_owner = dict(meta); self._probe_until = until; self._probe_wall_bounds = wall_bounds
            self._probe_view = self._probe_metadata(phase,count,completed=self._probe_completed)
            self.public_state['self_match_probe'] = copy.deepcopy(self._probe_view)

    def _probe_gallery(self):
        device = self.hub.speaker
        rows = device.store.db.execute(
            'SELECT i.id,i.name,t.model_id,t.dimension,t.embedding FROM identities i JOIN templates t ON i.id=t.identity_id '
            'WHERE t.model_id=? AND t.dimension=? ORDER BY i.id',
            (device.encoder.model_id,device.encoder.dimension)).fetchall()
        # Private local provenance only. No template, digest, name or ID is public.
        digest = hashlib.sha256(json.dumps(rows,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
        return (device.encoder.model_id,device.store.revision,digest,device.threshold,device.margin)

    def _probe_matcher(self):
        analyzer = self.hub.progressive_speaker if self.hub is not None else None
        return getattr(analyzer,'provisional',None)

    def _adopt_self_match(self,job,value):
        meta = job['meta'];actor=meta['board_boot_id'],meta['session_id']
        key=(*actor,meta['request_id']);pair=meta['capture_id'],meta['pcm_sha256']
        with self.lock:
            if not self._owns(job) or job['cancelled'].is_set() or self.closing.is_set():return value
            row=self._probe_cache.get(key)
            if (row is None or row['meta']!=meta or type(value) is not str
                    or value != row['reply']):return value
            phase,until,bounds=row['phase'],row['until'],row.get('wall_bounds')
        if phase=='CANCELLED':return '这次声音比对已取消，没有确认身份。'
        # Adoption must enforce the same absolute proof expiry on the returned
        # text, not just on metadata. Clock faults here remain real failures.
        expired=self.clock()>=until
        if bounds is not None:expired=expired or not bounds[0]<=self.wall_clock()<bounds[1]
        if expired:
            self._probe_publish(meta,'EXPIRED',0)
            return '这次声音比对结果已过期，请重新自然说五到八秒。'
        with self.lock:
            if not self._owns(job) or job['cancelled'].is_set() or self.closing.is_set():return value
            ledger=self._probe_captures.get(actor,{})
            contribution=ledger.get(pair)
            if contribution is not None and contribution['meta']==meta:
                contribution['adopted']=True
            row=self._probe_cache.get(key)
            if row is None or row['meta']!=meta or row['phase']=='CANCELLED':return value
            # No job/closure is retained: either could keep captured PCM alive.
            if row['phase']=='CANDIDATE' and not row.get('counted',False):
                self._probe_completed=min(65535,self._probe_completed+1);row['counted']=True
            self._probe_publish(meta,row['phase'],row['count'],until=row['public_until'],wall_bounds=row.get('wall_bounds'))
        return value

    def _clear_self_match(self,meta):
        actor = meta['board_boot_id'],meta['session_id']; generation = meta['generation']
        matcher = self._probe_matcher()
        if matcher is not None:
            row = matcher.streaks.get(actor)
            if row is not None and row['generation'] <= generation:matcher.streaks.pop(actor,None)
            for key,row in tuple(matcher.results.items()):
                owner = row['context']
                if (owner['board_boot_id'],owner['session_id']) == actor and owner['generation'] <= generation:
                    matcher.results.pop(key,None)
        ledger=self._probe_captures.get(actor,{})
        for pair,row in tuple(ledger.items()):
            if row['meta']['generation']<=generation:ledger.pop(pair,None)
        key = meta['board_boot_id'],meta['session_id'],meta['request_id']
        owned = self._probe_owner
        relevant = key in self._probe_cache or (owned is not None and
            (owned['board_boot_id'],owned['session_id']) == actor and owned['generation'] <= generation)
        for row in self._probe_cache.values():
            owner = row['meta']
            if (owner['board_boot_id'],owner['session_id']) == actor and owner['generation'] <= generation:
                row.update(phase='CANCELLED',count=0,until=0.,reply=None,voice=None)
        if relevant:
            self._probe_cache[key] = dict(meta=dict(meta),token=None,phase='CANCELLED',count=0,until=0.,reply=None,voice=None)
            while len(self._probe_cache)>64:self._probe_cache.popitem(last=False)
            if owned is not None and (owned['board_boot_id'],owned['session_id']) == actor and owned['generation'] <= generation:
                self._probe_publish(meta,'CANCELLED',0)

    def _self_match_query(self,meta,raw,original_reply):
        binding = self.hub.binding; analyzer = self.hub.progressive_speaker; device = self.hub.speaker
        actor = meta['board_boot_id'],meta['session_id']; key = (*actor,meta['request_id'])
        if (binding is None or analyzer is None or self._probe_matcher() is None
                or device.threshold < .35 or device.margin < .1
                or device.store.threshold != device.threshold or device.store.ambiguity_margin != device.margin):
            self._probe_publish(meta,'UNAVAILABLE',0);return original_reply
        if (device.store.model_id != device.encoder.model_id or device.store.dimension != device.encoder.dimension):
            self._clear_self_match(meta);self._probe_publish(meta,'SOURCE_CHANGED',0)
            return '声音模型与登记记录不一致，这次比对未采用。'
        if not device.store.people():
            self._probe_publish(meta,'NO_ENROLLMENT',0);return original_reply
        token = self._probe_gallery(); now = self.clock()
        old = self._probe_cache.get(key)
        if old is not None:
            if old['meta'] != meta:raise ValueError('Foreign self match retry')
            if old['phase'] == 'CANCELLED':
                self._probe_publish(meta,'CANCELLED',0);return '这次声音比对已取消，没有确认身份。'
            bounds = old.get('wall_bounds')
            if (old['token'] != token or now >= old['until']
                    or bounds is not None and not bounds[0] <= self.wall_clock() < bounds[1]):
                phase = 'SOURCE_CHANGED' if old['token'] != token else 'EXPIRED'
                if phase=='SOURCE_CHANGED':self._clear_self_match(meta)
                self._probe_publish(meta,phase,0)
                return '这次声音比对结果已过期或登记记录已变化，请重新自然说五到八秒。'
            binding._control_evidence(meta,voice=old['voice'])
            self._probe_publish(meta,old['phase'],old['count'],until=old['public_until'],wall_bounds=bounds)
            return old['reply']
        self._probe_publish(meta,'PROCESSING',0)
        matcher = self._probe_matcher()
        previous = self._probe_versions.get(actor)
        ledger=self._probe_captures.setdefault(actor,{})
        self._probe_captures.move_to_end(actor)
        while len(self._probe_captures)>32:self._probe_captures.popitem(last=False)
        streak=matcher.streaks.get(actor)
        invalid_streak=bool(streak and any(
            pair not in ledger or not ledger[pair]['adopted'] or ledger[pair]['cancelled'].is_set()
            for pair in zip(streak['captures'],streak['digests'])))
        if previous is not None and previous != token or invalid_streak:
            matcher.streaks.pop(actor,None)
            ledger.clear()
            for cached_key,row in tuple(matcher.results.items()):
                if (row['context']['board_boot_id'],row['context']['session_id']) == actor:
                    matcher.results.pop(cached_key,None)
        self._probe_versions[actor] = token; self._probe_versions.move_to_end(actor)
        while len(self._probe_versions)>32:self._probe_versions.popitem(last=False)
        try:
            analyzed = analyzer.analyze(meta,raw,is_current=self._current)
            if not self._current():raise InterruptedError('Self match capture cancelled')
            if self._probe_gallery() != token:
                self._clear_self_match(meta);self._probe_publish(meta,'SOURCE_CHANGED',0)
                return '登记记录发生变化，这次声音比对未采用，请重新说话。'
            voice = analyzed[0] if isinstance(analyzed,tuple) and len(analyzed)==2 else None
            count = 0; phase = 'UNAVAILABLE'; reply = original_reply; wall_bounds=None
            if isinstance(voice,dict) and voice.get('state') == 'INSUFFICIENT_SPEECH':
                phase = 'INSUFFICIENT_SPEECH'
                reply = '这段声音尚未通过原语音质量检查，有效发声需要至少两点五秒。请自然连续说五到八秒，例如：你可以根据我的声音辨认我是谁吗。'
            elif isinstance(voice,dict) and voice.get('state') == 'NOT_CALIBRATED':
                row = matcher.streaks.get(actor)
                if (row is not None and row['generation']==meta['generation'] and row['signature'][:2]==token[:2]
                        and meta['capture_id'] in row['captures'] and meta['pcm_sha256'] in row['digests']
                        and 0 <= self.wall_clock()-row['at'] <= 30):
                    count = min(3,len(row['captures']))
                    pair=meta['capture_id'],meta['pcm_sha256']
                    if pair not in ledger:
                        ledger[pair]=dict(meta=dict(meta),cancelled=self.local.job['cancelled'],adopted=False)
                    for old_pair in tuple(ledger):
                        if old_pair not in set(zip(row['captures'],row['digests'])):ledger.pop(old_pair,None)
                elif row is None:ledger.clear()
                phase = 'COLLECTING' if count else 'NO_CANDIDATE'
                reply = ('已完成第'+str(count)+'次声音比对，还需要'+str(3-count)+'次不同录音的稳定匹配。请自然连续说五到八秒。' if count else
                         '这段声音还未形成稳定的登记声纹候选。完整现场校准尚未完成，我先不确定称呼。')
                if count == 3:
                    proof = matcher.proof(meta,store_id=self.hub.voice_reference(None)['store_id'])
                    if (proof is not None and proof.get('context')==meta and proof.get('model_id')==token[0]
                            and proof.get('gallery_revision')==token[1] and proof.get('consecutive_distinct')==3
                            and proof.get('field_calibrated') is False and self._current()
                            and proof['observed_at'] <= self.wall_clock() < proof['expires_at'] <= proof['observed_at']+2):
                        person = next((p for p in device.store.people() if p['person_id']==proof['identity_id']),None)
                        if person is not None:
                            phase = 'CANDIDATE'
                            wall_bounds=(proof['observed_at'],proof['expires_at'])
                            reply = '声音候选称呼是'+person['display_name']+'。完整现场校准尚未完成。'
                    if phase != 'CANDIDATE':
                        phase = 'EXPIRED';count=0
                        reply = '这次声音候选已过期，尚不能确认称呼，请重新自然说五到八秒。'
            if not self._current():raise InterruptedError('Self match result cancelled')
            # The 600s original descriptor cache contains only its strict
            # NOT_CALIBRATED/insufficient evidence, never the candidate name.
            binding._control_evidence(meta,voice=voice if isinstance(voice,dict) else None)
            now = self.clock(); ttl=2. if wall_bounds is None else max(0.,min(2.,wall_bounds[1]-self.wall_clock()))
            public_until=now+(ttl if phase=='CANDIDATE' else 30.)
            self._probe_cache[key]=dict(meta=dict(meta),token=token,phase=phase,count=count,until=now+ttl,
                public_until=public_until,wall_bounds=wall_bounds,reply=reply,voice=copy.deepcopy(voice))
            while len(self._probe_cache)>64:self._probe_cache.popitem(last=False)
            # The original _call marks this result adopted before publishing
            # its phase. A later queued capture cannot reuse pending evidence.
            return reply
        except BaseException:
            self._clear_self_match(meta)
            raise

    def submit_analysis(self,meta,pcm,conversation_id,*,visual=None,gallery_provider=None,on_evidence=None,**kwargs):
        cid = validate_conversation_id(conversation_id); meta = context(meta,pcm)
        visual = validate_visual(visual,meta) if visual is not None else unavailable(meta)
        if gallery_provider is not None and not callable(gallery_provider):
            raise ValueError('Local read-only gallery provider must be callable')
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
                observed_visual = visual
                if binding is not None and gallery_provider is not None:
                    # Read/hash only on the original sole CPU worker, never the
                    # foreground route or GTK tick. This is observation only:
                    # no enrollment router, consent, template or grant is made.
                    try:
                        packet = gallery_provider()
                        if not self._current():
                            raise InterruptedError('Face observation no longer owns the capture')
                        if observed_visual['state'] == 'FACE_AT_CAPTURE_BOUNDARIES':
                            age = round(self.clock()*1000)-observed_visual['evidence']['source_end_ms']
                            if not 0 <= age < 3000:
                                observed_visual = unavailable(meta,'VISUAL_EXPIRED_BEFORE_ANALYSIS')
                        reference = None
                        if packet is not None:
                            from common.face_binding_wire import validate_packet
                            packet = validate_packet(packet,meta)
                            digest = binding.ingest_gallery(packet)['packet_sha256']
                            reference = binding._gallery_for(meta,digest)
                        binding._face_reference(meta,observed_visual,reference)
                    except InterruptedError:
                        raise
                    except (OSError,ValueError,KeyError,TypeError,TimeoutError,sqlite3.Error):
                        # A bad/missing face readback cannot invent a face name
                        # or suppress an otherwise valid independent voice.
                        binding._face_reference(meta,observed_visual,None)
                analyzer = self.hub.progressive_speaker
                if analyzer is None:
                    voice,alias = self.hub.speaker.analyze(meta,raw),None
                else:
                    voice,alias = analyzer.analyze(meta,raw,is_current=self._current)
                self._capture_conversation_address(meta,cid,voice)
                identity = None
                if binding is not None:
                    proof = analyzer.provisional.proof(meta,store_id=self.hub.voice_reference(None)['store_id'])
                    proofs = [proof] if proof is not None else []
                    face = binding.face_naming_proof(meta,observed_visual)
                    if face is not None:
                        proofs.append(face)
                    identity = binding.registry.resolve(meta,proofs,anonymous=alias)
                value = record(meta,cid,status='COMPLETE',reason='DESCRIPTIVE_EVIDENCE_ONLY',
                               voice=voice,visual=observed_visual,anonymous=alias,identity=identity)
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
                except Exception as exc:
                    name = type(exc).__name__
                    error = (name if name in ('PermissionError','TimeoutError','ValueError','TypeError',
                        'RuntimeError','OSError','ClockUnavailable','MemoryBusy','ScopeDenied',
                        'IdempotencyConflict') else
                        'SQLiteError' if isinstance(exc,sqlite3.Error) else 'OtherError')
                    with self.lock:
                        self.counts['evidence_errors'] += 1
                        self.last_evidence_error = dict(stage='evidence_callback',error=error)
        future.add_done_callback(finished)
        return self.analysis_result(meta,cid)

    def _capture_conversation_address(self,meta,cid,voice):
        """Reuse this capture's existing named match; never encode a second time."""
        if not self._current():raise InterruptedError('Address capture cancelled')
        device=self.hub.speaker
        if (device.store.model_id!=device.encoder.model_id or device.store.dimension!=device.encoder.dimension
                or device.threshold<.35 or device.margin<.1 or device.store.threshold!=device.threshold
                or device.store.ambiguity_margin!=device.margin):
            with self.lock:
                self._address_leases.pop((meta['board_boot_id'],meta['session_id'],cid),None)
            return
        token = self._probe_gallery(); phase = 'NO_FRESH_RESULT'; name = None
        matcher = self._probe_matcher(); row = matcher.streaks.get((meta['board_boot_id'],meta['session_id'])) if matcher else None
        state = voice.get('state') if isinstance(voice,dict) else None
        if state == 'INSUFFICIENT_SPEECH':phase = 'INSUFFICIENT_SPEECH'
        elif state == 'NOT_CALIBRATED' and voice.get('voiced_ms',0) >= 2500:
            if row is None:phase = 'NO_MATCH'
            elif (row['generation'] == meta['generation'] and row['signature'][:2] == token[:2]
                    and (meta['capture_id'],meta['pcm_sha256']) in set(zip(row['captures'],row['digests']))
                    and 0 <= self.wall_clock()-row['at'] <= 30):
                person = next((p for p in self.hub.speaker.store.people() if p['person_id']==row['signature'][2]),None)
                if person is not None:phase='MATCHED';name=person['display_name']
        if not self._current():raise InterruptedError('Address result cancelled')
        key = meta['board_boot_id'],meta['session_id'],meta['request_id']
        with self.lock:
            self._address_pending[key] = dict(meta=dict(meta),cid=cid,token=token,phase=phase,
                name=name,until=self.clock()+20.,cancelled=self.local.job['cancelled'],epoch=self._address_epoch)
            self._address_pending.move_to_end(key)
            while len(self._address_pending)>64:self._address_pending.popitem(last=False)

    def adopt_conversation_address(self,meta,conversation_id,*,is_current=lambda:True,cancel_event=None):
        """A current consumer adopts only private metadata, never a profile grant."""
        meta=context(meta);cid=validate_conversation_id(conversation_id)
        if not is_current() or cancel_event is not None and cancel_event.is_set():return False
        key=meta['board_boot_id'],meta['session_id'],meta['request_id'];actor=meta['board_boot_id'],meta['session_id']
        lease_key=(*actor,cid);now=self.clock()
        with self.lock:
            packet=self._address_pending.get(key);result=self.results.get(key)
            if (self.closing.is_set() or self.latest.get(actor)!=meta or packet is None
                    or result is None or result['cid']!=cid or result['value']['status']!='COMPLETE'
                    or packet['meta']!=meta or packet['cid']!=cid or packet['epoch']!=self._address_epoch
                    or packet['token']!=self._address_token or packet['cancelled'].is_set()
                    or now>=packet['until'] or cancel_event is not None and cancel_event.is_set()):return False
            if packet['phase']=='MATCHED':
                self._address_leases[lease_key]=dict(name=packet['name'],token=packet['token'],until=now+300.)
                self._address_leases.move_to_end(lease_key)
                while len(self._address_leases)>32:self._address_leases.popitem(last=False)
            elif packet['phase']=='NO_MATCH':self._address_leases.pop(lease_key,None)
            self._address_view.update(phase=packet['phase'],matched_captures=int(packet['phase']=='MATCHED'),
                session_cached=lease_key in self._address_leases)
            self.public_state['conversation_address']=copy.deepcopy(self._address_view)
            return packet['phase']=='MATCHED'

    def conversation_address(self,owner,conversation_id,*,cancel_event,deadline):
        """Bounded first-turn wait; later turns reuse this conversation's RAM name."""
        cid=validate_conversation_id(conversation_id)
        if not isinstance(owner,dict) or set(owner)!={'board_boot_id','session_id','generation','request_id'}:
            raise ValueError('Explicit request owner required for conversational address')
        if owner['board_boot_id']!=self.boot:raise ValueError('Foreign conversational address boot')
        key=owner['board_boot_id'],owner['session_id'],owner['request_id'];actor=owner['board_boot_id'],owner['session_id']
        lease_key=(*actor,cid)
        while not cancel_event.is_set():
            now=self.clock()
            with self.lock:
                row=self.results.get(key);latest=self.latest.get(actor)
                if (self.closing.is_set() or row is None or row['cid']!=cid or latest!=row['meta']
                        or any(row['meta'].get(k)!=v for k,v in owner.items()) or now>=deadline):return None
                lease=self._address_leases.get(lease_key)
                if lease and lease['token']==self._address_token and now<lease['until']:
                    return dict(display_name=lease['name'],source='current_conversation_voice_candidate',
                        field_calibrated=False,identity_verified=False,personal_memory_allowed=False)
                status=row['value']['status'];until=min(deadline,row['deadline']);meta=dict(row['meta'])
            if status!='PENDING':
                if status=='COMPLETE':
                    self.adopt_conversation_address(meta,cid,cancel_event=cancel_event,
                        is_current=lambda:not cancel_event.is_set() and self.clock()<deadline)
                    with self.lock:
                        lease=self._address_leases.get(lease_key)
                        if (lease and lease['token']==self._address_token and self.clock()<lease['until']
                                and not cancel_event.is_set() and self.latest.get(actor)==meta):
                            return dict(display_name=lease['name'],source='current_conversation_voice_candidate',
                                field_calibrated=False,identity_verified=False,personal_memory_allowed=False)
                return None
            if now>=until:
                self.analysis_result(meta,cid)
                return None
            cancel_event.wait(min(.02,max(.001,until-now)))
        return None

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

    def _clear_status_receipt(self,meta):
        actor=meta['board_boot_id'],meta['session_id']
        receipts=getattr(self.hub.speaker,'save_receipts',{}) if self.hub is not None else {}
        receipt=receipts.get(actor)
        if receipt is not None and receipt['generation']<=meta['generation']:
            receipts.pop(actor,None)

    def _cancel_actor(self,meta):
        hub = self.hub; actor = meta['board_boot_id'],meta['session_id']
        self._clear_status_receipt(meta)
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
        self._clear_self_match(meta)

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
            self._address_epoch += 1
            self._address_pending.clear();self._address_leases.clear()
            self._address_view.update(phase='WAITING',matched_captures=0,session_cached=False)
            self.public_state['conversation_address']=copy.deepcopy(self._address_view)
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
            hub.speaker.sessions.clear()
            getattr(hub.speaker,'save_receipts',{}).clear()
            matcher = self._probe_matcher()
            if matcher is not None:matcher.streaks.clear();matcher.results.clear()
            for row in self._probe_cache.values():row.update(phase='CANCELLED',count=0,until=0.,reply=None,voice=None)
            self._probe_versions.clear();self._probe_owner=None;self._probe_until=0.;self._probe_wall_bounds=None
            self._probe_captures.clear()
            self._probe_view=self._probe_metadata('CANCELLED',0,completed=self._probe_completed)
            self._refresh_public()
        if not self.closing.is_set():
            self.pool.submit(clear)

    def health(self):
        with self.lock:
            state = copy.deepcopy(self.public_state)
            state['ready'] = state['ready'] and not self.closing.is_set()
            value = dict(version=1,**state,**self.counts,
                        data_origin=self.data_origin,queued_or_active=len(self.jobs),maximum_job_slots=2,
                        last_evidence_error=copy.deepcopy(self.last_evidence_error),
                        identity_templates_exported=False,profile_grants_issued=False)
            limits=self._probe_until,self._probe_wall_bounds,self._probe_completed
        return self._probe_project(value,limits)

    def close(self,*,timeout=2.):
        if not self.closing.is_set():
            self.closing.set()
            with self.lock:
                for job in tuple(self.jobs.values()):
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
        if any(_fingerprint(source/name) != expected_sha256[name] or
               _fingerprint(target/name) != expected_sha256[name] for name in names):
            raise ValueError('Speaker snapshot changed before final handoff publication')
        _write_json(target/_NAMESPACE,dict(version=1,model_id=expected_model_id,store_id=namespace,
                                          origin='verified_active_voice_links' if namespaces else 'new_unlinked_namespace'))
        _write_json(owner_path,dict(version=1,data_origin=data_origin,model_id=expected_model_id,
                                   origin='imported_snapshot',source_sha256=expected_sha256))
        return dict(imported=True,idempotent=False,files=4,application_markers_preserved=True,
                    original_receipt_key_preserved=True,registry_epoch_preserved=True,
                    active_namespace_preserved=bool(namespaces),automatic_profile_access=False)
    finally:
        lease.close()

