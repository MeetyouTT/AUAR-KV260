"""Bounded project GPU admission; never loads, unloads or kills a model.

Observed allocator/device memory is not a guarantee against unrelated apps.
Adaptive enforcement requires an explicit measured calibration identifier and
phase budgets. The default observes availability while retaining pipelining.
"""
from collections import Counter,deque
from dataclasses import dataclass
import csv
import http.client
import json
import math
import subprocess
import socket
import threading
import time
from urllib.parse import urlsplit
import uuid

MIB=1024*1024

class GpuBusy(RuntimeError):pass
class GpuProbeUnavailable(RuntimeError):pass

@dataclass(frozen=True)
class MemorySample:
    gpu_uuid:str
    total_mib:int
    free_mib:int
    used_mib:int
    observed_at:float

    def public(self,now):
        return dict(available=True,gpu_uuid=self.gpu_uuid,total_mib=self.total_mib,free_mib=self.free_mib,
                    used_mib=self.used_mib,age_ms=round(max(0,now-self.observed_at)*1000,2),
                    scope='device snapshot; not a reservation or inference peak')

class NvidiaMemoryProbe:
    """At most one short CLI sample per TTL, with a bounded subprocess lifetime."""
    def __init__(self,*,gpu_index=0,ttl=.25,timeout=.4,clock=time.monotonic,run=subprocess.run):
        if type(gpu_index) is not int or not 0<=gpu_index<16:raise ValueError('Invalid GPU index')
        if not 0<ttl<=5 or not 0<timeout<=1:raise ValueError('Invalid GPU probe limits')
        self.gpu_index=gpu_index;self.ttl=ttl;self.timeout=timeout;self.clock=clock;self.run=run
        self.lock=threading.Lock();self.cached=None;self.checked=None;self.error='';self.calls=0

    def read(self,*,timeout=None):
        began=self.clock();limit=min(self.timeout,timeout) if timeout is not None else self.timeout
        if limit<=0:raise TimeoutError('GPU probe deadline expired')
        if not self.lock.acquire(timeout=limit):raise GpuProbeUnavailable('GPU probe refresh in progress')
        try:
            now=self.clock()
            if self.checked is not None and now-self.checked<self.ttl:
                if self.error:raise GpuProbeUnavailable(self.error)
                return self.cached
            limit-=max(0,self.clock()-began)
            if limit<=0:raise TimeoutError('GPU probe deadline expired')
            try:
                self.calls+=1
                result=self.run(['nvidia-smi','--id='+str(self.gpu_index),
                  '--query-gpu=uuid,memory.total,memory.free,memory.used','--format=csv,noheader,nounits'],
                  capture_output=True,text=True,timeout=limit,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                if result.returncode:raise ValueError('GPU CLI failed')
                rows=list(csv.reader(result.stdout.strip().splitlines()))
                if len(rows)!=1 or len(rows[0])!=4:raise ValueError('Invalid GPU CLI response')
                identity,total,free,used=[v.strip() for v in rows[0]];total,free,used=int(total),int(free),int(used)
                if not identity.startswith('GPU-') or not 0<=free<=total or not 0<=used<=total or total<=0:
                    raise ValueError('Invalid GPU memory sample')
                self.cached=MemorySample(identity,total,free,used,self.clock());self.error=''
            except (OSError,ValueError,subprocess.SubprocessError) as exc:
                self.error='GPU memory unavailable: '+type(exc).__name__
                self.cached=None
            self.checked=self.clock()
            if self.error:raise GpuProbeUnavailable(self.error)
            return self.cached
        finally:self.lock.release()

    def public(self):
        # Cached immutable samples keep health checks independent of a slow
        # in-progress CLI. Admission always uses the locked read() path.
        value=self.cached
        if value is not None:return dict(value.public(self.clock()),probe_calls=self.calls,ttl_ms=round(self.ttl*1000))
        return dict(available=False,error=self.error or 'Not sampled',probe_calls=self.calls,ttl_ms=round(self.ttl*1000))

class OllamaResidencyProbe:
    """Read /api/ps, separate from inventory/service readiness; never generates."""
    def __init__(self,host,model,*,ttl=2.,timeout=.4,clock=time.monotonic,fetch=None):
        target=urlsplit(host)
        if target.scheme!='http' or target.hostname not in ('127.0.0.1','localhost') or target.path not in ('','/'):
            raise ValueError('Residency probe must use a local Ollama endpoint')
        if not 0<ttl<=30 or not 0<timeout<=1:raise ValueError('Invalid residency limits')
        self.host,self.model,self.ttl,self.timeout,self.clock=host,model,ttl,timeout,clock
        self.fetch=fetch or self._fetch;self.lock=threading.Lock();self.checked=None;self.cached=None;self.calls=0
    def _remaining(self,deadline):
        remaining=deadline-self.clock()
        if remaining<=0:raise TimeoutError('Residency probe deadline expired')
        return remaining
    def _fetch(self,*,deadline):
        # Own the actual socket throughout response reading. A shutdown timer
        # bounds trickled HTTP headers/body, not merely each separate read.
        target=urlsplit(self.host);connection=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        response=None;timer=None
        try:
            connection.settimeout(self._remaining(deadline));connection.connect(('127.0.0.1',target.port or 80))
            def expire():
                try:connection.shutdown(socket.SHUT_RDWR)
                except OSError:pass
            timer=threading.Timer(self._remaining(deadline),expire);timer.daemon=True;timer.start()
            connection.settimeout(self._remaining(deadline))
            connection.sendall(('GET /api/ps HTTP/1.1\r\nHost: '+target.hostname+':'+str(target.port or 80)+'\r\nConnection: close\r\n\r\n').encode('ascii'))
            response=http.client.HTTPResponse(connection);response.begin();raw=response.read(1024*1024+1)
            self._remaining(deadline)
            if response.status!=200 or len(raw)>1024*1024:raise ValueError('Invalid residency response')
            return json.loads(raw)
        finally:
            if timer is not None:timer.cancel()
            if response is not None:response.close()
            connection.close()
    def _unavailable(self,error):
        return dict(available=False,llm_resident=None,llm_gpu_resident=None,llm_gpu_bytes=None,
                    model=self.model,error=error,fresh=False,sampled_mono=None,age_ms=None,ttl_ms=round(self.ttl*1000))
    def _result(self,*,fresh=False):
        return dict(self.cached,fresh=fresh,sampled_mono=self.checked,
                    age_ms=round(max(0,self.clock()-self.checked)*1000,2),ttl_ms=round(self.ttl*1000),probe_calls=self.calls)
    def status(self,*,deadline=None,refresh=False):
        began=self.clock()
        if deadline is not None and (type(deadline) not in (int,float) or not math.isfinite(deadline)):
            raise ValueError('Residency requires a finite absolute deadline')
        until=min(deadline,began+self.timeout) if deadline is not None else began+self.timeout
        remaining=until-self.clock()
        if remaining<=0:return self._unavailable('Residency request deadline expired')
        if not self.lock.acquire(timeout=remaining):return self._unavailable('Residency refresh lock exceeded request deadline')
        try:
            now=self.clock()
            if now>=until:return self._unavailable('Residency request deadline expired')
            if refresh or self.checked is None or now-self.checked>=self.ttl:
                try:
                    self.calls+=1;value=self.fetch(deadline=until);self._remaining(until)
                    if not isinstance(value,dict):raise ValueError('Invalid residency object')
                    rows=value.get('models')
                    if not isinstance(rows,list):raise ValueError('Invalid residency rows')
                    matching=[r for r in rows if isinstance(r,dict) and self.model in (r.get('name'),r.get('model'))]
                    if len(matching)>1:raise ValueError('Repeated configured model residency')
                    row=matching[0] if matching else None;gpu_bytes=row.get('size_vram') if row else 0
                    if type(gpu_bytes) is not int or gpu_bytes<0:raise ValueError('Invalid resident GPU byte count')
                    current=dict(available=True,llm_resident=bool(row),llm_gpu_resident=bool(row and gpu_bytes),llm_gpu_bytes=gpu_bytes,
                      model=self.model,scope='Ollama /api/ps; independent of /api/tags model availability')
                except (OSError,ValueError,http.client.HTTPException) as exc:
                    current=self._unavailable('Residency unavailable: '+type(exc).__name__)
                    # A tiny caller budget must not poison a healthy cached
                    # sample for subsequent callers with a full probe budget.
                    if deadline is not None and deadline<began+self.timeout:return current
                self.cached=current
                self.checked=self.clock()
                return self._result(fresh=self.cached.get('available') is True)
            return self._result()
        finally:self.lock.release()

@dataclass(frozen=True)
class GpuPolicy:
    mode:str='observe'
    max_pending:int=2
    max_wait_seconds:float=5.
    sample_max_age_seconds:float=.75
    reserve_mib:int=0
    llm_extra_mib:int=0
    llm_cold_extra_mib:int=0
    tts_extra_mib:int=0
    gpu_uuid:str=''
    calibration_id:str=''

    def __post_init__(self):
        if self.mode not in ('observe','adaptive','serial'):raise ValueError('Invalid GPU policy mode')
        if type(self.max_pending) is not int or not 1<=self.max_pending<=8:raise ValueError('GPU queue must be bounded')
        if type(self.max_wait_seconds) not in (int,float) or not math.isfinite(self.max_wait_seconds) or not 0<self.max_wait_seconds<=5:
            raise ValueError('GPU wait may not exceed the existing five-second admission bound')
        if type(self.sample_max_age_seconds) not in (int,float) or not math.isfinite(self.sample_max_age_seconds) or not .05<=self.sample_max_age_seconds<=5:raise ValueError('Invalid GPU sample age')
        for value in (self.reserve_mib,self.llm_extra_mib,self.llm_cold_extra_mib,self.tts_extra_mib):
            if type(value) is not int or not 0<=value<=65536:raise ValueError('Invalid measured GPU budget')
        if not isinstance(self.calibration_id,str) or len(self.calibration_id)>128 or not isinstance(self.gpu_uuid,str) or len(self.gpu_uuid)>80:
            raise ValueError('Invalid GPU calibration identity')
        if self.mode!='observe' and (not self.calibration_id or not self.gpu_uuid or self.reserve_mib<128 or self.llm_extra_mib<=0 or self.tts_extra_mib<=0):
            raise ValueError('Enforcement requires calibrated GPU identity, phase budgets and reserve')
        if self.mode!='observe' and self.llm_cold_extra_mib<self.llm_extra_mib:
            raise ValueError('Cold LLM budget must cover resident decoding budget')

    @classmethod
    def from_dict(cls,value):
        if not isinstance(value,dict) or set(value)-set(cls.__dataclass_fields__):raise ValueError('Unexpected GPU policy field')
        return cls(**value)

class Lease:
    def __init__(self,coordinator,token,kind,wait_ms):
        self.coordinator,self.token,self.kind,self.wait_ms=coordinator,token,kind,wait_ms;self.released=False
    def release(self):
        if not self.released:self.coordinator.release(self.token);self.released=True
    def __enter__(self):return self
    def __exit__(self,*_):self.release()

class GpuCoordinator:
    def __init__(self,policy=None,probe=None,*,llm_residency=None,clock=time.monotonic):
        self.policy=policy or GpuPolicy();self.probe=probe or NvidiaMemoryProbe();self.clock=clock
        self.llm_residency=llm_residency;self.last_residency=None
        self.condition=threading.Condition();self.active={};self.pending=deque();self.counts=Counter()
        self.last_reason='';self.last_wait_ms=0.;self.tts_stats={};self.tts_counts=Counter()

    @staticmethod
    def _cancelled(cancelled):return bool(cancelled is not None and (cancelled.is_set() if hasattr(cancelled,'is_set') else cancelled()))

    def _memory(self,deadline):
        try:return self.probe.read(timeout=max(.001,min(.4,deadline-self.clock())))
        except (GpuProbeUnavailable,OSError,ValueError,TimeoutError):return None

    def _fresh_resident(self,residency,*,after=None,after_sequence=None):
        if not (residency and residency.get('available') is True and residency.get('llm_resident') is True and residency.get('fresh') is True):return False
        sampled=residency.get('sampled_mono')
        if type(sampled) not in (int,float) or not 0<=self.clock()-sampled<=self.policy.sample_max_age_seconds:return False
        if after is None or sampled>after:return True
        sequence=residency.get('probe_calls')
        return (sampled==after and type(sequence) is int and type(after_sequence) is int
                and sequence>after_sequence)

    def _llm_extra(self,residency):
        # Unknown residency uses the larger measured load budget. Inventory
        # availability is never accepted as evidence that weights are loaded.
        return self.policy.llm_extra_mib if self._fresh_resident(residency) else self.policy.llm_cold_extra_mib

    def _eligible(self,kind,ticket,sample,residency):
        # One operation of each kind; queue order is FIFO within each phase.
        if any(v['kind']==kind for v in self.active.values()):return False,'same_phase_active'
        if any(row['kind']==kind for row in list(self.pending)[:list(self.pending).index(ticket)]):return False,'same_phase_queued'
        p=self.policy
        if p.mode=='observe':return True,'observed'
        if p.mode=='serial' and self.active:return False,'serialized_peak'
        if sample is None:return False,'memory_unavailable'
        if sample.gpu_uuid!=p.gpu_uuid:return False,'gpu_identity_changed'
        if not 0<=self.clock()-sample.observed_at<=p.sample_max_age_seconds:return False,'memory_sample_stale'
        extra=self._llm_extra(residency) if kind=='llm' else p.tts_extra_mib
        # A lease reserves its declared unmaterialized working peak. This is
        # intentionally conservative: visible live allocations can overlap it.
        # Once /api/ps confirms a cold load has completed, remaining decode
        # work uses its smaller budget. Do not keep reserving loaded weights
        # twice through the first-sentence TTS phase.
        reserved=sum((p.llm_extra_mib if self._fresh_resident(residency,after=v['admitted_at'],after_sequence=v['observation_sequence']) else p.llm_cold_extra_mib)
                     if v['kind']=='llm' else v['extra_mib'] for v in self.active.values())
        if sample.free_mib<p.reserve_mib+extra+reserved:return False,'insufficient_headroom'
        return True,'headroom_available'

    def acquire(self,kind,*,deadline,cancelled=None):
        if kind not in ('llm','tts'):raise ValueError('Invalid GPU phase')
        if type(deadline) not in (int,float) or not math.isfinite(deadline):raise ValueError('Require original finite deadline')
        began=self.clock();until=min(deadline,began+self.policy.max_wait_seconds);token=uuid.uuid4().hex
        ticket={'token':token,'kind':kind}
        with self.condition:
            if len(self.pending)>=self.policy.max_pending:self.counts['queue_full']+=1;raise GpuBusy('GPU admission queue is full')
            self.pending.append(ticket)
        try:
            while True:
                if self._cancelled(cancelled):raise InterruptedError('GPU admission cancelled')
                if self.clock()>=deadline:raise TimeoutError('Original GPU request budget expired')
                if self.clock()>=until:raise GpuBusy('GPU admission wait bound expired: '+self.last_reason)
                sample=self._memory(min(deadline,until))
                with self.condition:refresh_residency=(kind=='llm' or any(v['kind']=='llm' for v in self.active.values()))
                residency=(self.llm_residency.status(deadline=min(deadline,until),refresh=refresh_residency)
                           if self.llm_residency is not None else None)
                with self.condition:
                    if self._cancelled(cancelled):raise InterruptedError('GPU admission cancelled')
                    if self.clock()>=deadline:raise TimeoutError('Original GPU request budget expired')
                    if self.clock()>=until:raise GpuBusy('GPU admission wait bound expired: '+self.last_reason)
                    self.last_residency=residency
                    allowed,reason=self._eligible(kind,ticket,sample,residency);self.last_reason=reason
                    if allowed:
                        extra=self._llm_extra(residency) if kind=='llm' else self.policy.tts_extra_mib
                        self.active[token]={'kind':kind,'extra_mib':extra,
                            'admitted_at':self.clock(),'observation_sequence':residency.get('probe_calls') if residency else None,
                            'llm_was_resident':self._fresh_resident(residency)};self.pending.remove(ticket)
                        waited=(self.clock()-began)*1000;self.last_wait_ms=waited;self.counts[kind+'_admitted']+=1
                        return Lease(self,token,kind,waited)
                    remaining=min(until,deadline)-self.clock()
                    if remaining<=0:self.counts['resource_busy']+=1;raise GpuBusy('GPU admission unavailable: '+reason)
                    self.condition.wait(timeout=min(.05,remaining))
        finally:
            with self.condition:
                if ticket in self.pending:self.pending.remove(ticket)
                self.condition.notify_all()

    def release(self,token):
        with self.condition:
            self.active.pop(token,None);self.condition.notify_all()

    def note_tts(self,result,*,warmup=False):
        cache=bool(result.get('cache_hit'))
        with self.condition:
            self.tts_counts['warmup' if warmup else 'cache_hit' if cache else 'generated']+=1
            self.tts_stats['last_cache_hit']=cache;self.tts_stats['last_warmup']=bool(warmup)
            value=result.get('cuda_inference')
            # Never treat a cached WAV or cold warmup as a fresh inference peak.
            if not cache and isinstance(value,dict) and value.get('measured') is True:
                names=('baseline_allocated_bytes','baseline_reserved_bytes','peak_allocated_bytes','peak_reserved_bytes',
                       'allocated_extra_peak_bytes','reserved_extra_peak_bytes')
                if all(type(value.get(k)) is int and 0<=value[k]<=2**63-1 for k in names):
                    measured={key:value[key] for key in names}
                    if type(value.get('includes_cuda_initialization')) is bool:measured['includes_cuda_initialization']=value['includes_cuda_initialization']
                    self.tts_stats['warmup_inference' if warmup else 'last_inference']=measured
                    if not warmup:self.tts_stats['max_reserved_extra_peak_bytes']=max(self.tts_stats.get('max_reserved_extra_peak_bytes',0),value['reserved_extra_peak_bytes'])

    def public(self):
        # This probe only calls /api/ps, caches for two seconds, and never
        # interprets a prior age=0 snapshot as permanently fresh residency.
        residency=self.llm_residency.status() if self.llm_residency is not None else self.last_residency
        with self.condition:
            p=self.policy
            value=dict(version=1,mode=p.mode,calibration_id=p.calibration_id,enforcing=p.mode!='observe',
              active={kind:sum(v['kind']==kind for v in self.active.values()) for kind in ('llm','tts')},
              queued=len(self.pending),queue_limit=p.max_pending,max_wait_ms=round(p.max_wait_seconds*1000),
              last_reason=self.last_reason,last_wait_ms=round(self.last_wait_ms,2),counts=dict(self.counts),
              llm_residency=dict(residency) if residency else {'available':False,'llm_resident':None,'llm_gpu_bytes':None},
              llm_requirement={'extra_mib':self._llm_extra(residency),
                'kind':'resident_decode' if self._fresh_resident(residency) else 'cold_or_unknown','admission_refresh_required':True},
              tts_counts=dict(self.tts_counts),tts_stats=dict(self.tts_stats),speech_or_identity_stored=False,
              guarantee_scope='project admission only; external allocations can change after a sample')
        value['memory']=self.probe.public();return value

class DeferredLlmEvents:
    """Drain the small producer queue while TTS awaits GPU admission.

    Keeping the producer moving lets an LLM lease finish even when the consumer
    is waiting for TTS. Both event count and UTF-8 payload bytes remain bounded.
    """
    def __init__(self,max_events=1024,max_bytes=65536):
        self.rows=deque();self.bytes=0;self.max_events=max_events;self.max_bytes=max_bytes;self.high_water=0
    @staticmethod
    def size(item):
        kind,value=item
        try:payload=json.dumps(value,ensure_ascii=False,separators=(',',':')).encode('utf-8')
        except TypeError:payload=(type(value).__name__+': '+str(value)[:300]).encode('utf-8')
        return 16+len(kind.encode('utf-8'))+len(payload)
    def append(self,item):
        size=self.size(item)
        if len(self.rows)>=self.max_events or self.bytes+size>self.max_bytes:raise ValueError('Deferred LLM events exceed bound')
        self.rows.append((item,size));self.bytes+=size;self.high_water=max(self.high_water,self.bytes)
    def drain(self,pending,limit=64):
        import queue
        for _ in range(limit):
            try:item=pending.get_nowait()
            except queue.Empty:return
            self.append(item)
    def get(self,pending,timeout):
        if self.rows:
            item,size=self.rows.popleft();self.bytes-=size;return item
        return pending.get(timeout=timeout)
