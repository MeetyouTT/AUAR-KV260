"""Protocol, pipe failure, actual avatar queue and synthetic Gst checks.

No hardware device, camera, voice service or identity database is opened.
"""
import base64
from collections import deque
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
from types import SimpleNamespace,ModuleType
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'candidate/aura'))
from tools.audio_maintenance_wire import WorkerMaintenanceProtocol
from tools.maintenance_audio_output import MaintenanceAudioOutput
from tools.maintenance_recording import MaintenanceRecordingController,camera_only_services_idle

INSTANCE='a'*32
REQUEST='b'*32


class Clock:
    def __init__(self):self.now=100.
    def __call__(self):return self.now


def facade():
    out=MaintenanceAudioOutput.__new__(MaintenanceAudioOutput)
    out.lifecycle=threading.RLock();out.lock=threading.Lock();out.reference_lock=threading.RLock()
    out.reference_handler=None;out.reference_error='';out.streaming=False
    out.active=out.paused=out.closed=False;out.token=0;out.pipeline_epoch=0
    out.worker_instance=INSTANCE;out.dropped_messages=0;out.last_reference_sequence=0
    out.clock=Clock();out.maintenance_state='IDLE';out.maintenance_request=None
    out.maintenance_deadline=None;out.maintenance_held=False;out.transport_broken=False
    out.booted=threading.Event();out.boot_error='';out.log=None
    out.duration=out.last_time=0.;out.finished_count=0
    out.snapshot={'device_ready':True,'ready':False,'clock':0.,'done':False,'error':''}
    out.process=SimpleNamespace(poll=lambda:None)
    out.messages=[];out._write=out.messages.append
    return out


def ack(out,accepted=True,**fields):
    r=out.maintenance_request
    value=dict(kind='maintenance_ack',worker_instance=INSTANCE,request_id=r['id'],
        expected_token=r['expected'],requested_token=r['token'],
        engine_token=r['token'] if accepted else r['expected'],
        pipeline_epoch=r['epoch']+1 if accepted else r['epoch'],accepted=accepted)
    value.update(fields);out._message(value)


def state(out,phase='READY_UNVERIFIED',**fields):
    value=dict(kind='state',worker_instance=INSTANCE,token=out.token,pipeline_epoch=out.pipeline_epoch,
        maintenance_request_id=(out.maintenance_request or {}).get('id'),maintenance_state=phase,
        device_ready=True,error='')
    value.update(fields);out._message(value)


class ProtocolTests(unittest.TestCase):
    def setUp(self):
        self.engine=SimpleNamespace(token=3,pipeline_epoch=0)
        self.calls=[]
        def request(**kw):
            self.calls.append(kw);self.engine.token=kw['new_token'];self.engine.pipeline_epoch+=1;return True
        self.engine.request_idle_maintenance=request
        self.engine.command=lambda m:self.calls.append(m) or True
        self.wire=WorkerMaintenanceProtocol(self.engine,INSTANCE)
        self.message=dict(type='recover_idle',worker_instance=INSTANCE,request_id=REQUEST,expected_token=3,token=4)

    def test_matching_recovery_ack_uses_engine_observations(self):
        ok,value=self.wire.command(self.message,commands_pending=False)
        self.assertTrue(ok);self.assertEqual((value['engine_token'],value['pipeline_epoch']),(4,1))

    def test_wrong_instance_never_reaches_engine(self):
        self.message['worker_instance']='c'*32
        self.assertEqual(self.wire.command(self.message,commands_pending=False),(False,None))
        self.assertFalse(self.calls)

    def test_queued_commands_prevent_recovery(self):
        self.assertFalse(self.wire.command(self.message,commands_pending=True)[0]);self.assertFalse(self.calls)

    def test_malformed_request_never_reaches_engine(self):
        for field,value in [('token',True),('expected_token',3.),('request_id','unsafe\n'),('extra','unexpected')]:
            with self.subTest(field=field):
                msg=dict(self.message);msg[field]=value
                self.assertFalse(self.wire.command(msg,commands_pending=False)[0])
        self.assertFalse(self.calls)

    def test_ordinary_commands_keep_instance_gate(self):
        self.assertTrue(self.wire.command(dict(type='stop',token=4,worker_instance=INSTANCE),commands_pending=False)[0])
        self.assertEqual(self.wire.stamp({'kind':'reference'})['token'],3)


