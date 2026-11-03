"""Remote body, appended to the pinned publisher definitions by the local CLI."""
import contextlib


def exact_file(path, raw):
    path = Path(path)
    if path.exists():
        need(c.read(path) == raw, 'existing_prepared_artifact_changed')
    else:
        c.create(path, raw)


def private_directory(path):
    path = Path(path)
    if not path.exists():
        path.mkdir(mode=0o700)
    info = path.stat()
    need(path.resolve() == path and not path.is_symlink() and path.is_dir()
         and info.st_uid == os.geteuid() and not info.st_mode & 0o077, 'private_transaction_directory_required')


def fsync_directory(path):
    descriptor = os.open(str(path), os.O_DIRECTORY | os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def saved_pause():
    value = c.parse(c.read('/home/root/.local/share/aura-board-business/listening_preference.json'))
    need(set(value) == {'version', 'enabled'} and type(value['version']) is int
         and value['version'] == 1 and value['enabled'] is False, 'saved_user_pause_required')


def apply_rebind():
    boot()
    j = journal()
    inactive(j)
    need(j.get('phase') in ('NORMAL_CLOSED', 'CAMERA_REBIND_INTENT')
         and j.get('boot_id') == SPEC['boot_id'] and j.get('guard_removed') is False
         and j.get('active_root') == EXACT_TARGET and c.show()['ActiveState'] == 'inactive',
         'normal_closed_guarded_sameboot_required')
    root = Path(EXACT_TARGET)
    stage = Path(SPEC['camera_rebind']['stage'])
    backup = stage / 'before'
    need(stage.parent == CONTROL and str(stage / 'prepared-gui.json') == SPEC['minor_prepared_configuration_path'],
         'exact_rebind_stage_required')
    binding_sha = c.sha(c.encoded(SPEC['camera_rebind']['binding']))
    identity = dict(revision=REVISION, stage=str(stage), binding_sha256=binding_sha)
    existing = j.get('camera_rebind')
    if existing is not None:
        need(all(existing.get(key) == value for key, value in identity.items())
             and existing.get('state') in ('INTENT', 'APPLIED'), 'other_camera_rebind_transaction_present')
    if j['phase'] == 'CAMERA_REBIND_INTENT':
        need(existing is not None and existing['state'] == 'INTENT', 'exact_transaction_intent_required')
    elif existing is not None:
        need(existing['state'] == 'APPLIED', 'completed_rebind_marker_required')

    # All business Python and resources are unchanged. Validate before importing
    # the bootstrap module, including the original three cold-start fixes.
    for relative, pin in BASE_PINS.items():
        if relative != CONFIG_RELATIVE:
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

        paths = [str(root / 'runtime/aura' / CONFIG_RELATIVE), str(root / 'startup/config.json'),
                 str(root / 'production_source_manifest.json')]
        old_hashes = dict(zip(paths, (BASE_CONFIG_SHA, BASE_STARTUP_SHA, BASE_MANIFEST_SHA)))
        if existing is None:
            old = {path: c.read(path, old_hashes[path]) for path in paths}
        else:
            old = {path: c.read(backup / name, old_hashes[path]) for path, name in
                   zip(paths, ('gui-config.json', 'startup-config.json', 'production-source-manifest.json'))}
        need(c.parse(old[paths[0]]) == BASE_GUI and c.parse(old[paths[1]]) == BASE_STARTUP,
             'exact_v21_backup_configuration_required')
        manifest = c.parse(old[paths[2]])
        need(manifest['component_pins'] == BASE_PINS and manifest['configuration_sha256'] == BASE_CONFIG_SHA
             and manifest['configuration_path'] == OLD_EXTERNAL_PATH, 'original_manifest_closure_required')
        external = c.read(OLD_EXTERNAL_PATH, BASE_CONFIG_SHA)
        need(external == old[paths[0]], 'original_external_configuration_changed')
        sys.path.insert(0, str(root / 'runtime/aura'))
        from common.board_production_bootstrap import verify_production_bootstrap
        cfg = EXPECTED_GUI['board_business']
        proof = verify_production_bootstrap(private, cfg['bootstrap_receipt'], cfg['bootstrap_receipt_sha256'])
        need(proof['profiles_migration_verified'] is True, 'original_four_database_bootstrap_required')
        new_gui = c.encoded(EXPECTED_GUI)
        new_startup = c.encoded(EXPECTED_STARTUP)
        need(c.sha(new_gui) == SPEC['configuration_sha256']
             and c.sha(new_startup) == SPEC['startup_sha256'], 'new_configuration_bytes_changed')
        manifest['component_pins'] = SPEC['component_sha256']
        manifest['configuration_sha256'] = SPEC['configuration_sha256']
        manifest['configuration_path'] = SPEC['minor_prepared_configuration_path']
        manifest['files']['runtime/aura/' + CONFIG_RELATIVE] = dict(sha256=c.sha(new_gui), bytes=len(new_gui))
        manifest['files']['startup/config.json'] = dict(sha256=c.sha(new_startup), bytes=len(new_startup))
        manifest['camera_owner_rebind'] = dict(identity, previous_startup_sha256=BASE_STARTUP_SHA,
            previous_manifest_sha256=BASE_MANIFEST_SHA, previous_configuration_sha256=BASE_CONFIG_SHA,
            previous_configuration_path=OLD_EXTERNAL_PATH, camera_owner=SPEC['camera_owner'],
            face_readback=SPEC['face_readback'], observation_sha256=SPEC['camera_rebind']['binding']['written_proof']['observation_sha256'])
        new_manifest = c.encoded(manifest)
        completed = dict(SPEC, source_manifest_sha256=c.sha(new_manifest),
                         camera_rebind=dict(SPEC['camera_rebind'], state='APPLIED'))
        new = dict(zip(paths, (new_gui, new_startup, new_manifest)))
        transaction = dict(identity, old_sha256=old_hashes,
                           new_sha256={path: c.sha(raw) for path, raw in new.items()},
                           applied_spec_sha256=c.sha(c.encoded(completed)))
        transaction_sha = c.sha(c.encoded(transaction))
        if existing is not None:
            need(existing.get('transaction_sha256') == transaction_sha, 'resumed_transaction_bytes_changed')
        private_directory(stage)
        private_directory(backup)
        for path, name in zip(paths, ('gui-config.json', 'startup-config.json', 'production-source-manifest.json')):
            exact_file(backup / name, old[path])
        exact_file(backup / 'external-gui-config.json', external)
        if existing is None:
            exact_file(backup / 'publication-state.json', c.read(STATE))
        else:
            prior = c.parse(c.read(backup / 'publication-state.json'))
            need(prior['phase'] == 'NORMAL_CLOSED' and prior['guard_removed'] is False
                 and prior.get('camera_rebind') is None, 'original_normal_close_backup_required')
        exact_file(stage / 'prepared-gui.json', new_gui)
        exact_file(stage / 'prepared-startup.json', new_startup)
        exact_file(stage / 'prepared-manifest.json', new_manifest)
        exact_file(stage / 'applied-spec.json', c.encoded(completed))
        exact_file(stage / 'transaction.json', c.encoded(transaction))
        fsync_directory(backup)
        fsync_directory(stage)
        fsync_directory(CONTROL)
        if existing is None:
            j.update(phase='CAMERA_REBIND_INTENT', camera_rebind=dict(identity, state='INTENT',
                     transaction_sha256=transaction_sha), target_startup_sha256=SPEC['startup_sha256'])
            save(j)

        def transaction_guard():
            current = journal()
            need(current == j, 'publication_journal_changed_during_rebind')
            guarded(current)
            ownerless(c.show())
            saved_pause()
            reviewed_face()
            need(c.read(OLD_EXTERNAL_PATH, BASE_CONFIG_SHA) == external, 'old_external_configuration_modified')
            c.read(stage / 'transaction.json', transaction_sha)
            for relative, pin in BASE_PINS.items():
                if relative != CONFIG_RELATIVE:
                    c.read(root / 'runtime/aura' / c.relative(relative), pin)

        roll_forward(paths, old_hashes, new, read=c.read, replace=atomic, guard=transaction_guard)
        SPEC.update(completed)
        source()
        guarded(j)
        ownerless(c.show())
        saved_pause()
        need(c.read(SPEC['minor_prepared_configuration_path'], SPEC['configuration_sha256']) == new_gui,
             'prepared_configuration_copy_disagrees')
        need(c.read(OLD_EXTERNAL_PATH, BASE_CONFIG_SHA) == external, 'original_external_provenance_changed')
        j.update(phase='NORMAL_CLOSED', camera_rebind=dict(identity, state='APPLIED',
                 transaction_sha256=transaction_sha), target_startup_sha256=SPEC['startup_sha256'], target_pins=380)
        save(j)
    return dict(status='CAMERA_OWNER_REBOUND_UI_STOPPED', spec=completed,
                configuration_sha256=SPEC['configuration_sha256'], configuration_path=SPEC['minor_prepared_configuration_path'],
                source_files={CONFIG_RELATIVE: SPEC['configuration_sha256']}, component_pins=380,
                changed_component_count=1, unchanged_component_count=379, transaction_sha256=transaction_sha,
                backup_directory=str(backup), previous_configuration_path=OLD_EXTERNAL_PATH,
                previous_configuration_preserved=True, production_bootstrap_verified=True,
                profiles_migration_verified=True, private_data_replayed=False, ui_started=False,
                service_stop_or_kill=False, listening_preference_changed=False)


with open('/run/aura-production-publisher.lock', 'a') as lock:
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    result = apply_rebind()
print(json.dumps(result, ensure_ascii=True))
