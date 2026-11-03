"""Business integration against an explicit fake native executor; no models."""
import copy
import ast
import ctypes as C
import hashlib
import json
import os
from pathlib import Path
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np

from board.identity.deferred import DeferredIdentity
from board.identity.face_targets import FaceTargetService
from board.vision.dpu_sface import DpuSFace
from board.vision.dpu_yunet import DpuYuNet
from board.vision.dpu_vision_runtime import AdmissionCancelled, SlotAdmissionDenied, SlotUnavailable
from board.vision.native_binding import Execution, Report, State, Seed, Recovery, Ack
from board.vision.native_binding import CompletionUnknown
from board.vision.native_errors import PrimaryAdmissionDeferred
from board.vision.native_protection import (isolated_maintenance_seed, make_native_seed,
    checkpoint_document, load_business_checkpoint, consume_checkpoint, write_checkpoint)
from board.vision.native_runtime import NativePinnedRunner, TensorPort
from board.vision.native_schedule import NativeDpuSchedule
from board.vision.native_yolo import NativeYoloOwner, PrimaryFrameDeferred
from board.vision import native_startup


BOOT = '008f3e1b-c627-4b98-b120-d2a460cdbcbe'


class Clock:
    def __init__(self):self.ns=1_000_000_000_000
    def seconds(self):return self.ns/1e9
    def millis(self):return self.ns//1_000_000
    def advance(self, ns):self.ns+=ns


def policy(phase=0):
    return dict(enabled=1,phase=phase,reason=0,probe_successes=0,attempt_count=0,
        history_opaque=0,opaque_attempt_count=0,cooldown_until_ns=0,fault_primary_calls=0,
        fault_primary_overruns=0,faults=0,attempts=0,recoveries=0,observed_ns=0,
        attempt_times_ns=[0,0])


class FakeContext:
    def __init__(self,clock):
        self.clock=clock;self.adopted=True;self.quarantined=False;self.calls=[];self.next_token=1
        self.before_return=None;self.after_native=None;self.confirm_calls=[];self.gate=threading.Lock()
        self.state=dict(abi_version=2,active=0,active_task=3,fenced=0,fence_reason=0,
            primary_waiting=0,next_primary_ns=clock.ns+100_000_000,seed_loaded=1,
            quiesced=0,checkpoint_kind=1,disabled=[0,0,0],admissions=[50,10,8],
            overruns=[0,0,0],completed=[50,10,8],native_failures=[0,0,0],not_submitted=[0,0,0],
            primary_calls=50,primary_period_overruns=0,last_primary_ns=clock.ns,
            recovery=[policy(),policy()],pending_result_tokens=[0,0,0])
    def snapshot(self):return copy.deepcopy(self.state)
    def announce_primary(self,deadline):self.state['next_primary_ns']=deadline;self.calls.append(('announce',deadline))
    def wait_optional(self,task,until):
        self.calls.append(('wait',task,until));return not self.state['disabled'][task]
    def execute_yolo(self,image,**kwargs):
        with self.gate:
            self.calls.append(('yolo',kwargs))
            self.state['admissions'][0]+=1;self.state['primary_calls']+=1
        report=self.report(0,kwargs['source_expires_ns'])
        return Execution(report,((1.,2.,11.,22.,.9,0.),),self.clock.ns,kwargs['source_expires_ns'])
    def report(self,task,expires):
        start=self.clock.ns;self.clock.advance(1_000_000)
        return dict(abi_version=2,outcome=0,hardcap=0,guard=0,submitted=1,completed=1,
            native_status=0,task=task,start_ns=start,native_return_ns=self.clock.ns,
            release_decision_ns=self.clock.ns,after_unlock_ns=self.clock.ns,
            business_ready=int(task!=2 or self.state['recovery'][1]['phase']==0),
            result_fresh=int(self.clock.ns<expires),recovery_phase=self.state['recovery'][max(task-1,0)]['phase'],
            reserved=0,result_token=0)
    def confirm_result(self,execution):
        report=dict(execution.report)
        if report['result_token']:
            fresh=execution.native_usable
            self.confirm_calls.append((report['task'],report['result_token'],fresh))
            task=report['task'];p=self.state['recovery'][task-1]
            self.state['pending_result_tokens'][task]=0
            if fresh:
                p['probe_successes']+=1
                if p['probe_successes']==3:p['phase']=0;p['recoveries']+=1
            report.update(business_ready=int(fresh and p['phase']==0),result_fresh=int(fresh),recovery_phase=p['phase'])
        return Execution(report,execution.outputs,execution.returned_mono_ns,execution.source_expires_ns)
    def close(self):self.calls.append(('close',))


