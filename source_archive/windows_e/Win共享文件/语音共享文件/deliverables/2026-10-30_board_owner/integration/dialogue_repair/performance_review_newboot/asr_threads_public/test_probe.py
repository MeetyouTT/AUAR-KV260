import copy
import io
import json
from pathlib import Path
import sys
import time
import types
import unittest
from unittest.mock import patch

import compare_results as comparison
import probe_small_threads as probe


def fixture():
    slots=[]
    for threads in comparison.ORDER:
        rows=[dict(id=name,wav_sha256=str(index)*64,pcm_sha256='a'*64,samples=16000,
            rate=16000,audio_seconds=1.,decode_wall_ms=100. if threads==3 else 90.,
            decode_process_cpu_ms=200. if threads==3 else 140.,
            result_sha256='b'*64,normalized_sha256='c'*64)
            for index,name in enumerate(comparison.IDS)]
        slots.append(dict(status='PUBLIC_ASR_SLOT_MEASURED',threads=threads,
            warmups=copy.deepcopy(rows),measurements=rows,background_counter_changed=False,
            constructor_total=dict(wall_ms=3000.,process_cpu_ms=4000.),process_cpu_seconds=5.,
            slot_wall_seconds=4.,process_peak_rss_kib=200000,
            measurement_window_before=dict(observed_mono=1.,native_frames=10),
            measurement_window_after=dict(observed_mono=1.3,native_frames=14)))
    return dict(status='PUBLIC_ABBA_COMPLETE',order=list(comparison.ORDER),results=slots)


class ProbeTests(unittest.TestCase):
    def test_metadata_numbers_drop_strings_booleans_and_nonfinite_values(self):
        for value in ('PRIVATE_TEXT',True,None,float('nan'),float('inf'),-1):
            self.assertIsNone(probe.number(value))
        self.assertEqual(probe.number(12.5),12.5)

    def test_decode_uses_complete_original_pcm_and_returns_only_hashes(self):
        pcm=bytes(range(256))*125
        calls=[]
        class Model:
            def transcribe(self,value,**kwargs):
                calls.append((value,kwargs))
                return 'PUBLIC_TRANSCRIPT_不可输出'
        helper=types.SimpleNamespace(normalized=lambda text:text.replace('_',''))
        value=probe.decode(Model(),dict(id='P00',sha256='a'*64),pcm,helper,time.monotonic()+20)
        self.assertEqual(calls[0][0],pcm)
        self.assertEqual(calls[0][1]['sample_rate'],16000)
        self.assertEqual(value['samples'],16000)
        self.assertEqual(value['pcm_sha256'],probe.sha(pcm))
        self.assertNotIn('PUBLIC_TRANSCRIPT',json.dumps(value))
        self.assertEqual(len(value['result_sha256']),64)
        self.assertGreaterEqual(value['decode_process_cpu_ms'],0)

    def test_comparison_excludes_load_warmup_and_uses_exact_order(self):
        result=comparison.compare(fixture())
        self.assertAlmostEqual(result['observed_two_vs_three_wall_change_percent'],-10)
        self.assertEqual(result['aggregates']['2']['samples'],4)
        self.assertTrue(result['constructor_and_warmup_excluded'])
        self.assertFalse(result['causal_gain_claimed'])

    def test_incomplete_or_reordered_plan_rejected(self):
        value=fixture();value['results'].pop()
        with self.assertRaises(ValueError):comparison.compare(value)
        value=fixture();value['results'][0]['threads']=2
        with self.assertRaises(ValueError):comparison.compare(value)

    def test_pcm_or_warmup_change_rejected(self):
        value=fixture();value['results'][1]['measurements'][0]['pcm_sha256']='e'*64
        with self.assertRaises(ValueError):comparison.compare(value)
        value=fixture();value['results'][0]['warmups'].pop()
        with self.assertRaises(ValueError):comparison.compare(value)

    def test_text_changes_and_background_changes_are_visible(self):
        value=fixture();value['results'][1]['measurements'][0]['normalized_sha256']='e'*64
        value['results'][2]['background_counter_changed']=True
        result=comparison.compare(value)
        self.assertFalse(result['all_normalized_results_equal'])
        self.assertFalse(result['warmup_to_measurement_normalized_equal'])
        self.assertTrue(result['background_counter_changed'])

    def test_dry_mode_does_not_read_runtime_or_import_asr(self):
        baseline=dict(startup_sha256=probe.STARTUP)
        with patch.object(sys,'argv',['probe','--package-sha256','a'*64]), \
                patch.object(probe,'package',return_value=baseline), \
                patch.object(probe,'guard',side_effect=AssertionError('hardware access')):
            value=probe.main()
        self.assertEqual(value['status'],'DRY_PACKAGE_VALIDATED')
        self.assertNotIn('sherpa_onnx',sys.modules)


if __name__=='__main__':
    stream=io.StringIO()
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ProbeTests))
    report=dict(status='PASS' if result.wasSuccessful() else 'FAIL',tests_run=result.testsRun,
        failures=len(result.failures),errors=len(result.errors),log=stream.getvalue(),
        hardware_or_model_accessed=False)
    with Path(__file__).with_name('LOCAL_TESTS_'+str(time.time_ns())+'.json').open('x',encoding='utf8') as output:
        json.dump(report,output,indent=2);output.write('\n')
    print(json.dumps(report))
    raise SystemExit(0 if result.wasSuccessful() else 1)