class FacadeTests(unittest.TestCase):
    def setUp(self):self.out=facade()

    def test_success_requires_ack_ready_and_owner_finish(self):
        out=self.out;request=out.begin_idle_maintenance()
        with self.assertRaises(RuntimeError):out.begin_stream()
        state(out);self.assertEqual(out.maintenance_state,'REQUESTED')
        ack(out);self.assertEqual(out.maintenance_state,'ACCEPTED')
        state(out);self.assertEqual(out.maintenance_state,'READY_HELD')
        self.assertFalse(out.finish_idle_maintenance('wrong'))
        self.assertTrue(out.finish_idle_maintenance(request));self.assertFalse(out.maintenance_held)

    def test_wrong_instance_request_epoch_and_boolean_ack_do_not_release(self):
        out=self.out;out.begin_idle_maintenance()
        for fields in ({'worker_instance':'c'*32},{'request_id':'c'*32},{'expected_token':False}):
            with self.subTest(fields=fields):ack(out,**fields);self.assertEqual(out.maintenance_state,'REQUESTED')
        ack(out,pipeline_epoch=9);self.assertEqual(out.maintenance_state,'FAILED_PROTOCOL')

    def test_rejected_unmodified_engine_restores_parent_generation(self):
        out=self.out;out.begin_idle_maintenance();ack(out,False)
        self.assertEqual((out.token,out.pipeline_epoch,out.maintenance_held),(0,0,False))

    def test_rejected_mutated_engine_remains_held(self):
        out=self.out;out.begin_idle_maintenance();ack(out,False,engine_token=1)
        self.assertTrue(out.maintenance_held);self.assertEqual(out.maintenance_state,'FAILED_PROTOCOL')

    def test_late_ack_and_ready_after_timeout_cannot_release(self):
        out=self.out;request=out.begin_idle_maintenance();out.clock.now+=13
        self.assertEqual(out.maintenance_status()['state'],'FAILED_TIMEOUT')
        ack(out);state(out);self.assertFalse(out.finish_idle_maintenance(request))

    def test_stop_supersedes_inflight_recovery(self):
        out=self.out;request=out.begin_idle_maintenance();out.stop();ack(out);state(out)
        self.assertFalse(out.finish_idle_maintenance(request));self.assertEqual(out.maintenance_state,'FAILED_CANCELLED')

    def test_reference_old_generation_duplicate_and_held_are_dropped(self):
        out=self.out;received=[];out.subscribe_reference(lambda *a:received.append(a))
        msg=dict(kind='reference',worker_instance=INSTANCE,token=0,pipeline_epoch=0,
                 sequence=10,pcm=base64.b64encode(bytes(960)).decode(),at=1.)
        out._message(dict(msg,token=-1));out._message(dict(msg,pipeline_epoch=2))
        out._message(msg);out._message(msg)
        self.assertEqual(len(received),1)
        out.reference_handler=None;out.begin_idle_maintenance()
        out._message(dict(msg,token=1,sequence=11));self.assertEqual(len(received),1)
        with self.assertRaises(RuntimeError):out.subscribe_reference(lambda *a:None)

    def test_active_reference_or_playback_prevents_admission(self):
        for name,value in [('active',True),('paused',True),('streaming',True),('reference_handler',lambda:None)]:
            with self.subTest(name=name):
                out=facade();setattr(out,name,value)
                with self.assertRaises(ValueError):out.begin_idle_maintenance()
                self.assertFalse(out.messages)

    def test_duplicate_boot_is_ignored(self):
        out=self.out;boot=dict(kind='boot',worker_instance=INSTANCE,token=0,pipeline_epoch=0,error='')
        out._message(boot);out._message(dict(boot,error='late'))
        self.assertEqual(out.boot_error,'');self.assertEqual(out.dropped_messages,1)

    def test_full_pipe_write_is_bounded_and_holds_admission(self):
        out=self.out;read_fd,write_fd=os.pipe()
        try:
            os.set_blocking(write_fd,False)
            while True:
                try:os.write(write_fd,bytes(4096))
                except BlockingIOError:break
            out.process.stdin=SimpleNamespace(fileno=lambda:write_fd)
            started=time.monotonic()
            with self.assertRaises(TimeoutError):MaintenanceAudioOutput._write(out,{'type':'stop'})
            self.assertLess(time.monotonic()-started,1.)
            self.assertTrue(out.transport_broken);self.assertTrue(out.maintenance_held)
        finally:os.close(read_fd);os.close(write_fd)

    def test_close_terminates_only_owned_stuck_child_without_reader_lock(self):
        out=self.out;calls=[]
        def wait(timeout):
            calls.append(('wait',timeout))
            if len([x for x in calls if x[0]=='wait'])<3:raise subprocess.TimeoutExpired('owned-worker',timeout)
        out.process=SimpleNamespace(poll=lambda:None,wait=wait,
            terminate=lambda:calls.append(('terminate',)),kill=lambda:calls.append(('kill',)))
        out.reader=SimpleNamespace(join=lambda timeout:calls.append(('join',timeout)),is_alive=lambda:False)
        out.close();self.assertEqual(out.maintenance_state,'CLOSED')
        self.assertIn(('terminate',),calls);self.assertIn(('kill',),calls)
        self.assertEqual(out.messages[-1]['type'],'close')


