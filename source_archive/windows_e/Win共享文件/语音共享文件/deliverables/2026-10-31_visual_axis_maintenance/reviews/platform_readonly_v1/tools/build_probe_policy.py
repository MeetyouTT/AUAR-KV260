"""Bind a local-only, read-only probe to reviewed v24 owners and fixed paths."""
from pathlib import Path, PurePosixPath
import hashlib
import json

REVIEW = Path(__file__).resolve().parents[1]
TASK = REVIEW.parents[1]
BUSINESS = TASK.parents[1]
OWNER = BUSINESS / 'deliverables/2026-10-30_board_owner/integration'
EVIDENCE = OWNER / 'dialogue_repair/release_v24_memory_followup_candidate/memory_followup_evidence'
WIDE = BUSINESS.parent / '协作任务/2026-10-28_整机联动与舵机范围/offline_wide'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main():
    supplied = TASK / 'evidence/root_readonly_v24_1793520246085075300.json'
    assert sha(supplied.read_bytes()) == 'ec2541900e745d39941d940e396deae0d11e606321a70b5b494323d5d4005b89'
    observed = read(supplied)
    assert observed['owners_freshly_verified'] is True and observed['component_count'] == 380
    assert observed['gui_source_matches_candidate_before_sha'] is True
    assert observed['firmware_kind'] == observed['vart_kind'] == 'UNKNOWN'
    mapping = read(EVIDENCE / 'source_mapping.json')
    assert sha((EVIDENCE / 'source_mapping.json').read_bytes()) == '6fb9899571078207b7460ae71d6da52ccd211c150b7d39f54f4003e672ec21c9'
    aura = PurePosixPath(mapping['root']) / 'runtime/aura'
    local = TASK / 'baseline/aura'
    manual = read(local / 'config/pan_manual.local.json')
    face = read(local / 'config/pan_face.local.json')
    controller_raw = (WIDE / 'manifests/controller-manifest.json').read_bytes()
    firmware_raw = (WIDE / 'manifests/candidate-manifest.json').read_bytes()
    assert sha(controller_raw) == face['manifest_sha256']
    assert sha(firmware_raw) == face['arguments']['manifest-sha256']
    controller, firmware = json.loads(controller_raw), json.loads(firmware_raw)
    files = []

    def add(role, path, digest, size=None, parse_json=False):
        assert str(path).startswith('/') and '..' not in PurePosixPath(str(path)).parts
        assert len(digest) == 64 and set(digest) <= set('0123456789abcdef')
        files.append(dict(index=len(files), role=role, path=str(path), sha256=digest,
                          bytes=size, parse_json=parse_json))

    def gui(role, rel, parse_json=False):
        raw = (local / rel).read_bytes()
        assert sha(raw) == mapping['component_pins'][rel]
        add(role, aura / rel, sha(raw), len(raw), parse_json)

    gui('GUI_FOLLOW_BEFORE', 'tools/face_pan_controls.py')
    gui('GUI_MANUAL_CONFIG', 'config/pan_manual.local.json', True)
    gui('GUI_FACE_CONFIG_COPY', 'config/pan_face.local.json', True)
    gui('GUI_DIRECTION_COPY', 'config/pan_direction.current.json', True)
    gui('GUI_MANUAL_ADAPTER', 'board/motion/manual_vsrv.py')
    gui('GUI_DRIVER_SOURCE', 'board/motion/vsrv_driver.py')
    gui('GUI_TRANSPORT_SOURCE', 'board/motion/vsrv_transport.py')
    add('EFFECTIVE_GUI_CONFIG', mapping['configuration_path'], mapping['configuration_sha256'])
    add('EFFECTIVE_FACE_CONFIG', manual['face_follow_config'],
        mapping['component_pins']['config/pan_face.local.json'],
        (local / 'config/pan_face.local.json').stat().st_size, True)
    add('EFFECTIVE_DIRECTION', face['arguments']['direction-evidence'],
        mapping['component_pins']['config/pan_direction.current.json'],
        (local / 'config/pan_direction.current.json').stat().st_size, True)
    add('CONTROLLER_MANIFEST', str(PurePosixPath(face['release_root']) / 'deployment-manifest.json'),
        sha(controller_raw), len(controller_raw), True)
    add('FIRMWARE_MANIFEST', face['arguments']['manifest'], sha(firmware_raw), len(firmware_raw), True)
    add('MANUAL_RELEASE_MANIFEST', manual['release_manifest'], manual['release_manifest_sha256'], None, True)
    for row in controller['files']:
        add('CONTROLLER_FILE', row['destination'], row['sha256'], row['bytes'])
    for path, digest in firmware['runtime_files'].items():
        add('WIDE_RUNTIME_FILE', path, digest)
    release = PurePosixPath(face['arguments']['manifest']).parent
    for name, digest in firmware['payload_files'].items():
        add('FIRMWARE_DRIVER_FILE', release / name, digest)
    add('CONTEXT_VALIDATOR_SOURCE', release / 'bench_identity_stop.py', firmware['bench_sha256'])
    policy = dict(schema='aura-axis-fixed-readonly-policy-1', revision='V24_FIXED_OWNERS',
        boot_id=mapping['boot_id'], startup_path=str(PurePosixPath(mapping['root']) / 'startup/config.json'),
        startup_sha256=mapping['startup_sha256'],
        owners=[dict(role=role.upper(), **mapping[role]) for role in ('camera', 'supervisor', 'gtk')],
        files=files,
        manual_driver_files=[dict(index=i, name=name,
            path=str(PurePosixPath(manual['release_manifest']).parent / name))
            for i, name in enumerate(('libvsrv.so', 'vsrv_driver.py', 'vsrv_transport.py'))],
        os_paths=dict(boot='/proc/sys/kernel/random/boot_id', fdt='/sys/firmware/fdt',
            firmware='/proc/device-tree/fpga-full/firmware-name',
            fpga_state='/sys/class/fpga_manager/fpga0/state', vart='/etc/vart.conf',
            board_cid='/sys/block/mmcblk1/device/cid'),
        board_cid='0353445345333247805558c00401a100',
        firmware_names=dict(WIDE_V1='aura-visual-servo-b4096-wide-v1.bit.bin',
            BENCHMARK_B4096='kv260-benchmark-b4096.bit.bin'),
        vart_lines=dict(WIDE_V1='firmware: /lib/firmware/xilinx/aura-visual-servo-b4096-wide-v1/aura-visual-servo-b4096-wide-v1.xclbin\n',
            BENCHMARK_B4096='firmware: /lib/firmware/xilinx/kv260-benchmark-b4096/kv260-benchmark-b4096.xclbin\n'),
        limits=dict(per_file_bytes=16777216, total_bytes=67108864, json_bytes=262144,
                    health_bytes=262144, health_timeout_s=.8),
        camera_health=dict(host='127.0.0.1', port=8790, path='/health', samples=2),
        supplied_projection_sha256=sha(supplied.read_bytes()),
        no_import_or_execution_of_checked_files=True,
        current_physical_reference_or_direction_inferred=False)
    bundle = REVIEW / 'probe_bundle'
    bundle.mkdir(exist_ok=True)
    save(bundle / 'probe_policy.json', policy)
    policy_sha = sha((bundle / 'probe_policy.json').read_bytes())
    source = (REVIEW / 'source/readonly_probe_template.py').read_text(encoding='utf-8')
    assert source.count('__POLICY_SHA256__') == 1
    (bundle / 'run_readonly_probe.py').write_text(source.replace('__POLICY_SHA256__', policy_sha), encoding='utf-8')
    save(REVIEW / 'evidence/supplied_projection_review.json', dict(
        status='SUPPLIED_V24_PROJECTION_SHA_VERIFIED', source_sha256=sha(supplied.read_bytes()),
        verified_by_main_at_saved_observation=True, newly_read_live_by_this_window=False,
        confirmed_fields=observed, firmware_kind='UNKNOWN', vart_kind='UNKNOWN',
        no_benchmark_observation_reused=True, current_physical_reference_us=None,
        current_direction_qualified=None))
    save(REVIEW / 'evidence/probe_policy_manifest.json', dict(
        policy_sha256=policy_sha, script_sha256=sha((bundle / 'run_readonly_probe.py').read_bytes()),
        static_file_entries=len(files), controller_entries=25,
        effective_face_config_is_manual_reference=True,
        fixed_v24_startup_sha256=mapping['startup_sha256'],
        hardware_accessed=False, policy_created_from_local_evidence=True))
    print(json.dumps(dict(status='FIXED_READONLY_PROBE_BUILT', files=len(files), owners=3,
                         controller_entries=25, live_device_accessed=False)))


if __name__ == '__main__':
    main()
