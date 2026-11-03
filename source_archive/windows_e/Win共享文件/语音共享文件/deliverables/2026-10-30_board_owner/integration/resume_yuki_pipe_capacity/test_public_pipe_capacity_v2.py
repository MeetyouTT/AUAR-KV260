"""Narrow runtime-state exception tests: no actual POSIX/device/model operation."""
import copy
import ast
import importlib.util
import io
import json
from pathlib import Path
import stat
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('capacity_v2', HERE/'public_pipe_capacity_v2.py')
capacity = importlib.util.module_from_spec(spec)
spec.loader.exec_module(capacity)


def info(*, directory=False, mode=None, uid=0, size=2, links=1, inode=None):
    return SimpleNamespace(st_mode=(stat.S_IFDIR if directory else stat.S_IFREG) |
        (mode if mode is not None else (0o700 if directory else 0o600)),
        st_uid=uid,st_size=size,st_nlink=links,st_dev=1,st_ino=inode or (100 if directory else 101))


class StateFileTests(unittest.TestCase):
    def validate(self, raw=b'{}', *, file_info=None, path_info=None, parent_info=None,
                 redirected=False, changed_parent=False, after_info=None):
        file_info=file_info or info(size=len(raw))
        parent_info=parent_info or info(directory=True)
        path_info=path_info or file_info
        def path_stat(path):
            return path_info if path.name=='ui_settings.json' else parent_info
        def resolved(path,strict=False):
            return path.with_name('redirected') if redirected else path
        def fstat(fd):
            return parent_info if fd==100 else after_info or file_info
        opened=Mock(side_effect=[100,101]);closed=Mock()
        with patch.object(capacity.Path,'resolve',resolved), \
             patch.object(capacity.Path,'is_symlink',return_value=False), \
             patch.object(capacity.Path,'stat',path_stat), \
             patch.object(capacity.os,'open',opened), \
             patch.object(capacity.os,'fstat',fstat), \
             patch.object(capacity.os,'read',side_effect=[raw,b'']), \
             patch.object(capacity.os,'close',closed), \
             patch.object(capacity.os,'O_NOFOLLOW',0x80000,create=True), \
             patch.object(capacity.os,'O_DIRECTORY',0x20000,create=True), \
             patch.object(capacity.os,'O_NONBLOCK',0x800,create=True):
            result=capacity.runtime_state_file()
        return result,opened,closed

    def test_legitimate_json_reformat_or_preference_mutation_allowed_without_returning_body(self):
        for raw in (b'{"volume":70}',b'{\n  "volume": 70,\n  "monitoring": false\n}',
                    '{"display":"雪妃","last_window_size":[800,480]}'.encode()):
            with self.subTest(raw=raw):
                result,opened,closed=self.validate(raw)
                self.assertIs(result,True)
                self.assertEqual(opened.call_args_list[1].args[0],'ui_settings.json')
                self.assertEqual(opened.call_args_list[1].kwargs,{'dir_fd':100})
                self.assertEqual([x.args[0] for x in closed.call_args_list],[101,100])
                self.assertNotIn('volume',repr(result))

    def test_only_one_exact_relative_name_can_use_exception(self):
        for relative in ('private/other.json','private/../runtime/config.json',
                         '/tmp/ui_settings.json','private/./ui_settings.json',
                         'private/ui_settings.json/','private/ui_settings.json.bak'):
            with self.subTest(relative=relative),self.assertRaises(capacity.Refused):
                capacity.runtime_state_file(relative)

    def test_symlink_or_parent_redirect_refused_before_open(self):
        with self.assertRaisesRegex(capacity.Refused,'canonical_private_path'):
            self.validate(redirected=True)

    def test_non_root_or_group_public_or_executable_or_setid_state_refused(self):
        for value in (info(uid=1000),info(mode=0o644),info(mode=0o660),info(mode=0o700),info(mode=0o4600)):
            with self.subTest(value=value),self.assertRaises(capacity.Refused):
                self.validate(file_info=value)

    def test_readonly_owner_private_file_allowed(self):
        result,_,_=self.validate(file_info=info(mode=0o400))
        self.assertTrue(result)

    def test_fifo_hardlink_oversize_or_size_change_refused(self):
        fifo=info();fifo.st_mode=stat.S_IFIFO|0o600
        cases=(fifo,info(links=2),info(size=65537),info(size=3))
        for value in cases:
            with self.subTest(value=value),self.assertRaises(capacity.Refused):
                self.validate(file_info=value)

    def test_parent_must_remain_root_owned_private_directory(self):
        for value in (info(directory=True,uid=1000),info(directory=True,mode=0o755),info()):
            with self.subTest(value=value),self.assertRaises(capacity.Refused):
                self.validate(parent_info=value)

    def test_opened_file_cannot_be_replaced_by_another_inode(self):
        with self.assertRaisesRegex(capacity.Refused,'replaced_during_read'):
            self.validate(path_info=info(inode=102))

    def test_json_must_remain_one_valid_object_not_list_scalar_or_ambiguous(self):
        for raw in (b'[]',b'null',b'42',b'"value"',b'{bad',b'{"a":1,"a":2}',b'{"a":NaN}'):
            with self.subTest(raw=raw),self.assertRaises(ValueError):self.validate(raw)

    def test_exact_64k_valid_json_object_accepted(self):
        raw=b'{"x":"'+b'x'*(65536-len(b'{"x":""}'))+b'"}'
        self.assertEqual(len(raw),65536)
        self.assertTrue(self.validate(raw)[0])

    def test_stream_growth_beyond_64k_refused(self):
        with self.assertRaisesRegex(capacity.Refused,'size_bound'):
            self.validate(b'x'*65537,file_info=info(size=65536))


