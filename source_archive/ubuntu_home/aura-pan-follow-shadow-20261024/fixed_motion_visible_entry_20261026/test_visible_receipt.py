import unittest
from reference_receipt import validate_receipt


class VisibleReceiptTests(unittest.TestCase):
    def value(self):
        return dict(schema='aura-user-observed-fixed-reference-1',boot_id='fixture',fdt_sha256='fixture-fdt',
                    user_present=True,confirmed_current_position=True,user_observation='fixture earlier reference',
                    reference_us=1420,bounds_us=[1402,1420],polarity=1,camera_moves_with_axis=True,
                    authorization_id='fixture-visible',observed_mono_s=10.,authorization_recorded_mono_s=1000.,
                    expires_mono_s=1600.,stopped_readback=dict(flags=0,lease_left_ms=0,width_us=1420,target_us=1420,
                                                           reference_us=1420,session=1,epoch=4,ack_seq=98,reason=0))

    def test_fresh_attended_authorization_preserves_earlier_observation_time(self):
        result=validate_receipt(self.value(),boot_id='fixture',fdt_sha256='fixture-fdt',now=1001.)
        self.assertEqual(result['observed_mono_s'],10.)

    def test_remaining_window_must_cover_five_seconds(self):
        v=self.value();v['expires_mono_s']=1005.
        with self.assertRaises(ValueError):validate_receipt(v,boot_id='fixture',fdt_sha256='fixture-fdt',now=1001.)

    def test_future_authorization_or_old_boot_refused(self):
        for k,x in [('authorization_recorded_mono_s',1002.),('boot_id','old')]:
            v=self.value();v[k]=x
            with self.subTest(k=k),self.assertRaises(ValueError):validate_receipt(v,boot_id='fixture',fdt_sha256='fixture-fdt',now=1001.)

    def test_no_presence_or_default_width_refused(self):
        for mode in ('absent','default'):
            v=self.value()
            if mode=='absent':v['user_present']=False
            else:v['stopped_readback']['width_us']=1500
            with self.subTest(mode=mode),self.assertRaises(ValueError):validate_receipt(v,boot_id='fixture',fdt_sha256='fixture-fdt',now=1001.)


if __name__=='__main__':unittest.main()
