"""Execute pinned controller/selector methods with public RAM capture stand-ins."""
from collections import deque
from contextlib import contextmanager
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import tempfile
import threading
import time
from types import SimpleNamespace as NS
import unittest
import uuid

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[6]
REPAIR=PROJECT/'deliverables/2026-10-30_board_owner/integration/dialogue_repair'
MEMORY=HERE.parent/'memory_probe'
INDEX=json.loads((REPAIR/'summary_recall_acceptance_review_20261101/SOURCE_INDEX.json').read_text(encoding='utf-8'))
SOURCES={row['component']:row for row in INDEX['sources']}
SOURCES.update({row['component']:row for row in json.loads((MEMORY/'R3_CONSTRUCTION_SOURCE_INDEX.json').read_text(encoding='utf-8'))})
SOURCES['common/conversation_selection.py']={
    'path':str(PROJECT/'deliverables/2026-10-30_board_owner/integration/production_business_overlay/production_modules/common/conversation_selection.py'),
    'sha256':'69c80251ac3b531944bc151e0456c5b9cf4012edbe52e5e4780fdbc192cfa2b0'}


def pinned(relative):
    if relative in SOURCES:
        row=SOURCES[relative]
        path=Path(row['path'])
        assert hashlib.sha256(path.read_bytes()).hexdigest()==row['sha256']
        return path
    path=PROJECT/'aura'/relative
    expected={'tools/handsfree_recording.py':'a7e1a55e797e97fa605725ad7423e80704612c3ed4a703db177345ca4fe6a924',
              'tools/barge_in_recording.py':'59794f4f234ba0e6433e8b26a44ca65dbd5616af513a5111fb2c6d6738530b6d'}[relative]
    assert hashlib.sha256(path.read_bytes()).hexdigest()==expected
    return path


class PublicCapture:
    def __init__(self,*args,**kwargs):
        self.state='IDLE'
        self.on_speech_start=None
    def start(self):
        self.state='RECORDING'
        return 'authored-public-capture'
    def snapshot(self):return {'state':self.state,'speech_active':False}
    def cancel(self):self.state='CANCELLED'
    def close(self):self.state='CLOSED'


class PublicVisual:
    def __init__(self):
        self.last_error=''
        self.cancel_count=0
        self.fail_cancel=False
        self.output=NS(active=False,paused=False)
    def public(self):
        return dict(phase='IDLE',playing=False,paused=False,pending_job=None,audio_output_state='IDLE_READY')
    def cancel(self):
        self.cancel_count+=1
        if self.fail_cancel:raise RuntimeError('authored public cancellation failure')


class PublicPreference:
    def __init__(self,path):self.value=True;self.writes=[]
    def read(self):return self.value
    def write(self,value):self.value=value;self.writes.append(value)


def definitions(path,names,scope):
    tree=ast.parse(path.read_text(encoding='utf-8'))
    nodes=[node for node in tree.body if isinstance(node,(ast.ClassDef,ast.FunctionDef)) and node.name in names]
    assert {node.name for node in nodes}==set(names),(path,names)
    module=ast.Module(body=[ast.ImportFrom(module='__future__',names=[ast.alias(name='annotations')],level=0)]+nodes,type_ignores=[])
    ast.fix_missing_locations(module)
    exec(compile(module,str(path),'exec'),scope)


def classes(folder):
    scope=dict(time=time,uuid=uuid,threading=threading,json=json,os=os,Path=Path,stat=stat,
               re=re,hashlib=hashlib,deque=deque,contextmanager=contextmanager,
               Mcp01Capture=PublicCapture,HandsFreeSettings=PublicPreference)
    definitions(pinned('tools/board_recording.py'),['RecordingController'],scope)
    definitions(pinned('tools/handsfree_recording.py'),['HandsFreeRecordingController'],scope)
    definitions(pinned('tools/barge_in_recording.py'),['BargeInRecordingController'],scope)
    definitions(HERE/folder/'tools/voice_first_recording.py',['VoiceFirstRecordingController'],scope)
    definitions(pinned('board/runtime/audio/board_dialogue_jobs.py'),['BoardDialogueJobs'],scope)
    definitions(pinned('common/conversation_store.py'),['conversation_id'],scope)
    definitions(pinned('common/conversation_selection.py'),['ConversationSelection'],scope)
    definitions(pinned('tools/production_listening.py'),['ProductionMonitorChoice','bind_automatic_listening'],scope)
    return scope


