"""Synthetic vectors and temporary databases only; no board or user data."""
import bootstrap
import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest

from board.identity.deferred import DeferredIdentity
from board.identity.live import IdentityService
from board.identity.model_store import MODEL_ID, MODEL_SHA256, WINDOWS_MODEL_ID
from board.identity.model_store import open_dpu_store, validate_dpu_configuration
from board.identity.store import IdentityStore


def vector(axis=0):
    return tuple(1. if n == axis else 0. for n in range(128))


class IsolatedStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.legacy = self.root/'windows.sqlite3'
        old = IdentityStore(self.legacy, WINDOWS_MODEL_ID, 128, .85, .1)
        old.enroll('legacy', 'synthetic', vector(), consent=True)
        old.close()
        self.fallback = self.root/'windows.json'
        self.fallback.write_text(json.dumps({'schema_version':'aura-camera-identity-1',
            'model_id':WINDOWS_MODEL_ID, 'database':str(self.legacy),
            'feature_backend':{'kind':'windows_sface','host':'192.168.50.1','port':8792,'timeout_ms':650}}))
        self.config = {'model_id':MODEL_ID, 'database':str(self.root/(MODEL_ID+'.sqlite3')),
            'result_ttl_ms':1500, 'threshold':.9, 'ambiguity_margin':.1,
            'feature_backend':{'kind':'dpu_sface', 'model':'/candidate/sface.xmodel',
                'manifest':'/candidate/compiler-manifest.json', 'model_sha256':MODEL_SHA256,
                'manifest_sha256':'a'*64, 'fallback_config':str(self.fallback),'max_source_age_ms':1000}}
        self.original_hash = hashlib.sha256(self.legacy.read_bytes()).hexdigest()

    def test_configuration_check_does_not_create_database(self):
        validate_dpu_configuration(self.config)
        self.assertFalse(Path(self.config['database']).exists())
        self.assertEqual(hashlib.sha256(self.legacy.read_bytes()).hexdigest(), self.original_hash)

    def test_runtime_requires_shared_owner_before_opening_database(self):
        from board.identity.camera_faces import create_service
        config = copy.deepcopy(self.config)
        config.update(schema_version='aura-camera-identity-1', input_size=320,
            face_model='/review/yunet.onnx', embedding_model='/review/sface.onnx',
            minimum_face_pixels=48, minimum_blur_variance=40, minimum_face_score=.9)
        path = self.root/'candidate.json'
        path.write_text(json.dumps(config))
        with self.assertRaises(ValueError):create_service(self.root, path, SimpleNamespace())
        self.assertFalse(Path(self.config['database']).exists())

    def test_placeholder_threshold_cannot_start_runtime(self):
        from board.identity.camera_faces import config_for
        config = copy.deepcopy(self.config)
        config.update(schema_version='aura-camera-identity-1', threshold=None, ambiguity_margin=None)
        path = self.root/'not-deployable.json'
        path.write_text(json.dumps(config))
        with self.assertRaisesRegex(ValueError, 'Explicit model-specific'):
            config_for(self.root, path)
        self.assertFalse(Path(self.config['database']).exists())

    def test_new_store_is_bound_private_empty_and_persists(self):
        store = open_dpu_store(self.config)
        self.assertEqual(store.people(), [])
        self.assertEqual(store.match(vector()).state, 'UNKNOWN')
        self.assertEqual(os.stat(self.config['database']).st_mode & 0o777, 0o600)
        store.enroll('new', 'candidate', vector(), consent=True)
        store.close()
        store = open_dpu_store(self.config)
        self.assertEqual(store.match(vector()).identity_id, 'new')
        store.delete('new')
        store.close()
        self.assertEqual(hashlib.sha256(self.legacy.read_bytes()).hexdigest(), self.original_hash)

    def test_cannot_select_legacy_model_or_unversioned_database(self):
        for changes in ({'model_id':WINDOWS_MODEL_ID}, {'database':str(self.legacy)}):
            candidate = copy.deepcopy(self.config)
            candidate.update(changes)
            with self.assertRaises(ValueError):validate_dpu_configuration(candidate)

    def test_symlink_and_hardlink_aliases_are_rejected_without_write(self):
        path = Path(self.config['database'])
        path.symlink_to(self.legacy)
        with self.assertRaises(ValueError):validate_dpu_configuration(self.config)
        path.unlink()
        os.link(str(self.legacy), str(path))
        with self.assertRaises(ValueError):validate_dpu_configuration(self.config)
        self.assertEqual(hashlib.sha256(self.legacy.read_bytes()).hexdigest(), self.original_hash)

    def test_dangling_symlink_cannot_create_an_unreviewed_database(self):
        path = Path(self.config['database'])
        target = self.root/'unreviewed.sqlite3'
        path.symlink_to(target)
        with self.assertRaises(ValueError):open_dpu_store(self.config)
        self.assertFalse(target.exists())

    def test_renamed_unbound_and_mixed_database_are_rejected(self):
        path = Path(self.config['database'])
        path.write_bytes(self.legacy.read_bytes())
        with self.assertRaises(ValueError):open_dpu_store(self.config)
        path.unlink()
        store = open_dpu_store(self.config)
        with store.db:
            store.db.execute('INSERT INTO identities VALUES (?, ?)', ('foreign', 'synthetic'))
            store.db.execute('INSERT INTO templates VALUES (?, ?, ?, ?)',
                ('foreign', WINDOWS_MODEL_ID, 128, json.dumps(vector())))
        store.close()
        before = hashlib.sha256(path.read_bytes()).hexdigest()
        with self.assertRaises(ValueError):open_dpu_store(self.config)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), before)


