"""Synthetic preflight/only-monkeypatch tests; no board, model, HTTP or GUI."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import stat
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('capacity', HERE/'public_pipe_capacity.py')
capacity = importlib.util.module_from_spec(spec)
spec.loader.exec_module(capacity)
ORIGINAL = HERE.parent/'resume_inference/board_audio_pipeline_probe.py'
CONTROL = HERE.parent/'resume_ui_trial/restore_v2.py'
POLICY = HERE.parent/'resume_ui_trial/ui_trial_policy.v2.json'


def state():
    return dict(phase='IDLE', playing=False,
        handsfree_dialogue=dict(enabled=False, microphone_open=False),
        manual_pan=dict(state='FAULT', pulse_us=None, target_us=None, automatic_following=False),
        avatar_display=dict(kind='native_yuki_egl', visible=True, frame_scheduling_active=True, target_fps=16),
        character_pair=dict(state='READY', profile_version=capacity.PAIR, prompt_sha256=capacity.PROMPT),
        voice_barge_in=dict(listening=False, continuation_listening=False),
        automatic_conversation=dict(enabled=False),
        local_transcription=dict(service=dict(enabled=True, board_owned=True, pending=False)),
        local_recording=dict(state='IDLE',sample_count=0))


def set_path(value, name, replacement, *, delete=False):
    parts = name.split('.')
    for key in parts[:-1]:
        value = value[key]
    if delete:
        del value[parts[-1]]
    else:
        value[parts[-1]] = replacement


class FakeControl:
    LOCK = '/run/aura-avatar-ui.lock'
    UNIT = 'aura-avatar-ui.service'
    def __init__(self):
        self.owner = dict(pid=987654, birth='900000', cmdline_sha256='a'*64,
                          argv=['/usr/bin/python3', '-B', capacity.TARGET+'/runtime/aura/tools/board_avatar_pan.py'])
        self.unit = dict(MainPID='0', ActiveState='inactive', Restart='no', SendSIGKILL='no',
                         TimeoutStopUSec='infinity', Job='')
        self.receipt = dict(owner=copy.deepcopy(self.owner), target=capacity.TARGET,
                            source_inspection=capacity.INSPECTION, argv_sha256='a'*64, lock_inherited_fd=3)
        self.camera = dict(pid=260102, birth='784437')
        self.process_calls = 0
        self.change_second_owner = False
    def inactive(self, policy):
        return {}, self.unit
    def process(self, pid):
        if pid == 260102:
            return dict(self.camera)
        self.process_calls += 1
        value = copy.deepcopy(self.owner)
        if self.change_second_owner and self.process_calls % 2 == 0:
            value['birth'] = '900001'
        return value
    @staticmethod
    def same_owner(a, b):
        return bool(a and b and all(a.get(k) == b.get(k) for k in ('pid','birth','cmdline_sha256')))
    def candidate_owner(self):
        return self.receipt
    def command(self, args, timeout):
        assert args == ['/bin/systemctl','show','aura-camera-ui.service','--property=MainPID','--value']
        return '260102\n'


class SafetyTests(unittest.TestCase):
    def snapshot(self, control=None, value=None, *, include=False):
        control = control or FakeControl()
        read_state = Mock(return_value=value if value is not None else state())
        locked = Mock(return_value=True)
        verifier = capacity.Verifier(control, {}, copy.deepcopy(control.owner), read_state, locked)
        with patch.object(capacity.Path, 'read_text', return_value=capacity.BOOT), \
             patch.object(capacity, 'assembly_proof', return_value=control.owner['argv']):
            result = verifier.snapshot(include_service_pids=include)
        return result, read_state, locked

    def test_exact_detached_owner_allowed_with_original_unit_zero(self):
        result, reader, locked = self.snapshot()
        self.assertEqual(result['original_unit_main_pid'], 0)
        self.assertEqual(result['camera_pid'], 260102)
        self.assertTrue(result['inherited_publisher_lock'])
        reader.assert_called_once_with(); locked.assert_called_once()

    def test_inner_include_false_does_not_skip_any_protection(self):
        first, _, _ = self.snapshot(include=False)
        second, _, _ = self.snapshot(include=True)
        self.assertEqual(first, second)

    def test_guard_mismatch_or_active_original_fails_before_http(self):
        for key, bad in [('MainPID','1296'),('ActiveState','active'),('Restart','always'),
                         ('SendSIGKILL','yes'),('TimeoutStopUSec','6s'),('Job','23 start')]:
            with self.subTest(key=key):
                control = FakeControl(); control.unit[key] = bad
                with self.assertRaises(capacity.Refused): self.snapshot(control)

    def test_pid_reuse_during_preflight_refused(self):
        control = FakeControl(); control.change_second_owner = True
        with self.assertRaisesRegex(capacity.Refused, 'owner_changed_during'):
            self.snapshot(control)

    def test_current_camera_birth_required(self):
        control = FakeControl(); control.camera['birth'] = '784438'
        with self.assertRaisesRegex(capacity.Refused, 'camera_owner_changed'):
            self.snapshot(control)

    def test_exact_receipt_cannot_be_replaced_by_other_launch(self):
        for key, bad in [('target','/other'),('source_inspection','b'*64),('argv_sha256','b'*64)]:
            with self.subTest(key=key):
                control = FakeControl(); control.receipt[key] = bad
                with self.assertRaisesRegex(capacity.Refused, 'launch_receipt'):
                    self.snapshot(control)

    def test_cannot_reduce_to_base_gtk_to_hide_pan_load(self):
        control = FakeControl(); control.owner['argv'][-1] = capacity.TARGET+'/runtime/aura/tools/board_avatar_gtk.py'
        with patch.object(capacity.Path, 'read_text', return_value=capacity.BOOT), \
             patch.object(capacity, 'assembly_proof', return_value=['/usr/bin/python3','-B',capacity.TARGET+'/runtime/aura/tools/board_avatar_pan.py']):
            verifier = capacity.Verifier(control, {}, control.owner, lambda: state(), lambda *a:True)
            with self.assertRaisesRegex(capacity.Refused, 'owner_changed'):
                verifier.snapshot()

    def test_every_false_gate_requires_present_explicit_false(self):
        gates = ('playing','handsfree_dialogue.enabled','handsfree_dialogue.microphone_open',
                 'manual_pan.automatic_following','voice_barge_in.listening',
                 'voice_barge_in.continuation_listening','automatic_conversation.enabled',
                 'local_transcription.service.pending')
        for name in gates:
            for mode in ('true','missing','zero'):
                with self.subTest(name=name,mode=mode):
                    value = state(); set_path(value, name, True if mode=='true' else 0, delete=mode=='missing')
                    with self.assertRaises(capacity.Refused): capacity.protected_state(value)

    def test_fault_null_and_visible16_are_not_relaxed(self):
        for name,bad in [('phase','SPEAKING'),('manual_pan.state','READY'),
                         ('manual_pan.pulse_us',1400),('manual_pan.target_us',1400),
                         ('avatar_display.target_fps',8),('avatar_display.visible',False),
                         ('avatar_display.kind','native_sink_handoff'),('character_pair.state','PREPARED'),
                         ('local_recording.state','RECORDING'),('local_recording.sample_count',640)]:
            with self.subTest(name=name):
                value=state();set_path(value,name,bad)
                with self.assertRaises(capacity.Refused):capacity.protected_state(value)

    def test_no_raw_identity_or_conversation_leaves_state_filter(self):
        value=state();value.update(profile={'id':'PRIVATE'},conversation='PRIVATE',image='PRIVATE')
        self.assertNotIn('PRIVATE',json.dumps(capacity.protected_state(value)))


class StaticPinsTests(unittest.TestCase):
    def test_original_and_control_and_policy_files_unchanged(self):
        self.assertEqual(capacity.digest(ORIGINAL.read_bytes()),capacity.PROBE_SHA)
        self.assertEqual(capacity.digest(CONTROL.read_bytes()),capacity.CONTROL_SHA)
        self.assertEqual(capacity.digest(POLICY.read_bytes()),capacity.POLICY_SHA)

    def test_pinned_loader_uses_verified_bytes_without_bytecode_write(self):
        module=capacity.load_module(ORIGINAL,capacity.PROBE_SHA,'_test_frozen_public_probe')
        self.assertTrue(callable(module.main))
        self.assertEqual(module.WAV_SHA,'1a6bf94091d9c35e11aea5d494d05e3287b8f5c767f6de3bfd796d91b637500c')
        with self.assertRaises(capacity.Refused):capacity.load_module(ORIGINAL,'0'*64,'_bad')

    def test_v2_initializer_seals_exact_71_original_aliases_without_opening_them(self):
        control=capacity.load_module(CONTROL,capacity.CONTROL_SHA,'_frozen_ui_v2_test')
        value=control.read_policy(str(POLICY),capacity.POLICY_SHA)
        self.assertEqual(len(value['source_aliases']),71)
        self.assertEqual(len(control._READ_ALIASES),71)
        with self.assertRaises(TypeError):control._READ_ALIASES['invented']={}

    def test_duplicate_json_and_nan_rejected(self):
        for raw in ('{"a":1,"a":2}', '{"a":NaN}'):
            with self.subTest(raw=raw),self.assertRaises(capacity.Refused):capacity.strict_json(raw)

    def test_fixed_args_do_not_expose_faster_nice_or_larger_queue(self):
        self.assertEqual(capacity.probe_argv(), ['--code-root',capacity.TARGET+'/runtime/aura',
            '--resources-root',capacity.BASE,'--mode','pipeline','--runs','1','--num-threads','1',
            '--process-nice','0','--queue-frames','8'])

    def test_only_one_assigned_attribute_of_probe(self):
        import ast
        tree=ast.parse((HERE/'public_pipe_capacity.py').read_text())
        assigned=[]
        for node in ast.walk(tree):
            if isinstance(node,ast.Assign):
                for target in node.targets:
                    if isinstance(target,ast.Attribute) and isinstance(target.value,ast.Name) and target.value.id=='probe':
                        assigned.append(target.attr)
        self.assertEqual(assigned,['safety_snapshot','safety_snapshot'])  # install + finally restore


class AssemblyTests(unittest.TestCase):
    def test_inspection_encoding_matches_frozen_real_assembler_function(self):
        import ast
        source=HERE.parent/'resume_yuki_run_assembly/assemble_v2.py'
        tree=ast.parse(source.read_text())
        node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='encoded')
        namespace={'json':json}
        exec(compile(ast.Module(body=[node],type_ignores=[]),str(source),'exec'),namespace)
        value={'原始资源':'雪妃','value':[1,True,None]}
        self.assertEqual(capacity.encoded(value),namespace['encoded'](value))

    def fixture(self):
        launch=dict(command=['/usr/bin/python3','-B',capacity.TARGET+'/runtime/aura/tools/board_avatar_pan.py'],
                    single_publisher_lock=FakeControl.LOCK,original_service=FakeControl.UNIT)
        raw=b'public'
        files={f'resource-{i}':dict(bytes=len(raw),sha256=capacity.digest(raw)) for i in range(356)}
        manifest=dict(target=capacity.TARGET,ready=True,data_origin='synthetic',candidate_files=files,launch=launch)
        inspection=capacity.digest(capacity.encoded(manifest));manifest['inspection_sha256']=inspection
        config=dict(board_business=dict(enabled=True,data_origin='synthetic',model_port=8797,asr_threads=2,frontend_threads=1))
        def read(path,maximum=0):
            if path.endswith('/assembly_manifest.json'):return capacity.encoded(manifest)
            if path.endswith('/launch.json'):return capacity.encoded(launch)
            if path.endswith('/board_avatar_gtk.json'):return capacity.encoded(config)
            return raw
        return manifest,config,inspection,read

    def test_complete_private_synthetic_source_closure(self):
        manifest,config,inspection,read=self.fixture()
        with patch.object(capacity,'INSPECTION',inspection),patch.object(capacity,'read',read):
            self.assertEqual(capacity.assembly_proof(FakeControl()),manifest['launch']['command'])

    def test_model_configuration_change_is_refused_after_source_check(self):
        manifest,config,inspection,read=self.fixture();config['board_business']['model_port']=8795
        with patch.object(capacity,'INSPECTION',inspection),patch.object(capacity,'read',read):
            with self.assertRaisesRegex(capacity.Refused,'business_models'):
                capacity.assembly_proof(FakeControl())

    def test_manifest_mutation_cannot_reuse_reviewed_inspection(self):
        manifest,config,inspection,read=self.fixture();manifest['data_origin']='board'
        with patch.object(capacity,'INSPECTION',inspection),patch.object(capacity,'read',read):
            with self.assertRaisesRegex(capacity.Refused,'manifest_changed'):
                capacity.assembly_proof(FakeControl())


class ExecutionTests(unittest.TestCase):
    def verifier(self):
        verifier=Mock();verifier.calls=4;verifier.snapshot.return_value={'stable':'metadata'}
        return verifier

    def args(self,action='run'):
        return SimpleNamespace(action=action,probe_file=ORIGINAL)

    def fake_probe(self,status='PASS_PUBLIC_PCM_PUMP_ENDPOINT_AND_ASR',code=0):
        probe=SimpleNamespace(safety_snapshot=lambda **kw:None,other=object())
        original=probe.safety_snapshot
        def main(argv):
            self.assertEqual(argv,capacity.probe_argv())
            self.assertIsNot(probe.safety_snapshot,original)
            probe.safety_snapshot(include_service_pids=True)
            probe.safety_snapshot(include_service_pids=False)
            print(json.dumps(dict(status=status,input_queue=dict(error='',reader_alive=False,capacity_frames=8),
                resources=dict(numpy='1.21.2',onnxruntime='1.17.3',sherpa_onnx='1.13.8'))))
            return code
        probe.main=main
        return probe,original

    def test_inspect_does_not_load_probe_or_models(self):
        loader=Mock(side_effect=AssertionError('must not import'))
        result,code=capacity.execute(self.args('inspect'),self.verifier(),loader)
        loader.assert_not_called();self.assertEqual(code,0)
        self.assertFalse(result['actual_model_probe_executed'])

    def test_run_only_replaces_snapshot_and_restores_it(self):
        probe,original=self.fake_probe();attrs=dict(probe.__dict__)
        verifier=self.verifier()
        result,code=capacity.execute(self.args(),verifier,lambda *a:probe)
        self.assertEqual(code,0);self.assertEqual(result['status'],'PASS_DETACHED_GUI_PUBLIC_PIPE_ONLY')
        self.assertEqual(probe.__dict__,attrs);self.assertIs(probe.safety_snapshot,original)
        self.assertFalse(result['residency']['shared_model_instances'])

    def test_original_probe_failure_not_promoted_to_pass(self):
        probe,_=self.fake_probe('FAILED',2)
        result,code=capacity.execute(self.args(),self.verifier(),lambda *a:probe)
        self.assertEqual(code,2);self.assertEqual(result['probe_result']['status'],'FAILED')

    def test_postcheck_failure_invalidates_success_and_restores_patch(self):
        probe,original=self.fake_probe();verifier=self.verifier()
        verifier.snapshot.side_effect=[{'stable':'metadata'}, {}, {}, capacity.Refused('changed')]
        result,code=capacity.execute(self.args(),verifier,lambda *a:probe)
        self.assertEqual(code,2);self.assertIs(probe.safety_snapshot,original)
        self.assertIn('post_probe',result['failure_type'])

    def test_owner_precheck_failure_never_imports_models(self):
        verifier=self.verifier();verifier.snapshot.side_effect=capacity.Refused('wrong_owner')
        loader=Mock()
        with self.assertRaises(capacity.Refused):capacity.execute(self.args(),verifier,loader)
        loader.assert_not_called()

    def test_other_numpy_runtime_cannot_be_reported_as_matched_pass(self):
        probe,_=self.fake_probe()
        def main(argv):
            print(json.dumps(dict(status='PASS_PUBLIC_PCM_PUMP_ENDPOINT_AND_ASR',
                input_queue=dict(error='',reader_alive=False,capacity_frames=8),
                resources=dict(numpy='1.26.4',onnxruntime='1.17.3',sherpa_onnx='1.13.8'))))
            return 0
        probe.main=main
        result,code=capacity.execute(self.args(),self.verifier(),lambda *a:probe)
        self.assertEqual(code,2)


class SocketTests(unittest.TestCase):
    class Client:
        def __init__(self, packets, peer='127.0.0.1'):
            self.packets=list(packets);self.peer=peer;self.sent=[]
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def getpeername(self):return self.peer,8783
        def sendall(self,raw):self.sent.append(raw)
        def settimeout(self,value):pass
        def recv(self,size):
            value=self.packets.pop(0) if self.packets else b''
            if isinstance(value,Exception):raise value
            return value

    def response(self,body=None,headers=None,status=b'200 OK'):
        body=body or json.dumps(state()).encode()
        headers=headers if headers is not None else b'Content-Length: '+str(len(body)).encode()+b'\r\n'
        return b'HTTP/1.0 '+status+b'\r\n'+headers+b'\r\n'+body

    def test_bounded_get_only_fixed_loopback_path_and_no_raw_body_retained(self):
        raw=self.response();client=self.Client([raw[:23],raw[23:],b''])
        with patch.object(capacity.socket,'create_connection',return_value=client) as connect:
            result=capacity.loopback_state()
        connect.assert_called_once_with(('127.0.0.1',8783),timeout=1.)
        self.assertEqual(result,state())
        self.assertEqual(client.sent,[b'GET /api/state HTTP/1.0\r\nHost: 127.0.0.1:8783\r\nConnection: close\r\n\r\n'])

    def test_redirect_chunked_duplicate_header_and_wrong_length_rejected(self):
        responses=[self.response(status=b'302 Found'),self.response(headers=b'Transfer-Encoding: chunked\r\n'),
                   self.response(headers=b'Content-Length: 1\r\nContent-Length: 1\r\n'),
                   self.response(headers=b'Content-Length: 1\r\n')]
        for response in responses:
            with self.subTest(response=response[:100]):
                with patch.object(capacity.socket,'create_connection',return_value=self.Client([response,b''])):
                    with self.assertRaises(capacity.Refused):capacity.loopback_state()

    def test_peer_address_cannot_be_redirected_elsewhere(self):
        with patch.object(capacity.socket,'create_connection',return_value=self.Client([],peer='192.168.50.1')):
            with self.assertRaisesRegex(capacity.Refused,'nonloopback'):capacity.loopback_state()

    def test_absolute_deadline_not_extended_by_drips_or_socket_timeouts(self):
        client=self.Client([capacity.socket.timeout(),b'x'])
        with patch.object(capacity.socket,'create_connection',return_value=client), \
             patch.object(capacity.time,'monotonic',side_effect=[0.,.2,2.1]):
            with self.assertRaisesRegex(capacity.Refused,'deadline'):capacity.loopback_state()


class InheritedLockTests(unittest.TestCase):
    def check(self,*,line='9: FLOCK  ADVISORY  WRITE 123 00:01:77 0 EOF',fd_target=None,fd_inode=77):
        control=FakeControl();owner=control.owner;receipt=control.receipt
        def path_stat(path):
            is_fd='fd' in path.parts
            return SimpleNamespace(st_mode=stat.S_IFREG|0o600,st_uid=0,st_nlink=1,
                                   st_dev=1,st_ino=fd_inode if is_fd else 77)
        with patch.object(capacity.Path,'stat',path_stat), \
             patch.object(capacity.Path,'is_symlink',return_value=False), \
             patch.object(capacity.Path,'read_text',return_value=line), \
             patch.object(capacity.os,'readlink',return_value=fd_target or control.LOCK), \
             patch.object(capacity.os,'major',return_value=0,create=True), \
             patch.object(capacity.os,'minor',return_value=1,create=True):
            return capacity.lock_proof(owner,receipt,control)

    def test_inherited_flock_keeps_launcher_pid_and_is_not_acquired_or_released(self):
        self.assertTrue(self.check())  # 123 is launcher, candidate is 987654.

    def test_fd_does_not_imply_held_flock(self):
        with self.assertRaisesRegex(capacity.Refused,'not_held'):self.check(line='')

    def test_other_inode_or_descriptor_target_is_rejected(self):
        for args in (dict(fd_inode=78),dict(fd_target='/tmp/other'),
                     dict(line='9: FLOCK ADVISORY WRITE 123 00:01:78 0 EOF')):
            with self.subTest(args=args),self.assertRaises(capacity.Refused):self.check(**args)


if __name__=='__main__':unittest.main()
