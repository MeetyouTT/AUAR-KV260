"""Commit and rollback with real temporary files and simulated devices/time."""
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import control
from test_live_checks import fixture


class ControllerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.root = Path(self.temp.name)
        self.live = self.root/'live'; self.previous = self.live/'previous'; self.previous.mkdir(parents=True)
        self.source = self.previous/'aura'; self.source.mkdir()
        (self.source/'original.py').write_text('original=True\n')
        local = Path(__file__).resolve().parent
        wrapper = Path('/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-23_coordinated_camera_audio/active_source/gil_camera_launcher.py')
        shutil.copyfile(wrapper, self.previous/'gil_camera_launcher.py')
        shutil.copyfile(local/'runtime_entry.py', self.previous/'runtime_entry.py')
        self.base = self.root/'base'; self.base.mkdir()
        self.private=self.root/'private';self.private.mkdir()
        self.old_db=self.private/'old.sqlite3';self.old_db.write_bytes(b'protected original store')
        self.identity=self.base/'identity.json';self.identity.write_text(json.dumps({'feature_backend':{'kind':'windows_sface'},
            'threshold':.5,'ambiguity_margin':.1,'database':str(self.old_db),'model_id':'old-model'}))
        (self.base/'board_camera_ui.json').write_text(json.dumps({'identity': {'config': str(self.identity)},'yunet_dpu_recovery':True,'yunet_slot_wait_ms':100}))
        self.model=self.root/'model';self.model.write_bytes(b'model')
        self.model_manifest=self.root/'manifest';self.model_manifest.write_bytes(b'manifest')
        self.unit = self.root/'camera.unit'
        self.unit.write_text('[Service]\nEnvironment="AURA_EXPERIMENT_GIL_MS=1"\nWorkingDirectory='+str(self.previous/'aura')+'\n'
            'ExecStart=/usr/bin/python3 '+str(self.previous/'runtime_entry.py')+' '+str(self.previous/'aura/tools/board_camera_motion.py')+
            ' --config /home/root/aura-dpu-vision-20261021/runtime/81fdb11903abb71e-live-134783/board_camera_ui.json\n')
        self.original_unit = self.unit.read_bytes(); self.parent_sha = control.sha(self.unit)
        report = {'complete': True, 'accepted': True, 'passed': True, 'release': str(self.previous),
            'unit_sha256': self.parent_sha, 'source_manifest': control.tree_manifest(self.source),
            'runtime_entry_sha256': control.sha(self.previous/'runtime_entry.py')}
        self.parent_report = self.root/'parent.json'; self.parent_report.write_text(json.dumps(report))
        self.folder = self.root/'controller'; self.folder.mkdir()
        for name in ('control.py', 'handoff.py', 'live_checks.py', 'migration.py','migrate_entry.py'):
            shutil.copyfile(local/name, self.folder/name)
        shutil.copytree(local/'candidate', self.folder/'candidate')
        self.pins = {str(path.relative_to(self.folder/'candidate/aura')): control.sha(path)
                     for path in (self.folder/'candidate/aura').rglob('*.py')}
        self.session_root = self.root/'sessions'; self.session_root.mkdir()
        self.wrapper = self.root/'entry.py'; self.wrapper.write_text('pass\n')
        self.clock = 1000.; self.ops = None; self.commands = []; self.usb = False; self.bad_injected = False
        self.patches = [patch.object(control, 'PARENT_RELEASE', str(self.previous)),
            patch.object(control.handoff, 'BOOT', Path('/proc/sys/kernel/random/boot_id').read_text().strip()),
            patch.object(control, 'PARENT_UNIT_SHA', self.parent_sha),
            patch.object(control, 'PARENT_REPORT', self.parent_report), patch.object(control, 'LIVE_ROOT', self.live),
            patch.object(control, 'SESSION_ROOT', self.session_root), patch.object(control, 'UNIT', self.unit),
            patch.object(control,'PRIVATE_ROOT',self.private),patch.object(control,'SFACE_MODEL',self.model),
            patch.object(control,'SFACE_MANIFEST',self.model_manifest),
            patch.object(control, 'time', SimpleNamespace(monotonic=lambda:self.clock, sleep=self.sleep)),
            patch.object(control.handoff, 'BoardOps', self.make_ops),
            patch.object(control.handoff, 'transition', self.transition)]
        for value in self.patches: value.start()

    def tearDown(self):
        for value in reversed(self.patches): value.stop()
        self.temp.cleanup()

    def sleep(self, seconds): self.clock += seconds

    def camera(self):
        target = self.ops.target if self.ops is not None else 'original'
        state = fixture(fault=target=='injected' or (self.bad_injected and target=='candidate'))
        if self.bad_injected and target == 'candidate':
            state['dpu_schedule']['optional_diagnostics']['fault_events'][0]['guard_exceeded'] = 1
        state.update(pid=202 if target=='candidate' else 201, detected_frames=int(self.clock*10),
                     capture_frames=int(self.clock*12.5),identity_ready=True,identity_error='',
                     feature_inference={'kind':'DPU_SFACE_INT8','completed':int(self.clock)},
                     match_diagnostics={'counts':{'KNOWN':int(self.clock),'UNKNOWN':0,'AMBIGUOUS':0},'last_state':'KNOWN','last_score':.8},
                     identity_backend='DPU_SFACE_INT8' if target=='candidate' else 'WINDOWS_CPU_SFACE_ORT')
        state['dpu_schedule']['primary_period_overruns'] = 1
        state['dpu_schedule']['yunet_slot_wait'] = {'enabled':True,'maximum_wait_ms':100,
            'calls':int(self.clock*2),'ready':int(self.clock*2),'timeouts':0,'disabled':0,
            'condition_waits':int(self.clock*2),'total_wall_ms':self.clock*10,'maximum_wall_ms':5.}
        state['dpu_schedule']['sface_slot_wait']={'maximum_wait_ms':100}
        state['dpu_schedule']['optional_diagnostics']['counters'] = {
            'yunet': {'native_completed': int(self.clock*3), 'native_failed': 0}}
        state['face_targets'].update(processed=int(self.clock*3), slot_retry={
            'recovery_interval_ms':50, 'withdrawn_after_slot':0,'independent_admission':True,'busy':0}, freshness_metrics={
            'observer_failures':0, 'gap_records_dropped':0, 'counters':{key:0 for key in (
                'observed_gap_intervals','post_commit_at_or_over_ttl','process_errors','callback_errors',
                'input_ttl_discarded','publish_ttl_discarded')}})
        return state

    def make_ops(self, session):
        outer = self
        class Ops:
            def __init__(self):
                self.folder = session; self.target = 'original'; self.guard = False
                self.m = SimpleNamespace(BASE=outer.base, camera=outer.camera, single_owner=lambda pid:None,
                    cpu=lambda:{'mono':outer.clock}, cpu_delta=lambda a,b:{'duration_s':b['mono']-a['mono'], 'cpu_percent_of_board':55},
                    audio_warnings=lambda cursor:int(outer.usb), command=outer.command,
                    get=lambda port,route:{'modules':{'identity':{'state':'KNOWN','person_id':'private-id','face_count':1}}})
            def capture(self, wrapper):
                (self.folder/'camera.original').write_bytes(outer.original_unit)
                self.meta = {'config':str(outer.base/'board_camera_ui.json'),
                    'configs':{'original':str(outer.base/'board_camera_ui.json')},
                    'unit_hashes':{'original':outer.parent_sha},'runtimes':{'original':str(outer.source)},
                    'protected':{},'guard_armed':False}
                self.save_meta(); return outer.camera()
            def save_meta(self): (self.folder/'session.json').write_text(json.dumps(self.meta))
            def verify(self):
                assert control.sha(outer.unit) in self.meta['unit_hashes'].values()
                for path,digest in self.meta['protected'].items(): assert control.sha(path)==digest
            def assert_guard_armed(self): assert self.guard and self.meta['guard_armed']
            def pid(self,name):
                if name==control.handoff.CAMERA:return 202 if self.target=='candidate' else 201
                return 300 if name==control.handoff.AUDIO else 100
            def ready(self,target): return self.target==target
            def service(self,*args):
                outer.commands.append(('service',args))
                if args[0]=='stop' and str(args[1]).endswith('.timer'):self.guard=False;return ''
                return 'active' if self.guard else 'inactive'
            def disarm(self):
                assert self.target=='original';self.guard=False;self.meta['guard_armed']=False;self.save_meta()
            def assert_idle_or_stopped(self):pass
            def stop_audio(self):pass
            def wait_pcm_closed(self):pass
        self.ops = Ops(); return self.ops

    def command(self,args,timeout=None):
        self.commands.append(('command',args))
        if args[0]=='systemd-run':self.ops.guard=True;return ''
        if len(args)>3 and args[2].endswith('migrate_entry.py'):
            config=json.loads(Path(args[5]).read_text());db=Path(config['database']);db.parent.mkdir(exist_ok=True)
            con=sqlite3.connect(db);con.execute('CREATE TABLE identities(id TEXT,name TEXT)')
            con.execute('INSERT INTO identities VALUES (?,?)',('private-id','private-name'));con.commit();con.close()
            return json.dumps({'passed':True,'identities_migrated':1})
        self.ops.target='original';self.unit.write_bytes(self.original_unit)
        return json.dumps({'restored':True})

    def transition(self,ops,target):
        ops.verify();ops.assert_guard_armed();ops.target=target
        self.unit.write_bytes((ops.folder/('camera.'+target)).read_bytes())
        ops.meta['quiescent_cursor']='owned-pcm-closed';ops.save_meta()
        if target=='candidate':
            (self.folder/'operator-frontal-ready.json').write_text(json.dumps({'boot':control.handoff.BOOT,
                'helper_sha256':control.sha(self.wrapper),'user_frontal_ready':True}))
        if target=='injected':
            release=Path(ops.meta['runtimes'][target]).parent
            (release/'injected-once.json').write_text(json.dumps({'one_time':True,'native_completed_before_delay':True,
                'requested_delay_ms':31,'started_monotonic_s':self.clock,'ended_monotonic_s':self.clock+.031}))

    def run_release(self):
        result=control.run(self.folder,self.wrapper,self.pins)
        return result,json.loads((self.folder/'report.json').read_text())

    def test_short_window_and_active_notifications_precede_retained_release(self):
        result,report=self.run_release()
        self.assertTrue(result['accepted'],report)
        self.assertEqual(self.clock,1061.)
        self.assertEqual(len(report['stages']),1)
        self.assertEqual([stage['native_completed_delta'] for stage in report['stages']],[180])
        self.assertGreater(report['stages'][0]['slot_wait_delta']['condition_waits'],0)
        self.assertEqual(report['stages'][0]['sface_native_completed_delta'],60)
        self.assertEqual(report['stages'][0]['known_correct_samples'],13)
        self.assertEqual(self.old_db.read_bytes(),b'protected original store')
        self.assertEqual(self.ops.target,'candidate');self.assertFalse(self.ops.guard)
        self.assertNotIn(b'injection_entry',self.unit.read_bytes())
        self.assertEqual(self.unit.read_bytes(),(self.ops.folder/'camera.candidate').read_bytes())
        self.assertTrue(Path(result['release'],'restore_previous.py').exists())
        self.assertFalse(Path(result['release'],'injection_entry.py').exists())
        self.assertTrue(json.loads(Path(result['release'],'activation-short.json').read_text())['complete'])

    def test_usb_error_restores_previous_unit_and_stops_guard(self):
        self.usb=True;result,report=self.run_release()
        self.assertFalse(result['accepted']);self.assertTrue(report['restoration']['restored'])
        self.assertEqual(self.unit.read_bytes(),self.original_unit);self.assertFalse(self.ops.guard)

    def test_unexpected_real_guard_violation_is_rejected(self):
        self.bad_injected=True;result,report=self.run_release()
        self.assertFalse(result['accepted']);self.assertTrue(report['restoration']['restored'])
        self.assertEqual(self.ops.target,'original')

    def test_changed_candidate_is_rejected_before_services_or_guard(self):
        first=next(iter(self.pins));(self.folder/'candidate/aura'/first).write_text('foreign=True\n')
        result,report=self.run_release()
        self.assertFalse(result['accepted']);self.assertIsNone(self.ops);self.assertEqual(self.commands,[])
        self.assertEqual(self.unit.read_bytes(),self.original_unit)


if __name__=='__main__':unittest.main()
