import copy
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest

from board.interaction.ui_contract import (ACTIONS, PROTOCOL, SnapshotGate,
    validate_ack, validate_action, validate_snapshot)
from board.interaction.ui_services import ConnectionStore, UiServiceClient, validate_connection


def snapshot(now=10000, sequence=1, epoch='service-1'):
    key = {'camera_epoch':'camera-1','track_id':7,'track_generation':2}
    return {'protocol_version':PROTOCOL,'board_boot_id':'boot-1','service_epoch':epoch,
            'sequence':sequence,'observed_mono_ms':now,'ttl_ms':2500,'source_kind':'fixture',
            'context':{'session_id':'session-1','request_id':'request-1','generation':1},
            'capabilities':{name:True for name in ACTIONS},
            'modules':{'interaction':{'state':'IDLE','reply':'当前回答'},
                       'audio':{'state':'READY'},'camera':{'state':'READY'},
                       'target':{'state':'CONFIRMED','selected':key,'tracks':[{'key':key,'label':'对象 7'}]},
                       'identity':{'state':'KNOWN','db_version':4,
                                   'people':[{'person_id':'person-1','display_name':'小蓝'}]}}}


def wait_for(predicate):
    deadline = time.monotonic()+2
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(.005)
    raise AssertionError('Background adapter did not settle')


class GateTests(unittest.TestCase):
    def setUp(self):
        self.now = 10000
        self.gate = SnapshotGate('boot-1',lambda:self.now)

    def test_missing_modules_remain_unreported(self):
        value = snapshot();value['modules'] = {}
        self.gate.ingest(value)
        self.assertEqual(self.gate.read()['modules'],{})

    def test_old_boot_and_wrong_protocol_rejected(self):
        for key,value in [('board_boot_id','old-boot'),('protocol_version','1.0')]:
            data = snapshot();data[key] = value
            with self.subTest(key=key),self.assertRaises(ValueError):
                self.gate.ingest(data)

    def test_source_time_expires_even_if_poll_repeats_payload(self):
        self.gate.ingest(snapshot())
        self.now += 2000
        self.assertFalse(self.gate.ingest(snapshot()))
        self.now += 500
        self.assertIsNone(self.gate.read())
        with self.assertRaises(ValueError):
            self.gate.ingest(snapshot())

    def test_out_of_order_and_mutated_duplicate_rejected(self):
        self.gate.ingest(snapshot(sequence=4))
        for value in (snapshot(sequence=3),snapshot(sequence=4,now=10001)):
            with self.assertRaises(ValueError):
                self.gate.ingest(value)

    def test_service_restart_does_not_accept_retired_epoch(self):
        self.gate.ingest(snapshot(sequence=9))
        self.gate.ingest(snapshot(epoch='service-2'))
        with self.assertRaises(ValueError):
            self.gate.ingest(snapshot(sequence=10))

    def test_cancel_masks_late_subtitle_until_context_changes(self):
        self.gate.ingest(snapshot())
        self.gate.cancel()
        value = snapshot(sequence=2)
        value['modules']['interaction'].update(state='PROCESSING',reply='迟到回答')
        self.gate.ingest(value)
        self.assertEqual(self.gate.read()['modules']['interaction']['reply'],'')
        self.assertEqual(self.gate.read()['modules']['interaction']['state'],'CANCELLED')
        value = snapshot(sequence=3);value['context']['generation'] = 2
        self.gate.ingest(value)
        self.assertEqual(self.gate.read()['modules']['interaction']['reply'],'当前回答')

    def test_fault_is_independent_of_interaction(self):
        value = snapshot();value['modules']['motion'] = {'state':'FAULT'}
        value['modules']['interaction']['state'] = 'PROCESSING'
        self.gate.ingest(value)
        self.assertEqual(self.gate.read()['modules']['motion']['state'],'FAULT')

    def test_unbounded_or_invalid_payloads_rejected(self):
        mutations = [lambda v:v.update(ttl_ms=6000),lambda v:v.update(sequence=True),
            lambda v:v.update(observed_mono_ms=11000),
            lambda v:v['modules']['interaction'].update(reply='x'*8001),
            lambda v:v['modules']['interaction'].update(timings_ms={'tts':float('nan')}),
            lambda v:v['capabilities'].update(record_start=1),
            lambda v:v['modules']['target']['tracks'].append(copy.deepcopy(v['modules']['target']['tracks'][0]))]
        for mutate in mutations:
            value = snapshot();mutate(value)
            with self.subTest(mutate=mutate),self.assertRaises(ValueError):
                validate_snapshot(value,'boot-1',self.now)

    def test_snapshots_are_copied(self):
        value = snapshot();self.gate.ingest(value)
        value['modules']['audio']['state'] = 'ERROR'
        view = self.gate.read();view['modules']['audio']['state'] = 'ERROR'
        self.assertEqual(self.gate.read()['modules']['audio']['state'],'READY')


