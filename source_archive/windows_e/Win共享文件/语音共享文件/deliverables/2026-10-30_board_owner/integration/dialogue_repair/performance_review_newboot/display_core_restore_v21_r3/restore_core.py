"""Restore the saved core screen-saver timeout, then observe the paused UI passively."""
import ctypes as C
import time

import query_display as query
import read_only_guard as guard
import xcb_screensaver as xcb


POLICY_SHA = 'a39849aeb1fe7b69776efefd05c9f258c22438b203202d529d0238c7d188e23c'
BEFORE = dict(screen_saver=guard.TEMPORARY, dpms_enabled=True, dpms_level=0,
              dpms_timeouts=[600, 600, 600], xss_state=3, xss_kind=0)


def validate_before(value):
    guard.need(all(value.get(key) == expected for key, expected in BEFORE.items())
        and value.get('dpms_enabled') is True, 'ACTUAL_MIXED_POLICY_CHANGED')


def restore_and_observe(session, live_guard, persist, result, finish,
                        clock=time.monotonic, sleep=time.sleep):
    # Resolve all three existing Xlib symbols before any mutation.
    xcb.signature(session.x, 'XSetScreenSaver', [C.c_void_p, C.c_int, C.c_int, C.c_int, C.c_int])
    xcb.signature(session.x, 'XResetScreenSaver', [C.c_void_p])
    xcb.signature(session.x, 'XSync', [C.c_void_p, C.c_int])
    live_guard()
    before = session.query()
    validate_before(before)
    result.update(status='CORE_RESTORE_INTENT_SAVED', before=before,
                  core_policy_write_attempted=False, initial_reset_calls=0,
                  passive_observer_reset_calls=0, dpms_write_calls=0)
    persist(result)
    live_guard()
    result['core_policy_write_attempted'] = True
    values = guard.ORIGINAL
    session.x.XSetScreenSaver(session.display, values['timeout'], values['interval'],
                              values['prefer_blank'], values['allow_exposures'])
    session.x.XResetScreenSaver(session.display)
    result['initial_reset_calls'] = 1
    session.x.XSync(session.display, 0)
    after = session.query()
    query.validate_policy(after, 'original')
    result.update(status='ORIGINAL_CORE_POLICY_RESTORED', after=after, core_policy_last_verified='ORIGINAL')
    persist(result)
    result.update(query.collect(session, live_guard, 'original', 30, clock, sleep))
    finish()
    result['status'] = ('ORIGINAL_POLICY_RESTORED_PAUSED_KEEPALIVE_OBSERVED'
                        if result['observed_periodic_idle_resets'] else 'ORIGINAL_POLICY_RESTORED_KEEPALIVE_UNCONFIRMED')
    persist(result)
    return result


def execute(arguments):
    result = dict(status='CORE_RESTORE_STARTED', startup_sha256=guard.STARTUP_SHA,
        microphone_control_sent=False, audio_played=False, production_database_opened=False,
        dpms_write_calls=0, initial_reset_calls=0, passive_observer_reset_calls=0,
        core_policy_write_attempted=False, external_input_not_excluded=True,
        core_policy_last_verified='UNKNOWN', fallback_policy_mutation=False)
    session = None
    owned = False
    path = guard.CONTROL / ('temporary-display-v21-core-restore-' + str(arguments['token']) + '.json')
    try:
        guard.need(type(arguments['token']) is int and arguments['token'] > 0, 'VALID_RECEIPT_TOKEN_REQUIRED')
        guard.need(not path.exists(), 'NEW_RECEIPT_PATH_REQUIRED')
        owned = True
        expected = guard.full_guard(arguments)
        evidence = arguments['current_policy_evidence']['result']
        guard.need(evidence.get('status') == 'READONLY_CURRENT_X_POLICY'
            and evidence.get('owners') == expected == evidence.get('final_owners')
            and evidence.get('policy_modified') is False and evidence.get('observer_reset_calls') == 0,
            'ROOT_ACTUAL_POLICY_EVIDENCE_CHANGED')
        validate_before(evidence['sample'])
        raw = guard.bounded(guard.POLICY_PATH, 8192)
        guard.need(guard.sha(raw) == POLICY_SHA, 'SAVED_ORIGINAL_POLICY_CHANGED')
        guard.policy(raw)
        result.update(owners=expected, policy_file_sha256=POLICY_SHA,
            current_policy_evidence_sha256=arguments['current_policy_evidence_sha256'],
            observed_mono=time.monotonic(), remote_receipt_path=str(path))
        session = xcb.ReadOnlyXSession(guard.helper_module(arguments['spec']))
        def finish():
            guard.need(guard.full_guard(arguments) == expected, 'FINAL_SEALED_OWNER_CHANGED')
            guard.need(guard.sha(guard.bounded(guard.POLICY_PATH, 8192)) == POLICY_SHA,
                       'SAVED_ORIGINAL_POLICY_CHANGED')
            result['full_component_checks'] = [380, 380]
        result = restore_and_observe(session, lambda: guard.paused_guard(expected),
            lambda value: guard.save_receipt(path, value), result, finish)
    except BaseException as error:
        result.update(status='CORE_RESTORE_OR_OBSERVATION_FAILED', failure=query.metadata(error))
    finally:
        if session is not None:
            session.close()
    if owned:
        guard.save_receipt(path, result)
    return result