class FakeLowRunner:
    def __init__(self,context,task):
        self.context=context;self.task=task;self.calls=0;self.reject=False
    def execute_encoded(self,source,*,source_expires_ns):
        self.calls+=1
        task=self.task
        if self.reject:
            report=dict(abi_version=2,outcome=1,hardcap=0,guard=0,submitted=0,completed=0,
                native_status=-1,task=task,start_ns=0,native_return_ns=0,release_decision_ns=0,
                after_unlock_ns=0,business_ready=0,result_fresh=0,recovery_phase=0,result_token=0)
            return Execution(report,(),self.context.clock.ns,source_expires_ns)
        with self.context.gate:
            report=self.context.report(task,source_expires_ns)
            self.context.state['admissions'][task]+=1;self.context.state['completed'][task]+=1
            if self.context.state['recovery'][task-1]['phase']==2:
                report['result_token']=self.context.next_token;self.context.next_token+=1
                self.context.state['pending_result_tokens'][task]=report['result_token']
        if self.context.after_native:self.context.after_native(report)
        outputs=(bytes([32])+bytes(127),) if task==2 else ()
        if self.context.before_return:self.context.before_return(source_expires_ns)
        return Execution(report,outputs,self.context.clock.ns,source_expires_ns)
    def close(self):pass


class Metrics:
    optional_diagnostics=None
    def __init__(self):self.values=[];self.after_dequantize=None
    def value(self,key,value):self.values.append((key,value))
    def elapsed(self,key,began):
        if self.after_dequantize and key.endswith('.dequantize'):self.after_dequantize()


def pinned(context,schedule,metrics,task):
    runner=NativePinnedRunner.__new__(NativePinnedRunner)
    runner.owner=SimpleNamespace(native_context=context)
    runner.schedule=schedule;runner.runner=FakeLowRunner(context,task)
    shape=[1,112,112,3] if task==2 else [1,320,320,3]
    runner.inputs=[TensorPort(dict(name='input',dims=shape,dtype='xint8',fix_point=7))]
    runner.outputs=[TensorPort(dict(name='output',dims=[1,128],dtype='xint8',fix_point=5))]
    runner.input_fix=7;runner.metrics=metrics;runner.stage_kind='sface' if task==2 else 'yunet'
    runner.last_ms=runner.last_execution=runner.last_report=None
    return runner