def create(folder,temp):
    scope=classes(folder)
    selection=scope['ConversationSelection'](Path(temp)/'public_selection.json')
    selection.select(False)
    class Jobs(scope['BoardDialogueJobs']):
        def __init__(self):
            self.condition=threading.Condition(threading.RLock())
            self.closed=False
            self.conversation_selection=selection
            self.scope_provider=None
            self.profile_selection=None
            self.session_id='public-initial-session'
            self.boot_id='public-boot'
            self.generation=5
            self.waiting=self.active=self._active_job=self._playback=None
            self._stream_clock=None
            self.progress=deque()
            self.playback_invalidator=None
            self.calls=[]
            self.lock_held_for_resume=[]
            self.reset_count=0
        def enabled(self):return not self.closed
        def public(self):return dict(feedback_ready=True,pending=False)
        def reset_enrollment(self):self.reset_count+=1
        def select_conversation(self,*,resume):
            self.calls.append(resume)
            if resume:self.lock_held_for_resume.append(self.condition._is_owned())
            return super().select_conversation(resume=resume)
    jobs=Jobs()
    visual=PublicVisual()
    recording=object.__new__(scope['VoiceFirstRecordingController'])
    now=NS(value=10.)
    attributes=dict(transcriber=jobs,controller=visual,clock=lambda:now.value,
        closed=False,_closing=False,wake_word_required=False,barge_enabled=False,voice_first=True,
        wake_rearm=False,_pause_resume=None,monitor_enabled=True,monitor_owned=True,monitor_entered=True,
        monitor_state='CONVERSATION',monitor_reason='DIRECT_SPEECH',monitor_error='',
        monitor_key=('audio','public-boot','public-old-owner'),cooldown_until=0.,listen_started=10.,listen_id=None,
        proof_lock=threading.Lock(),speech_proof=None,last_presence=None,last_voice_activity=10.,
        early_listen=False,entry_stable=True,awaiting_entry=False,entry_deadline=None,visual_hold_since=None,
        last_stop_reason='',stop_reasons={},monitor_stats=dict(armed=1,speech_starts=0,submitted=0,entry_rejected=0,visual_stops=0),
        attention_gate=NS(boot_id='public-boot',reset=lambda:None),capture=None,capture_kind=None,
        capture_factory=PublicCapture,auto_capture_factory=PublicCapture,recording_state='IDLE',recording_error='',
        auto_enabled=True,auto_state='LISTENING',auto_error='',auto_turns=0,rearm_at=None,ack_deadline=None,
        utterance=None,barge_capture=None,barge_lock=threading.Lock(),barge_speech=None,
        social_active=False,social_opened=False,social_ended_at=None)
    for key,value in attributes.items():setattr(recording,key,value)
    recording.transcription=scope['RecordingController']._empty_transcription('ANSWERED')
    recording.monitor_settings=scope['ProductionMonitorChoice'](Path(temp))
    pair=NS(ready_now=lambda:True)
    runtime=NS(config=NS(data_origin='board'),started=True,closed=False)
    business=NS(runtime=runtime,character_pair=pair,recording=recording)
    scope['bind_automatic_listening'](recording,business,pair)
    return recording,jobs,selection,now,visual


