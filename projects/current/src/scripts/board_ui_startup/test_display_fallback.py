"""Test only explicit, previously measured timing when live EDID is absent."""
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import launcher

TIMING=['49.000','1024','1072','1168','1312','600','603','613','624','-HSync','-VSync']
MODE='''  1024x600 (0x59) 49.000MHz -HSync -VSync
        h: width  1024 start 1072 end 1168 total 1312 skew 0
        v: height  600 start  603 end  613 total  624
'''


class DisplayFallbackTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory();self.addCleanup(self.directory.cleanup)
        self.edid=Path(self.directory.name)/'edid';self.edid.write_bytes(b'')
        self.status=self.edid.with_name('status');self.status.write_text('connected\n')
        self.names=['WaveShare WS170120'];self.modes='DP-1 connected primary 1024x768+0+0\n'
        self.calls=[]
        self.config={'display_wait_seconds':.002,'edid_file':str(self.edid),
            'edid_sha256':hashlib.sha256(b'original-edid').hexdigest(),'touch_name':'WaveShare WS170120',
            'mode':'1024x600','output':'DP-1','rate':'59.85','verified_timing_fallback':TIMING}
        self.patch=patch.object(launcher,'run',self.run_command);self.patch.start();self.addCleanup(self.patch.stop)
        self.wait=patch.object(launcher.STOP,'wait',lambda _:None);self.wait.start();self.addCleanup(self.wait.stop)

    def run_command(self,args,env):
        self.calls.append(args)
        if args==['xinput','list','--name-only']:return '\n'.join(self.names)
        if args==['xrandr','--verbose']:return self.modes
        if args[1:2]==['--newmode']:self.modes+=MODE
        if args==['xrandr','--current']:return 'DP-1 connected primary 1024x600+0+0\n'
        return ''

    def test_missing_edid_uses_exact_reviewed_timing_and_reports_origin(self):
        result=launcher.configure_display(self.config,{})
        self.assertEqual(result['mode_source'],'previously_verified_timing')
        self.assertIsNone(result['edid_sha256'])
        self.assertIn(['xrandr','--newmode','1024x600']+TIMING,self.calls)

    def test_different_live_edid_is_not_overridden(self):
        self.edid.write_bytes(b'other-screen')
        with self.assertRaises(RuntimeError):launcher.configure_display(self.config,{})
        self.assertFalse(any('--newmode' in c for c in self.calls))

    def test_disconnected_output_or_missing_touch_cannot_use_fallback(self):
        for status,names in [('disconnected',['WaveShare WS170120']),('connected',[])]:
            self.status.write_text(status);self.names=names;self.calls=[]
            with self.subTest(status=status,names=names),self.assertRaises(RuntimeError):
                launcher.configure_display(self.config,{})
            self.assertFalse(any('--newmode' in c for c in self.calls))

    def test_conflicting_existing_mode_cannot_be_reused(self):
        self.modes+=MODE.replace('49.000','65.000')
        with self.assertRaises(RuntimeError):launcher.configure_display(self.config,{})
        self.assertFalse(any('--output' in c for c in self.calls))

    def test_live_matching_edid_stays_on_original_path(self):
        self.edid.write_bytes(b'original-edid');self.modes+=MODE
        result=launcher.configure_display(self.config,{})
        self.assertEqual(result['mode_source'],'live_edid')
        self.assertEqual(result['edid_sha256'],self.config['edid_sha256'])
        self.assertFalse(any('--newmode' in c for c in self.calls))


if __name__=='__main__':unittest.main(verbosity=2)
