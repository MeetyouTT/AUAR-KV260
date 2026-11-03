import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from firmware_trial_controller import CAMERA,GUI,Trial


class GuiReadinessTests(unittest.TestCase):
    def exercise(self,ready_after):
        with tempfile.TemporaryDirectory() as name:
            config=Path(name)/'gui.json';config.write_text(json.dumps({'display_wait_seconds':90,'ready_wait_seconds':90}))
            trial=Trial.__new__(Trial);trial.base={'gui_config':str(config)}
            now=[0.];started={'camera':False};commands=[];saved=[]
            def props(unit):
                if unit==CAMERA:return {'MainPID':'12' if started['camera'] else '0','ActiveState':'active'}
                return {'MainPID':'20','ActiveState':'active' if now[0]>=ready_after else 'activating'}
            def command(args,**kwargs):
                commands.append(args)
                if args[-1]==CAMERA and 'start' in args:started['camera']=True
                return ''
            health={'detected_frames':8,'native_critical':True,'owner_fenced':False,'worker_alive':True,
                    'identity_ready':True,'primary_calls':11,'optional':{'yunet':{'overruns':0},'sface':{'overruns':0}}}
            def get(port,path):
                if port==8790:return health
                if now[0]<ready_after:raise ConnectionRefusedError('GUI still inside configured display grace')
                return {'playing':False,'phase':'IDLE','audio_output_state':'IDLE_READY'}
            trial.props=props;trial.command=command;trial.get=get;trial.brief=lambda h:h
            trial.state=lambda:{'stopped_counter_snapshot':{'primary_calls':10,'optional':{'yunet':{'overruns':0},'sface':{'overruns':0}}}}
            trial.save=lambda phase,**kwargs:saved.append(phase)
            with patch('firmware_trial_controller.time.monotonic',side_effect=lambda:now[0]),patch('firmware_trial_controller.time.sleep',side_effect=lambda seconds:now.__setitem__(0,now[0]+seconds)):
                trial.start_models()
            return now[0],commands,saved

    def test_gui_ready_after_old_70_second_limit_is_accepted_without_restarting_again(self):
        elapsed,commands,saved=self.exercise(95)
        self.assertEqual(elapsed,95)
        self.assertEqual(saved,['ORIGINAL_R4_AND_GUI_RUNNING'])
        self.assertEqual(sum(c[-1]==CAMERA and 'start' in c for c in commands),1)
        self.assertEqual(sum(c[-1]==GUI and 'start' in c for c in commands),1)

    def test_gui_never_ready_still_fails_with_bound(self):
        with self.assertRaisesRegex(RuntimeError,'Original GUI restart not confirmed'):
            self.exercise(9999)


if __name__=='__main__':unittest.main()
