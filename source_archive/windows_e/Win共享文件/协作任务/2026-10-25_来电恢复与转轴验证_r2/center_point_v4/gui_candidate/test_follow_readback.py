import hashlib,json,tempfile,unittest
from pathlib import Path
import follow_readback as module


class ReadbackTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.consumer=self.root/'release';(self.consumer/'runs').mkdir(parents=True)
        self.source=self.consumer/'a.py';self.source.write_text('pinned source')
        self.manifest=self.consumer/'deployment-manifest.json'
        self.manifest.write_text(json.dumps({'files':[{'destination':str(self.source),'sha256':self.sha(self.source)}]}))
        self.settings=self.root/'new-boot/zone.json';self.settings.parent.mkdir()
        self.settings.write_text(json.dumps({'board_boot_id':'new-boot'}))
        self.face=self.root/'face.json';self.face.write_text(json.dumps({'release_root':str(self.consumer),
            'manifest_sha256':self.sha(self.manifest),'arguments':{'zone-settings':str(self.settings)}}))
        self.config=dict(boot_id='new-boot',face_follow_config=str(self.face),manual_minimum_us=1445,manual_maximum_us=1465)
        self.state=dict(flags=0,lease_left_ms=0,width_us=1442,target_us=1442,ack_seq=8,epoch=7,session=91,reference_us=1445)
        self.report=dict(status='CONTINUOUS_FACE_ZONE_STOPPED',boot_id='new-boot',target_kind='face',range_us=[1400,1600],
            consumer_manifest_sha256=self.sha(self.manifest),result={'stopped':self.state.copy()})
        self.path=self.consumer/'runs/trial.json';self.save()
    def tearDown(self):self.temp.cleanup()
    def sha(self,p):return hashlib.sha256(p.read_bytes()).hexdigest()
    def save(self):
        self.path.write_text(json.dumps(self.report))
        (self.settings.parent/'face-stopped-readback.json').write_text(json.dumps({'report':str(self.path),'sha256':self.sha(self.path)}))
    def test_new_boot_exact_stopped_receipt_only_recovers_readback(self):
        self.assertTrue(module.verified_stopped_face_command(self.config,self.state))
        self.assertEqual([self.config['manual_minimum_us'],self.config['manual_maximum_us']],[1445,1465])
    def test_active_or_any_context_or_command_change_is_rejected(self):
        for key,value in [('flags',15),('lease_left_ms',1),('width_us',1443),('target_us',1443),('ack_seq',9),('epoch',8),('session',92),('reference_us',1446)]:
            with self.subTest(key=key):self.assertFalse(module.verified_stopped_face_command(self.config,dict(self.state,**{key:value})))
    def test_stale_boot_and_bad_range_or_nonface_report_are_rejected(self):
        for key,value in [('boot_id','old-boot'),('range_us',[500,2500]),('target_kind','body'),('status','RUNNING')]:
            original=self.report[key];self.report[key]=value;self.save()
            self.assertFalse(module.verified_stopped_face_command(self.config,self.state))
            self.report[key]=original
    def test_modified_source_manifest_or_receipt_is_rejected(self):
        for p in [self.source,self.manifest,self.path]:
            original=p.read_bytes();p.write_text('changed')
            self.assertFalse(module.verified_stopped_face_command(self.config,self.state));p.write_bytes(original)
    def test_report_outside_pinned_release_runs_is_rejected(self):
        self.path=self.root/'outside.json';self.save()
        self.assertFalse(module.verified_stopped_face_command(self.config,self.state))
    def test_settings_must_belong_to_the_same_boot(self):
        self.settings.write_text(json.dumps({'board_boot_id':'old-boot'}))
        self.assertFalse(module.verified_stopped_face_command(self.config,self.state))


if __name__=='__main__':unittest.main()
