def validate_original_operator_migration(expected, snapshot, native, intent):
    """Accept only the pinned original RAM migration, never a rewritten config."""
    if native.get('source_unit_sha256') == SOURCE_UNIT:
        return
    operator = Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/native-operator-v1')
    old_unit = '29786434df9bb9b94a8e640a7a48db47019c224d3876037ce27d3467bb2f5512'
    old_library_sha = 'c675ba698d45acd8742e52403e6186f43dc56d7d313d0e740896b19412bde656'
    new_library_sha = '704f561a50b5f0fb8f9b4cf72c024acce0cdafd888cad0784507f484518fc224'
    require(native.get('source_unit_sha256') == old_unit and native.get('library_sha256') == old_library_sha,
            'Unknown config unit/library is not the approved original migration')
    observation = snapshot.pinned(expected['original_operator_migration_pin'])
    require(observation['schema'] == 'aura-original-operator-config-migration-observation-1'
            and observation['boot_id'] == expected['boot_id']
            and observation['source_owner'] == expected['camera_owner']
            and observation['owner_run_config_pin'] == expected['owner_run_config_pin']
            and type(observation['observed_mono_ns']) is int
            and 0 < observation['observed_mono_ns'] < intent['stop_intent_mono_ns']
            and observation['metadata_observation_only'] is True
            and observation['original_migration_or_Native_code_executed_by_this_observer'] is False,
            'Original migration observation is not from this owner before normal stop')
    def read_bytes(entry):
        pin(entry)
        raw = snapshot.read(entry['path'])
        require(sha(raw) == entry['sha256'], 'Original migration source bytes differ')
        return raw
    runtime_pin = observation['native_operator_manifest_pin']
    require(runtime_pin == {'path': str(operator / 'runtime-manifest.json'),
                            'sha256': '74e011db30a9d943a9512f7648190ac0c01060af06df1280d1e8ea006dc882ad'},
            'Original operator runtime manifest differs')
    runtime = snapshot.pinned(runtime_pin)
    require(runtime['schema'] == 'aura-native-operator-runtime-1' and len(runtime['files']) == 7,
            'Original seven-member migration closure required')
    for path, checksum in runtime['files'].items():
        read_bytes({'path': path, 'sha256': checksum})
    fixed_sources = {
        str(operator / 'native_entry_operator.py'): '0576a388e2c17174b4102665602aa42fbf078a3f016bdfb641c269571ce13943',
        str(operator / 'identity_recovery.py'): '64831498d8497c2087b3bb1543367e8cc1917ca131694000884f2d58e60990f7',
    }
    require(observation['original_migration_sources'] == fixed_sources
            and all(runtime['files'].get(path) == checksum for path, checksum in fixed_sources.items()),
            'Original entry/RAM-migration source differs')
    settings_pin = observation['settings_pin']
    require(settings_pin['path'] == str(operator / 'settings.json')
            and runtime['files'].get(settings_pin['path']) == settings_pin['sha256'],
            'Original migration settings are not in the pinned runtime')
    settings = snapshot.pinned(settings_pin)
    require(native['library'] == settings['old_library'] and native['library_sha256'] == settings['old_library_sha256'] == old_library_sha
            and native['source_unit_sha256'] == settings['predecessor_unit_sha256'] == old_unit
            and settings['unit_sha256'] == SOURCE_UNIT
            and settings['library'] == str(operator / 'libaura_native_operator.so')
            and settings['library_sha256'] == new_library_sha,
            'Original approved migration input/output tuple differs')
    read_bytes({'path': settings['old_library'], 'sha256': old_library_sha})
    unit_pin = observation['native_c_unit_manifest_pin']
    require(unit_pin == {'path': str(operator / 'source-manifest.json'), 'sha256': SOURCE_UNIT}, 'Original six-member C unit differs')
    unit = snapshot.pinned(unit_pin)
    require(unit['schema'] == 'aura-native-operator-source-unit-1' and unit['existing_abi'] == 2 and len(unit['files']) == 6,
            'Original C ABI/source member set differs')
    for path, checksum in unit['files'].items():
        relative = Path(path)
        require(not relative.is_absolute() and '..' not in relative.parts, 'Original C source path escapes')
        read_bytes({'path': str(operator / relative), 'sha256': checksum})
    library_pin = observation['native_library_pin']
    require(library_pin == {'path': settings['library'], 'sha256': new_library_sha}, 'Actual original migrated library differs')
    read_bytes(library_pin)
    audit_pin = observation['original_audit_pin']
    require(audit_pin['path'] == str(operator / ('recovery-audit-' + str(expected['camera_owner']['pid']) + '.json')),
            'Original migration audit is not this owner')
    audit = snapshot.pinned(audit_pin)
    handoff = observation['original_live_handoff_migration']
    require(audit['audit_path'] == audit_pin['path'] and audit['request'] == settings
            and audit['artificial_counter_reset'] is False and type(audit['mechanical_actions']) is int and audit['mechanical_actions'] == 0
            and audit['checkpoint_sha256'] == native['seed']['sha256']
            and audit['checkpoint_unit_sha256'] in (old_unit, SOURCE_UNIT)
            and audit['exact_seed_before_operator_request']['boot_id'] == expected['boot_id']
            and handoff['operator_recovery_audit'] == audit_pin['path']
            and handoff['native_abi_compatible_migration'] is True
            and handoff['predecessor_unit_sha256'] == audit['checkpoint_unit_sha256']
            and handoff['native_unit_sha256'] == SOURCE_UNIT
            and observation['mapped_original_operator_library'] == settings['library'],
            'Original audit and observed live migration linkage differs')
