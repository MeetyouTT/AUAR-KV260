"""Exercise activation commit/rollback decisions with fake devices and real files."""
import hashlib,json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import release_control as release
from test_release_control import fixture

BOOT='7924ac9f-311d-4fcd-98be-57bf023cf1aa'


class OperationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.live=self.root/'live';self.qroot=self.live/'coordinated50-1';source=self.qroot/'aura';source.mkdir(parents=True)
        for name in ('synthetic.py','board/identity/camera_faces.py','board/vision/ui_camera_service.py'):
            p=source/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('pass\n')
        launcher=b'frozen wrapper';(self.qroot/'gil_camera_launcher.py').write_bytes(launcher)
        unit=('[Service]\nEnvironment="AURA_EXPERIMENT_GIL_MS=1"\nExecStart=/usr/bin/python3 -B '+str(self.qroot/'gil_camera_launcher.py')+' '+str(source/'tools/board_camera_motion.py')+' --config /retained/config.json\n').encode()
        (self.qroot/'camera.service.candidate').write_bytes(unit)
        self.hashes={'candidate/aura/synthetic.py':release.sha(source/'synthetic.py')}
        self.d=fixture();self.d.update(retry_hashes=self.hashes,candidate_runtime=str(source),source_hashes={},
            freshness_wiring_sha256=release.sha(source/'board/identity/camera_faces.py'),
            candidate_ui_sha256=release.sha(source/'board/vision/ui_camera_service.py'),candidate_unit_sha256=hashlib.sha256(unit).hexdigest())
        self.qfile=self.qroot/'deployment-result.json';self.qfile.write_text(json.dumps(self.d))
        self.folder=self.root/'activation';self.folder.mkdir();self.clock=0.;self.usb=False;self.mutate=False;self.ops=None;self.commands=[]
        self.parent=SimpleNamespace(BASELINE={},RETRY_HASHES=self.hashes,RETRY_WRAPPER_SHA=hashlib.sha256(launcher).hexdigest(),
            atomic=lambda p,b:Path(p).write_bytes(b),healthy=lambda h:None,single_owner=lambda p:None,
            camera=self.camera,cpu=lambda:0,cpu_delta=lambda a,b:{'cpu_percent_of_board':56},audio_warnings=lambda c:int(self.usb),
            prepare_handoff=self.prepare,rollback_source=lambda root:'pass\n',command=self.command)
        self.patches=[patch.object(release,'LIVE_ROOT',self.live),patch.object(release,'load_parent',return_value=self.parent),
            patch.object(release,'time',SimpleNamespace(monotonic=lambda:self.clock,sleep=self.sleep))]
        for p in self.patches:p.start()
    def tearDown(self):
        for p in reversed(self.patches):p.stop()
        self.temp.cleanup()
    def sleep(self,seconds):self.clock+=seconds
    def camera(self):
        return {'pid':200,'detected_frames':int(self.clock*10)+100,'capture_frames':int(self.clock*12.5)+100,
            'face_targets':{'processed':int(self.clock*3)+100,'source_age_ms':100,'slot_retry':{'recovery_interval_ms':50},
                'freshness_metrics':{'observer_failures':0,'counters':{'observed_gap_intervals':0}}},
            'dpu_schedule':{'primary_period_overruns':1,'optional':{'yunet':{'overruns':0,'disabled':False,'maximum_ms':10}}}}
    def prepare(self,wrapper,unit,candidate):
        outer=self;folder=self.root/'handoff';folder.mkdir();(folder/'camera.original').write_bytes(b'original unit')
        class Ops:
            def __init__(self):
                self.folder=folder;self.meta={'boot':BOOT,'guard_armed':False};self.target='original';self.guard=False
            def save_meta(self):(self.folder/'session.json').write_text(json.dumps(self.meta))
            def assert_guard_armed(self):assert self.guard and self.meta['guard_armed']
            def verify(self):pass
            def pid(self,name):return 300 if name=='aura-avatar-ui.service' else 100
            def ready(self,target):return self.target==target
            def service(self,*args):
                outer.commands.append(('service',args))
                if args[0]=='stop':self.guard=False;return ''
                return 'active' if self.guard else 'inactive'
            def disarm(self):assert self.target=='original';self.guard=False;self.meta['guard_armed']=False
        ops=Ops();self.ops=ops
        def transition(owned,target):
            owned.assert_guard_armed();owned.target=target
            owned.meta['quiescent_cursor']='fixture-pcm-closed-cursor'
            record=candidate.parent/'process-settings'/BOOT/'launch-test';record.mkdir(parents=True)
            (record/'process-setting-200.json').write_text(json.dumps({'actual_start_seconds':.001,'previous_seconds':.005}))
            if self.mutate:(candidate/'synthetic.py').write_text('foreign=True\n')
        return ops,SimpleNamespace(transition=transition)
    def command(self,args,timeout=None):
        self.commands.append(('command',args))
        if args[0]=='systemd-run':self.ops.guard=True;return ''
        self.ops.target='original';return json.dumps({'restored':True})
    def run_candidate(self):
        entry=("WRAPPER_SHA="+repr(self.parent.RETRY_WRAPPER_SHA)+'\n').encode()
        result=release.run_release(self.folder,self.root/'wrapper.py',entry)
        return result,json.loads((self.folder/'report.json').read_text())
    def test_qualified_healthy_candidate_is_committed_only_after_full_window(self):
        result,report=self.run_candidate()
        self.assertTrue(result['accepted']);self.assertTrue(result['passed']);self.assertEqual(self.clock,120)
        self.assertEqual(self.ops.target,'candidate');self.assertFalse(self.ops.guard)
        self.assertTrue(Path(report['release'],'activation-qualified.json').exists())
    def test_usb_failure_restores_original_instead_of_accepting(self):
        self.usb=True;result,report=self.run_candidate()
        self.assertFalse(result['accepted']);self.assertFalse(result['passed'])
        self.assertEqual(self.ops.target,'original');self.assertFalse(self.ops.guard)
        self.assertTrue(report['restoration']['restored'])
    def test_source_changed_after_start_is_rejected_and_restored(self):
        self.mutate=True;result,report=self.run_candidate()
        self.assertFalse(result['accepted']);self.assertEqual(self.ops.target,'original')
        self.assertTrue(report['restoration']['restored'])
    def test_unqualified_trial_never_arms_or_switches_services(self):
        self.d['passed']=False;self.qfile.write_text(json.dumps(self.d))
        result,report=self.run_candidate()
        self.assertFalse(result['accepted']);self.assertIsNone(self.ops);self.assertEqual(self.commands,[])


if __name__=='__main__':unittest.main()
