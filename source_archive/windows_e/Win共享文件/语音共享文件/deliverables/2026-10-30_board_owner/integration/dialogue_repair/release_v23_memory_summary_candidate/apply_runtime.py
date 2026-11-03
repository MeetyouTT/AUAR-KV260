"""The existing guarded transaction, restricted to two memory sources."""
import ast
import base64
import contextlib


def apply_summary():
    boot()
    j = journal()
    inactive(j)
    need(j.get('phase') in ('NORMAL_CLOSED', 'SUMMARY_SOURCE_INTENT') and j.get('boot_id') == SPEC['boot_id']
         and j.get('guard_removed') is False and j.get('active_root') == EXACT_TARGET
         and c.show()['ActiveState'] == 'inactive', 'normal_closed_guarded_sameboot_required')
    root = Path(EXACT_TARGET)
    revision = SPEC['summary_revision']
    stage = Path(revision['stage'])
    backup = stage / 'before'
    selected = revision['payload']['sources']
    need(stage.parent == CONTROL and set(selected) == set(SOURCE_PATHS) == set(BASE_SOURCE_PINS)
         and set(PAYLOAD) == set(selected), 'exact_two_selected_memory_sources_required')
    new_sources = {}
    for relative in SOURCE_PATHS:
        row = selected[relative]
        need({key: value for key, value in PAYLOAD[relative].items() if key != 'base64'} == row
             and row['before_sha256'] == BASE_SOURCE_PINS[relative], 'payload_does_not_match_root_selection')
        raw = base64.b64decode(PAYLOAD[relative]['base64'], validate=True)
        need(0 < len(raw) < 2097152 and c.sha(raw) == row['sha256'], 'selected_source_bytes_changed')
        ast.parse(raw, feature_version=(3, 9))
        new_sources[relative] = raw
    payload_sha = c.sha(c.encoded({relative: row['sha256'] for relative, row in selected.items()}))
    identity = dict(name=REVISION, stage=str(stage), payload_sha256=payload_sha)
    existing = j.get('summary_revision')
    if existing is not None:
        need(all(existing.get(key) == value for key, value in identity.items())
             and existing.get('state') in ('INTENT', 'APPLIED'), 'other_summary_transaction_present')
    if j['phase'] == 'SUMMARY_SOURCE_INTENT':
        need(existing is not None and existing['state'] == 'INTENT', 'exact_summary_intent_required')
    elif existing is not None:
        need(existing['state'] == 'APPLIED', 'completed_summary_marker_required')
    need(j.get('camera_rebind', {}).get('state') == 'APPLIED'
         and j['camera_rebind'].get('stage') == SPEC['camera_rebind']['stage'], 'v22_camera_rebind_must_remain_applied')
    camera_tx = c.parse(c.read(Path(SPEC['camera_rebind']['stage']) / 'transaction.json',
                              j['camera_rebind']['transaction_sha256']))
    need(camera_tx.get('applied_spec_sha256') == BASE_SPEC_SHA, 'original_camera_transaction_changed')
    for relative, pin in BASE_PINS.items():
        if relative not in selected:
            c.read(root / 'runtime/aura' / c.relative(relative), pin)
    c.read(root / 'startup/launcher.py', LAUNCHER_SHA)
    reviewed_face()
    saved_pause()
    private = Path('/home/root/.local/share/aura-board-business')
    leases = [Path('/run/aura-avatar-ui.lock'), private / 'writer.lock', private / 'speaker/speaker-writer.lock']
    with contextlib.ExitStack() as stack:
        for path in leases:
            descriptor = os.open(str(path), os.O_RDWR | os.O_NOFOLLOW)
            stream = stack.enter_context(os.fdopen(descriptor, 'r+b'))
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        ownerless(c.show())
        guarded(j)
        reviewed_face()
        saved_pause()
        paths = [str(root / 'runtime/aura' / relative) for relative in SOURCE_PATHS]
        paths += [str(root / 'startup/config.json'), str(root / 'production_source_manifest.json')]
        old_hashes = dict(zip(paths, [BASE_SOURCE_PINS[relative] for relative in SOURCE_PATHS]
                             + [BASE_STARTUP_SHA, BASE_MANIFEST_SHA]))
        names = ('memory-core.py', 'memory-policy.py', 'startup-config.json', 'production-source-manifest.json')
        if existing is None:
            old = {path: c.read(path, old_hashes[path]) for path in paths}
        else:
            old = {path: c.read(backup / name, old_hashes[path]) for path, name in zip(paths, names)}
        need(c.parse(old[paths[2]]) == BASE_STARTUP, 'exact_v22_startup_backup_required')
        gui = c.read(root / 'runtime/aura/config/board_avatar_gtk.json', BASE_CONFIG_SHA)
        need(c.parse(gui) == EXPECTED_GUI and c.read(CONFIGURATION_PATH, BASE_CONFIG_SHA) == gui,
             'v22_gui_and_external_configuration_must_match')
        manifest = c.parse(old[paths[3]])
        need(manifest['component_pins'] == BASE_PINS and manifest['configuration_sha256'] == BASE_CONFIG_SHA
             and manifest['configuration_path'] == CONFIGURATION_PATH, 'original_manifest_closure_required')
        sys.path.insert(0, str(root / 'runtime/aura'))
        from common.board_production_bootstrap import verify_production_bootstrap
        cfg = EXPECTED_GUI['board_business']
        proof = verify_production_bootstrap(private, cfg['bootstrap_receipt'], cfg['bootstrap_receipt_sha256'])
        need(proof['profiles_migration_verified'] is True, 'original_four_database_bootstrap_required')
        new_startup = c.encoded(EXPECTED_STARTUP)
        need(c.sha(new_startup) == SPEC['startup_sha256'], 'selected_startup_bytes_changed')
        manifest['component_pins'] = SPEC['component_sha256']
        for relative, raw in new_sources.items():
            manifest['files']['runtime/aura/' + relative] = dict(sha256=c.sha(raw), bytes=len(raw))
        manifest['files']['startup/config.json'] = dict(sha256=c.sha(new_startup), bytes=len(new_startup))
        manifest['summary_revision'] = dict(identity, previous_startup_sha256=BASE_STARTUP_SHA,
            previous_manifest_sha256=BASE_MANIFEST_SHA, previous_source_sha256=BASE_SOURCE_PINS,
            configuration_sha256=BASE_CONFIG_SHA, private_data_replayed=False)
        new_manifest = c.encoded(manifest)
        completed = dict(SPEC, source_manifest_sha256=c.sha(new_manifest),
                         summary_revision=dict(revision, state='APPLIED'))
        new = dict(zip(paths, [new_sources[relative] for relative in SOURCE_PATHS] + [new_startup, new_manifest]))
        transaction = dict(identity, old_sha256=old_hashes,
                           new_sha256={path: c.sha(raw) for path, raw in new.items()},
                           applied_spec_sha256=c.sha(c.encoded(completed)))
        transaction_sha = c.sha(c.encoded(transaction))
        if existing is not None:
            need(existing.get('transaction_sha256') == transaction_sha, 'summary_transaction_changed_on_retry')
        private_directory(stage)
        private_directory(backup)
        for path, name in zip(paths, names):
            exact_file(backup / name, old[path])
        exact_file(backup / 'gui-config.json', gui)
        if existing is None:
            exact_file(backup / 'publication-state.json', c.read(STATE))
        else:
            prior = c.parse(c.read(backup / 'publication-state.json'))
            need(prior['phase'] == 'NORMAL_CLOSED' and prior['guard_removed'] is False
                 and prior.get('summary_revision') is None, 'original_normal_close_backup_required')
        for relative, name in zip(SOURCE_PATHS, ('prepared-memory.py', 'prepared-policy.py')):
            exact_file(stage / name, new_sources[relative])
        exact_file(stage / 'prepared-startup.json', new_startup)
        exact_file(stage / 'prepared-manifest.json', new_manifest)
        exact_file(stage / 'applied-spec.json', c.encoded(completed))
        exact_file(stage / 'transaction.json', c.encoded(transaction))
        fsync_directory(backup)
        fsync_directory(stage)
        fsync_directory(CONTROL)
        if existing is None:
            j.update(phase='SUMMARY_SOURCE_INTENT', summary_revision=dict(identity, state='INTENT',
                     transaction_sha256=transaction_sha), target_startup_sha256=SPEC['startup_sha256'])
            save(j)

        def transaction_guard():
            need(journal() == j, 'publication_journal_changed_during_summary_update')
            guarded(j)
            ownerless(c.show())
            saved_pause()
            reviewed_face()
            c.read(stage / 'transaction.json', transaction_sha)
            need(c.read(CONFIGURATION_PATH, BASE_CONFIG_SHA) == gui, 'external_gui_configuration_changed')
            for relative, pin in BASE_PINS.items():
                if relative not in selected:
                    c.read(root / 'runtime/aura' / c.relative(relative), pin)

        roll_forward(paths, old_hashes, new, read=c.read, replace=atomic, guard=transaction_guard)
        SPEC.update(completed)
        source()
        guarded(j)
        ownerless(c.show())
        saved_pause()
        need(c.read(root / 'runtime/aura/config/board_avatar_gtk.json', BASE_CONFIG_SHA) == gui
             and c.read(CONFIGURATION_PATH, BASE_CONFIG_SHA) == gui, 'gui_changed_during_summary_update')
        j.update(phase='NORMAL_CLOSED', summary_revision=dict(identity, state='APPLIED', transaction_sha256=transaction_sha),
                 target_startup_sha256=SPEC['startup_sha256'], target_pins=380)
        save(j)
    return dict(status='SUMMARY_MEMORY_SOURCES_APPLIED_UI_STOPPED', spec=completed,
                source_files={relative: row['sha256'] for relative, row in selected.items()}, component_pins=380,
                changed_component_count=2, unchanged_component_count=378, transaction_sha256=transaction_sha,
                backup_directory=str(backup), production_bootstrap_verified=True, profiles_migration_verified=True,
                gui_configuration_bytes_unchanged=True, face_readback_unchanged=True,
                private_data_replayed=False, ui_started=False, service_stop_or_kill=False, listening_preference_changed=False)


with open('/run/aura-production-publisher.lock', 'a') as lock:
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    result = apply_summary()
print(json.dumps(result, ensure_ascii=True))
