import importlib.util
import json
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('bounded_kernel_window',Path(__file__).resolve().parents[1]/'tools/bounded_kernel_window.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class KernelWindowTests(unittest.TestCase):
    def setUp(self):
        self.boot='1'*32
        self.mapping={'boot_id':self.boot,'verified_current_boot_device':True,
            'mapping_basis':'READ_CURRENT_USB_AND_XHCI_CONTEXTS','observed_mono_us':9990000,
            'slot_id':7,'device_address':4,'endpoint_index':3,'endpoint_address':2,
            'usb_vid':'1234','usb_pid':'abcd','direction':'out','transfer_type':'isochronous'}
    def line(self,stamp,slot=7,ep=3,boot=None):
        return json.dumps({'_BOOT_ID':boot or self.boot,'__MONOTONIC_TIMESTAMP':str(stamp),
            'MESSAGE':"xhci: WARN: HC couldn't access mem fast enough for slot "+str(slot)+' ep '+str(ep)})
    def parse(self,lines,mapping=None,**kwargs):
        return module.parse_window(lines,boot_id=self.boot,since_us=5000000,until_us=10000000,
                                   mapping=self.mapping if mapping is None else mapping,**kwargs)
    def test_monotonic_fields_filter_stale_warning_and_wrong_boot(self):
        result=self.parse([self.line(1000),self.line(6000000),self.line(7000000,boot='2'*32),self.line(10000001)])
        self.assertEqual(result['matching_warning_entries'],1)
        self.assertEqual(result['old_or_future_entries'],2)
        self.assertEqual(result['other_boot_entries'],1)
        self.assertEqual(result['first_matching_mono_us'],6000000)
        self.assertNotIn('MESSAGE',str(result))
    def test_slot_is_revalidated_and_never_assumed_equal_to_usb_address(self):
        result=self.parse([self.line(6000000,slot=4),self.line(6000001,slot=7),self.line(6000002,ep=5)])
        self.assertEqual(result['matching_warning_entries'],1)
        self.assertEqual(result['other_device_warning_entries'],2)
    def test_stale_or_wrong_boot_mapping_never_claims_zero_device_faults(self):
        for patch in ({'observed_mono_us':1000},{'boot_id':'2'*32},{'verified_current_boot_device':False},
                      {'mapping_basis':'USB_ADDRESS_GUESSED_AS_SLOT'},{'endpoint_address':1}):
            result=self.parse([self.line(6000000)],mapping=dict(self.mapping,**patch))
            self.assertEqual(result['status'],'MAPPING_UNVERIFIED')
            self.assertIsNone(result['matching_warning_entries'])
    def test_tail_saturation_is_count_lower_bound_not_precise_warning_rate(self):
        result=self.parse((self.line(6000000+i) for i in range(1000)),max_entries=16)
        self.assertEqual(result['entries_parsed'],16)
        self.assertEqual(result['matching_warning_entries'],16)
        self.assertEqual(result['status'],'INCOMPLETE_SATURATED_TAIL')
        self.assertFalse(result['observation_complete'])
        self.assertTrue(result['reported_count_is_lower_bound'])
    def test_zero_fresh_warnings_does_not_certify_audio_delivery(self):
        result=self.parse([self.line(1000)])
        self.assertEqual(result['matching_warning_entries'],0)
        self.assertEqual(result['usb_playback_health'],'UNVERIFIED')
        self.assertFalse(result['observation_complete'])
    def test_malformed_bounded_input_and_invalid_window(self):
        result=self.parse(['{bad}',self.line(6000000)])
        self.assertEqual(result['status'],'INCOMPLETE_MALFORMED_TAIL')
        self.assertEqual(result['matching_warning_entries'],1)
        with self.assertRaises(ValueError):
            module.parse_window([],boot_id=self.boot,since_us=0,until_us=100000000,mapping=self.mapping)


if __name__=='__main__':unittest.main(verbosity=2)