class BusinessTests(unittest.TestCase):
    def setUp(self):
        self.clock=Clock();self.context=FakeContext(self.clock)
        self.schedule=NativeDpuSchedule(self.context,yunet_slot_wait_ms=100,sface_slot_wait_ms=100)
        self.metrics=Metrics()
        self.mono=patch('time.monotonic_ns',side_effect=lambda:self.clock.ns);self.mono.start();self.addCleanup(self.mono.stop)
        self.seconds=patch('time.monotonic',side_effect=self.clock.seconds);self.seconds.start();self.addCleanup(self.seconds.stop)

    def sface(self,phase=0):
        self.context.state['recovery'][1]=policy(phase)
        face=DpuSFace.__new__(DpuSFace);face.native_critical=True
        face.schedule=self.schedule;face.clock=self.clock.millis;face.source_ttl=1000;face._closed=False
        face.runner=pinned(self.context,self.schedule,self.metrics,2)
        for n in ('requests','execution_attempts','completed','features_returned','deferred','slot_denials','expired_after_admission'):
            setattr(face,n,0)
        return face

    def test_sface_first_two_probes_deferred_third_feature_and_ACK_after_return(self):
        face=self.sface(2);crop=np.zeros((112,112,3),dtype=np.uint8)
        for i in range(2):
            with self.assertRaises(DeferredIdentity):face.feature(crop,source_mono_ms=self.clock.millis())
            self.assertEqual(face.completed,i+1)
            self.assertEqual(face.features_returned,0)
            self.assertEqual(self.context.state['recovery'][1]['phase'],2)
        value=face.feature(crop,source_mono_ms=self.clock.millis())
        self.assertEqual(value.shape,(128,));self.assertEqual(value[0],1.)
        self.assertEqual(face.completed,3);self.assertEqual(face.features_returned,1)
        self.assertEqual(self.context.state['recovery'][1]['phase'],0)
        self.assertEqual(len(self.context.confirm_calls),3)

    def test_sface_late_GIL_return_does_not_count_probe(self):
        face=self.sface(2)
        self.context.before_return=lambda expires:setattr(self.clock,'ns',expires)
        with self.assertRaises(DeferredIdentity):
            face.feature(np.zeros((112,112,3),np.uint8),source_mono_ms=self.clock.millis())
        self.assertEqual(face.completed,1);self.assertEqual(face.features_returned,0)
        self.assertEqual(self.context.state['recovery'][1]['probe_successes'],0)
        self.assertFalse(self.context.confirm_calls[-1][2])

    def test_source_expiring_after_decode_never_returns_identity(self):
        face=self.sface()
        stamp=self.clock.millis()
        self.metrics.after_dequantize=lambda:setattr(self.clock,'ns',(stamp+face.source_ttl)*1_000_000)
        with self.assertRaises(DeferredIdentity):face.feature(np.zeros((112,112,3),np.uint8),source_mono_ms=stamp)
        self.assertEqual(face.completed,1);self.assertEqual(face.features_returned,0)

    def test_sface_rejection_is_not_a_probe_or_completed_feature(self):
        face=self.sface(2);face.runner.runner.reject=True
        self.schedule.sface_slot_wait_ms=0
        with self.assertRaises(DeferredIdentity):face.feature(np.zeros((112,112,3),np.uint8),source_mono_ms=self.clock.millis())
        self.assertEqual(face.execution_attempts,0);self.assertEqual(face.completed,0)
        self.assertFalse(self.context.confirm_calls)

    def test_pre_execute_cancel_never_calls_native_runner(self):
        runner=pinned(self.context,self.schedule,self.metrics,2)
        def cancel():raise AdmissionCancelled('closed')
        with self.assertRaises(AdmissionCancelled) as error:
            runner.execute_encoded(np.zeros((1,112,112,3),np.int8),source_expires_ns=self.clock.ns+1000,pre_execute=cancel)
        self.assertEqual(runner.runner.calls,0);self.assertTrue(error.exception.native_not_submitted)

    def test_yunet_guard_uses_source_expiry_and_existing_retry_deadline(self):
        detector=DpuYuNet.__new__(DpuYuNet);detector.native_critical=True;detector.schedule=self.schedule
        detector.runner=pinned(self.context,self.schedule,self.metrics,1);detector.runner.runner.reject=True
        self.schedule.yunet_slot_wait_ms=0
        def check():pass
        check.source_expires_monotonic_ns=self.clock.ns+500_000_000
        check.deadline_monotonic=self.clock.seconds()+.2
        with self.assertRaises(SlotAdmissionDenied):detector._native_scheduled(np.zeros((1,320,320,3),np.int8),check)
        self.assertEqual(detector.runner.runner.calls,1)

    def test_no_legacy_python_optional_lease_can_be_used(self):
        with self.assertRaises(RuntimeError):self.schedule.optional('sface')

    def test_primary_original_deadline_and_captured_TTL_are_not_reanchored(self):
        original=SimpleNamespace(handle=None,config={'score_threshold':.3},fingerprint='0x101000056010407',
            reference_check={},pipeline_metrics=self.metrics,ownership=None)
        owner=NativeYoloOwner(original,self.context,self.schedule)
        stamp=self.clock.millis();deadline=self.clock.seconds()+.1
        with self.schedule.primary(deadline):
            self.clock.advance(30_000_000)
            detections=owner.detect_bgr(np.zeros((24,24,3),np.uint8),source_mono_ms=stamp)
        args=[c[1] for c in self.context.calls if c[0]=='yolo'][-1]
        self.assertEqual(args['primary_finish_ns'],int(deadline*1e9))
        self.assertEqual(args['source_expires_ns'],(stamp+750)*1_000_000)
        self.assertTrue(detections)

    def test_yolo_expired_result_defers_without_closing_owner(self):
        original=SimpleNamespace(handle=None,config={'score_threshold':.3},fingerprint='0x101000056010407',
            reference_check={},pipeline_metrics=self.metrics,ownership=None)
        owner=NativeYoloOwner(original,self.context,self.schedule)
        with self.schedule.primary(self.clock.seconds()+.1):
            with self.assertRaises(PrimaryFrameDeferred):
                owner.detect_bgr(np.zeros((2,2,3),np.uint8),source_mono_ms=self.clock.millis()-750)
        self.assertFalse(any(c[0]=='close' for c in self.context.calls))

    def test_native_wait_is_one_condition_call_and_owns_no_Python_metrics_lock(self):
        original=self.context.wait_optional
        def wait(task,until):
            self.assertTrue(self.schedule._metrics_lock.acquire(False));self.schedule._metrics_lock.release()
            return original(task,until)
        self.context.wait_optional=wait
        self.assertTrue(self.schedule.wait_for_optional('sface',self.clock.seconds()+.1))
        self.assertEqual(len([x for x in self.context.calls if x[0]=='wait']),1)

    def test_native_health_preserves_LATCHED_and_opaque_history(self):
        p=self.context.state['recovery'][0];p.update(phase=3,reason=1,faults=5,attempts=4,recoveries=4,
            history_opaque=1,opaque_attempt_count=1)
        self.context.state['disabled'][1]=1;self.context.state['overruns'][1]=5
        health=self.schedule.health()
        self.assertEqual(health['yunet_recovery']['faults'],5)
        self.assertEqual(health['yunet_recovery']['phase'],'LATCHED')
        self.assertFalse(self.schedule.recovery_ready('yunet'))
        self.assertTrue(self.schedule.disabled('yunet'))

    def test_both_LATCHED_health_preserves_each_known_counter_without_recovery(self):
        # Numeric shape of the latest observed production state. This fake
        # test does not claim health is an exact executable migration seed.
        for index, reason, faults, attempts, recoveries, window in (
                (0,1,5,4,4,1),(1,2,3,2,2,2)):
            self.context.state['recovery'][index].update(phase=3,reason=reason,
                faults=faults,attempts=attempts,recoveries=recoveries,
                history_opaque=1,opaque_attempt_count=window)
            self.context.state['disabled'][index+1]=1
            self.context.state['overruns'][index+1]=faults
        self.context.state['admissions'][1:]=[62491,755]
        self.context.state['completed'][2]=755
        self.schedule.inherited_sface_counters=dict(requests=1178,execution_attempts=755,
            completed=755,features_returned=748,deferred=430,slot_denials=397,
            expired_after_admission=0)
        face=self.sface(3)
        # sface() creates a fixture policy; restore the observed latched policy.
        self.context.state['recovery'][1].update(reason=2,faults=3,attempts=2,
            recoveries=2,history_opaque=1,opaque_attempt_count=2)
        health=self.schedule.health()
        for task, expected in (('yunet',(5,4,4,1)),('sface',(3,2,2,2))):
            value=health[task+'_recovery']
            self.assertEqual((value['faults'],value['attempts'],value['recoveries'],
                value['attempts_in_window']),expected)
            self.assertEqual(value['phase'],'LATCHED')
            self.assertTrue(value['history_opaque'])
            self.assertTrue(self.schedule.disabled(task))
            self.assertFalse(self.schedule.recovery_ready(task))
            self.assertFalse(self.schedule.recovery_probe_allowed(task))
        self.assertFalse(face.availability()['ready'])
        self.assertFalse(any(c[0]=='wait' for c in self.context.calls))
        self.assertEqual(self.schedule.inherited_sface_counters['completed'],755)

    def test_face_target_attaches_original_expiry_and_skip_is_not_negative_observation(self):
        service=FaceTargetService.__new__(FaceTargetService)
        service.clock=self.clock.millis;service.ttl=1000;service.closed=False
        service.lock=threading.Lock();service.discarded=0
        stamp=self.clock.millis()-100;seen=[]
        class Detector:
            native_critical=True
            def detect_with_admission_guard(inner,image,check):
                check();seen.append(check.source_expires_monotonic_ns)
                raise SlotUnavailable('fake notification denial')
        service._process((np.zeros((2,2,3),np.uint8),1,stamp),Detector())
        self.assertEqual(seen,[(stamp+1000)*1_000_000])
        self.assertEqual(service.discarded,1)

    def test_optional_caller_paused_after_native_release_does_not_block_primary(self):
        runner=pinned(self.context,self.schedule,self.metrics,2)
        released=threading.Event();resume=threading.Event();errors=[]
        def pause(report):released.set();resume.wait(2)
        self.context.after_native=pause
        def optional():
            try:runner.execute_encoded(np.zeros((1,112,112,3),np.int8),source_expires_ns=self.clock.ns+1_000_000_000)
            except BaseException as exc:errors.append(exc)
        thread=threading.Thread(target=optional);thread.start()
        try:
            self.assertTrue(released.wait(1))
            with self.schedule.primary(self.clock.seconds()+.1):
                value=self.context.execute_yolo(np.zeros((24,24,3),np.uint8),
                    source_expires_ns=self.clock.ns+750_000_000,
                    primary_finish_ns=self.schedule.primary_deadline_ns())
            self.assertTrue(value.usable)
            self.assertTrue(thread.is_alive())
        finally:resume.set();thread.join(2)
        self.assertFalse(errors)

    def test_yunet_native_execution_never_enters_legacy_optional_context(self):
        detector=DpuYuNet.__new__(DpuYuNet);detector.native_critical=True;detector.schedule=self.schedule
        calls=[]
        class Runner:
            input_fix=7;last_report=None
            def execute_encoded(inner,source,*,source_expires_ns,pre_execute):
                pre_execute();calls.append((source.copy(),source_expires_ns))
                inner.last_report=self.context.report(1,source_expires_ns)
                return {'head':np.array([7],np.float32)}
        detector.runner=Runner()
        def check():pass
        check.source_expires_monotonic_ns=self.clock.ns+1_000_000_000;check.deadline_monotonic=None
        detector._admission_check=check
        values=detector.scheduled(np.zeros((1,320,320,3),np.float32))
        self.assertEqual(values['head'][0],7)
        self.assertEqual(len(calls),1);self.assertEqual(calls[0][0].dtype,np.int8)

    def test_yunet_LATCHED_uses_CPU_fallback_without_native_submit(self):
        detector=DpuYuNet.__new__(DpuYuNet);detector.native_critical=True;detector.schedule=self.schedule
        p=self.context.state['recovery'][0];p.update(phase=3,reason=1,faults=5,attempts=4,recoveries=4,
            history_opaque=1,opaque_attempt_count=1)
        self.context.state['disabled'][1]=1
        detector._health_lock=threading.Lock()
        detector.fallback_calls=detector.fallback_failures=0
        detector.fallback_total_ms=0.;detector.fallback_last_ms=detector.fallback_reason=None
        calls=[];detector.fallback=SimpleNamespace(detect=lambda image:calls.append(image) or [])
        self.assertEqual(detector.detect(np.zeros((2,2,3),np.uint8)),[])
        self.assertEqual(len(calls),1);self.assertEqual(detector.fallback_calls,1)
        self.assertEqual(detector.kind,'CPU_YUNET_FALLBACK_AFTER_DPU_OVERRUN')

    def ui_inference(self,context,*,unknown=False):
        """Execute the actual nested UI loop for bounded synthetic packets."""
        source=Path(__file__).resolve().parents[1]/'candidate/aura/board/vision/ui_camera_service.py'
        module=ast.parse(source.read_text())
        run=next(node for node in module.body if isinstance(node,ast.FunctionDef) and node.name=='run')
        function=copy.deepcopy(next(node for node in ast.walk(run) if isinstance(node,ast.FunctionDef) and node.name=='inference'))
        function.body[0]=ast.Global(names=['detector'])
        code=compile(ast.fix_missing_locations(ast.Module(body=[function],type_ignores=[])),str(source),'exec')
        class Stop:
            value=False
            def is_set(inner):return inner.value
            def wait(inner,delay):
                if not inner.value:self.clock.advance(int(max(0,delay)*1e9))
        stop=Stop();latest=[None];observations=[]
        class Condition:
            calls=0
            def __enter__(inner):return inner
            def __exit__(inner,*args):pass
            def wait_for(inner,predicate,timeout):
                inner.calls+=1
                if inner.calls>2:stop.value=True
                latest[0]=(inner.calls,self.clock.millis(),np.zeros((480,640,3),np.uint8))
                return predicate()
        condition=Condition()
        state=SimpleNamespace(pipeline_metrics=self.metrics,dpu_schedule=self.schedule,lock=threading.RLock(),
            requested_target=None,identity=None,detector_error=None)
        def observed(fid,*args):observations.append(fid);stop.value=True
        state.observed=observed
        tracker=SimpleNamespace(update=lambda *args:{'tracks':[]})
        original=SimpleNamespace(handle=None,config={'score_threshold':.3},fingerprint='0x101000056010407',
            reference_check={},pipeline_metrics=self.metrics,ownership=None)
        owner=NativeYoloOwner(original,context,self.schedule)
        namespace=dict(detector=owner,stop=stop,condition=condition,latest=latest,state=state,
            tracker=tracker,config={'inference_fps':10},time=time,millis=self.clock.millis,
            PrimaryAdmissionDeferred=PrimaryAdmissionDeferred)
        exec(code,namespace)
        namespace['inference']()
        return namespace,state,observations,owner

    def test_UI_native_primary_denial_keeps_owner_and_next_packet_runs(self):
        original=self.context.execute_yolo;calls=[]
        def execute(image,**args):
            calls.append(args)
            if len(calls)==1:
                r=self.context.report(0,args['source_expires_ns'])
                r.update(outcome=1,submitted=0,completed=0,business_ready=0)
                return Execution(r,(),self.clock.ns,args['source_expires_ns'])
            return original(image,**args)
        self.context.execute_yolo=execute
        namespace,state,observations,owner=self.ui_inference(self.context)
        self.assertEqual(len(calls),2);self.assertEqual(observations,[2])
        self.assertIs(namespace['detector'],owner)
        self.assertIsNone(state.detector_error)
        self.assertFalse(any(c[0]=='close' for c in self.context.calls))

    def test_UI_unknown_native_completion_retains_owner_and_stops_new_primary(self):
        def execute(image,**args):
            self.context.quarantined=True;self.context.state['fenced']=1
            raise CompletionUnknown('fake unconfirmed completion')
        def close():raise CompletionUnknown('fenced owner retained')
        self.context.execute_yolo=execute;self.context.close=close
        namespace,state,observations,owner=self.ui_inference(self.context,unknown=True)
        self.assertIsNone(namespace['detector']);self.assertFalse(observations)
        self.assertIs(state._retained_native_owner,owner)
        self.assertTrue(state.detector_error)