class ExplicitResumeMethodsTests(unittest.TestCase):
    @contextmanager
    def fixture(self,folder='after'):
        with tempfile.TemporaryDirectory(prefix='public-pause-resume-',dir=HERE) as temp:
            assert Path(temp).resolve().parent==HERE.resolve()
            yield create(folder,temp)

    def arm(self,recording,now):
        now.value+=1.
        recording._monitor_tick()

    def test_explicit_continue_retains_scope_once_and_uses_original_generation_path(self):
        with self.fixture() as (recording,jobs,selection,now,visual):
            cid,session,generation=selection.active,jobs.session_id,jobs.generation
            recording.handsfree_toggle()
            self.assertFalse(recording.monitor_enabled)
            self.assertEqual(recording._pause_resume[0],'paused')
            recording.handsfree_toggle()
            self.assertEqual(recording._pause_resume[0],'pending')
            self.arm(recording,now)
            self.assertEqual(jobs.calls,[True])
            self.assertEqual(selection.active,cid)
            self.assertEqual(selection.saved,cid)
            self.assertNotEqual(jobs.session_id,session)
            self.assertGreater(jobs.generation,generation)
            self.assertEqual(jobs.lock_held_for_resume,[True])
            self.assertIsNone(recording._pause_resume)
            self.assertTrue(recording.monitor_owned)
            self.assertEqual(recording.monitor_settings.backend.writes,[False,True])

    def test_old_code_started_a_new_scope_for_the_same_explicit_toggle_sequence(self):
        with self.fixture('before') as (recording,jobs,selection,now,visual):
            old=selection.active
            recording.handsfree_toggle();recording.handsfree_toggle();self.arm(recording,now)
            self.assertEqual(jobs.calls,[False])
            self.assertNotEqual(selection.active,old)

    def test_missing_active_or_selection_changed_before_continue_does_not_restore(self):
        for change in ['no_active','different_selection','transport_owner','new_selection_object','provider']:
            with self.fixture() as (recording,jobs,selection,now,visual):
                old=selection.active
                recording.handsfree_toggle()
                if change=='no_active':selection.active=None
                elif change=='different_selection':selection.select(False)
                elif change=='transport_owner':jobs.session_id='public-replaced-session'
                elif change=='new_selection_object':
                    replacement=classes('after')['ConversationSelection'](selection.path)
                    replacement.active=selection.active
                    jobs.conversation_selection=replacement
                else:jobs.scope_provider=lambda meta: {'kind':'conversation','id':'c'*32}
                recording.handsfree_toggle();self.arm(recording,now)
                self.assertEqual(jobs.calls,[False],change)
                self.assertNotEqual(jobs.conversation_selection.active,old,change)
                self.assertIsNone(recording._pause_resume)

    def test_pending_resume_rechecks_profile_scope_and_never_mints_a_grant(self):
        with self.fixture() as (recording,jobs,selection,now,visual):
            old=selection.active
            recording.handsfree_toggle();recording.handsfree_toggle()
            grant=object()
            jobs.profile_selection=dict(scope=dict(kind='profile',id='public-profile',grant=grant),conversation_id='b'*32)
            self.arm(recording,now)
            self.assertEqual(jobs.calls,[False])
            self.assertIs(jobs.profile_selection['scope']['grant'],grant)
            self.assertIs(jobs._scope({})['grant'],grant)
            self.assertNotEqual(jobs.profile_selection['conversation_id'],'b'*32)
            self.assertEqual(selection.active,old)
            self.assertIsNone(recording._pause_resume)

    def test_scope_or_boot_changes_after_continue_are_rechecked_at_consumption(self):
        for change in ['saved','active','session','boot']:
            with self.fixture() as (recording,jobs,selection,now,visual):
                old=selection.active
                recording.handsfree_toggle();recording.handsfree_toggle()
                if change=='saved':selection.saved='b'*32
                elif change=='active':selection.active='b'*32
                elif change=='session':jobs.session_id='changed-after-click'
                else:jobs.boot_id='different-public-boot'
                self.arm(recording,now)
                self.assertEqual(jobs.calls,[False],change)
                self.assertNotEqual(selection.active,old,change)

    def test_automatic_silence_ends_owner_and_next_start_is_still_new(self):
        with self.fixture() as (recording,jobs,selection,now,visual):
            recording.handsfree_toggle();recording.handsfree_toggle();self.arm(recording,now)
            old=selection.active
            recording.monitor_entered=True
            recording.auto_enabled=True
            now.value=recording.listen_started+31.
            recording._monitor_tick()
            self.assertEqual(recording.last_stop_reason,'CONVERSATION_SILENCE')
            self.assertIsNone(recording._pause_resume)
            self.assertTrue(recording.monitor_enabled)
            self.arm(recording,now)
            self.assertEqual(jobs.calls,[True,False])
            self.assertNotEqual(selection.active,old)

    def test_repeat_toggle_and_explicit_or_internal_cancel_cannot_reuse_stale_marker(self):
        with self.fixture() as (recording,jobs,selection,now,visual):
            recording.handsfree_toggle();recording.handsfree_toggle();recording.handsfree_toggle()
            self.assertFalse(recording.monitor_enabled)
            self.assertEqual(recording._pause_resume[0],'paused')
            recording.cancel()
            self.assertIsNone(recording._pause_resume)
            recording.handsfree_toggle();self.arm(recording,now)
            self.assertEqual(jobs.calls,[False])
            recording.cancel()  # Existing production wrapper rearms only an enabled owner.
            self.assertTrue(recording.monitor_enabled)
            self.assertIsNone(recording._pause_resume)
            self.arm(recording,now)
            self.assertEqual(jobs.calls,[False,False])

    def test_cancellation_failure_does_not_publish_a_resume_credential(self):
        with self.fixture() as (recording,jobs,selection,now,visual):
            visual.fail_cancel=True
            with self.assertRaises(RuntimeError):recording.handsfree_toggle()
            self.assertIsNone(recording._pause_resume)
            self.assertFalse(recording.monitor_enabled)
            self.assertEqual(jobs.calls,[])


if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ExplicitResumeMethodsTests))
    proof=dict(schema='aura.explicit-pause-resume-public-method-tests.v1',tests=result.testsRun,
        failures=len(result.failures),errors=len(result.errors),passed=result.wasSuccessful(),
        actual_controller_selector_and_production_wrapper_methods=True,
        capture_visual_backend_and_preference_backends_are_public_standins=True,
        only_authored_temporary_selection_files=True,
        actual_device_model_HTTP_service_private_database_or_grant_access=False)
    (HERE/'PUBLIC_TEST_RESULT.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(proof))
    raise SystemExit(0 if result.wasSuccessful() else 1)
