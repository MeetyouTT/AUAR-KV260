"""Pinned rate propagation and truthful timing with real candidate functions."""
import ast
from collections import deque
import json
import os
from pathlib import Path
import queue
from types import SimpleNamespace as S
import unittest
from unittest.mock import patch

from tools.native_yuki import native_callback_metrics
from tools.formal_native_yuki import StrictLocalPortrait,display_status
from tools.formal_yuki import CandidatePair,PAIR_CONFIG_SHA256,PairRejected
from tools.board_avatar_worker import portrait_control_fps

HERE=Path(__file__).resolve().parents[1]
FPS=int(os.environ['AURA_NATIVE_RATE_TEST_FPS'])
GUI=HERE/('paired_'+str(FPS))/'aura/tools/board_avatar_gtk.py'


def gui_function(name):
    tree=ast.parse(GUI.read_text(encoding='utf-8'))
    function=next((node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name==name),None)
    if function is None:
        function=next(node for owner in tree.body if isinstance(owner,ast.ClassDef)
                      for node in owner.body if isinstance(node,ast.FunctionDef) and node.name==name)
    return function


class NativeRateTests(unittest.TestCase):
    def test_exact_16_and_24_timestamps_are_reported_as_measured(self):
        for fps in (16,24):
            with self.subTest(fps=fps):
                result=native_callback_metrics([10.+i/fps for i in range(fps*4)])
                self.assertAlmostEqual(result['callback_fps'],fps,places=8)
                self.assertAlmostEqual(result['callback_interval_ms']['p95'],1000./fps,places=6)

    def test_a_configured_rate_does_not_hide_slow_callbacks(self):
        result=native_callback_metrics([10.,10.2,10.4,10.6])
        self.assertAlmostEqual(result['callback_fps'],5.)
        self.assertAlmostEqual(result['callback_interval_ms']['p95'],200.,places=8)

    def test_insufficient_and_invalid_timestamps_do_not_fabricate_fps(self):
        self.assertIsNone(native_callback_metrics([])['callback_fps'])
        self.assertIsNone(native_callback_metrics([10.])['callback_fps'])
        for value in ([10.,10.],[10.,9.],[10.,float('nan')]):
            with self.subTest(value=value),self.assertRaises(ValueError):native_callback_metrics(value)

    def test_startup_rate_reaches_worker_and_public_native_status(self):
        mailbox=StrictLocalPortrait(S(),fps=FPS)
        self.assertEqual(mailbox.target_fps,FPS)
        self.assertEqual(portrait_control_fps(mailbox),FPS)
        self.assertEqual(mailbox.status()['target_fps'],FPS)
        self.assertEqual(display_status(mailbox)['target_fps'],FPS)
        self.assertIsNone(display_status(mailbox)['fps'])

    def test_prepared_pair_cannot_hot_switch_or_fall_back_to_eight(self):
        mailbox=StrictLocalPortrait(S())
        mailbox.set_fps(FPS);mailbox.ready=True;mailbox._drawn=True
        with self.assertRaises(PairRejected):mailbox.set_fps(24 if FPS==16 else 16)
        with self.assertRaises(PairRejected):mailbox.set_fps(8)
        self.assertEqual(mailbox.target_fps,FPS)
        for value in (8,12,True,24.):
            with self.subTest(value=value),self.assertRaises(ValueError):
                portrait_control_fps(S(candidate_fixed_native=True,target_fps=value))

    def test_pair_constant_native_config_and_gui_changes_agree(self):
        receipt=json.loads((HERE/('paired_'+str(FPS))/'PAIRING_RECEIPT.json').read_text(encoding='utf-8'))
        meta=json.loads((HERE/('paired_'+str(FPS))/'aura/config/yuki_pair.formal.json').read_text(encoding='utf-8'))
        self.assertEqual(receipt['selection_sha256'],PAIR_CONFIG_SHA256)
        self.assertEqual(meta['native_config']['fps'],FPS)
        self.assertEqual(receipt['gui_config_changes']['stable_avatar_fps'],FPS)
        self.assertEqual(receipt['gui_config_changes']['native_yuki.fps'],FPS)
        pair=CandidatePair(Path('.'),meta,S(system_prompt='public test'))
        self.assertEqual(pair.status()['target_fps'],FPS)
        self.assertNotIn('tools/yuki_jobs_candidate.py',meta['runtime_pins'])

    def test_native_rate_label_uses_observed_fps(self):
        namespace={}
        exec(compile(ast.Module(body=[gui_function('avatar_rate_text')],type_ignores=[]),str(GUI),'exec'),namespace)
        value=namespace['avatar_rate_text'](dict(avatar_display=dict(kind='native_yuki_egl',fps=5.8,age_ms=10.,target_fps=24)))
        self.assertIn('5.8',value);self.assertNotIn('24',value)

    def test_business_public_stall_is_included_in_ui_timing(self):
        class Clock:
            value=10.
            def perf_counter(self):return self.value
            def monotonic(self):return self.value
            def advance(self,seconds):self.value+=seconds
        clock=Clock();published=[]
        state=dict(phase='IDLE',state='IDLE',asset='public-role',index=0,speech_gain=0.,mouth_level=0.,
            blink_active=False,playing=False,paused=False,audio_time=0.,visual_time=0.,error='',reply='')
        def read():
            clock.advance(.003)
            return dict(state=state,image=None,rgb=None,jpeg=b'',sequence=1)
        def health():clock.advance(.5);return dict(started=True)
        widget=S(set_text=lambda _:None)
        fake=S(closed=False,last_tick=None,diagnostic_result=None,
            bridge=S(commands=queue.Queue(),publish=lambda s,j:published.append(s)),
            controller=S(read=read),native_video=None,character_pair=None,
            last_avatar_sequence=0,displayed_frames=0,last_runtime_refresh=0.,
            refresh_settings=lambda s:'',demo_status=widget,reply=widget,
            refresh_runtime=lambda *_:None,samples=deque(),diagnostic_job=None,
            board_business=S(runtime=S(public=health)),character='public-role',errors=[])
        namespace=dict(time=clock,queue=queue)
        exec(compile(ast.Module(body=[gui_function('tick')],type_ignores=[]),str(GUI),'exec'),namespace)
        with patch('tools.production_business_ui.project_business_ui',lambda *_:None), \
             patch('tools.production_memory_presentation.project_presentation',lambda s,state:state):
            self.assertTrue(namespace['tick'](fake))
        self.assertEqual(len(published),1)
        self.assertGreaterEqual(published[0]['ui_tick_ms'],500.)
        self.assertAlmostEqual(published[0]['ui_stage_timings_ms']['business_public'],500.,places=3)
        self.assertGreaterEqual(fake.samples[-1]['render_ms'],500.)


if __name__=='__main__':unittest.main()
