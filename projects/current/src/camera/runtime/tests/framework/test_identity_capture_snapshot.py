"""Cancellation display masks must never erase an actual capture-start owner."""
import copy
import threading
import unittest
from unittest.mock import patch

from board.identity.voice_enrollment import VoiceEnrollment
from board.interaction.ui_contract import SnapshotGate,validate_snapshot
from board.interaction.ui_services import UiServiceClient
from board.runtime.audio.channel_jobs import ChannelConversationJobs
from tests.framework.test_simple_enrollment import snapshot


class IdentityCaptureSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.now=1000
        self.client=object.__new__(UiServiceClient)
        self.client.condition=threading.Condition();self.client.boot_id='boot'
        self.client.clock=lambda:self.now;self.client.link='READY'
        self.client.gate=SnapshotGate('boot',self.client.clock)
        self.view=snapshot()
        self.view['modules']['interaction']={'state':'IDLE','reply':'late subtitle'}
        self.client.gate.ingest(self.view)
        self.jobs=object.__new__(ChannelConversationJobs)
        self.jobs.boot_id='boot';self.jobs.condition=threading.Condition();self.jobs.capture_owners={}
        self.jobs.identity_snapshot=self.client.identity_snapshot

    def capture(self):
        with patch('board.interaction.ui_contract.millis',return_value=self.now):
            self.jobs.capture_started('clip')
        return self.jobs.capture_owners['clip']

    def test_reproduces_cancelled_display_rejection_and_source_keeps_owner(self):
        self.client.gate.cancel()
        display=self.client.gate.read()
        self.assertTrue(display['interaction_suppressed'])
        self.assertEqual(display['modules']['interaction']['reply'],'')
        with self.assertRaises(ValueError):validate_snapshot(display,'boot',self.now)
        self.jobs.identity_snapshot=self.client.gate.read
        self.assertIsNone(self.capture())
        self.jobs.identity_snapshot=self.client.identity_snapshot
        owner=self.capture()
        self.assertIsNotNone(owner);self.assertEqual(owner,self.view)
        self.assertNotIn('interaction_suppressed',owner)
        self.assertEqual(self.client.gate.read()['modules']['interaction']['reply'],'')

    def test_capture_after_cancel_can_prepare_name_without_issuing_a_write(self):
        self.client.gate.cancel();owner=self.capture();commands=[]
        flow=VoiceEnrollment('boot',self.client.identity_snapshot,commands.append,
            simple=True,now_ms=lambda:self.now,clock=lambda:self.now/1000)
        self.assertEqual(flow.handle('帮我登记身份，我叫小林',owner)['code'],'prepare_name')
        self.assertEqual(commands,[])

    def test_disconnected_and_expired_source_are_still_unavailable(self):
        self.client.link='OFFLINE';self.assertIsNone(self.capture())
        self.client.link='READY';self.now=3000;self.assertIsNone(self.capture())

    def test_invalid_boot_source_and_unknown_fields_are_not_sanitized_into_trust(self):
        for mutation in (lambda v:v.update(board_boot_id='other'),lambda v:v.update(unexpected=True),
                         lambda v:v.update(observed_mono_ms=2000)):
            with self.subTest(mutation=mutation):
                self.client.gate.value=copy.deepcopy(self.view);mutation(self.client.gate.value)
                self.assertIsNone(self.capture())

    def test_returned_source_is_independent_of_protocol_cache(self):
        owner=self.capture();owner['modules']['identity']['db_version']=99
        self.assertEqual(self.client.identity_snapshot()['modules']['identity']['db_version'],0)

    def test_changed_target_after_capture_is_still_rejected(self):
        owner=self.capture();changed=copy.deepcopy(self.view)
        key=changed['modules']['target']['selected'];key['track_generation']+=1
        changed.update(sequence=2);self.client.gate.ingest(changed);commands=[]
        flow=VoiceEnrollment('boot',self.client.identity_snapshot,commands.append,
            simple=True,now_ms=lambda:self.now,clock=lambda:self.now/1000)
        self.assertEqual(flow.handle('帮我登记身份，我叫小林',owner)['code'],'face_unavailable')
        self.assertEqual(commands,[])

    def test_source_read_never_restores_cancelled_authorization(self):
        owner=self.capture();commands=[]
        flow=VoiceEnrollment('boot',self.client.identity_snapshot,commands.append,
            simple=True,now_ms=lambda:self.now,clock=lambda:self.now/1000)
        self.assertEqual(flow.handle('帮我登记身份，我叫小林',owner)['code'],'prepare_name')
        flow.reset();self.client.gate.cancel()
        self.assertIsNone(flow.handle('确认登记',self.capture()))
        self.assertEqual(commands,[]);self.assertFalse(flow.public()['active'])


if __name__=='__main__':unittest.main()