class ActionTests(unittest.TestCase):
    def test_unconnected_or_unadvertised_capability_rejected(self):
        with self.assertRaises(ValueError):validate_action('record_start',{},None)
        value = snapshot();value['capabilities']['record_start'] = False
        with self.assertRaises(ValueError):validate_action('record_start',{},value)

    def test_wrong_target_generation_rejected(self):
        value = snapshot();key = copy.deepcopy(value['modules']['target']['selected'])
        key['track_generation'] += 1
        with self.assertRaises(ValueError):validate_action('target_select',{'target':key},value)

    def test_identity_write_requires_confirmation_and_current_database(self):
        value = snapshot();key = value['modules']['target']['selected']
        with self.assertRaises(ValueError):
            validate_action('identity_enroll',{'target':key,'display_name':'x','confirmed':False},value)
        params = {'person_id':'person-1','db_version':3,'confirmed':True}
        with self.assertRaises(ValueError):validate_action('identity_delete',params,value)
        params['db_version'] = 4
        self.assertEqual(validate_action('identity_delete',params,value),params)

    def test_recording_and_playback_are_half_duplex(self):
        value = snapshot();value['modules']['audio']['state'] = 'PLAYING'
        with self.assertRaises(ValueError):validate_action('record_start',{},value)
        with self.assertRaises(ValueError):validate_action('record_stop',{},value)
        value['modules']['audio']['state'] = 'RECORDING'
        self.assertEqual(validate_action('record_stop',{},value),{})

    def test_ui_cannot_arm_move_or_write_raw_registers(self):
        for name in ('motion_arm','servo_move','write_register','clear_fault'):
            with self.subTest(name=name),self.assertRaises(ValueError):validate_action(name,{},snapshot())

    def test_ack_is_correlated_and_not_completion(self):
        command = {k:v for k,v in zip(('protocol_version','board_boot_id','service_epoch','command_id','ui_epoch','ui_generation'),
                    (PROTOCOL,'boot-1','service-1','cmd-1','ui-1',3))}
        command['deadline_mono_ms'] = 12000
        ack = dict(command,accepted=True,detail='queued')
        self.assertEqual(validate_ack(ack,command,10000),{'accepted':True,'detail':'queued'})
        for key,value in [('command_id','other'),('ui_generation',2),('accepted','true')]:
            altered = dict(ack,**{key:value})
            with self.subTest(key=key),self.assertRaises(ValueError):validate_ack(altered,command,10000)
        with self.assertRaises(ValueError):validate_ack(ack,command,12000)


