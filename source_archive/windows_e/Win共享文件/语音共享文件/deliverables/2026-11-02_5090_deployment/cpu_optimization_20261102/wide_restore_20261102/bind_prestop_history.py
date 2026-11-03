"""Bind observed original one-prefix edge to the accepted old ordered receipt.

No history traversal or Native validation is replaced; no stop is sent here.
"""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import time

ns = {'__name__': 'reviewed_original_stop_helper', 'EXPECTED': FRESH['normal_stop_expected']}
exec(compile(STOP_SOURCE, '<original-stop-helper-4a5>', 'exec'), ns)
regular, digest, require = ns['regular'], ns['digest'], ns['require']
expected = FRESH['normal_stop_expected']
ns['checked'](expected)
require(digest(ACCEPTED_SUFFIX_RAW) == '44f2b79cd9bca5d1a9ab13fa757df923e9b6f4d0b6c3fbd1d44bcafd06ff0ca1', 'Accepted suffix bytes differ')
accepted = json.loads(ACCEPTED_SUFFIX_RAW)['board_result']
require(accepted['original_python_validator_passed'] is True and accepted['full_previous_kernel_archive_chain_verified'] is True, 'Accepted ordered suffix proof missing')
rows = accepted['archives']
require(len(rows) == accepted['archive_count'] and rows, 'Accepted exact suffix count differs')
old_head = accepted['loaded']['document']['previous_kernel_history']
run = json.loads(ns['pinned'](expected['source_closure']['owner_run_config']))
native = run['native_execution']
health = ns['get']('/health'); handoff = health['dpu_schedule']['protection_handoff']
require(ns['owner'](GRANT['camera_owner']) == GRANT['camera_owner'] and health['pid'] == GRANT['camera_owner']['pid'], 'Prestop owner changed')
head = handoff['previous_kernel_history']
require(head == FRESH['prestop_source_observation']['head'] and handoff['mode'] == 'native_new_kernel_boot'
        and handoff['current_boot'] == GRANT['boot_id'], 'Original live bootstrap head changed')
directory = Path(native['new_boot_marker_directory'])
marker_path = directory / ('kernel-boot-' + GRANT['boot_id'] + '.consumed')
marker_raw = regular(marker_path, 262144); marker = json.loads(marker_raw)
require(marker['schema'] == 'aura-native-current-kernel-consumption-1' and marker['boot'] == GRANT['boot_id']
        and marker['archive_path'] == head['archive_path'] and marker['archive_sha256'] == head['archive_sha256']
        and marker['source_checkpoint_sha256'] == head['source_checkpoint_sha256']
        and 0 < marker['captured_mono_ns'] <= time.monotonic_ns(), 'Original marker/head linkage differs')
archive_path = Path(head['archive_path'])
require(archive_path.parent == directory / 'archive', 'Original archive root differs')
archive_raw = regular(archive_path, 262144); archive = json.loads(archive_raw)
require(digest(archive_raw) == head['archive_sha256'] and archive['schema'] == 'aura-native-previous-kernel-archive-1'
        and archive['current_boot'] == GRANT['boot_id'] and archive['source_boot'] == head['source_boot']
        and archive['source_checkpoint_sha256'] == head['source_checkpoint_sha256']
        and archive['history_is_lower_bound'] is head['history_is_lower_bound']
        and archive['checkpoint']['previous_kernel_history'] == old_head, 'Observed single prefix does not link directly to accepted suffix')
require(archive['checkpoint']['seed']['boot_id'] == head['source_boot'] != GRANT['boot_id'], 'Prefix predecessor boot differs')
prefix = dict(path=str(archive_path), sha256=digest(archive_raw), current_boot=archive['current_boot'],
              source_boot=archive['source_boot'], source_checkpoint_sha256=archive['source_checkpoint_sha256'],
              history_is_lower_bound=archive['history_is_lower_bound'])
observed = dict(schema='aura-live-native-prestop-source-1', boot_id=GRANT['boot_id'], source_owner=GRANT['camera_owner'],
                observed_mono_ns=time.monotonic_ns(), head=head, archive_prefix=[prefix],
                original_marker_pin=dict(path=str(marker_path), sha256=digest(marker_raw)),
                original_archive_pin=dict(path=str(archive_path), sha256=digest(archive_raw)))
session = Path(SESSION)
require(session.resolve() == session and session.is_dir() and session.stat().st_uid == 0, 'Original phase directory differs')
def put(name, raw):
    path = session / name
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    parent = os.open(session, os.O_RDONLY | os.O_DIRECTORY)
    try: os.fsync(parent)
    finally: os.close(parent)
    return dict(path=str(path), sha256=digest(raw))
def encoded(value): return (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()
suffix_pin = put('accepted-suffix-original-44f2.json', ACCEPTED_SUFFIX_RAW)
source_pin = put('prestop-original-prefix-source.json', encoded(observed))
history = dict(head=head, archive_count=len(observed['archive_prefix']) + len(rows),
               archives=observed['archive_prefix'] + rows,
               legacy_pin=dict(path='/home/root/aura-native-critical-20261024/legacy-prefix/ecda1d52dbc4d3a0/legacy-boot-archive.json',
                   sha256='ecda1d52dbc4d3a0005f55c6a85d489c92293076661403c1d834666adae4e2c7'),
               observed_mono_ns=observed['observed_mono_ns'])
bindings = {key: dict(pin=source_pin, pointer='/' + key) for key in ('boot_id', 'source_owner', 'observed_mono_ns', 'head')}
bindings['archive_segments'] = [dict(pin=source_pin, pointer='/archive_prefix'), dict(pin=suffix_pin, pointer='/board_result/archives')]
provenance = dict(schema='aura-prestop-native-history-manifest-1', boot_id=GRANT['boot_id'],
                  source_owner=GRANT['camera_owner'], history=history, source_bindings=bindings)
provenance_pin = put('prestop-history-provenance.json', encoded(provenance))
history['provenance_pin'] = provenance_pin
history_pin = put('history-expected-before-camera-stop.json', encoded(history))
normal_expected_pin = put('normal-stop.expected.json', encoded(expected))
output = io.StringIO(); previous = sys.argv
try:
    sys.argv = ['original_normal_stop_default_dryrun']
    with contextlib.redirect_stdout(output): ns['main']()
finally: sys.argv = previous
dryrun = json.loads(output.getvalue())
require(dryrun['status'] == 'CURRENT_OWNER_NORMAL_STOP_DRY_RUN_READY' and dryrun['stop_submitted'] is False, 'Original dry-run did not pass')
print(json.dumps(dict(status='PRESTOP_ORIGINAL_HISTORY_BOUND_AND_DEFAULT_DRY_RUN_PASSED',
                     history_expected=history, history_expected_pin=history_pin, original_dryrun=dryrun,
                     normal_stop_expected_pin=normal_expected_pin,
                     run_config_native_unit=native['source_unit_sha256'], run_config_native_library_sha256=native['library_sha256'],
                     source_manifest_pin=expected['source_closure']['native_python_manifest'],
                     camera_stop_sent=False, Native_checkpoint_seed_counter_marker_written=False), sort_keys=True))
