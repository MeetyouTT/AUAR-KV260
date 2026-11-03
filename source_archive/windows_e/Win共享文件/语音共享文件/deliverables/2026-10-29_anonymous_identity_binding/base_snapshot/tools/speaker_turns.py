"""Bounded asynchronous CPU evidence using the existing hub's one speaker worker."""
import copy,threading,time
from collections import OrderedDict
from common.asr_wire import context
from common.speaker_turns import record

class SpeakerTurns:
    def __init__(self,hub,*,clock=time.monotonic):
        self.hub=hub;self.clock=clock;self.lock=threading.RLock()
        self.rows=OrderedDict();self.latest=OrderedDict();self.streaks=OrderedDict()
        # Futures receive a mutable descriptor, never an immutable PCM argument
        # retained in the executor queue after cancellation.
        self.work={}
        self.max_rows=256;self.result_lifetime=600.;self.analysis_seconds=12.
    @staticmethod
    def key(meta):return meta['board_boot_id'],meta['session_id'],meta['request_id']
    @staticmethod
    def actor(meta):return meta['board_boot_id'],meta['session_id']
    def _expire(self):
        now=self.clock()
        for key,row in list(self.rows.items()):
            if row['value']['status']=='PENDING' and now>=row['deadline']:
                row['value']=record(row['meta'],row['cid'],status='EXPIRED',reason='ANALYSIS_DEADLINE',visual=row['visual'])
                self.streaks.pop(self.actor(row['meta']),None)
                self._release_pending(key)
            if now>=row['remove_at']:self._release_pending(key);self.rows.pop(key)
    def _release_pending(self,key):
        job=self.work.get(key)
        if job is None:return
        job['cancelled']=True;job['pcm']=None
        future=job.get('future')
        if future is not None:future.cancel()
    def _finished(self,key,job):
        with self.lock:
            job['pcm']=None
            if self.work.get(key) is job:self.work.pop(key)
        self.hub.speaker_gate.release()
    def _row(self,meta,cid):
        self._expire();row=self.rows.get(self.key(meta))
        if row is None or row['meta']!=context(meta) or row['cid']!=cid:raise ValueError('Foreign or expired speaker receipt')
        return row
    def submit(self,meta,pcm,cid,visual=None):
        meta=context(meta,pcm);value=record(meta,cid,visual=visual)
        actor=self.actor(meta);key=self.key(meta)
        with self.lock:
            self._expire()
            if key in self.rows:return copy.deepcopy(self._row(meta,cid)['value'])
            previous=self.latest.get(actor)
            if previous is not None and meta['generation']<=previous[0]:raise ValueError('Stale or reused speaker generation')
            self.latest[actor]=(meta['generation'],meta['request_id']);self.latest.move_to_end(actor)
            while len(self.latest)>32:
                expired,_=self.latest.popitem(last=False);self.streaks.pop(expired,None)
            while len(self.rows)>=self.max_rows:
                removed,_=self.rows.popitem(last=False);self._release_pending(removed)
            now=self.clock();row=dict(meta=meta,cid=cid,visual=value['visual'],value=value,
              deadline=now+min(self.analysis_seconds,meta['budget_ms']/1000),remove_at=now+self.result_lifetime)
            self.rows[key]=row
            if self.hub.speaker is None:
                row['value']=record(meta,cid,status='UNAVAILABLE',reason='SPEAKER_MODEL_UNAVAILABLE',visual=visual)
            elif not self.hub.speaker_gate.acquire(False):
                row['value']=record(meta,cid,status='UNAVAILABLE',reason='SPEAKER_WORKER_BUSY',visual=visual)
            else:
                job={'pcm':pcm,'cancelled':False,'started':False};pcm=None;self.work[key]=job
                try:future=self.hub.speaker_pool.submit(self._analyze,key,meta,job)
                except Exception:
                    job['pcm']=None;self.work.pop(key,None)
                    self.hub.speaker_gate.release();row['value']=record(meta,cid,status='UNAVAILABLE',reason='SPEAKER_DISPATCH_FAILED',visual=visual)
                else:
                    job['future']=future;future.add_done_callback(lambda _,key=key,job=job:self._finished(key,job))
            return copy.deepcopy(row['value'])
    def _analyze(self,key,meta,job):
        raw=None
        with self.lock:
            self._expire();row=self.rows.get(key)
            if job['cancelled'] or row is None or row['value']['status']!='PENDING':
                job['pcm']=None;return
            raw=job['pcm'];job['pcm']=None;job['started']=True
        try:
            if job['cancelled']:return
            voice=self.hub.speaker.analyze(meta,raw)
        except Exception:voice=None
        finally:raw=None
        # No PCM, embeddings, face pixels or text are retained in any row.
        with self.lock:
            self._expire();row=self.rows.get(key)
            if row is None or row['meta']!=meta or row['value']['status']!='PENDING':return
            actor=self.actor(meta)
            latest=self.latest.get(actor)==(meta['generation'],meta['request_id'])
            if voice is None:
                self.streaks.pop(actor,None);row['value']=record(meta,row['cid'],status='UNAVAILABLE',reason='SPEAKER_ANALYSIS_FAILED',visual=row['visual']);return
            if voice['state']=='CANDIDATE' and latest:
                signature=(voice['model_id'],voice['gallery_revision'],voice['candidate_id'])
                old=self.streaks.get(actor)
                count=1
                if old and old['signature']==signature and self.clock()-old['at']<=30:
                    # Replayed PCM under a new request cannot strengthen identity.
                    distinct=meta['pcm_sha256'] not in old['digests'] and meta['capture_id'] not in old['captures']
                    count=min(3,old['count']+int(distinct))
                    digests=(old['digests']+[meta['pcm_sha256']])[-3:] if distinct else old['digests']
                    captures=(old['captures']+[meta['capture_id']])[-3:] if distinct else old['captures']
                else:digests=[meta['pcm_sha256']];captures=[meta['capture_id']]
                self.streaks[actor]={'signature':signature,'count':count,'digests':digests,'captures':captures,'at':self.clock()}
                self.streaks.move_to_end(actor)
                while len(self.streaks)>32:self.streaks.popitem(last=False)
                voice=dict(voice,consecutive_distinct=count,state='CANDIDATE_STABLE' if count==3 else 'CANDIDATE')
            elif latest:self.streaks.pop(actor,None)
            row['value']=record(meta,row['cid'],status='COMPLETE',reason='DESCRIPTIVE_EVIDENCE_ONLY',voice=voice,visual=row['visual'])
    def result(self,meta,cid):
        with self.lock:return copy.deepcopy(self._row(context(meta),cid)['value'])
    def cancel(self,meta,cid):
        with self.lock:
            row=self._row(context(meta),cid)
            row['value']=record(meta,cid,status='CANCELLED',reason='REQUEST_CANCELLED',visual=row['visual'])
            self._release_pending(self.key(meta))
            self.streaks.pop(self.actor(meta),None)
            return copy.deepcopy(row['value'])
    def health(self):
        with self.lock:
            self._expire();return dict(version=1,buffered_results=len(self.rows),maximum_results=self.max_rows,
              pending=sum(row['value']['status']=='PENDING' for row in self.rows.values()),single_cpu_worker=True,
              descriptive_only=True,automatic_profile_access=False,pcm_persisted=False)
