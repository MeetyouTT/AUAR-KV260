"""Synthetic vectors/audio only; not a field accuracy claim."""
import math
from pathlib import Path
import struct
import sqlite3
import hashlib
import json
import tempfile
import unittest
import wave

from board.identity.store import IdentityStore
from common.speaker_identity import MODEL_FILES, SpeakerStore, enrollment_vector, read_pcm, verify_model
from common.speaker_validation import metrics, calibrate, validate_trial_partitions


class SpeakerTests(unittest.TestCase):
    def test_model_fingerprint_detects_drift(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            for name in MODEL_FILES: (path/name).write_bytes(b'test fixture, not a model')
            hashes = {name:hashlib.sha256((path/name).read_bytes()).hexdigest() for name in MODEL_FILES}
            model_id = 'ecapa-voxceleb-'+hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest()
            (path/'manifest.json').write_text(json.dumps({'sha256':hashes,'model_id':model_id}),encoding='utf-8')
            self.assertEqual(verify_model(path),model_id)
            (path/'embedding_model.ckpt').write_bytes(b'changed')
            with self.assertRaises(ValueError): verify_model(path)

    def test_separate_database_marker(self):
        with tempfile.TemporaryDirectory() as directory:
            face = Path(directory)/'renamed.sqlite3'
            original = IdentityStore(face,'face',2,.8,.1)
            original.close()
            before = face.read_bytes()
            with self.assertRaises(ValueError):
                SpeakerStore(face,'speaker',2,.7,.1,create=True)
            self.assertEqual(before,face.read_bytes())
            speaker = Path(directory)/'speaker.sqlite3'
            with self.assertRaises(ValueError): SpeakerStore(speaker,'speaker',2,.7,.1)
            self.assertFalse(speaker.exists())
            store = SpeakerStore(speaker,'speaker',2,.7,.1,create=True)
            store.enroll('a','A',[1,0],consent=True,expected_revision=0)
            store.close()
            store = SpeakerStore(speaker,'speaker',2,.7,.1)
            self.assertEqual(store.match([1,0]).identity_id,'a')
            store.close()

    def test_calibration_leakage_and_rates(self):
        trials = [{'identity_id':'a','scores':{'a':.9,'b':.1},'session_id':'one','pcm_sha256':'x'},
                  {'identity_id':'stranger','scores':{'a':.6,'b':.3},'session_id':'two','pcm_sha256':'y'}]
        self.assertEqual(metrics(trials,.5,.1)['false_accept_unknown'],1)
        result = calibrate(trials,[.5,.8],[.1],0)
        self.assertEqual(result['threshold'],.8)
        self.assertFalse(result['field_calibrated'])
        with self.assertRaises(ValueError): validate_trial_partitions(trials,trials)
        held = [dict(trials[0],session_id='three',pcm_sha256='z')]
        validate_trial_partitions(trials,held)
        with self.assertRaises(ValueError): calibrate(trials[:1],[.8],[.1],0)
        self.assertEqual(calibrate(trials,[.99],[.1],0)['state'],'NO_OPERATING_POINT')

    def test_gallery_rejection_and_ambiguity(self):
        store = IdentityStore(':memory:', 'speaker-test', 2, .8, .1)
        self.addCleanup(store.close)
        self.assertEqual(store.match([1,0]).state, 'UNKNOWN')
        store.enroll('a', 'A', [1,0], consent=True, expected_revision=0)
        self.assertEqual(store.match([1,0]).identity_id, 'a')
        self.assertEqual(store.match([0,1]).state, 'UNKNOWN')
        store.enroll('b', 'B', [1,.01], consent=True, expected_revision=1)
        self.assertEqual(store.match([1,0]).state, 'AMBIGUOUS')
        with self.assertRaises(ValueError):
            store.enroll('a','A',[1,0],consent=True,expected_revision=0)

    def test_enrollment_consistency(self):
        self.assertEqual(enrollment_vector([[1,0]]*3,2,.8), (1.,0.))
        for vectors in ([[1,0]]*2, [[1,0],[1,0],[0,1]], [[1,0],[1,0],[math.nan,0]]):
            with self.assertRaises(ValueError):
                enrollment_vector(vectors,2,.8)

    def test_audio_gate(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'sample.wav'
            for value,rate,seconds,valid in [(1000,16000,3,True),(0,16000,3,False),
                                             (32767,16000,3,False),(1000,8000,3,False),
                                             (1000,16000,1,False)]:
                with wave.open(str(path),'wb') as output:
                    output.setparams((1,2,rate,0,'NONE','not compressed'))
                    output.writeframes(struct.pack('<h',value)*int(rate*seconds))
                if valid:
                    self.assertEqual(len(read_pcm(path)),96000)
                else:
                    with self.assertRaises(ValueError): read_pcm(path)


if __name__ == '__main__':
    unittest.main()
