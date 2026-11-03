"""Deterministic cached-start races with full original ACKs and snapshot validation."""
import copy

import pytest

from board.identity import voice_enrollment as module
from tests.framework.test_simple_enrollment import snapshot


class ImmediateThread:
    def __init__(self, target, args=(), daemon=False, **kwargs):
        self.target, self.args = target, args
    def start(self): self.target(*self.args)


class Fixture:
    def __init__(self, monkeypatch, *, publish_after=0., previous=''):
        self.now = 1.
        self.view = snapshot()
        self.commands, self.sleeps = [], []
        self.publish_after = publish_after
        self.server = None
        self.ack_change = None
        self.after_send = None
        self.after_snapshot = None
        self.mutate_published = None
        if previous:
            self.view['modules']['identity']['enrollment_sampling'].update(session_id=previous, stage='failed')
        self.flow = module.VoiceEnrollment('boot', self.read, self.command, simple=True,
            clock=lambda: self.now, now_ms=lambda: round(self.now*1000))
        self.flow.stage = 'authorize'
        self.flow.name = '合成登记'
        self.flow.owner = copy.deepcopy(self.flow.owner_of(self.view))
        self.flow.until = self.now + 120
        monkeypatch.setattr(module.time, 'sleep', self.sleep)
        monkeypatch.setattr(module.threading, 'Thread', ImmediateThread)

    def read(self):
        value = copy.deepcopy(self.view)
        if self.after_snapshot:
            self.after_snapshot()
        return value

    def publish(self):
        self.view['sequence'] += 1
        self.view['observed_mono_ms'] = round(self.now*1000)
        self.view['modules']['identity']['enrollment_sampling'].update(self.server)
        self.view['capabilities'].update(identity_sample_start=False, identity_sample_cancel=True)
        if self.mutate_published:
            self.mutate_published(self.view)

    def command(self, command):
        self.commands.append(copy.deepcopy(command))
        if command['action'] == 'identity_sample_start':
            self.server = {'session_id': 'new-owned-session', 'stage': 'collect',
                           'bound_target': copy.deepcopy(command['params']['target'])}
            if self.publish_after == 0:
                self.publish()
            if self.after_send:
                self.after_send()
        elif command['action'] == 'identity_sample_cancel':
            if self.server and self.server['session_id'] == command['params']['session_id']:
                self.server.update(session_id='', stage='idle', bound_target=None)
                self.publish()
        fields = ('protocol_version', 'board_boot_id', 'service_epoch', 'command_id', 'ui_epoch', 'ui_generation')
        ack = {key: command[key] for key in fields}
        ack.update(accepted=True, detail='合成回执')
        if self.ack_change and command['action'] == 'identity_sample_start':
            self.ack_change(ack)
        return ack

    def sleep(self, duration):
        self.sleeps.append(duration)
        self.now += duration
        if (self.publish_after is not None and self.server
                and self.now >= 1. + self.publish_after):
            self.publish()

    def start(self, **kwargs):
        return self.flow._start_simple(copy.deepcopy(self.view), **kwargs)

    def actions(self): return [command['action'] for command in self.commands]
    def cancelled_ids(self):
        return [command['params']['session_id'] for command in self.commands if command['action']=='identity_sample_cancel']


@pytest.mark.parametrize('delay', [0., .05, .6, 1.2])
def test_original_immediate_and_delayed_publications_bind_one_start_without_new_consent(monkeypatch, delay):
    fixture = Fixture(monkeypatch, publish_after=delay)
    assert fixture.start()['code'] == 'sample_auto'
    assert fixture.flow.sampling_id == 'new-owned-session'
    assert fixture.flow.stage == 'sampling' and fixture.flow.authorized is True
    assert fixture.actions() == ['identity_sample_start']
    assert fixture.flow.until == 91.  # Camera/client sample window is never extended by cache wait.
    assert fixture.flow.owner == fixture.flow.owner_of(fixture.view)