class ClosureTests(unittest.TestCase):
    def fixture(self):
        control=SimpleNamespace(LOCK='/run/aura-avatar-ui.lock',UNIT='aura-avatar-ui.service')
        launch={'command':['/usr/bin/python3','-B',capacity.TARGET+'/runtime/aura/tools/board_avatar_pan.py'],
                'single_publisher_lock':control.LOCK,'original_service':control.UNIT}
        config={'board_business':{'enabled':True,'data_origin':'synthetic','model_port':8797,
                                'asr_threads':2,'frontend_threads':1}}
        payload={f'public-{i}':b'public' for i in range(353)}
        payload.update({'launch.json':capacity.encoded(launch),
                        'runtime/aura/config/board_avatar_gtk.json':capacity.encoded(config),
                        capacity.RUNTIME_STATE:b'{"volume":70}'})
        files={key:{'bytes':len(raw),'sha256':capacity.digest(raw)} for key,raw in payload.items()}
        manifest={'target':capacity.TARGET,'ready':True,'data_origin':'synthetic',
                  'candidate_files':files,'launch':launch}
        inspection=capacity.digest(capacity.encoded(manifest));manifest['inspection_sha256']=inspection
        raw_manifest=capacity.encoded(manifest)
        def reader(path,maximum=0):
            if path.endswith('/assembly_manifest.json'):return raw_manifest
            return payload[path[len(capacity.TARGET)+1:]]
        return control,manifest,payload,inspection,reader

    def test_state_mutation_does_not_change_or_rewrite_initial_manifest_pin(self):
        control,manifest,payload,inspection,reader=self.fixture()
        original_pin=copy.deepcopy(manifest['candidate_files'][capacity.RUNTIME_STATE])
        payload[capacity.RUNTIME_STATE]=b'{\n "volume":70,"fullscreen":true\n}'
        with patch.object(capacity,'INSPECTION',inspection),patch.object(capacity,'read',reader), \
             patch.object(capacity,'runtime_state_file',return_value=True) as state:
            self.assertEqual(capacity.assembly_proof(control),manifest['launch']['command'])
            self.assertEqual(capacity.assembly_proof(control),manifest['launch']['command'])
        self.assertEqual(state.call_count,2)
        self.assertEqual(manifest['candidate_files'][capacity.RUNTIME_STATE],original_pin)

    def test_any_of_remaining_355_file_mutations_still_refused(self):
        for relative in ('public-0','public-352','launch.json','runtime/aura/config/board_avatar_gtk.json'):
            with self.subTest(relative=relative):
                control,manifest,payload,inspection,reader=self.fixture();payload[relative]+=b'changed'
                with patch.object(capacity,'INSPECTION',inspection),patch.object(capacity,'read',reader), \
                     patch.object(capacity,'runtime_state_file',return_value=True):
                    with self.assertRaisesRegex(capacity.Refused,'candidate_component_changed'):
                        capacity.assembly_proof(control)

    def test_invalid_mutable_state_still_refuses_whole_assembly(self):
        control,manifest,payload,inspection,reader=self.fixture()
        with patch.object(capacity,'INSPECTION',inspection),patch.object(capacity,'read',reader), \
             patch.object(capacity,'runtime_state_file',side_effect=capacity.Refused('bad_state')):
            with self.assertRaisesRegex(capacity.Refused,'bad_state'):capacity.assembly_proof(control)

    def test_exception_cannot_be_moved_to_another_private_file(self):
        control,manifest,payload,inspection,reader=self.fixture()
        manifest['candidate_files']['private/other.json']=manifest['candidate_files'].pop(capacity.RUNTIME_STATE)
        inspection=capacity.digest(capacity.encoded({k:v for k,v in manifest.items() if k!='inspection_sha256'}))
        manifest['inspection_sha256']=inspection
        def changed_reader(path,maximum=0):
            return capacity.encoded(manifest) if path.endswith('/assembly_manifest.json') else reader(path,maximum)
        with patch.object(capacity,'INSPECTION',inspection),patch.object(capacity,'read',changed_reader):
            with self.assertRaisesRegex(capacity.Refused,'exact_runtime_state'):capacity.assembly_proof(control)

    def test_pending_round2_pins_fail_closed_before_any_preflight_or_import(self):
        argv=['--probe-file','x','--control-file','y','--policy','z',
              '--candidate-pid','10','--candidate-birth','10','--candidate-cmdline-sha256','a'*64]
        with patch.object(capacity,'ROUND2_READY',False),patch.object(capacity,'load_module') as load, \
             patch('sys.stdout',new_callable=io.StringIO) as stream:
            self.assertEqual(capacity.main(argv),2)
        load.assert_not_called()
        self.assertEqual(json.loads(stream.getvalue())['error_code'],'round2_reviewed_control_and_policy_not_frozen')


