"""Public synthetic counterexamples for the frozen identity cooperation candidate."""
from pathlib import Path
import sys
import threading

import pytest


REPAIR = Path(__file__).resolve().parents[2]
CANDIDATE = REPAIR / 'feature_trigger_collaboration/identity_cooperation_v90'
sys.path.insert(0, str(CANDIDATE))
from test_identity_cooperation import Harness
from tests.framework.test_board_speaker_business import capture, packet, visual


def derived_state(harness):
    def read():
        binding = harness.service.hub.binding
        with binding.registry._db() as db:
            people = tuple(tuple(row) for row in db.execute(
                'SELECT person_id,state FROM linked_people ORDER BY person_id'))
            links = tuple(tuple(row) for row in db.execute(
                'SELECT modality,identity_id,state FROM modality_links ORDER BY modality,identity_id'))
        return people, links, tuple(binding.gallery_versions.items())
    return harness.service.pool.submit(read).result(2)


@pytest.mark.parametrize('field,value', [
    ('request_id', 'foreign-public-request'),
    ('capture_id', 'foreign-public-capture'),
    ('board_boot_id', 'foreign-public-boot'),
    ('generation', 999),
])
def test_foreign_packet_cannot_revoke_existing_derived_links_or_poison_gallery_version(tmp_path, field, value):
    harness = Harness(tmp_path)
    try:
        before = derived_state(harness)
        original = harness.scene.read

        def foreign_inventory(meta, snapshot):
            packet = original(meta, snapshot)
            packet['context'] = dict(meta, **{field: value})
            packet['gallery']['revision'] += 100
            packet['current'] = None
            packet['inventory'] = []
            return packet

        harness.scene.read = foreign_inventory
        _, result = harness.say('用于独立审查的公开普通对话')
        assert result['status'] == 'COMPLETE'
        assert 'face' not in result['identity']['modalities']
        assert not harness.bundle.access.grants
        assert derived_state(harness) == before
    finally:
        harness.close()


def test_blocked_gallery_read_keeps_health_and_cancellation_available(tmp_path):
    harness = Harness(tmp_path)
    entered = threading.Event()
    release = threading.Event()
    try:
        meta, pcm = capture(30)
        before = derived_state(harness)
        encoder_calls = harness.encoder.calls

        def slow_read():
            entered.set()
            assert release.wait(2)
            return packet(meta)

        value = harness.service.submit_analysis(meta, pcm, 'b' * 32,
            visual=visual(meta), gallery_provider=slow_read)
        assert value['status'] == 'PENDING'
        assert entered.wait(.5)
        health = []
        reader = threading.Thread(target=lambda: health.append(harness.service.health()))
        reader.start()
        reader.join(.5)
        assert not reader.is_alive()
        assert health and health[0]['queued_or_active'] == 1
        cancelled = harness.service.cancel_analysis(meta, 'b' * 32)
        assert cancelled['status'] == 'CANCELLED'
        release.set()
        harness.service.pool.submit(lambda: None).result(2)
        assert harness.encoder.calls == encoder_calls
        assert derived_state(harness) == before
    finally:
        release.set()
        harness.close()


@pytest.mark.parametrize('field,value', [
    ('session_id', 'foreign-public-session'),
    ('sample_count', 3200),
    ('pcm_sha256', 'd' * 64),
    ('budget_ms', 501),
    ('protocol', 'foreign-public-protocol'),
])
def test_remaining_packet_context_fields_are_checked_before_mutation(tmp_path, field, value):
    test_foreign_packet_cannot_revoke_existing_derived_links_or_poison_gallery_version(
        tmp_path, field, value)


def test_provider_keeps_submitted_capture_when_latest_capture_slot_changes(tmp_path):
    harness = Harness(tmp_path)
    try:
        original_asr = harness.asr.transcribe
        original_read = harness.scene.read
        seen = []

        def change_latest_slot(*args, **kwargs):
            harness.bundle.jobs.capture_owners = {'foreign-new-capture': harness.scene.snapshot()}
            return original_asr(*args, **kwargs)

        def read_bound(meta, snapshot):
            seen.append(dict(meta))
            return original_read(meta, snapshot)

        harness.asr.transcribe = change_latest_slot
        harness.scene.read = read_bound
        _, result = harness.say('公开采集闭包归属检查')
        assert len(seen) == 1
        assert seen[0] == result['context']
        assert seen[0]['capture_id'] == 'public-cooperation-1'
        assert 'public-cooperation-1' not in harness.bundle.jobs.capture_owners
        assert 'face' in result['identity']['modalities']
        assert result['identity']['claim_scope'] == 'visible_person'
        assert result['identity']['single_speaker_verified'] is False
    finally:
        harness.close()


def test_worker_readback_current_face_cannot_replace_captured_face(tmp_path):
    harness = Harness(tmp_path)
    try:
        harness.add_other_public_face_link()
        original = harness.scene.read

        def changed_current(meta, snapshot):
            packet = original(meta, snapshot)
            packet['current'] = dict(identity_id='public-face-b', template_fingerprint='c' * 64)
            return packet

        harness.scene.read = changed_current
        _, result = harness.say('公开采集人脸替换检查')
        assert result['status'] == 'COMPLETE'
        assert result['visual']['evidence']['face_identity_id'] == 'public-face'
        assert 'face' not in result['identity']['modalities']
        assert result['identity']['identity_verified'] is False
        assert not harness.bundle.access.grants
    finally:
        harness.close()