def test_continuously_old_snapshot_fails_bounded_without_retry_or_guess_cancel(monkeypatch):
    fixture = Fixture(monkeypatch, publish_after=None)
    assert fixture.start()['code'] == 'sample_failed'
    assert fixture.flow.stage == 'idle' and not fixture.flow.sampling_id
    assert fixture.now <= 3.5 and len(fixture.sleeps) <= 50
    assert fixture.actions() == ['identity_sample_start']


def test_old_retained_session_cannot_be_reused_or_cancelled(monkeypatch):
    fixture = Fixture(monkeypatch, publish_after=None, previous='old-failed-session')
    assert fixture.start()['code'] == 'sample_failed'
    assert fixture.cancelled_ids() == [] and fixture.actions() == ['identity_sample_start']
    assert fixture.server['session_id'] == 'new-owned-session'


@pytest.mark.parametrize('mutation', [
    lambda view: view.update(service_epoch='other-service'),
    lambda view: view['context'].update(session_id='other-context'),
    lambda view: view['modules']['identity'].update(db_version=1),
    lambda view: view.update(source_kind='fixture'),
    lambda view: view['modules']['identity']['enrollment_sampling']['bound_target'].update(track_id=99),
])
def test_other_owner_context_revision_or_target_cannot_be_adopted_or_cancelled(monkeypatch, mutation):
    fixture = Fixture(monkeypatch)
    fixture.mutate_published = mutation
    assert fixture.start()['code'] == 'sample_failed'
    assert fixture.cancelled_ids() == [] and fixture.actions() == ['identity_sample_start']


@pytest.mark.parametrize('stage', ['validate', 'ready'])
def test_old_ready_or_noncollection_id_is_not_adopted_or_cancelled(monkeypatch, stage):
    fixture = Fixture(monkeypatch)
    fixture.mutate_published = lambda view: view['modules']['identity']['enrollment_sampling'].update(stage=stage)
    assert fixture.start()['code'] == 'sample_failed'
    assert fixture.cancelled_ids() == []
    assert fixture.actions() == ['identity_sample_start']


def test_selected_target_change_cannot_prove_or_cancel_new_sample(monkeypatch):
    fixture = Fixture(monkeypatch)
    fixture.mutate_published = lambda view: view['modules']['target']['selected'].update(track_generation=2)
    assert fixture.start()['code'] == 'sample_failed'
    assert fixture.cancelled_ids() == []


def test_cancellation_before_command_never_starts(monkeypatch):
    fixture = Fixture(monkeypatch)
    with pytest.raises(InterruptedError): fixture.start(is_current=lambda: False)
    assert fixture.commands == []


def test_cancellation_after_proved_publication_cancels_only_own_id(monkeypatch):
    fixture = Fixture(monkeypatch)
    checks = [0]
    def current():
        checks[0] += 1
        return checks[0] < 3  # Cancel once a post-ACK status has actually been published.
    with pytest.raises(InterruptedError): fixture.start(is_current=current)
    assert fixture.cancelled_ids() == ['new-owned-session']
    assert fixture.flow.stage == 'idle'


def test_cancellation_while_cache_still_old_does_not_cancel_unknown_camera_id(monkeypatch):
    fixture = Fixture(monkeypatch, publish_after=None)
    current = [True]
    fixture.after_send = lambda: current.__setitem__(0, False)
    with pytest.raises(InterruptedError): fixture.start(is_current=lambda: current[0])
    assert fixture.cancelled_ids() == [] and fixture.actions() == ['identity_sample_start']


def test_later_local_epoch_is_neither_reset_nor_cancelled(monkeypatch):
    fixture = Fixture(monkeypatch)
    def replace():
        fixture.flow.reset()
        fixture.flow.stage = 'authorize'
        fixture.flow.name = '另一次合成登记'
        fixture.flow.owner = ('boot','other-service',None,7)
        fixture.flow.sampling_id = 'other-local-id'
    fixture.after_send = replace
    with pytest.raises(InterruptedError): fixture.start()
    assert fixture.flow.name == '另一次合成登记'
    assert fixture.flow.sampling_id == 'other-local-id'
    assert fixture.cancelled_ids() == []


