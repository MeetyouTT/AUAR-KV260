"""Finite passive XCB screen-saver observations under the sealed paused v21 owners."""
import json
import time

import read_only_guard as guard
import xcb_screensaver as xcb


def metadata(error):
    if isinstance(error, (guard.Refused, xcb.Refused)):
        return dict(code=str(error), exception_class='Refused')
    return guard.error_metadata(error)


def validate_policy(value, expected):
    original = expected == 'original'
    guard.need(expected in ('original', 'temporary'), 'EXPECTED_POLICY_REQUIRED')
    guard.need(value['screen_saver'] == (guard.ORIGINAL if original else guard.TEMPORARY)
        and value['dpms_enabled'] is original and value['dpms_timeouts'] == [600, 600, 600],
        'READONLY_POLICY_OBSERVATION_MISMATCH')
    guard.need(value['dpms_level'] == 0 and value['xss_state'] in ((0,) if original else (0, 3)),
               'DISPLAY_NOT_AWAKE')


def collect(session, live_guard, expected_policy, seconds, clock=time.monotonic, sleep=time.sleep):
    guard.need(type(seconds) is int and seconds in (0, 30), 'BOUNDED_OBSERVATION_REQUIRED')
    started = clock()
    samples = []
    for index in range(seconds + 1):
        sleep(max(0., started + index - clock()))
        guard.need(clock() - started <= seconds + 8., 'READONLY_OBSERVATION_DEADLINE')
        live = live_guard()
        value = session.query()
        validate_policy(value, expected_policy)
        samples.append(dict(elapsed_seconds=clock() - started, **value, **live))
    drops = [sample['elapsed_seconds'] for before, sample in zip(samples, samples[1:])
             if before['xss_idle_ms'] - sample['xss_idle_ms'] >= 1000]
    return dict(samples=samples, idle_drop_count=len(drops), idle_drop_times_seconds=drops,
                max_idle_ms=max(sample['xss_idle_ms'] for sample in samples),
                observed_periodic_idle_resets=seconds == 30 and len(drops) >= 4
                    and all(sample['xss_idle_ms'] <= 7500 for sample in samples))


def execute(arguments):
    result = dict(status='READONLY_QUERY_STARTED', action=arguments['action'],
        startup_sha256=guard.STARTUP_SHA, policy_modified=False, observer_reset_calls=0,
        microphone_control_sent=False, audio_played=False, production_database_opened=False,
        libxss_required=False, backend='libxcb_MIT_SCREEN_SAVER', expected_policy=arguments['expected_policy'])
    session = None
    owned = False
    path = guard.CONTROL / ('temporary-display-v21-xcb-query-' + str(arguments['token']) + '.json')
    try:
        guard.need(type(arguments['token']) is int and arguments['token'] > 0, 'VALID_RECEIPT_TOKEN_REQUIRED')
        guard.need(not path.exists(), 'NEW_RECEIPT_PATH_REQUIRED')
        owned = True
        expected = guard.full_guard(arguments)
        raw = guard.bounded(guard.POLICY_PATH, 8192)
        guard.policy(raw)
        result.update(owners=expected, policy_file_sha256=guard.sha(raw), observed_mono=time.monotonic(),
                      remote_receipt_path=str(path))
        guard.save_receipt(path, result)
        session = xcb.ReadOnlyXSession(guard.helper_module(arguments['spec']))
        guard.need(arguments['action'] in ('preflight', 'observe'), 'READONLY_ACTION_REQUIRED')
        seconds = 0 if arguments['action'] == 'preflight' else 30
        result.update(collect(session, lambda: guard.paused_guard(expected), arguments['expected_policy'], seconds))
        guard.need(guard.full_guard(arguments) == expected, 'FINAL_SEALED_OWNER_CHANGED')
        result.update(status='XCB_READONLY_PREFLIGHT_PASS' if seconds == 0 else 'XCB_READONLY_OBSERVATION_COMPLETE',
            full_component_checks=[380, 380], extension_major_opcode=session.xcb.major_opcode,
            server_version=session.xcb.version, policy_left=arguments['expected_policy'],
            core_screen_saver_state_observed=True, external_input_not_excluded=True)
    except BaseException as error:
        result.update(status='READONLY_QUERY_REFUSED_OR_FAILED', failure=metadata(error))
    finally:
        if session is not None:
            session.close()
    if owned:
        guard.save_receipt(path, result)
    return result
