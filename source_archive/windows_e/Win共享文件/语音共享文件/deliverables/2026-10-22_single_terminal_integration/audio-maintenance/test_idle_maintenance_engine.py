"""Exercise the actual persistent engine with controlled Gst state transitions."""
import importlib.util
import os
from pathlib import Path
import sys
import threading
from types import SimpleNamespace
import unittest

from idle_maintenance_engine import IdleMaintenanceEngine

LOCAL_ENGINE=Path(__file__).resolve().parent/'recovered-engine'
LIVE=Path(os.environ.get('AURA_AUDIO_SOURCE',str(LOCAL_ENGINE if LOCAL_ENGINE.exists()
    else Path('/home/ghmd/aura-audio-recovery-20261021/live-source'))))
sys.path.insert(0,str(LIVE))
spec=importlib.util.spec_from_file_location('actual_persistent',LIVE/'tools/gstreamer_persistent_engine.py')
persistent=importlib.util.module_from_spec(spec);spec.loader.exec_module(persistent)


class Pipeline:
    def __init__(self):
        self.states=[];self.null_return='SUCCESS';self.play_return='SUCCESS'
        self.query=('SUCCESS','NULL','VOID_PENDING')
        self.position=None;self.running_ns=None;self.error_message=None

    def set_state(self,state):
        self.states.append(state)
        return self.null_return if state=='NULL' else self.play_return

    def get_state(self,timeout):
        assert timeout==0
        return self.query

    def get_bus(self):
        def message(*args):return self.error_message
        return SimpleNamespace(timed_pop_filtered=message)

    def get_clock(self):
        return None if self.running_ns is None else SimpleNamespace(get_time=lambda:self.running_ns)

    def get_base_time(self):return 0


class Engine(IdleMaintenanceEngine,persistent.PersistentGstAudioEngine):
    pass