@pytest.mark.parametrize('key', ['protocol_version','board_boot_id','service_epoch','command_id','ui_epoch','ui_generation'])
def test_start_ack_owner_mismatch_cannot_authorize_publication(monkeypatch, key):
    fixture = Fixture(monkeypatch)
    fixture.ack_change = lambda ack: ack.update({key: 9 if key=='ui_generation' else 'other-owner'})
    assert fixture.start()['code'] == 'sample_failed'
    assert fixture.actions() == ['identity_sample_start'] and fixture.cancelled_ids() == []


def test_unknown_accepted_reply_is_not_success_or_retry(monkeypatch):
    fixture = Fixture(monkeypatch)
    fixture.ack_change = lambda ack: ack.update(result={'session_id':'untrusted-extra-id'})
    assert fixture.start()['code'] == 'sample_failed'
    assert fixture.actions() == ['identity_sample_start']


def test_rejected_ack_never_polls_or_adopts_current_session(monkeypatch):
    fixture = Fixture(monkeypatch)
    fixture.ack_change = lambda ack: ack.update(accepted=False)
    assert fixture.start()['code'] == 'sample_failed'
    assert fixture.actions() == ['identity_sample_start'] and fixture.cancelled_ids() == []


def test_expired_start_ack_does_not_gain_a_new_deadline(monkeypatch):
    fixture = Fixture(monkeypatch)
    fixture.after_send = lambda: setattr(fixture, 'now', 3.6)
    assert fixture.start()['code'] == 'sample_failed'
    assert fixture.actions() == ['identity_sample_start']


def test_cancel_cleanup_rechecks_token_and_does_not_cancel_replacement(monkeypatch):
    fixture = Fixture(monkeypatch)
    checks = [0]
    def current():
        checks[0] += 1
        if checks[0] == 2:
            fixture.server['session_id'] = 'other-client-session'
            fixture.publish()
            return False
        return True
    with pytest.raises(InterruptedError): fixture.start(is_current=current)
    assert fixture.cancelled_ids() == [] and fixture.actions() == ['identity_sample_start']
    assert fixture.server['session_id'] == 'other-client-session'


@pytest.mark.parametrize('stage', ['failed', 'ready', 'collect'])
def test_precommand_intermediate_cache_b_cannot_be_adopted_or_cancelled(monkeypatch, stage):
    fixture = Fixture(monkeypatch, publish_after=.6, previous='cached-A')
    fixture.now = 1.1
    def old_b():
        fixture.view['sequence'] += 1
        fixture.view['observed_mono_ms'] = 1050  # Genuine old source stamp, before issued1100.
        fixture.view['modules']['identity']['enrollment_sampling'].update(
            session_id='precommand-B', stage=stage,
            bound_target=copy.deepcopy(fixture.flow.owner[2]))
    fixture.after_send = old_b
    assert fixture.start()['code'] == 'sample_auto'
    assert fixture.flow.sampling_id == 'new-owned-session'
    assert fixture.cancelled_ids() == [] and fixture.actions() == ['identity_sample_start']


def test_snapshot_generated_before_ack_even_if_after_issue_is_not_claimed(monkeypatch):
    fixture = Fixture(monkeypatch, publish_after=.6, previous='cached-A')
    fixture.now = 1.1
    def old_b():
        fixture.now = 1.2
        fixture.view['sequence'] += 1
        fixture.view['observed_mono_ms'] = 1150
        fixture.view['modules']['identity']['enrollment_sampling'].update(
            session_id='pre-ACK-B', stage='collect',
            bound_target=copy.deepcopy(fixture.flow.owner[2]))
    fixture.after_send = old_b
    assert fixture.start()['code'] == 'sample_auto'
    assert fixture.flow.sampling_id == 'new-owned-session'
    assert fixture.cancelled_ids() == []