class Extractor:
    def __init__(self, result=None, callback=None):
        self.result, self.callback = result, callback
        self.closed = threading.Event()

    def extract(self, *_):
        if self.callback:self.callback()
        if isinstance(self.result, Exception):raise self.result
        return self.result or vector(), ''

    def close(self):self.closed.set()


class DeferredIdentityTests(unittest.TestCase):
    def setUp(self):
        self.now = 1000
        self.key = {'camera_epoch':'epoch','track_id':1,'track_generation':1}
        self.store = IdentityStore(':memory:', MODEL_ID, 128, .9, .1, allow_cross_thread=True)
        self.store.enroll('one', 'synthetic', vector(), consent=True)
        self.service = IdentityService(self.store, lambda:Extractor(), lambda:self.key,
            clock=lambda:self.now, backend='DPU_SFACE_INT8')
        self.service.ready = True
        self.addCleanup(self.service.close)
        self.packet = (None, 1, 1000, {}, copy.deepcopy(self.key))

    def test_busy_packet_preserves_known_identity_without_refreshing_its_ttl(self):
        self.service.process(self.packet, Extractor())
        result = self.service.result
        self.now = 1200
        self.service.process((None, 2, 1200, {}, copy.deepcopy(self.key)), Extractor(DeferredIdentity('busy')))
        self.assertIs(self.service.result, result)
        self.assertEqual(self.service.processed, 1)
        self.assertEqual(self.service.deferred, 1)
        self.assertEqual(self.service.view()[0]['state'], 'KNOWN')
        self.now = 2500
        self.assertEqual(self.service.view()[0]['state'], 'UNKNOWN')

    def test_target_or_database_change_cannot_publish_inflight_feature(self):
        self.service.process(self.packet, Extractor(callback=lambda:self.key.update(track_generation=2)))
        self.assertIsNone(self.service.result)
        self.assertEqual(self.service.discarded, 1)
        self.key['track_generation'] = 1
        def change_database():self.store.enroll('two', 'synthetic2', vector(1), consent=True)
        self.service.process(self.packet, Extractor(callback=change_database))
        self.assertIsNone(self.service.result)
        self.assertEqual(self.service.discarded, 2)

    def test_expired_packet_never_calls_extractor(self):
        self.now = 2500
        def unexpected():raise AssertionError('expired source reached extractor')
        self.service.process(self.packet, Extractor(callback=unexpected))
        self.assertIsNone(self.service.result)
        self.assertEqual(self.service.discarded, 1)

    def test_worker_closes_local_runner_on_exit(self):
        extractor = Extractor()
        service = IdentityService(IdentityStore(':memory:', MODEL_ID, 128, .9, .1,
            allow_cross_thread=True), lambda:extractor, lambda:None)
        service.start()
        service.close()
        self.assertTrue(extractor.closed.wait(1))


if __name__ == '__main__':unittest.main()
