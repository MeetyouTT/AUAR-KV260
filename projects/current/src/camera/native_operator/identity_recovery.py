"""Audited one-time operator recovery; no identity DB or motor access."""
import copy,ctypes as C,hashlib,json,os,threading,time
from pathlib import Path


class RealtimeCall:
    """Only the current calling thread, precisely around the C optional call."""
    def __init__(self,function):self.function=function
    def __call__(self,*args):
        policy=os.sched_getscheduler(0);param=os.sched_getparam(0)
        os.sched_setscheduler(0,os.SCHED_FIFO,os.sched_param(10))
        try:return self.function(*args)
        finally:os.sched_setscheduler(0,policy,param)


def atomic(path,value):
    temp=path.with_name(path.name+'.'+str(os.getpid()))
    with temp.open('x') as f:json.dump(value,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
    os.chmod(temp,0o600);os.replace(temp,path)


class RecoveryWorker:
    def __init__(self,feature,settings,record):
        self.feature,self.settings,self.record=feature,settings,record
        self.context=feature.runner.owner.native_context
        self.closed=threading.Event();self.lock=threading.RLock()
        self.thread=threading.Thread(target=self.work,name='identity-operator-recovery',daemon=True)
        self.native=self.context.native.aura_native_request_operator_recovery
        self.native.restype=C.c_int
        self.native.argtypes=[C.c_uint64,C.c_uint,C.c_uint64,C.c_uint64,C.c_uint64]
    def start(self):self.thread.start()
    def close(self):
        self.closed.set();self.thread.join(timeout=3)
        if self.thread.is_alive():
            self.context._retain(self,'operator diagnostic did not join')
            raise RuntimeError('Operator diagnostic still active; retain native owner')
    def save(self):atomic(Path(self.record['audit_path']),self.record)
    def request(self,task):
        expected=self.settings['requests'][task];index={'yunet':1,'sface':2}[task]
        end=time.monotonic()+180;refused=0
        while not self.closed.is_set() and time.monotonic()<end:
            before=self.context.snapshot();r=before['recovery'][index-1]
            if (before['fenced'] or r['history_opaque'] or r['faults']!=expected['faults']
                    or r['attempts']!=expected['attempts'] or r['phase']!=3 or r['reason']!=2):
                self.record[task]={'status':'PRECONDITION_CHANGED_NO_UNLOCK','before':before};self.save();return False
            code=self.native(self.context.handle,index,r['faults'],r['attempts'],before['primary_period_overruns'])
            if code==0:
                after=self.context.snapshot();updated=after['recovery'][index-1]
                assert all(updated[k]==r[k] for k in ('faults','attempts','recoveries','attempt_count','attempt_times_ns'))
                assert updated['phase']==1 and after['disabled'][index]
                self.record[task]={'status':'COOLDOWN_REQUEST_ACCEPTED','before':before,'after':after,'guard_refusals':refused}
                self.save();return True
            if code!=1:raise RuntimeError('Native operator API error')
            refused+=1
            if self.closed.wait(1):return False
        self.record[task]={'status':'HEALTHY_INTERVAL_NOT_OBTAINED_NO_UNLOCK','guard_refusals':refused};self.save();return False
    def sface_probes(self):
        # A declared synthetic health request has its own creation time/TTL.
        # No camera timestamp, face match or enrollment result is fabricated.
        source=bytes(112*112*3);runner=self.feature.runner.runner
        expected_hash=None;submitted=0;end=time.monotonic()+60;events=[]
        while not self.closed.is_set() and time.monotonic()<end:
            state=self.context.snapshot();policy=state['recovery'][1]
            if policy['phase']==0:
                self.record['health_probes']={'status':'RUNNING','synthetic_submissions':submitted,'events':events,
                    'accuracy_evaluated':False,'business_match_published':False}
                self.save();return True
            if policy['phase']==3:return False
            if policy['phase']==1 and time.monotonic_ns()<policy['cooldown_until_ns']:
                self.closed.wait(.1);continue
            if submitted>=3:break
            with self.lock:
                if self.closed.is_set():return False
                created=time.monotonic_ns();execution=runner.execute_encoded(source,source_expires_ns=created+250_000_000)
                report=execution.report;submitted+=int(bool(report['submitted']))
                row={'report':report,'source_kind':'synthetic_zero_health_probe','created_mono_ns':created}
                events.append(row)
                if report['hardcap'] or report['guard'] or self.context.quarantined:break
                if report['completed']:
                    if len(execution.outputs)!=1 or len(execution.outputs[0])!=128 or not any(execution.outputs[0]):
                        row['output_check']='INVALID_NO_ACK';break
                    digest=hashlib.sha256(execution.outputs[0]).hexdigest()
                    if expected_hash is not None and digest!=expected_hash:
                        row['output_check']='INCONSISTENT_NO_ACK';break
                    expected_hash=digest;row['output_sha256']=digest
                    execution=self.context.confirm_result(execution);row['confirmed_report']=execution.report
                    self.feature.schedule.note_result('sface',execution.report)
            self.closed.wait(.1)
        self.record['health_probes']={'status':'NOT_RECOVERED','synthetic_submissions':submitted,'events':events,
            'accuracy_evaluated':False,'business_match_published':False};self.save();return False
    def work(self):
        try:
            marker=Path(self.record['operator_marker'])
            if self.settings['request_boot_id']!=Path('/proc/sys/kernel/random/boot_id').read_text().strip():return
            try:
                with marker.open('x') as f:json.dump({'audit':self.record['audit_path'],'pid':os.getpid(),'scope':'one operator recovery per task in this boot'},f)
                os.chmod(marker,0o600)
            except FileExistsError:
                self.record['status']='OPERATOR_REQUEST_ALREADY_CONSUMED';self.save();return
            self.record['status']='WAITING_NATIVE_HEALTH_GUARD';self.save()
            if not self.request('sface'):return
            if not self.sface_probes():return
            # Restore the face detector only after identity's three real
            # native health completions. Natural current frames certify YuNet.
            if not self.request('yunet'):return
            end=time.monotonic()+90
            while not self.closed.wait(.2) and time.monotonic()<end:
                snapshot=self.context.snapshot();p=snapshot['recovery'][0]
                if p['phase']==0:
                    self.record['status']='BOTH_OPTIONAL_RUNNING';self.record['final']=snapshot;self.save();return
                if p['phase']==3:break
            self.record['status']='YUNET_NOT_RECOVERED';self.record['final']=self.context.snapshot();self.save()
        except BaseException as exc:
            self.record['status']='FAILED_NO_OPERATOR_RETRY';self.record['error']=type(exc).__name__+': '+str(exc)[:300]
            self.save()


def install(settings,root):
    from board.vision import native_startup as ns,dpu_sface, native_binding
    original_preflight,original_attach=ns.preflight,ns.attach
    original_init=native_binding.NativeContext.__init__
    feature_init,feature_close,feature_feature=dpu_sface.DpuSFace.__init__,dpu_sface.DpuSFace.close,dpu_sface.DpuSFace.feature
    record={'status':'PREPARING','audit_path':str(root/('recovery-audit-'+str(os.getpid())+'.json')),
        'operator_marker':str(root/('operator-consumed-'+settings['request_boot_id']+'.json')),
        'request':settings,'artificial_counter_reset':False,'mechanical_actions':0}
    def preflight(config,**kwargs):
        native=config['native_execution']
        if native['library']!=settings['old_library'] or native['library_sha256']!=settings['old_library_sha256']:
            raise RuntimeError('Native predecessor differs; explicit migration required')
        pin=native['seed'];raw=Path(pin['path']).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=pin['sha256']:raise RuntimeError('Checkpoint changed')
        document=json.loads(raw);predecessor=document['source_unit_sha256']
        if predecessor not in (settings['predecessor_unit_sha256'],settings['unit_sha256']):
            raise RuntimeError('Checkpoint unit not in explicit ABI-compatible migration')
        record['checkpoint_sha256']=pin['sha256'];record['checkpoint_unit_sha256']=predecessor
        native.update(library=settings['library'],library_sha256=settings['library_sha256'],source_unit_sha256=predecessor)
        try:loaded=original_preflight(config,**kwargs)
        finally:native['source_unit_sha256']=settings['unit_sha256']
        record['exact_seed_before_operator_request']=copy.deepcopy(loaded['seed'])
        atomic(Path(record['audit_path']),record)
        return loaded
    def context_init(self,owner,library,digest):
        original_init(self,owner,library,digest)
        self.native.aura_native_optional_execute=RealtimeCall(self.native.aura_native_optional_execute)
    def attach(config,state,owner,loaded):
        result=original_attach(config,state,owner,loaded)
        result[1].protection_handoff.update(operator_recovery_audit=record['audit_path'],
            native_abi_compatible_migration=True,predecessor_unit_sha256=record['checkpoint_unit_sha256'],
            native_unit_sha256=settings['unit_sha256'],optional_execution_thread_policy='SCHED_FIFO_10_scoped_restore')
        return result
    def initialize(self,*args,**kwargs):
        feature_init(self,*args,**kwargs)
        self._operator_worker=RecoveryWorker(self,settings,record);self._operator_worker.start()
    def feature(self,*args,**kwargs):
        with self._operator_worker.lock:return feature_feature(self,*args,**kwargs)
    def close(self):
        worker=getattr(self,'_operator_worker',None)
        if worker is not None:worker.close()
        return feature_close(self)
    ns.preflight=preflight;ns.attach=attach;native_binding.NativeContext.__init__=context_init
    dpu_sface.DpuSFace.__init__=initialize;dpu_sface.DpuSFace.feature=feature;dpu_sface.DpuSFace.close=close