class Round2EvidenceArgTests(unittest.TestCase):
    def fixture(self):
        control=SimpleNamespace(TARGET=capacity.TARGET,CONTROL=capacity.CONTROL_ROOT)
        argv=['/usr/bin/python3','-B',capacity.TARGET+'/runtime/aura/tools/board_avatar_pan.py',
              '--root',capacity.TARGET+'/stage','--config',capacity.TARGET+'/runtime/aura/config/board_avatar_gtk.json',
              '--settings-file',capacity.TARGET+'/private/ui_settings.json',
              '--evidence-root',capacity.TARGET+'/evidence/gui-capacity-1']
        return control,argv

    def test_only_reviewed_evidence_directory_changes_and_original_list_is_untouched(self):
        control,argv=self.fixture();original=list(argv)
        expected=capacity.round2_owner_argv(argv,control)
        changes=[(a,b) for a,b in zip(argv,expected) if a!=b]
        self.assertEqual(changes,[(capacity.TARGET+'/evidence/gui-capacity-1',
                                  capacity.CONTROL_ROOT+'/evidence/gui-capacity-round2')])
        self.assertEqual(argv,original)

    def test_missing_duplicate_or_arbitrary_evidence_argument_refused(self):
        control,argv=self.fixture()
        cases=[argv[:-2],argv+['--evidence-root','/tmp/anything'],argv[:-1]+['/tmp/anything']]
        for value in cases:
            with self.subTest(value=value),self.assertRaises(capacity.Refused):
                capacity.round2_owner_argv(value,control)

    def test_control_root_cannot_redirect_expected_evidence(self):
        control,argv=self.fixture();control.CONTROL='/tmp/other'
        with self.assertRaisesRegex(capacity.Refused,'exact_target_and_control'):
            capacity.round2_owner_argv(argv,control)