class Recording:
    def __init__(self,output):
        self.controller=SimpleNamespace(phase='IDLE',pending=None,ready=None,audio_waiting=None,
            stream=None,pause_started=None,completed_streams=[],last_meta=None)
        self.base_ticks=0;self.ticks=0;self.publics=0;self.starts=0;self.cancels=0;self.closed=False
        self.controller.tick=self.base_tick
        self.transcriber=SimpleNamespace(condition=threading.Condition(),closed=False,
            waiting=None,active=None,results=deque(),progress=deque(),channel=None)
        self.capture=self.utterance=self.barge_capture=self.listen_id=self.barge_id=None
        self.speech_proof=self.barge_speech=self.rearm_at=self.ack_deadline=self.entry_deadline=None
        self.auto_enabled=self.monitor_owned=self.awaiting_entry=False
        self.monitor_enabled=True;self.preference_writes=0;self.last_error='';self.output=output
    def base_tick(self):self.base_ticks+=1;return None
    def tick(self):self.ticks+=1;return self.controller.tick()
    def public(self):
        self.publics+=1
        return {'phase':'IDLE','local_recording':{'can_start':True},
                'handsfree_dialogue':{'enabled':self.monitor_enabled,'state':'WAITING_PERSON'}}
    def record_start(self):self.starts+=1;return 'started'
    def cancel(self):self.cancels+=1;self.monitor_enabled=False;self.preference_writes+=1;self.output.stop()
    def close(self):self.closed=True


