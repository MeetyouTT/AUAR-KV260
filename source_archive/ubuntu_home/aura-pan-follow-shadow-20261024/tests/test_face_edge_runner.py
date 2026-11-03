import contextlib,http.client,importlib.util,io,json,sys,tempfile,threading,time,unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];APP=Path('/home/ghmd/aura-native-live-20261024/r4/candidate/aura')
sys.path.insert(0,str(ROOT/'motion_v2'));sys.path.insert(0,str(APP))
from board.vision import ui_camera_service as camera
from board.identity.face_targets import FaceTargetService
from face_source import install
install(camera)
spec=importlib.util.spec_from_file_location('face_runner',ROOT/'face_edge_v5/run_face_shadow.py');runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)

class RunnerTests(unittest.TestCase):
    def evaluate(self,x):
        state=camera.CameraState(Path('/proc/sys/kernel/random/boot_id').read_text().strip())
        face=FaceTargetService(lambda:None,lambda *args:None,state.camera_epoch,lock=state.lock,clock=state.clock)
        state.identity=SimpleNamespace(face_targets=face);stop=threading.Event()
        def publish():
            fid=0
            while not stop.is_set():
                fid+=1;stamp=int(time.monotonic()*1000)
                state.captured(stamp)
                with state.lock:
                    face.ready=True;face.count=1;face.stamp=stamp
                    face.key={'camera_epoch':state.camera_epoch,'track_id':1,'track_generation':1}
                    face.tracker.last_frame=fid
                    face.tracker.tracks={1:{'visible':True,'confirmed':True,'frame_id':fid,'observed_time':stamp/1000.,'box':[x,100.,80.,80.],'score':.95}}
                face.on_face(None,None,fid,stamp,face.key);stop.wait(.04)
        producer=threading.Thread(target=publish);producer.start()
        server=ThreadingHTTPServer(('127.0.0.1',0),camera.handler_for(state));threading.Thread(target=server.serve_forever,daemon=True).start()
        original=http.client.HTTPConnection
        try:
            with tempfile.TemporaryDirectory() as folder:
                out=Path(folder)/'trial.jsonl';argv=['run_face_shadow.py','--app-root',str(APP),'--config',str(ROOT/'face_edge_v5/config.json'),'--output',str(out),'--duration','.6']
                with patch.object(sys,'argv',argv),patch.object(runner.os,'uname',return_value=SimpleNamespace(machine='aarch64')):
                    with patch.object(runner.http.client,'HTTPConnection',side_effect=lambda *a,**kw:original('127.0.0.1',server.server_port,timeout=kw.get('timeout',1))):
                        with contextlib.redirect_stdout(io.StringIO()):code=runner.main()
                self.assertEqual(code,0)
                return json.loads(Path(str(out)+'.summary.json').read_text())
        finally:stop.set();producer.join(1);server.shutdown();server.server_close()

    def test_face_in_safe_zone_does_not_propose_position_change(self):
        r=self.evaluate(280.)
        self.assertTrue(r['full_duration_completed']);self.assertGreaterEqual(r['distinct_ready_sources'],5)
        self.assertEqual(r['proposal_min_us'],1425);self.assertEqual(r['proposal_max_us'],1425)
        self.assertEqual(r['maximum_speed_us_s'],0)

    def test_face_at_edge_proposes_smooth_bounded_turn_without_io(self):
        r=self.evaluate(550.)
        self.assertTrue(r['full_duration_completed']);self.assertGreater(r['proposal_max_us'],1425)
        self.assertLessEqual(r['proposal_max_us'],1445);self.assertLessEqual(r['maximum_speed_us_s'],12)
        self.assertFalse(r['physical_actuation']);self.assertEqual(r['register_writes'],0)

if __name__=='__main__':unittest.main()