class PreservedGateTests(unittest.TestCase):
    def test_round2_exact_control_and_policy_initialize_71_sealed_aliases(self):
        root=HERE.parent/'resume_ui_trial_round2'
        control=capacity.load_module(root/'control_round2.py',capacity.CONTROL_SHA,'_frozen_round2_control_test')
        policy=control.read_policy(str(root/'policy.json'),capacity.POLICY_SHA)
        self.assertEqual(control.TARGET,capacity.TARGET)
        self.assertEqual(control.CONTROL,capacity.CONTROL_ROOT)
        self.assertEqual(policy['inspection_sha256'],capacity.INSPECTION)
        self.assertEqual(len(control._READ_ALIASES),71)
        self.assertTrue(capacity.ROUND2_READY)

    def test_audio_device_and_transport_gates_remain_exact_original_functions(self):
        old=ast.parse((HERE/'public_pipe_capacity.py').read_text(encoding='utf-8'))
        new=ast.parse((HERE/'public_pipe_capacity_v2.py').read_text(encoding='utf-8'))
        names=('protected_state','probe_argv','loopback_state','lock_proof','load_module')
        old_functions={node.name:node for node in old.body if isinstance(node,ast.FunctionDef)}
        new_functions={node.name:node for node in new.body if isinstance(node,ast.FunctionDef)}
        for name in names:
            with self.subTest(name=name):
                self.assertEqual(ast.dump(old_functions[name]),ast.dump(new_functions[name]))


class FullRound2SnapshotTests(unittest.TestCase):
    def fixture(self):
        spec=importlib.util.spec_from_file_location('prior_capacity_fixtures',HERE/'test_public_pipe_capacity.py')
        old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
        control=old.FakeControl();control.TARGET=capacity.TARGET;control.CONTROL=capacity.CONTROL_ROOT
        _,descriptor=Round2EvidenceArgTests().fixture()
        control.owner['argv']=capacity.round2_owner_argv(descriptor,control)
        control.receipt.update(owner=copy.deepcopy(control.owner),target=capacity.TARGET,
                               source_inspection=capacity.INSPECTION)
        verifier=capacity.Verifier(control,{},copy.deepcopy(control.owner),old.state,lambda *args:True)
        return control,descriptor,verifier

    def test_whole_round2_owner_and_exact_evidence_override_accepted(self):
        control,descriptor,verifier=self.fixture()
        with patch.object(capacity.Path,'read_text',return_value=capacity.BOOT), \
             patch.object(capacity,'assembly_proof',return_value=descriptor):
            result=verifier.snapshot(include_service_pids=False)
        self.assertEqual(result['assembly_immutable_file_count'],355)
        self.assertTrue(result['runtime_ui_settings_initial_manifest_pin_preserved'])
        self.assertEqual(result['original_unit_main_pid'],0)

    def test_extra_actual_owner_argument_is_not_ignored(self):
        control,descriptor,verifier=self.fixture();control.owner['argv']+=['--other','unexpected']
        with patch.object(capacity.Path,'read_text',return_value=capacity.BOOT), \
             patch.object(capacity,'assembly_proof',return_value=descriptor):
            with self.assertRaisesRegex(capacity.Refused,'candidate_owner_changed'):
                verifier.snapshot(include_service_pids=False)


if __name__=='__main__':unittest.main()
