import copy
from pathlib import Path
import tempfile
import unittest
import release_control as release


HASHES={'candidate/aura/synthetic.py':'fixed-source-sha'}


def fixture():
    sample={'face_targets':{'source_age_ms':100},'dpu_schedule':{'primary_period_overruns':1,
        'optional':{'yunet':{'overruns':0,'disabled':False,'maximum_ms':25}}}}
    return {'scope':release.QUALIFIED_SCOPE,'complete':True,'passed':True,'rollback_verified':True,
        'protected_audio_source_verified':True,'gap_record_retention_passed':True,'rollback_timer_left_armed':False,
        'error':None,'rollback_error':None,'retry_hashes':dict(HASHES),'observed_seconds':1800.2,
        'observed_yolo_hz':9.95,'observed_yunet_hz':3.1,'native_completed_delta':5580,'usb_warning_count':0,
        'samples':[copy.deepcopy(sample) for _ in range(361)],'sample_count':361,
        'freshness_final':{'schema_version':'aura-face-freshness-light-3','observer_failures':0,'gap_records_dropped':0,
            'counters':dict.fromkeys(('process_errors','callback_errors','invalid_source_ages','source_clock_pairs_rejected',
                'counter_saturation','observed_gap_intervals','post_commit_at_or_over_ttl'),0)},
        'original_unit_sha256':'84116d8faf6f4d3972f5f2eac35f8c98cf8ecbe51752a8f78d803aa8a7cdd75c'}


class QualificationTests(unittest.TestCase):
    def test_complete_exact_source_long_report_qualifies(self):self.assertTrue(release.qualify(fixture(),HASHES))
    def test_incomplete_unrestored_or_wrong_scope_never_qualifies(self):
        for key,value in [('complete',False),('passed',False),('rollback_verified',False),
                          ('protected_audio_source_verified',False),('rollback_timer_left_armed',True),('scope','120S')]:
            d=fixture();d[key]=value
            with self.subTest(key=key),self.assertRaises(AssertionError):release.qualify(d,HASHES)
    def test_different_sources_are_rejected(self):
        d=fixture();d['retry_hashes']={}
        with self.assertRaises(AssertionError):release.qualify(d,HASHES)
    def test_nonfinite_or_low_throughput_and_usb_are_rejected(self):
        for key,value in [('observed_seconds',1799),('observed_yolo_hz',8.9),('observed_yunet_hz',1.9),
                          ('observed_yunet_hz',float('nan')),('observed_yolo_hz',True),('usb_warning_count',1),
                          ('native_completed_delta',3599)]:
            d=fixture();d[key]=value
            with self.subTest(key=key,value=value),self.assertRaises(AssertionError):release.qualify(d,HASHES)
    def test_stale_sample_or_missing_observations_are_rejected(self):
        d=fixture();d['samples'][42]['face_targets']['source_age_ms']=1000
        with self.assertRaises(AssertionError):release.qualify(d,HASHES)
        d=fixture();d['samples'].pop()
        with self.assertRaises(AssertionError):release.qualify(d,HASHES)
    def test_primary_or_optional_overrun_is_rejected(self):
        d=fixture();d['samples'][-1]['dpu_schedule']['primary_period_overruns']=2
        with self.assertRaises(AssertionError):release.qualify(d,HASHES)
        d=fixture();d['samples'][-1]['dpu_schedule']['optional']['yunet']['disabled']=True
        with self.assertRaises(AssertionError):release.qualify(d,HASHES)
    def test_gap_and_missing_diagnostic_records_are_rejected(self):
        for field in ('observer_failures','gap_records_dropped'):
            d=fixture();d['freshness_final'][field]=1
            with self.assertRaises(AssertionError):release.qualify(d,HASHES)
        d=fixture();d['freshness_final']['counters']['observed_gap_intervals']=1
        with self.assertRaises(AssertionError):release.qualify(d,HASHES)


class PackagingTests(unittest.TestCase):
    def test_source_manifest_detects_changes_and_rejects_external_links(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);p=root/'model.py';p.write_text('pass\n');before=release.tree_manifest(root)
            p.write_text('value=1\n');self.assertNotEqual(release.tree_manifest(root),before)
            (root/'outside').symlink_to('/etc')
            with self.assertRaises(AssertionError):release.tree_manifest(root)
    def test_only_owned_runtime_paths_are_rewritten(self):
        raw=b'[Service]\nEnvironment="AURA_EXPERIMENT_GIL_MS=1"\nExecStart=/usr/bin/python3 -B /old/gil_camera_launcher.py /old/aura/tools/board_camera_motion.py --config /retained/config.json\n'
        updated=release.rewrite_unit(raw,Path('/old'),Path('/new'))
        self.assertIn(b'/new/runtime_entry.py',updated);self.assertIn(b'/new/aura/tools/board_camera_motion.py',updated)
        self.assertIn(b'--config /retained/config.json',updated)
        self.assertIn(b'AURA_EXPERIMENT_GIL_MS=1',updated)
    def test_unit_without_exact_parent_paths_is_not_modified(self):
        with self.assertRaises(AssertionError):release.rewrite_unit(b'[Service]\nExecStart=/unrelated\n','/old','/new')


if __name__=='__main__':unittest.main()
