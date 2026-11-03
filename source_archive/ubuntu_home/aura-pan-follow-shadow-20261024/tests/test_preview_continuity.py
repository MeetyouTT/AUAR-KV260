"""Display grace does not change source expiry or retain cleared frames."""
import importlib.util,json,sys,threading,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,'/home/ghmd/aura-native-live-20261024/r4/candidate/aura')
from board.vision.local_preview import MAGIC,PIXELS,PREFIX,unpack
spec=importlib.util.spec_from_file_location('preview_continuity',ROOT/'preview_fix_v1/board_camera_preview.py')
preview=importlib.util.module_from_spec(spec);spec.loader.exec_module(preview)

class PreviewTests(unittest.TestCase):
    def setUp(self):
        self.worker=object.__new__(preview.CameraPreviewWorker);self.worker.lock=threading.RLock()
        self.worker.reader_owner={'camera_epoch':'camera'};self.worker.error=''
        self.output=dict(reference=dict(camera_epoch='camera',frame_id=3,captured_mono_ms=1000),times=[],ages=[],count=3)
        self.worker.outputs={'vision':self.output}
    def visible(self,now):
        with patch.object(preview.time,'monotonic',return_value=now/1000):return self.worker.read('vision')['frame_visible']
    def test_display_survives_one_delayed_refresh_but_expires_at_500ms(self):
        self.assertTrue(self.visible(1300));self.assertTrue(self.visible(1499));self.assertFalse(self.visible(1500))
    def test_camera_clear_hides_frame_immediately_inside_display_grace(self):
        self.assertTrue(self.visible(1300));self.output['reference']=None;self.assertFalse(self.visible(1301))
    def test_packet_acceptance_is_still_strictly_250ms(self):
        owner=dict(board_boot_id='boot',service_epoch='service',camera_epoch='a'*32)
        header=json.dumps(dict(owner,frame_id=1,captured_mono_ms=1000)).encode()
        raw=PREFIX.pack(MAGIC,len(header))+header+b'\0'*PIXELS
        self.assertEqual(unpack(raw,owner,1249)[0]['frame_id'],1)
        with self.assertRaises(ValueError):unpack(raw,owner,1250)

    def test_delayed_gtk_metadata_does_not_cover_a_running_raw_sink(self):
        value=dict(frame_visible=False,sink_active=True,transport='raw-local',error='')
        self.assertFalse(preview.CameraPreviewWorker.placeholder_visible(value,'READY'))
        self.assertTrue(preview.CameraPreviewWorker.placeholder_visible(value,'LOST'))
        value['error']='Invalid raw source'
        self.assertTrue(preview.CameraPreviewWorker.placeholder_visible(value,'READY'))

    def test_unconnected_or_jpeg_source_keeps_placeholder_until_first_frame(self):
        for value in (dict(frame_visible=False,sink_active=False,transport='raw-local'),
                      dict(frame_visible=False,sink_active=True,transport='jpeg-http')):
            self.assertTrue(preview.CameraPreviewWorker.placeholder_visible(value,'READY'))

if __name__=='__main__':unittest.main()
