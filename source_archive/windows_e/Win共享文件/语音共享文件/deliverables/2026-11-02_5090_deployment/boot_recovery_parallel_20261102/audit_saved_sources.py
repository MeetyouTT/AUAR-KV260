"""Read saved public source/metadata only; write evidence in this task directory."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
SOURCE = BASE / 'parallel_platform_review/sources'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def save(relative, raw):
    target = HERE / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)
    return str(target.relative_to(HERE)).replace('\\', '/')


def load(relative):
    value = json.loads((BASE / relative).read_text(encoding='utf-8-sig'))
    return value.get('board_result', value)


def main():
    rows = []
    source_index = json.loads((BASE / 'parallel_platform_review/source_index.json').read_text(encoding='utf-8-sig'))
    for prefix, remote in [
        ('platform_readonly_01', '/lib/systemd/system/dfx-mgr.service'),
        ('platform_readonly_01', '/etc/dfx-mgrd/daemon.conf'),
        ('platform_readonly_01', '/etc/dfx-mgrd/default_firmware'),
        ('startup_sources_readonly_04', '/usr/bin/xlnx-firmware-detect'),
        ('startup_sources_readonly_04', '/etc/dfx-mgrd/kv260-benchmark-b4096'),
        ('startup_sources_readonly_04', '/etc/systemd/system/kv260-repaired-zocl.service'),
        ('startup_sources_readonly_04', '/usr/local/lib/kv260-runtime-repair/load-repaired-zocl.sh'),
    ]:
        cached = SOURCE / (prefix + '__' + remote.replace('/', '__'))
        raw = cached.read_bytes()
        matches = [row for row in source_index if Path(row['local_path']).resolve() == cached.resolve()]
        if len(matches) != 1 or matches[0]['remote_path'] != remote or matches[0]['sha256'] != digest(raw):
            raise ValueError('Cached source bytes differ from the original saved remote hash: ' + remote)
        output = save('evidence/baseline' + remote, raw)
        rows.append(dict(remote_path=remote, cached_path=str(cached), sha256=digest(raw),
                         bytes=len(raw), snapshot=output, historical_boot_only=True,
                         saved_remote_sha256=matches[0]['sha256'], exact_cached_bytes_match_saved_remote_sha=True))

    platform = load('parallel_platform/platform_readonly_01.json')
    dependencies = {}
    for unit, saved in platform['units'].items():
        properties = dict(line.split('=', 1) for line in saved['show']['stdout'].splitlines() if '=' in line)
        keys = ('Id', 'Requires', 'Wants', 'After', 'Before', 'Restart', 'KillMode',
                'SendSIGKILL', 'TimeoutStopUSec', 'ExecStart', 'FragmentPath', 'DropInPaths')
        dependencies[unit] = {key: properties.get(key) for key in keys}
        save('evidence/merged_units/' + unit + '.cat.txt', saved['cat']['stdout'].encode())
        save('evidence/merged_units/' + unit + '.show.txt', saved['show']['stdout'].encode())
    save('evidence/default_loader_journal.txt', platform['dfx_journal']['stdout'].encode())
    save('evidence/original_list_package.txt', platform['xmutil_apps']['stdout'].encode())

    inventory = load('parallel_platform_review/loader_inventory_01.json')
    for remote in ('/etc/systemd/system/dfx-mgr.service.d/10-kv260-repaired.conf',
                   '/etc/systemd/system/dfx-mgr.service.d/20-kv260-dfx-state-repaired.conf'):
        entry = inventory['files'][remote]
        raw = entry['text'].encode()
        if digest(raw) != entry['sha256']:
            raise ValueError('Saved exact source digest differs')
        output = save('evidence/baseline' + remote, raw)
        rows.append(dict(remote_path=remote, sha256=digest(raw), bytes=len(raw), snapshot=output,
                         historical_boot_only=True))

    loader_sources = load('parallel_platform_review/loader_sources_01.json')['sources']
    json_config = [(path, v) for path, v in loader_sources.items()
                   if path.endswith('/src/sys/linux/json-config.c')]
    if len(json_config) != 1:
        raise ValueError('Saved loader parser source is ambiguous')
    remote, entry = json_config[0]
    parser_raw = entry['text'].encode()
    if digest(parser_raw) != entry['sha256']:
        raise ValueError('Loader parser source bytes differ')
    parser_copy = save('evidence/original_sources/json-config.c', parser_raw)

    references = [
        ('parallel_platform_review/sources/loader__ed9864fa6d__daemon_helper.c', 'daemon_helper.c'),
        ('parallel_platform_review/sources/loader__5809d26552__dfx-mgr-client.c', 'dfx-mgr-client.c'),
        ('maintenance_original_axis_20261101/launch_original_remove.py', 'launch_original_remove.py'),
        ('maintenance_original_axis_20261101/read_original_remove_result.py', 'read_original_remove_result.py'),
        ('maintenance_original_axis_20261101/launch_original_load.py', 'launch_original_load.py'),
        ('maintenance_original_axis_20261101/read_original_load_result.py', 'read_original_load_result.py'),
        ('maintenance_original_axis_20261101/launch_original_idstop.py', 'launch_original_idstop.py'),
        ('axis_follow_restore/original_sources/c9e91f74336c__bench_identity_stop.py', 'bench_identity_stop.py'),
        ('parallel_platform_review/checkpoint_readonly_call_recipe.py', 'checkpoint_readonly_call_recipe.py'),
    ]
    for relative, name in references:
        source = BASE / relative
        raw = source.read_bytes()
        rows.append(dict(role=name, cached_path=str(source), sha256=digest(raw), bytes=len(raw),
                         snapshot=save('evidence/original_sources/' + name, raw),
                         executed=False, old_boot_script_executable_as_is=False))

    reuse = {}
    for name in ('normal_stop_current_owner.py', 'validate_fresh_final_history_readonly.py'):
        path = BASE / 'cpu_optimization_20261102/camera' / name
        reuse[name] = dict(path=str(path), sha256=digest(path.read_bytes()),
                           copied_or_modified=False, executed=False,
                           scope='Reuse by current CPU/main owner with fresh arguments; never this offline task')

    facts = {
        'schema': 'aura-boot-recovery-saved-source-audit-1',
        'evidence_boot': platform['boot_id'], 'evidence_is_current_device_state': False,
        'sources': rows, 'effective_historical_dependencies': dependencies,
        'default_entry': {
            'vendor_prestart': '/usr/bin/xlnx-firmware-detect',
            'configuration': '/etc/dfx-mgrd/daemon.conf',
            'default_accel_pointer': '/etc/dfx-mgrd/default_firmware',
            'saved_value': 'kv260-benchmark-b4096',
            'parser_source': parser_copy,
            'parser_semantics': 'parse_config opens default_accel filename and scans the accelerator name',
            'daemon_semantics': 'dfx_init calls load_accelerator(config.defaul_accel_name) after package scan',
            'effective_daemon': '/usr/local/lib/kv260-dfx-state-repair-20261003/dfx-mgrd',
            'effective_daemon_saved_sha256': inventory['files']['/usr/local/lib/kv260-dfx-state-repair-20261003/dfx-mgrd']['sha256'],
            'note': 'No default_app setting was found in these saved configs; default_accel is the actual key.',
        },
        'dependency_findings': [
            'Effective saved camera unit has no Requires/After edge to dfx-mgr.service.',
            'Effective saved GUI unit has no Requires/After edge to camera or fresh source binding.',
            'dfx-mgr.service already requires/starts after the original repaired ZOCL unit.',
            'The existing Native camera entry has Restart=no, KillMode=process, SendSIGKILL=no, infinite stop timeout.',
            'After=dfx alone cannot prove automatic accelerator load completion; original client reply and dynamic platform must agree.',
        ],
        'candidate_decision': 'Retain existing defaults and daemon/ZOCL patches; one guarded original-client transition to wide before original camera, then rebind before original GUI launcher.',
        'unresolved_auxiliary_startup_source': {
            'unit': 'dpu-auto-config.service',
            'listed_in_saved_unit_inventory': 'dpu-auto-config.service' in platform['unit_files']['stdout'],
            'generated_unit_and_init_script_body_available': False,
            'candidate_response': 'Ordering-only After edge; fresh public source/ordering review or proven current absence required by capture; no enable/start action',
        },
        'cpu_adapters_reused_by_reference': reuse,
        'board_calls': 0, 'hardware_or_models_opened': False,
        'identity_db_audio_images_or_keys_opened': False,
    }
    save('evidence/SOURCE_AUDIT.json', (json.dumps(facts, ensure_ascii=False, indent=2) + '\n').encode())
    print(json.dumps(dict(status='SAVED_SOURCE_AUDIT_COMPLETE', source_rows=len(rows),
                          output=str(HERE / 'evidence/SOURCE_AUDIT.json'), board_calls=0)))


if __name__ == '__main__':
    main()
