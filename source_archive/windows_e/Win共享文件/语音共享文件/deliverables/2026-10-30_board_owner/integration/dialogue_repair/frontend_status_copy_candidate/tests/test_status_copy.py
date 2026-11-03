"""Fixed-shape copy contracts; only public synthetic status/transport data."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
REPAIR = ROOT.parent
sys.path.insert(0, str(ROOT.parents[4] / 'aura'))
import board.runtime.audio as package
package.__path__.insert(0, str(REPAIR / 'frontend_balance_candidate/before/board/runtime/audio'))
package.__path__.insert(0, str(REPAIR / 'frontend_balance_candidate/after/board/runtime/audio'))
package.__path__.insert(0, str(ROOT / 'after/board/runtime/audio'))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


module = load('board.runtime.audio.board_frontend_auto', ROOT / 'after/board/runtime/audio/board_frontend_auto.py')
support = load('_status_copy_diagnostics_fixtures', REPAIR /
    'capture_diagnostics_candidate/tests/test_capture_diagnostics.py')
support.remote = module


def status():
    return support.Transport().start(20)


def test_validated_status_is_equal_to_original_copy_and_fully_detached():
    original = status()
    original['audio_frontend'].update(endpoint_feed_calls=20, enabled=True, consumer_gap_max_ms=33.)
    result = module.validate_status(original, generation=1, capture_id=original['capture_id'])
    assert result == copy.deepcopy(original)
    result['state'] = 'CANCELLED'
    result['audio_frontend']['endpoint_feed_calls'] = -1
    result['input_queue']['capacity_frames'] = -1
    assert original['state'] == 'RECORDING'
    assert original['audio_frontend']['endpoint_feed_calls'] == 20
    assert original['input_queue']['capacity_frames'] == 8


@pytest.mark.parametrize('kind', ['extra_root', 'nested_frontend', 'nested_queue', 'pcm', 'text',
    'nan', 'negative', 'numeric_bool', 'unknown_error', 'owner', 'generation_bool', 'state_bool'])
def test_complete_strict_validation_still_rejects_bad_metadata(kind):
    value = status()
    if kind == 'extra_root': value['text'] = 'PRIVATE'
    elif kind == 'nested_frontend': value['audio_frontend']['frames'] = {'private': 1}
    elif kind == 'nested_queue': value['input_queue']['peak_frames'] = [1]
    elif kind == 'pcm': value['audio_frontend']['pcm'] = b'PRIVATE'
    elif kind == 'text': value['input_queue']['text'] = 'PRIVATE'
    elif kind == 'nan': value['audio_frontend']['endpoint_feed_cpu_total_ms'] = float('nan')
    elif kind == 'negative': value['input_queue']['queued_frames'] = -1
    elif kind == 'numeric_bool': value['audio_frontend']['frames'] = True
    elif kind == 'unknown_error': value['error'] = 'PRIVATE_ERROR'
    elif kind == 'owner': value['capture_id'] = 'wrong-owner'
    elif kind == 'generation_bool': value['generation'] = True
    elif kind == 'state_bool': value['speech_started'] = 1
    with pytest.raises(module.wire.FrontendProcessError): module.validate_status(value)


def test_uninitialized_snapshot_has_no_cached_or_shared_metadata():
    proxy = module.RemoteAutomaticCapture(lambda: False, transport=SimpleNamespace())
    first = proxy.snapshot()
    assert first['state'] == 'IDLE' and first['audio_frontend']['capture_failures'] == 0
    first['input_queue']['private'] = 'PRIVATE'
    first['audio_frontend']['frames'] = -1
    second = proxy.snapshot()
    assert second['input_queue'] == {} and 'frames' not in second['audio_frontend']


def test_one_filtered_failure_record_detaches_both_nested_metric_containers():
    proxy = module.RemoteAutomaticCapture(lambda: False, transport=SimpleNamespace())
    value = status(); value.update(state='ERROR', error='pcm_input_queue_overflow')
    value['input_queue'].update(peak_frames=8, error='pcm_input_queue_overflow')
    with proxy._lock:
        proxy._generation = value['generation']; proxy.capture_id = value['capture_id']
        proxy._install(value)
    first = proxy.snapshot()['audio_frontend']['last_capture_failure']
    assert first['error_code'] == 'pcm_input_queue_overflow'
    first['input_queue']['peak_frames'] = 0
    first['audio_frontend']['endpoint_feed_calls'] = -1
    first['text'] = 'PRIVATE'
    again = proxy.snapshot()['audio_frontend']['last_capture_failure']
    assert again['input_queue']['peak_frames'] == 8
    assert again['audio_frontend']['endpoint_feed_calls'] == 0
    assert 'PRIVATE' not in json.dumps(again)
    assert 'capture_id' not in again


def test_failure_filter_remains_before_fast_copy_not_a_new_untrusted_input_path():
    proxy = module.RemoteAutomaticCapture(lambda: False, transport=SimpleNamespace())
    # Internal failure capture uses the original fixed _metrics allowlist.
    proxy._status = dict(audio_frontend=dict(frames=2, text='PRIVATE', pcm=b'PRIVATE'),
                         input_queue=dict(peak_frames=8, body={'secret': 'PRIVATE'}))
    proxy._generation = 1; proxy.error = 'PRIVATE_ERROR'
    with proxy._lock: proxy._remember_capture_failure()
    result = module._copy_failure(proxy._last_capture_failure)
    assert result['error_code'] == 'frontend_auto_capture_failed'
    assert result['audio_frontend'] == dict(frames=2)
    assert result['input_queue'] == dict(peak_frames=8)
    assert 'PRIVATE' not in json.dumps(result)


def test_retired_status_copy_cannot_mutate_old_owner_tombstone():
    old = status(); old.update(state='CANCELLED', input_ready=False)
    owner = module.ChildAutomaticSession.__new__(module.ChildAutomaticSession)
    owner.retired = {(1, old['capture_id']): old}
    result = owner.retired_status(1, old['capture_id'], module.AUTO_CLOSE)
    assert result['state'] == 'CLOSED'
    result['audio_frontend']['endpoint_feed_calls'] = -1
    result['input_queue']['capacity_frames'] = 0
    assert old['audio_frontend']['endpoint_feed_calls'] == 0
    assert old['input_queue']['capacity_frames'] == 8
