"""Real before/after UI functions; synthetic controls and public metadata only."""
import copy
import itertools
from pathlib import Path
import queue
import sys
import threading
import time
import unittest
from unittest.mock import patch

import replay_common as replay

HERE=Path(__file__).resolve().parent
OLD=replay.load('before_final_values_ui',HERE/'before/aura/tools/board_avatar_gtk.py')
NEW=replay.load('after_final_values_ui',HERE/'candidate/aura/tools/board_avatar_gtk.py')
OLD_BUSINESS=replay.load('before_final_values_business_ui',HERE/'before/aura/tools/production_business_ui.py')
NEW_BUSINESS=replay.load('after_final_values_business_ui',HERE/'candidate/aura/tools/production_business_ui.py')


def make_tick_stage():
    stage=replay.FIXTURE.tick_stage()
    stage.module=NEW
    stage._ui_set=lambda *args:NEW.BoardAvatarStage._ui_set(stage,*args)
    stage.refresh_settings=lambda state:NEW.BoardAvatarStage.refresh_settings(stage,state)
    stage.refresh_runtime=lambda state,text:NEW.BoardAvatarStage.refresh_runtime(stage,state,text)
    return stage


class FinalValuesTests(unittest.TestCase):
    def test_final_widgets_match_for_layers_modes_and_control_states(self):
        phases=(('IDLE',False,'IDLE'),('THINKING',False,'GENERATING'),
            ('SPEAKING',False,'PLAYING'),('SPEAKING',True,'PLAYING'),
            ('IDLE',False,'CANCELLED'),('IDLE',False,'ERROR'))
        for production,layer,mode,phase in itertools.product((False,True),('presentation','debug'),('manual','automatic','handsfree'),phases):
            with self.subTest(production=production,layer=layer,mode=mode,phase=phase):
                old,new=replay.make_stage(OLD,production),replay.make_stage(NEW,production)
                value=replay.FIXTURE.state_for(*phase)
                for stage in (old,new):
                    stage.config['automatic_turns']=mode!='manual';stage.ui_layer=layer
                if mode=='manual':value['automatic_conversation']={};value['handsfree_dialogue']={}
                elif mode=='automatic':value['handsfree_dialogue']={}
                replay.refresh(old,copy.deepcopy(value),OLD_BUSINESS)
                replay.refresh(new,copy.deepcopy(value),NEW_BUSINESS)
                self.assertEqual(old.snapshot(),new.snapshot())

    def test_reproduced_fourteen_applied_writes_become_zero_when_stable(self):
        old,new=replay.make_stage(OLD),replay.make_stage(NEW)
        replay.refresh(old,replay.state(),OLD_BUSINESS);replay.refresh(new,replay.state(),NEW_BUSINESS)
        old_counts=replay.trace_applied(old,OLD);new_counts=replay.trace_applied(new,NEW)
        before_old,before_new=old.writes(),new.writes()
        replay.refresh(old,replay.state(),OLD_BUSINESS);replay.refresh(new,replay.state(),NEW_BUSINESS)
        self.assertEqual(14,sum(old_counts.values()));self.assertEqual(0,sum(new_counts.values()))
        self.assertEqual(0,new.writes()-before_new)
        self.assertGreater(old.writes()-before_old,14)
        self.assertEqual(old.snapshot(),new.snapshot())

    def test_identity_controls_keep_original_final_conditions(self):
        for identity,capable,pending in itertools.product(({},dict(state='UNKNOWN')),(False,True),(0,1)):
            with self.subTest(identity=bool(identity),capable=capable,pending=pending):
                old,new=replay.make_stage(OLD),replay.make_stage(NEW)
                for stage in (old,new):
                    original=stage.services.read
                    def read(original=original):
                        view=original();view['pending_count']=pending
                        view['snapshot']['modules']['identity']=identity
                        view['snapshot']['capabilities']['identity_enroll']=capable
                        return view
                    stage.services.read=read
                replay.refresh(old,replay.state(),OLD_BUSINESS);replay.refresh(new,replay.state(),NEW_BUSINESS)
                self.assertEqual(old.snapshot(),new.snapshot())
                self.assertEqual(bool(identity) and not pending,new.controls['identity_enroll'].get_sensitive())

    def test_production_toast_stays_visible_then_expires(self):
        old,new=replay.make_stage(OLD),replay.make_stage(NEW)
        for stage in (old,new):stage.toast='SYNTHETIC_NOTICE';stage.toast_until=time.monotonic()+60
        replay.refresh(old,replay.state(),OLD_BUSINESS);replay.refresh(new,replay.state(),NEW_BUSINESS)
        self.assertEqual(old.snapshot(),new.snapshot());self.assertEqual('SYNTHETIC_NOTICE',new.footer.get_text())
        for stage in (old,new):stage.toast_until=0
        replay.refresh(old,replay.state(),OLD_BUSINESS);replay.refresh(new,replay.state(),NEW_BUSINESS)
        self.assertEqual(old.snapshot(),new.snapshot());self.assertNotEqual('SYNTHETIC_NOTICE',new.footer.get_text())

    def test_capture_error_and_recovery_update_in_same_refresh(self):
        old,new=replay.make_stage(OLD),replay.make_stage(NEW)
        previous=None
        for error in ('','capture_timeout',''):
            for stage in (old,new):stage.board_business.recording.recording_error=error
            replay.refresh(old,replay.state(),OLD_BUSINESS);replay.refresh(new,replay.state(),NEW_BUSINESS)
            self.assertEqual(old.snapshot(),new.snapshot())
            if previous is not None:self.assertNotEqual(previous,new.host_status_label.get_text())
            previous=new.host_status_label.get_text()

    def test_readonly_entry_is_reapplied_if_its_current_value_changes(self):
        stage=replay.make_stage(NEW);replay.refresh(stage,replay.state(),NEW_BUSINESS)
        self.assertFalse(stage.host_entry.get_editable())
        stage.host_entry.set_editable(True);stage.port_entry.set_editable(True)
        NEW_BUSINESS.project_business_ui(stage,replay.state())
        self.assertFalse(stage.host_entry.get_editable());self.assertFalse(stage.port_entry.get_editable())

    def test_other_shell_without_guard_keeps_original_projection(self):
        old,new=replay.make_stage(OLD),replay.make_stage(NEW)
        del new._ui_set
        OLD_BUSINESS.project_business_ui(old,replay.state());NEW_BUSINESS.project_business_ui(new,replay.state())
        self.assertEqual(old.snapshot(),new.snapshot())

    def test_pause_cancel_and_error_are_not_delayed_by_ui_layering(self):
        for action in ('pause','cancel','error'):
            with self.subTest(action=action):
                stage=make_tick_stage()
                if action=='error':
                    def fail():raise ValueError('SYNTHETIC_PRIVATE_ERROR')
                    stage.controller.read=fail
                else:
                    request=dict(data=dict(type=action),deadline=time.monotonic()+3,done=threading.Event())
                    stage.bridge.commands.put_nowait(request)
                with patch.dict(sys.modules,{'tools.production_business_ui':NEW_BUSINESS}):
                    self.assertTrue(NEW.BoardAvatarStage.tick(stage))
                if action=='error':
                    self.assertEqual('ValueError',stage.status.get_text());stage.controller.cancel.assert_called_once()
                else:
                    self.assertTrue(request['done'].is_set());self.assertTrue(request['result']['ok'])
                    self.assertEqual(action=='pause',stage.published['paused'])
                    if action=='cancel':self.assertFalse(stage.cancel_button.get_sensitive())


if __name__=='__main__':unittest.main(verbosity=2)
