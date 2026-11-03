"""Only fake state dictionaries and AST; no SSH, device, models or private IO."""
import ast
import copy
import unittest
from guard_v16_paused import QUIET_HELPER, build_remote
from release_common import PUBLISH_SHA, remote_from


def paused_fixture():
    return dict(phase='IDLE', playing=False, audio_output_state='IDLE_READY', error='',
        pending_job=None, avatar_command_pending=0, streaming_reply=False,
        handsfree_dialogue=dict(enabled=False,state='PAUSED',microphone_open=False,conversation_entered=False),
        safe_capture_diagnostics=dict(snapshot_available=False,capture_state='UNKNOWN',
            monitor_enabled=False,monitor_state='PAUSED',recording_state='IDLE',error_code='none',
            error_source='none',capture={},input_queue={},audio_frontend={},
            counters=dict(armed=0,speech_starts=0,submitted=0)),
        local_recording=dict(state='IDLE',error='',sample_count=0,can_stop=False),
        local_transcription=dict(state='DISABLED',error=''),
        runtime_faults=dict(count=0,last=None),board_business=dict(dialogue=dict(pending=False)),
        manual_pan=dict(automatic_following=False,state='FAULT',pulse_us=None))


def state_function(remote, value):
    tree=ast.parse(remote)
    selected=[n for n in tree.body if isinstance(n,ast.FunctionDef)
              and n.name in ('never_armed_paused_capture','state')]
    def need(value, code):
        if not value:raise ValueError(code)
    namespace=dict(SPEC={'automatic_listening':True},need=need,listening_readonly_state=lambda:value)
    exec(compile(ast.Module(body=selected,type_ignores=[]),'<source-only-state>','exec'),namespace)
    return namespace['state']


class GuardReviewTests(unittest.TestCase):
    def setUp(self):
        self.old=remote_from('production_business_acceptance/publish_business_ui.py',PUBLISH_SHA)
        self.new=build_remote()

    def test_original_rejects_exact_no_object_pause_and_new_accepts(self):
        value=paused_fixture()
        with self.assertRaises(ValueError):state_function(self.old,value)()
        self.assertIs(state_function(self.new,value)(),value)

    def test_reject_active_fault_pending_and_previously_armed(self):
        changes=[('handsfree_dialogue','enabled',True),('handsfree_dialogue','microphone_open',True),
            ('handsfree_dialogue','state','WAITING_SPEECH'),('local_recording','state','RECORDING'),
            ('local_recording','sample_count',320),('local_recording','error','failed'),
            ('local_transcription','state','TRANSCRIBING'),('local_transcription','error','failed'),
            ('safe_capture_diagnostics','snapshot_available',True),
            ('safe_capture_diagnostics','error_code','capture_failed'),
            ('safe_capture_diagnostics','capture',{'state':'RECORDING'}),
            ('safe_capture_diagnostics','capture_state','RECORDING'),
            ('runtime_faults','count',1)]
        for group,key,changed in changes:
            with self.subTest(group=group,key=key):
                value=paused_fixture();value[group][key]=changed
                with self.assertRaises(ValueError):state_function(self.new,value)()
        for counter in ('armed','speech_starts','submitted'):
            value=paused_fixture();value['safe_capture_diagnostics']['counters'][counter]=1
            with self.assertRaises(ValueError):state_function(self.new,value)()
        for mutation in ('pending','avatar','job','playing','fault_error'):
            value=paused_fixture()
            if mutation=='pending':value['board_business']['dialogue']['pending']=True
            elif mutation=='avatar':value['avatar_command_pending']=1
            elif mutation=='job':value['pending_job']='synthetic'
            elif mutation=='playing':value['playing']=True
            else:value['error']='synthetic'
            with self.assertRaises(ValueError):state_function(self.new,value)()

    def test_old_safe_idle_case_unchanged_and_pan_guards_preserved(self):
        value=paused_fixture()
        value['safe_capture_diagnostics']['capture_state']='IDLE'
        self.assertEqual(state_function(self.old,value)(),state_function(self.new,value)())
        for changed in (dict(automatic_following=True),dict(state='READY'),dict(pulse_us=1500)):
            bad=copy.deepcopy(value);bad['manual_pan'].update(changed)
            with self.assertRaises(ValueError):state_function(self.new,bad)()

    def test_all_other_original_functions_ast_identical(self):
        get=lambda raw:{n.name:ast.dump(n,include_attributes=False) for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef)}
        old,new=get(self.old),get(self.new)
        self.assertEqual(set(new)-set(old),{'never_armed_paused_capture'})
        for name,definition in old.items():
            if name!='state':self.assertEqual(new[name],definition,name)
        self.assertIn("'887546c09eb1897845c8d7f55a9e3f9b9c761448c7410f2b599259ae0b51efd2'",self.new)
        self.assertIn("assert ACTION in ('guard','window-inspect','normal-close')",self.new)


if __name__=='__main__':unittest.main(verbosity=2)
