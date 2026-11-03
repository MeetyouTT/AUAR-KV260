"""Diagnostics must acknowledge without waiting for capture or growing a queue."""
from collections import deque
import json
from pathlib import Path
import sys
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0,'/home/ghmd/Win共享文件/共享文件夹/aura')
from tools.board_avatar_gtk import BoardAvatarStage

class DiagnosticTests(unittest.TestCase):
    def stage(self, directory):
        s=BoardAvatarStage.__new__(BoardAvatarStage)
        s.evidence_root=Path(directory)
        s.diagnostic_thread=s.diagnostic_job=s.diagnostic_result=None
        s.samples=deque();s.controls={}
        s.Gtk=SimpleNamespace(Window=SimpleNamespace(list_toplevels=lambda:[]))
        s.window=SimpleNamespace(get_allocated_width=lambda:1024,get_allocated_height=lambda:600)
        s.controller=SimpleNamespace(read=lambda:{'jpeg':b'cached-jpeg'},public=lambda:{'phase':'IDLE'})
        s.mixer=SimpleNamespace(read=lambda:{'volume':18})
        for key in ('config','preferences','runtime_view','device_inventory','source_hashes'):setattr(s,key,{})
        for key in ('errors','touch_inputs','input_events'):setattr(s,key,[])
        s.font_hash='test';s.page='main'
        return s

    def test_slow_capture_does_not_block_or_duplicate_job(self):
        started=threading.Event();release=threading.Event()
        def capture(argv,**kwargs):
            started.set();release.wait(2);Path(argv[-1]).write_bytes(b'screen')
            return SimpleNamespace(returncode=0,stderr=b'')
        with tempfile.TemporaryDirectory() as directory:
            s=self.stage(directory)
            with patch('tools.board_avatar_gtk.subprocess.run',side_effect=capture) as child:
                begin=time.monotonic();first=s.save_evidence();elapsed=time.monotonic()-begin
                self.assertLess(elapsed,.25);self.assertTrue(first['queued']);self.assertTrue(started.wait(1))
                second=s.save_evidence();self.assertEqual(first['diagnostic_id'],second['diagnostic_id'])
                self.assertFalse(Path(first['report']).exists());self.assertEqual(child.call_count,1)
                release.set();s.diagnostic_thread.join(2)
            report=json.loads(Path(first['report']).read_text())
            self.assertEqual(s.diagnostic_job['state'],'COMPLETE')
            self.assertEqual(Path(report['screenshot_path']).read_bytes(),b'screen')
            self.assertEqual((s.evidence_root/('frame_'+first['diagnostic_id']+'.jpg')).read_bytes(),b'cached-jpeg')

    def test_capture_failure_is_reported_without_publishing_success(self):
        with tempfile.TemporaryDirectory() as directory:
            s=self.stage(directory)
            with patch('tools.board_avatar_gtk.subprocess.run',return_value=SimpleNamespace(returncode=1,stderr=b'failed')):
                first=s.save_evidence();s.diagnostic_thread.join(2)
            self.assertEqual(s.diagnostic_job['state'],'FAILED')
            self.assertFalse(s.diagnostic_result['ok'])
            self.assertFalse(Path(first['report']).exists())
            self.assertFalse((s.evidence_root/'latest_verification.json').exists())

if __name__=='__main__':unittest.main(verbosity=2)