class OwnerTests(unittest.TestCase):
    def setUp(self):
        self.out=facade();self.recording=Recording(self.out)
        self.owner=MaintenanceRecordingController(self.recording,self.out)

    def test_barrier_blocks_public_side_effects_and_new_inputs_but_keeps_visual_tick(self):
        r=self.recording;o=self.owner;o.audio_maintenance();counts=(r.publics,r.ticks)
        o.tick();value=o.public()
        self.assertEqual((r.publics,r.ticks),counts);self.assertEqual(r.base_ticks,1)
        self.assertTrue(value['handsfree_dialogue']['enabled']);self.assertFalse(value['local_recording']['can_start'])
        with self.assertRaises(ValueError):o.record_start()
        self.assertEqual((r.starts,r.preference_writes),(0,0))

    def test_busy_states_reject_without_cancelling_or_mutating_preferences(self):
        for target,name,value in [(self.recording,'capture',object()),(self.recording,'utterance',object()),
                (self.recording.transcriber,'active','http-job'),(self.recording.transcriber,'results',[{}]),
                (self.recording.transcriber,'channel',object()),(self.recording.controller,'stream',{}),
                (self.recording,'auto_enabled',True),(self.recording,'speech_proof',('old',))]:
            with self.subTest(name=name):
                old=getattr(target,name);setattr(target,name,value)
                with self.assertRaises(ValueError):self.owner.audio_maintenance()
                setattr(target,name,old)
                self.assertFalse(self.owner._held)
        self.assertEqual(self.recording.preference_writes,0);self.assertFalse(self.out.messages)

    def test_ready_requires_final_owner_idle_recheck(self):
        o=self.owner;o.audio_maintenance();ack(self.out);state(self.out)
        self.recording.transcriber.active='late';o.tick()
        self.assertTrue(o._held);self.assertEqual(o._failure,'FAILED_OWNER_RECHECK')
        self.recording.transcriber.active=None;o.tick();self.assertTrue(o._held)

    def test_matching_ready_reopens_only_on_owner_tick(self):
        o=self.owner;o.audio_maintenance();ack(self.out);state(self.out)
        self.assertTrue(o._held);o.tick();self.assertFalse(o._held)
        self.assertEqual(o.record_start(),'started');self.assertEqual(self.recording.preference_writes,0)

    def test_rejection_releases_owner_gate_without_work_cancellation(self):
        o=self.owner;o.audio_maintenance();ack(self.out,False);o.tick()
        self.assertFalse(o._held);self.assertEqual(self.recording.cancels,0)

    def test_explicit_cancel_keeps_gate_held_after_late_completion(self):
        o=self.owner;o.audio_maintenance();o.cancel();ack(self.out);state(self.out);o.tick()
        self.assertTrue(o._held);self.assertEqual(self.recording.preference_writes,1)

    def test_foreign_thread_cannot_submit_intent(self):
        self.owner.tick();errors=[]
        def foreign():
            try:self.owner.record_start()
            except RuntimeError as exc:errors.append(str(exc))
        t=threading.Thread(target=foreign);t.start();t.join(1)
        self.assertEqual(len(errors),1);self.assertEqual(self.recording.starts,0)

    def test_uncertain_transport_keeps_owner_and_output_held(self):
        def broken(message):self.out._hold_failure('FAILED_TRANSPORT');raise BrokenPipeError('synthetic')
        self.out._write=broken
        with self.assertRaises(BrokenPipeError):self.owner.audio_maintenance()
        self.assertTrue(self.owner._held);self.assertTrue(self.out.maintenance_held)

    def test_identity_flow_unknown_or_active_rejects_without_nested_job_lock(self):
        tr=self.recording.transcriber
        def public():
            self.assertFalse(tr.condition._is_owned());return {'active':False}
        tr.identity_flow=SimpleNamespace(public=public)
        self.assertTrue(self.owner._idle())
        tr.identity_flow.public=lambda:{'stage':'unknown'}
        self.assertFalse(self.owner._idle())

    def test_settings_and_selection_are_rejected_before_side_effects(self):
        writes=[]
        self.owner._transcription_store=SimpleNamespace(update=lambda v:writes.append(v))
        self.recording.transcriber.select_conversation=lambda **kw:writes.append(kw)
        self.owner.audio_maintenance()
        with self.assertRaises(ValueError):self.owner.configure_transcription_saved({'enabled':True})
        with self.assertRaises(ValueError):self.owner.conversation_start_selected(False)
        self.assertFalse(writes)

    def test_external_audio_service_stale_or_pending_blocks_idle(self):
        view=dict(link='READY',pending_count=0,snapshot={'source_kind':'actual',
            'capabilities':{'record_start':False,'record_stop':False,'ask_frame':False},
            'modules':{'interaction':{'state':'IDLE'},'audio':{'state':'UNAVAILABLE'}}})
        services=SimpleNamespace(read=lambda:view)
        self.owner.external_idle=lambda:camera_only_services_idle(services)
        self.assertTrue(self.owner._idle())
        for field,value in [('link','STALE'),('pending_count',1)]:
            old=view[field];view[field]=value;self.assertFalse(self.owner._idle());view[field]=old
        view['snapshot']['capabilities']['ask_frame']=True;self.assertFalse(self.owner._idle())

    def test_real_avatar_dispatch_rejects_following_queued_record(self):
        path=ROOT/'recovered/tools/board_avatar_worker.py'
        if not path.exists():self.fail('Actual recovered AvatarRenderWorker is required')
        spec=importlib.util.spec_from_file_location('_actual_avatar_worker_test',path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        affine=ModuleType('tools.board_avatar_affine');affine.resize_rgb=lambda *a:None
        with patch.dict(sys.modules,{'tools.board_avatar_affine':affine}):
            worker=module.AvatarRenderWorker(self.owner,'black',(2,2),interval=.01)
            try:
                with worker.condition:
                    first=worker.request('audio_maintenance');second=worker.request('record_start')
                deadline=time.monotonic()+2
                while time.monotonic()<deadline:
                    with worker.condition:results=list(worker.results)
                    if len(results)>=2:break
                    time.sleep(.01)
                result={v['command_id']:v for v in results}
                self.assertTrue(result[first]['ok']);self.assertFalse(result[second]['ok'])
                self.assertEqual(self.recording.starts,0)
            finally:worker.close()


class GtkRoutingTests(unittest.TestCase):
    def setUp(self):
        path=ROOT/'candidate/aura/tools/board_avatar_gtk.py'
        spec=importlib.util.spec_from_file_location('_maintenance_gtk_routing_test',path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        self.stage=module.BoardAvatarStage.__new__(module.BoardAvatarStage)
        self.stage.idle_audio_maintenance=True;self.calls=[]
        self.stage.controller=SimpleNamespace(request=lambda *args:self.calls.append(args) or 'intent',
            public=lambda:{'phase':'IDLE','avatar_command_pending':0,'automatic_conversation':{}})
        self.stage.transcription_store=SimpleNamespace(update=lambda *args:self.fail('GTK must not save settings'))
        self.stage.transcriber=SimpleNamespace(conversation_selection=SimpleNamespace(saved=None),
            select_conversation=lambda **kw:self.fail('GTK must not change conversation selection'))
        self.stage.config={}
        self.stage.services=SimpleNamespace(read=lambda:{'snapshot':{'modules':{},'capabilities':{'record_start':True}}},
            submit=lambda *args:self.fail('Held audio must not enter another service'))

    def test_maintenance_disabled_and_extra_fields_cannot_queue(self):
        with self.assertRaises(ValueError):self.stage.command({'type':'audio_maintenance','unexpected':True})
        self.stage.idle_audio_maintenance=False
        with self.assertRaises(ValueError):self.stage.command({'type':'audio_maintenance'})
        self.assertFalse(self.calls)

    def test_settings_and_conversation_change_queue_before_side_effects(self):
        self.stage.command({'type':'asr_config','values':{'enabled':True}})
        self.stage.command({'type':'conversation_toggle'})
        self.assertEqual(self.calls,[('configure_transcription_saved',{'enabled':True}),
                                     ('conversation_start_selected',False)])

    def test_remote_recording_branch_respects_authoritative_output_gate(self):
        self.stage.output=facade();self.stage.output.begin_idle_maintenance()
        with self.assertRaises(RuntimeError):self.stage.command({'type':'service_action','action':'record_stop'})


@unittest.skipUnless(importlib.util.find_spec('gi'),'Real GStreamer requires PyGObject')
class RealSyntheticGstTests(unittest.TestCase):
    def test_actual_pipe_worker_recovers_and_keeps_old_references_out(self):
        out=MaintenanceAudioOutput(device='SYNTHETIC_FAKESINK_NO_ALSA',synthetic_sink=True,echo_reference=True)
        received=[]
        try:
            self.wait(lambda:out.read().get('device_ready'),3)
            release=out.subscribe_reference(lambda *args:received.append(args))
            self.wait(lambda:bool(received),2);release();last=received[-1][2]
            request=out.begin_idle_maintenance()
            with self.assertRaises(RuntimeError):out.begin_stream()
            self.wait(lambda:out.maintenance_status()['state']=='READY_HELD',5)
            self.assertEqual(out.pipeline_epoch,1)
            self.assertTrue(out.finish_idle_maintenance(request))
            newer=[];release=out.subscribe_reference(lambda *args:newer.append(args))
            self.wait(lambda:bool(newer),2);release()
            self.assertGreater(newer[0][2],last)
            # Cooldown rejection is an ACK, with no second epoch or token drift.
            out.begin_idle_maintenance();self.wait(lambda:out.maintenance_status()['state']=='REJECTED',2)
            self.assertFalse(out.maintenance_held);self.assertEqual((out.pipeline_epoch,out.token),(1,1))
            out.begin_stream();out.append_pcm(bytes(960),0);out.end_stream()
            self.wait(out.finished,2);out.stop()
            self.assertFalse(out.streaming);self.assertFalse(out.active)
        finally:
            out.close();self.assertIsNotNone(out.process.poll());self.assertFalse(out.reader.is_alive())
            self.assertTrue(out.process.stdin.closed);self.assertTrue(out.process.stdout.closed)

    def test_worker_rejects_unsafe_synthetic_configuration_before_device_open(self):
        worker=ROOT/'candidate/aura/tools/gstreamer_audio_worker.py'
        result=subprocess.run([sys.executable,'-B',str(worker),'--maintenance-fakesink'],
            capture_output=True,text=True,timeout=3)
        self.assertEqual(result.returncode,2);self.assertIn('Synthetic sink requires',result.stderr)

    def wait(self,predicate,seconds):
        deadline=time.monotonic()+seconds
        while time.monotonic()<deadline:
            if predicate():return
            time.sleep(.01)
        self.fail('Bounded synthetic lifecycle wait expired')


if __name__=='__main__':unittest.main(verbosity=2)