class StoreTests(unittest.TestCase):
    def test_connections_persist_without_changing_audio_preferences(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'connection.json'
            store = ConnectionStore(path)
            self.assertFalse(store.read()['enabled'])
            store.update({'enabled':True,'host':'192.168.1.2','port':8790})
            self.assertEqual(ConnectionStore(path).read(),store.read())
            self.assertEqual(path.stat().st_mode & 0o777,0o600)

    def test_corrupt_configuration_is_reported_and_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'connection.json';path.write_text('{broken')
            store = ConnectionStore(path)
            self.assertTrue(store.error)
            self.assertEqual(path.read_text(),'{broken')

    def test_urls_shell_text_multicast_and_invalid_ports_rejected(self):
        for host in ('http://127.0.0.1','1.2.3.4;id','0.0.0.0','224.0.0.1','300.1.1.1'):
            with self.subTest(host=host),self.assertRaises(ValueError):
                validate_connection({'enabled':True,'host':host,'port':8790})
        with self.assertRaises(ValueError):validate_connection({'enabled':True,'host':'127.0.0.1','port':True})


class FakeTransport:
    def __init__(self):
        self.sequence = 0
        self.commands = []
        self.block = self.release = None
        self.fail = False

    def json(self,base,path,data=None):
        if self.fail:raise OSError('offline')
        if data:
            self.commands.append(copy.deepcopy(data))
            if self.block:
                self.block.set();self.release.wait(1.5)
            return dict(data,accepted=True,detail='fixture queued')
        self.sequence += 1
        return snapshot(sequence=self.sequence)


class ClientTests(unittest.TestCase):
    def client(self,transport):
        client = UiServiceClient('boot-1',{'enabled':True,'host':'127.0.0.1','port':8790},
                                transport=transport,clock=lambda:10000,poll_seconds=.02)
        self.addCleanup(client.close)
        wait_for(lambda:client.read()['snapshot'] is not None)
        return client

    def test_commands_use_correlated_envelope_and_real_ack(self):
        transport = FakeTransport();client = self.client(transport)
        submitted = client.submit('record_start')
        wait_for(lambda:bool(client.read()['results']))
        self.assertTrue(client.read()['results'][-1]['accepted'])
        self.assertEqual(transport.commands[0]['command_id'],submitted['command_id'])
        self.assertEqual(transport.commands[0]['board_boot_id'],'boot-1')

    def test_network_wait_does_not_block_read_and_queue_is_bounded(self):
        transport = FakeTransport();client = self.client(transport)
        transport.block,transport.release = threading.Event(),threading.Event()
        self.addCleanup(transport.release.set)
        client.submit('record_start');self.assertTrue(transport.block.wait(1))
        started = time.monotonic();client.read()
        self.assertLess(time.monotonic()-started,.1)
        for _ in range(4):client.submit('record_start')
        with self.assertRaises(ValueError):client.submit('record_start')
        transport.release.set()

    def test_reconfiguration_discards_inflight_old_ack_and_old_snapshot(self):
        transport = FakeTransport();client = self.client(transport)
        transport.block,transport.release = threading.Event(),threading.Event()
        client.submit('record_start');self.assertTrue(transport.block.wait(1))
        client.configure({'enabled':False,'host':'127.0.0.1','port':8790})
        transport.release.set();time.sleep(.04)
        view = client.read()
        self.assertEqual(view['link'],'DISABLED')
        self.assertIsNone(view['snapshot'])
        self.assertEqual(view['results'],[])

    def test_cancel_discards_old_ack_and_suppresses_old_reply(self):
        transport = FakeTransport();client = self.client(transport)
        transport.block,transport.release = threading.Event(),threading.Event()
        old = client.submit('record_start');self.assertTrue(transport.block.wait(1))
        cancelled = client.submit('cancel')
        transport.release.set()
        wait_for(lambda:bool(client.read()['results']))
        ids = [r['command_id'] for r in client.read()['results']]
        self.assertNotIn(old['command_id'],ids)
        self.assertIn(cancelled['command_id'],ids)
        self.assertEqual(client.read()['snapshot']['modules']['interaction']['reply'],'')

    def test_disconnect_hides_even_previously_fresh_state(self):
        transport = FakeTransport();client = self.client(transport)
        transport.fail = True;client.refresh()
        wait_for(lambda:client.read()['link'] == 'OFFLINE')
        self.assertIsNone(client.read()['snapshot'])
        with self.assertRaises(ValueError):client.submit('record_start')


if __name__ == '__main__':
    unittest.main()