class MaintenanceTests(unittest.TestCase):
    def setUp(self):
        self.now=1000.;self.created=[];self.inject_play_failure=False;self.inject_factory_error=False
        self.gst=SimpleNamespace(State=SimpleNamespace(NULL='NULL',PLAYING='PLAYING',VOID_PENDING='VOID_PENDING'),
            StateChangeReturn=SimpleNamespace(SUCCESS='SUCCESS',ASYNC='ASYNC',FAILURE='FAILURE'),
            MessageType=SimpleNamespace(ERROR='ERROR'),Format=SimpleNamespace(TIME='TIME'),SECOND=1000000000,
            FlowReturn=SimpleNamespace(OK='OK'),
            Buffer=SimpleNamespace(new_allocate=lambda *args:SimpleNamespace(fill=lambda *args:None)))
        def factory(gst,device):
            if self.inject_factory_error:raise RuntimeError('Synthetic factory failure')
            p=Pipeline()
            if self.inject_play_failure:p.play_return='FAILURE'
            source=SimpleNamespace(emit=lambda *args:'OK')
            sink=SimpleNamespace(query_position=lambda fmt:(p.position is not None,p.position or 0))
            self.created.append(p)
            return p,source,sink
        self.factory=factory
        self.engine=Engine.__new__(Engine);self.engine.configure_idle_maintenance(factory)
        persistent.PersistentGstAudioEngine.__init__(self.engine,self.gst,'SYNTHETIC_DEVICE',
            clock=lambda:self.now,pipeline_factory=factory)

    def request(self,**changes):
        args=dict(request_id='REQUEST_1',expected_token=self.engine.token,new_token=self.engine.token+1,
            controller_idle=True,capture_idle=True,reference_idle=True,commands_pending=False)
        args.update(changes)
        return self.engine.request_idle_maintenance(**args)

    def warm(self):
        self.engine.poll()
        p=self.created[-1];p.running_ns=1000000000;p.position=1000000000
        self.now+=1.1
        return self.engine.poll()

    def test_busy_and_external_gate_refuse_without_mutation(self):
        for field,value in [('active',True),('paused',True),('audible',True),('queue',[b'x']),('intervals',[1])]:
            old=getattr(self.engine,field);setattr(self.engine,field,value)
            self.assertFalse(self.request(),field);setattr(self.engine,field,old)
        for change in [dict(controller_idle=False),dict(capture_idle=False),dict(reference_idle=False),
                       dict(commands_pending=True),dict(controller_idle=1),dict(reference_idle=1)]:
            self.assertFalse(self.request(**change),change)
        self.assertEqual(len(self.created),1);self.assertEqual(self.engine.token,0)

    def test_bad_tokens_ids_and_capacity_never_start_close(self):
        for change in [dict(expected_token=True),dict(expected_token=-1),dict(new_token=2),
                       dict(request_id=''),dict(request_id='bad name'),dict(request_id='x'*65)]:
            self.assertFalse(self.request(**change),change)
        self.assertEqual(self.created[0].states,['PLAYING'])

    def test_null_must_complete_before_new_pipeline(self):
        old=self.created[0];old.null_return='ASYNC';old.query=('ASYNC','PLAYING','NULL')
        self.assertTrue(self.request());self.engine.poll();self.assertEqual(len(self.created),1)
        old.query=('SUCCESS','NULL','NULL');self.engine.poll();self.assertEqual(len(self.created),1)
        old.query=('SUCCESS','NULL','VOID_PENDING');self.engine.poll()
        self.assertEqual(len(self.created),2);self.assertEqual(self.engine.maintenance_state,'WARMING')

    def test_null_failure_timeout_or_query_error_holds_old_owner(self):
        old=self.created[0];old.null_return='FAILURE'
        self.assertTrue(self.request());self.assertEqual(self.engine.maintenance_reason,'NULL_STATE_FAILED')
        self.assertIs(self.engine.pipeline,old);self.assertEqual(len(self.created),1)

    def test_null_timeout_rejects_late_completion(self):
        old=self.created[0];old.query=('ASYNC','PLAYING','NULL')
        self.request();self.now+=2.1;self.engine.poll()
        self.assertEqual(self.engine.maintenance_reason,'NULL_STATE_TIMEOUT')
        old.query=('SUCCESS','NULL','VOID_PENDING');self.engine.poll()
        self.assertEqual(len(self.created),1)

    def test_null_query_failure_or_exception_never_opens_replacement(self):
        for mode in ('failure','exception'):
            self.setUp()
            p=self.created[0]
            if mode=='failure':p.query=('FAILURE','PLAYING','NULL')
            else:p.get_state=lambda *args:(_ for _ in ()).throw(RuntimeError('Synthetic query failure'))
            self.assertTrue(self.request());self.engine.poll()
            self.assertEqual(self.engine.maintenance_state,'FAILED_HELD')
            self.assertEqual(len(self.created),1);self.assertIs(self.engine.pipeline,p)

    def test_rebuild_resets_pts_token_and_reference_epoch_preserves_sequence(self):
        e=self.engine;e.device_ready=True;e.next_pts=9000000000;e.reference_sequence=91
        e.references.append({'pcm':b'old','sequence':91});self.assertTrue(self.request())
        self.assertEqual(e.token,1);self.assertEqual(e.pipeline_epoch,1);self.assertEqual(e.take_references(),[])
        e.poll();self.assertEqual(e.next_pts,0);self.assertFalse(e.device_ready)
        self.assertEqual(e.reference_sequence,91);state=self.warm()
        self.assertEqual(state['maintenance_state'],'READY_UNVERIFIED')
        self.assertEqual(state['usb_playback_health'],'UNVERIFIED')
        values=e.take_references();self.assertTrue(values)
        self.assertTrue(all(v['pipeline_epoch']==1 and v['sequence']>91 for v in values))

    def test_warmup_timeout_is_held_and_late_ready_cannot_admit(self):
        self.request();self.engine.poll();self.now+=8.1;self.engine.poll()
        self.assertEqual(self.engine.maintenance_reason,'WARMUP_TIMEOUT')
        p=self.created[-1];p.position=p.running_ns=1000000000
        self.engine.poll();self.assertFalse(self.engine.command({'type':'stream','token':2}))
        self.assertFalse(self.engine.device_ready)

    def test_warmup_native_return_after_deadline_requests_null_and_holds(self):
        self.request();self.engine.poll();p=self.created[-1]
        def late_clock():
            self.now+=9
            return SimpleNamespace(get_time=lambda:1000000000)
        p.get_clock=late_clock;p.position=1000000000
        result=self.engine.poll()
        self.assertEqual(result['maintenance_reason'],'WARMUP_TIMEOUT')
        self.assertTrue(result['maintenance_admission_held'])
        self.assertEqual(p.states[-1],'NULL');self.assertFalse(result['device_ready'])

    def test_warmup_poll_exception_requests_null_without_new_factory(self):
        self.request();self.engine.poll();p=self.created[-1]
        p.get_clock=lambda:(_ for _ in ()).throw(RuntimeError('Synthetic native poll error'))
        result=self.engine.poll()
        self.assertEqual(result['maintenance_reason'],'WARMUP_POLL_EXCEPTION')
        self.assertEqual(p.states[-1],'NULL');self.assertIs(self.engine.pipeline,p)
        self.assertEqual(len(self.created),2)

    def test_rebuild_exception_and_play_failure_hold_without_retry(self):
        self.request();self.inject_factory_error=True;self.engine.poll()
        self.assertEqual(self.engine.maintenance_reason,'REBUILD_FAILED')
        self.assertEqual(len(self.created),1);self.engine.poll();self.assertEqual(len(self.created),1)

    def test_play_failure_keeps_new_pipeline_reachable_for_close(self):
        self.request();self.inject_play_failure=True;self.engine.poll()
        p=self.created[-1];self.assertEqual(p.states,['PLAYING','NULL'])
        self.assertIs(self.engine.pipeline,p)
        self.assertTrue(self.engine.command({'type':'close','token':2}))
        self.assertIsNone(self.engine.pipeline)

    def test_ordinary_stop_still_keeps_pipeline_and_maintenance_stop_latches(self):
        old=self.engine.pipeline;self.assertTrue(self.engine.command({'type':'stop','token':1}))
        self.assertIs(self.engine.pipeline,old);self.assertEqual(old.states,['PLAYING'])
        self.request();self.assertTrue(self.engine.command({'type':'stop','token':3}))
        self.assertEqual(self.engine.maintenance_reason,'STOP_DURING_MAINTENANCE')
        self.engine.poll();self.assertEqual(len(self.created),1)

    def test_close_remains_available_in_maintenance_and_blocks_future_stream(self):
        self.request();self.assertTrue(self.engine.command({'type':'close','token':2}))
        self.assertIsNone(self.engine.pipeline);self.assertEqual(self.engine.take_references(),[])
        self.assertFalse(self.engine.command({'type':'stream','token':3}))

    def test_duplicate_request_is_idempotent_not_second_rebuild(self):
        args=dict(request_id='IDEMPOTENT',expected_token=0,new_token=1,
            controller_idle=True,capture_idle=True,reference_idle=True,commands_pending=False)
        self.assertTrue(self.engine.request_idle_maintenance(**args))
        self.assertTrue(self.engine.request_idle_maintenance(**args))
        self.warm();self.now+=61
        self.assertTrue(self.engine.request_idle_maintenance(**args))
        self.assertEqual(len(self.created),2);self.assertEqual(self.engine.pipeline_epoch,1)
        self.assertFalse(self.engine.request_idle_maintenance(**{**args,'new_token':2}))
        self.assertFalse(self.engine.request_idle_maintenance(**{**args,'controller_idle':1}))

    def test_old_request_cannot_replay_after_a_new_transaction(self):
        self.assertTrue(self.request());self.warm();self.now+=61
        self.assertTrue(self.request(request_id='REQUEST_2'))
        self.assertFalse(self.request(request_id='REQUEST_1',expected_token=0,new_token=1))

    def test_request_ledger_is_bounded_and_does_not_evict_for_replay(self):
        for index in range(32):
            self.assertTrue(self.request(request_id='R_'+str(index)))
            self.warm();self.now+=601
        self.assertEqual(len(self.engine._maintenance_requests),32)
        before=len(self.created)
        self.assertFalse(self.request(request_id='CAPACITY_FULL'))
        self.assertEqual(len(self.created),before)

    def test_cooldown_and_window_limit(self):
        self.request();self.warm();self.now+=58
        self.assertFalse(self.request(request_id='R2'))
        self.now+=2;self.assertTrue(self.request(request_id='R2'));self.warm();self.now+=60
        self.assertFalse(self.request(request_id='R3'));self.now+=480
        self.assertTrue(self.request(request_id='R3'))

    def test_owner_thread_must_control_poll_command_and_recovery(self):
        errors=[]
        def other():
            for fn in [self.request,self.engine.poll,lambda:self.engine.command({'type':'stop','token':1})]:
                try:fn()
                except RuntimeError:errors.append(True)
        thread=threading.Thread(target=other);thread.start();thread.join()
        self.assertEqual(len(errors),3);self.assertEqual(self.engine.token,0)

    def test_native_poll_sink_error_drops_old_reference_and_holds(self):
        self.request();self.engine.poll();self.engine.references.append({'pcm':b'old'})
        self.created[-1].error_message=SimpleNamespace(parse_error=lambda:('Synthetic sink error',None))
        state=self.engine.poll()
        self.assertEqual(state['maintenance_reason'],'WARMUP_DEVICE_ERROR')
        self.assertEqual(self.engine.take_references(),[])


if __name__=='__main__':unittest.main(verbosity=2)