class ProtectionTests(unittest.TestCase):
    def test_exact_ABI_struct_sizes(self):
        self.assertEqual([C.sizeof(t) for t in (Report,Ack,Recovery,State,Seed)],[88,32,104,432,520])
        self.assertEqual(Report.result_token.offset,80);self.assertEqual(State.recovery.offset,224)

    def test_maintenance_seed_is_clean_separate_scope(self):
        values=isolated_maintenance_seed(boot_id=BOOT,captured_mono_ns=1000,production_snapshot_sha256='1'*64)
        seed=make_native_seed(values,Seed,Recovery)
        self.assertEqual(seed.source_pid,0);self.assertEqual(seed.checkpoint_kind,0)
        values['overruns'][1]=5
        with self.assertRaises(ValueError):make_native_seed(values,Seed,Recovery)

    def test_health_prefix_cannot_be_declared_executable(self):
        values=isolated_maintenance_seed(boot_id=BOOT,captured_mono_ns=1000,production_snapshot_sha256='1'*64)
        values.update(purpose='final_quiescent_business_checkpoint',checkpoint_kind=2,source_pid=2,source_birth_ticks=3)
        with self.assertRaises(ValueError):make_native_seed(values,Seed,Recovery)

    def test_legacy_health_pin_is_not_an_exact_final_checkpoint(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'legacy.json';path.write_text(json.dumps({'schema':'aura-dpu-protection-handoff-1'}))
            pin={'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
            with self.assertRaises(ValueError):load_business_checkpoint(pin,boot_id=BOOT,now_ns=2000)

    def document(self):
        state=FakeContext(Clock()).state;state['quiesced']=1
        seed={name:copy.deepcopy(state[name]) for name in ('primary_calls','primary_period_overruns',
            'last_primary_ns','admissions','overruns','completed','native_failures','not_submitted','disabled','recovery')}
        birth=int(Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19])
        seed.update(abi_version=2,checkpoint_kind=1,purpose='final_quiescent_business_checkpoint',
            fenced=0,captured_mono_ns=1_000_000_000_000,source_pid=os.getpid(),source_birth_ticks=birth,
            boot_id=BOOT,source_manifest_sha256='1'*64)
        counters={name:0 for name in ('requests','execution_attempts','completed','features_returned',
            'deferred','slot_denials','expired_after_admission')}
        return checkpoint_document(state,native_seed=seed,source_unit_sha256='2'*64,sface_counters=counters)

    def test_atomic_checkpoint_requires_native_seal_and_stopped_predecessor(self):
        doc=self.document()
        with tempfile.TemporaryDirectory() as folder:
            pin=write_checkpoint(Path(folder)/'checkpoint.json',doc)
            with self.assertRaises(ValueError):load_business_checkpoint(pin,boot_id=BOOT,now_ns=2_000_000_000_000)
            doc['seed']['source_pid']=1_000_000_000;doc['seed']['source_birth_ticks']=42
            pin=write_checkpoint(Path(folder)/'checkpoint.json',doc)
            loaded=load_business_checkpoint(pin,boot_id=BOOT,now_ns=2_000_000_000_000)
            self.assertEqual(loaded['seed']['admissions'],[50,10,8])
            make_native_seed(loaded['seed'],Seed,Recovery)
            consume_checkpoint(loaded)
            with self.assertRaises(ValueError):load_business_checkpoint(pin,boot_id=BOOT,now_ns=2_000_000_000_000)

    def test_checkpoint_with_pending_results_is_rejected(self):
        doc=self.document();doc['auxiliary']['pending_result_tokens'][2]=1
        with tempfile.TemporaryDirectory() as folder:
            pin=write_checkpoint(Path(folder)/'checkpoint.json',doc)
            with self.assertRaises(ValueError):load_business_checkpoint(pin,boot_id=BOOT,now_ns=2_000_000_000_000)

    def test_missing_predecessor_is_rejected_during_preflight_before_owner_creation(self):
        doc=self.document();doc['seed']['source_pid']=0;doc['seed']['source_birth_ticks']=0
        with tempfile.TemporaryDirectory() as folder:
            pin=write_checkpoint(Path(folder)/'checkpoint.json',doc)
            with self.assertRaises(ValueError):load_business_checkpoint(pin,boot_id=BOOT,now_ns=2_000_000_000_000)

    def test_attach_cleanup_refusal_retains_owner_and_preserves_original_error(self):
        original=SimpleNamespace(label='existing owner')
        class Context:
            quarantined=False
            retained=None
            def restore_seed(inner,seed):raise ValueError('original invalid seed')
            def close(inner):raise RuntimeError('cleanup refused')
            def _retain(inner,*values):inner.quarantined=True;inner.retained=values
        context=Context()
        with patch.object(native_startup,'configuration',return_value={'library':'unused','library_sha256':'1'*64}), \
             patch.object(native_startup,'NativeContext',return_value=context):
            with self.assertRaisesRegex(ValueError,'original invalid seed'):
                native_startup.attach({},SimpleNamespace(),original,{'seed':{}})
        self.assertTrue(context.quarantined)
        self.assertIs(context.retained[0],original)
        self.assertIsInstance(context.retained[1],ValueError)
        self.assertIsInstance(context.retained[2],RuntimeError)

    def test_attach_unknown_result_retains_original_and_does_not_attempt_close(self):
        original=SimpleNamespace(label='existing owner')
        class Context:
            quarantined=False
            retained=None
            close_called=False
            def restore_seed(inner,seed):
                inner.quarantined=True
                raise CompletionUnknown('seed operation interrupted')
            def close(inner):inner.close_called=True
            def _retain(inner,*values):inner.retained=values
        context=Context()
        with patch.object(native_startup,'configuration',return_value={'library':'unused','library_sha256':'1'*64}), \
             patch.object(native_startup,'NativeContext',return_value=context):
            with self.assertRaises(CompletionUnknown):
                native_startup.attach({},SimpleNamespace(),original,{'seed':{}})
        self.assertFalse(context.close_called)
        self.assertIs(context.retained[0],original)

    def test_serialized_dual_LATCHED_opaque_history_is_preserved_not_reset(self):
        # This is a hypothetical already-sealed v2 document, not a conversion
        # of the current legacy health snapshot into an exact checkpoint.
        doc=self.document();seed=doc['seed']
        seed['admissions'][1:]=[62491,755]
        seed['overruns'][1:]=[5,3];seed['completed'][2]=755
        seed['disabled'][1:]=[1,1]
        for index,reason,faults,attempts,recoveries,window in (
                (0,1,5,4,4,1),(1,2,3,2,2,2)):
            seed['recovery'][index].update(phase=3,reason=reason,faults=faults,
                attempts=attempts,recoveries=recoveries,history_opaque=1,
                opaque_attempt_count=window,attempt_count=0,attempt_times_ns=[0,0])
        result=make_native_seed(seed,Seed,Recovery)
        self.assertEqual(list(result.disabled),[0,1,1])
        self.assertEqual(list(result.overruns),[0,5,3])
        self.assertEqual([(r.faults,r.attempts,r.recoveries,r.opaque_attempt_count)
                          for r in result.recovery],[(5,4,4,1),(3,2,2,2)])
        seed['recovery'][1]['phase']=0
        with self.assertRaises(ValueError):make_native_seed(seed,Seed,Recovery)


if __name__=='__main__':unittest.main()
