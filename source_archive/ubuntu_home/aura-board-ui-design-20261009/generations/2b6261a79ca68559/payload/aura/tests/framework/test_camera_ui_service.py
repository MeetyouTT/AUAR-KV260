"""Contract/freshness and command tests without a camera, detector or motion."""
import unittest
from board.interaction.ui_contract import validate_snapshot
from board.vision.ui_camera_service import CameraState


class CameraUiTests(unittest.TestCase):
    def setUp(self):
        self.now=1000
        self.state=CameraState('boot','camera-service',clock=lambda:self.now)

    def frame(self,fid=1):
        self.state.captured(self.now)
        self.state.processed(fid,self.now,b'jpeg',{'target_id':1,'tracks':[
            {'track_id':1,'generation':1,'visible':True,'confirmed':True},
            {'track_id':2,'generation':1,'visible':True,'confirmed':True},
            {'track_id':3,'generation':1,'visible':False,'confirmed':True}]},45.)

    def command(self):
        value=self.state.snapshot()
        return {'protocol_version':'aura-ui-1','board_boot_id':'boot','service_epoch':'camera-service',
                'command_id':'one','ui_epoch':'ui','ui_generation':0,'context':value['context'],
                'snapshot_sequence':value['sequence'],'issued_mono_ms':self.now,'deadline_mono_ms':self.now+2500,
                'action':'target_select','params':{'target':value['modules']['target']['tracks'][1]['key']}}

    def test_no_frames_no_ready_or_preview(self):
        value=validate_snapshot(self.state.snapshot(),'boot',self.now)
        self.assertEqual(value['modules']['camera']['state'],'LOST')
        self.assertNotIn('preview',value)
        self.assertFalse(any(value['capabilities'].values()))

    def test_actual_faces_and_modules_do_not_imply_identity_or_dpu(self):
        self.frame();value=validate_snapshot(self.state.snapshot(),'boot',self.now)
        self.assertEqual(value['source_kind'],'actual')
        self.assertEqual(value['modules']['vision']['people_count'],2)
        self.assertEqual(value['modules']['vision']['count_kind'],'faces')
        self.assertEqual(set(value['modules']),{'camera','vision','target'})
        self.assertEqual([k for k,v in value['capabilities'].items() if v],['target_select'])

    def test_freeze_expires_detection_before_preview(self):
        self.frame();self.now+=751;value=self.state.snapshot()
        self.assertEqual(value['modules']['vision']['state'],'DEGRADED')
        self.assertEqual(value['modules']['target']['state'],'LOST')
        self.assertIn('preview',value)
        self.now+=250;value=self.state.snapshot()
        self.assertEqual(value['modules']['camera']['state'],'LOST')
        self.assertNotIn('preview',value)
        self.assertIsNone(self.state.preview(self.state.camera_epoch,1))

    def test_old_camera_epoch_and_evicted_frame_rejected(self):
        for fid in range(1,11):self.frame(fid)
        self.assertEqual(len(self.state.frames),8)
        self.assertIsNone(self.state.preview(self.state.camera_epoch,1))
        self.assertIsNone(self.state.preview('old',10))
        self.assertEqual(self.state.preview(self.state.camera_epoch,10),b'jpeg')

    def test_fresh_target_selection_and_duplicate(self):
        self.frame();command=self.command();ack=self.state.command(command)
        self.assertTrue(ack['accepted'])
        self.assertEqual(self.state.command(command),ack)
        self.assertEqual(self.state.requested_target,2)
        self.assertEqual(self.state.snapshot()['modules']['target']['selected']['track_id'],1)

    def test_stale_target_cannot_be_selected(self):
        self.frame();command=self.command();self.now+=800
        self.assertFalse(self.state.command(command)['accepted'])

    def test_extra_command_fields_rejected(self):
        self.frame();command=self.command();command['unreviewed_field']=True
        self.assertFalse(self.state.command(command)['accepted'])

    def test_no_record_identity_or_motion_control(self):
        self.frame()
        for action in ('record_start','identity_enroll','motion_disarm','ask_frame'):
            command=self.command();command['action']=action
            self.assertFalse(self.state.command(command)['accepted'])

    def test_cross_boot_context_and_expired_commands_rejected(self):
        self.frame()
        for name,value in [('board_boot_id','old'),('service_epoch','old'),('context',{}),
                           ('deadline_mono_ms',999),('snapshot_sequence',10**6),('ui_generation',True)]:
            command=self.command();command[name]=value
            self.assertFalse(self.state.command(command)['accepted'],name)


if __name__=='__main__':unittest.main()
