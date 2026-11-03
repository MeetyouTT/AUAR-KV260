import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('gui_trial',str(Path(__file__).resolve().parents[1]/'gui_trial_controller.py'))
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class GuiPublicationTests(unittest.TestCase):
    def test_stop_only_targets_gui(self):
        trial=module.GuiTrial.__new__(module.GuiTrial);calls=[]
        trial.command=lambda args:calls.append(args)
        trial.props=lambda unit:{'MainPID':'0'}
        trial.stop_gui()
        self.assertEqual(calls,[['systemctl','stop','--no-block',module.GUI]])

    def test_restore_refuses_unowned_override_before_stopping(self):
        with tempfile.TemporaryDirectory() as name:
            path=Path(name)/'override.conf';path.write_text('belongs to another update')
            trial=module.GuiTrial.__new__(module.GuiTrial);trial.override=path
            trial.state=lambda:{'override_sha256':'0'*64}
            trial.stop_gui=lambda:self.fail('Unowned file must be rejected before a service stop')
            with self.assertRaisesRegex(RuntimeError,'another override'):trial.restore()
            self.assertTrue(path.exists())

    def test_restore_removes_only_own_override_and_keeps_camera(self):
        with tempfile.TemporaryDirectory() as name:
            path=Path(name)/'override.conf';path.write_text('owned GUI override')
            trial=module.GuiTrial.__new__(module.GuiTrial);trial.override=path;trial.prefix='test-gui'
            trial.state=lambda:{'override_sha256':module.sha(path)}
            calls=[];trial.stop_gui=lambda:calls.append(['stop_gui'])
            trial.command=lambda args:calls.append(args);trial.wait_gui=lambda new:None
            trial.verify=lambda:None;trial.save=lambda phase:{'phase':phase}
            result=trial.restore()
            self.assertFalse(path.exists())
            self.assertEqual(result['phase'],'ORIGINAL_GUI_RESTORED_CAMERA_UNCHANGED')
            self.assertFalse(any(module.CAMERA in c for c in calls))

    def wait_check(self,pan,accept):
        trial=module.GuiTrial.__new__(module.GuiTrial)
        trial.get=lambda port,path:{'phase':'IDLE','playing':False,'audio_output_state':'IDLE_READY','manual_pan':pan}
        trial.props=lambda unit:{'ActiveState':'active'}
        now=[0.]
        with patch.object(module.time,'monotonic',side_effect=lambda:now[0]),patch.object(module.time,'sleep',side_effect=lambda s:now.__setitem__(0,now[0]+s)):
            if accept:trial.wait_gui(True)
            else:
                with self.assertRaises(RuntimeError):trial.wait_gui(True)

    def test_ready_off_and_observed_range_accept(self):
        self.wait_check({'state':'READY','minimum_us':1425,'maximum_us':1445,'automatic_following':False,
                        'history':[],'readback':{'flags':0,'lease_left_ms':0}},True)

    def test_output_active_even_if_ready_is_rejected(self):
        self.wait_check({'state':'READY','minimum_us':1425,'maximum_us':1445,'automatic_following':False,
                        'history':[],'readback':{'flags':15,'lease_left_ms':100}},False)

    def test_broader_than_observed_range_is_rejected(self):
        self.wait_check({'state':'READY','minimum_us':1400,'maximum_us':1600,'automatic_following':False,
                        'history':[],'readback':{'flags':0,'lease_left_ms':0}},False)


if __name__=='__main__':unittest.main()
