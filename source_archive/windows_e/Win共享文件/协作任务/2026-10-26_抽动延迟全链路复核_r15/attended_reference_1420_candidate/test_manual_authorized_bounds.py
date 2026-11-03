import hashlib,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).parent))
import manual_release as m

class BoundsTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.auth=self.root/'authorization.json';self.prior=self.root/'old.json'
        self.auth.write_text(json.dumps(dict(schema='aura-user-bounded-manual-1',boot_id='boot',bounds_us=[1425,1505],
            implementation_choice='align_manual_with_authorized_face_follow_range',physical_calibration_claimed=False,user_instruction_quote='autonomous completion')))
        self.prior.write_text(json.dumps({'payload_files':{'driver':'sha'},'runtime_files':{'firmware':'sha'},'manual_minimum_us':1425,'manual_maximum_us':1445}))
        sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
        self.cfg=dict(boot_id='boot',manual_minimum_us=1425,manual_maximum_us=1505,maximum_step_us=20,maximum_duration_s=2)
        self.release=dict(self.cfg,status='USER_BOUNDED_MANUAL_VSRV2',scope='finite_manual_user_authorized_bounds',
            external_waveform_verified=False,physical_range_verified=False,mechanical_reference_calibrated=False,automatic_following_enabled=False,
            authorization_sha256=sha(self.auth),observed_predecessor={'path':str(self.prior),'sha256':sha(self.prior)},
            payload_files={'driver':'sha'},runtime_files={'firmware':'sha'})
    def tearDown(self):self.temp.cleanup()
    def test_explicit_scope_preserves_original_proof_in_its_original_bounds(self):
        with patch.object(m,'observed_bounds',return_value=(1425,1445)) as old:
            self.assertEqual(m.authorized_bounds(self.release,self.cfg,self.root),(1425,1505))
            self.assertEqual(old.call_args.args[1]['manual_maximum_us'],1445)
            self.assertEqual(self.cfg['manual_maximum_us'],1505)
    def test_bounds_step_duration_boot_and_measurement_claims_cannot_be_expanded(self):
        for change in ({'manual_maximum_us':1506},{'maximum_step_us':30},{'maximum_duration_s':3},{'boot_id':'other'}):
            with self.assertRaises(RuntimeError):m.authorized_bounds(self.release,dict(self.cfg,**change),self.root)
        for change in ({'physical_range_verified':True},{'external_waveform_verified':True},{'automatic_following_enabled':True}):
            with self.assertRaises(RuntimeError):m.authorized_bounds(dict(self.release,**change),self.cfg,self.root)
    def test_changed_authorization_or_predecessor_is_rejected_before_proof(self):
        for p in (self.auth,self.prior):
            original=p.read_bytes();p.write_bytes(b'changed')
            with patch.object(m,'observed_bounds') as old:
                with self.assertRaises(RuntimeError):m.authorized_bounds(self.release,self.cfg,self.root)
                old.assert_not_called()
            p.write_bytes(original)
    def test_payload_cannot_drift_from_observed_hardware(self):
        with self.assertRaises(RuntimeError):m.authorized_bounds(dict(self.release,payload_files={}),self.cfg,self.root)
    def attended(self):
        a=json.loads(self.auth.read_text());a.update(bounds_us=[1402,1420],implementation_choice='attended_reference_window',user_instruction_quote='是的')
        self.auth.write_text(json.dumps(a));self.cfg.update(manual_minimum_us=1402,manual_maximum_us=1420)
        p=json.loads(self.prior.read_text());p.update(manual_minimum_us=1445,manual_maximum_us=1465);self.prior.write_text(json.dumps(p))
        self.release.update(self.cfg,authorization_sha256=hashlib.sha256(self.auth.read_bytes()).hexdigest())
        self.release['observed_predecessor']['sha256']=hashlib.sha256(self.prior.read_bytes()).hexdigest()
    def test_attended_scope_validates_predecessor_in_actual_1445_1465_bounds(self):
        self.attended()
        with patch.object(m,'observed_bounds',return_value=(1445,1465)) as old:
            self.assertEqual(m.authorized_bounds(self.release,self.cfg,self.root),(1402,1420))
            self.assertEqual([old.call_args.args[1][k] for k in ('manual_minimum_us','manual_maximum_us')],[1445,1465])
    def test_attended_scope_cannot_use_the_old_broad_authorization_label(self):
        self.attended();a=json.loads(self.auth.read_text());a['implementation_choice']='align_manual_with_authorized_face_follow_range'
        self.auth.write_text(json.dumps(a));self.release['authorization_sha256']=hashlib.sha256(self.auth.read_bytes()).hexdigest()
        with self.assertRaises(RuntimeError):m.authorized_bounds(self.release,self.cfg,self.root)
    def test_attended_scope_refuses_target_above_1420_even_with_matching_config(self):
        self.attended();self.cfg['manual_maximum_us']=self.release['manual_maximum_us']=1421
        with self.assertRaises(RuntimeError):m.authorized_bounds(self.release,self.cfg,self.root)

if __name__=='__main__':unittest.main()
