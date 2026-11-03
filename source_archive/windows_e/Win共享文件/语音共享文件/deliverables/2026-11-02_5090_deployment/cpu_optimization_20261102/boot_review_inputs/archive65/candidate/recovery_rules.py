"""Small metadata rules around the original DFX, camera and GUI mechanisms.

No devices, networks, models, stores or project runtime modules are opened here.
"""
import copy
import hashlib
import json
import re

APP = 'aura-visual-servo-b4096-wide-v1'
BENCHMARK = 'kv260-benchmark-b4096'
CLIENT = '/usr/bin/dfx-mgr-client'
CLIENT_SHA = 'a37d8449c3362a509d459f9e57aa3711314602369354f7d98ca60c3e51607ad7'
DAEMON_SHA = '369c7fb0ddd023a7cf7af14896a7fda6036219a36f4980c73640889720c95dfd'
MANIFEST_SHA = '6a4b645a5bbfd35c9107976edf27886cf8e0c91e40f48be6f052a95e1172c1cf'
IDSTOP_SHA = 'c9e91f74336c1e73d7c60408739abc8537b80066eb666a1a79e32b81d7d267aa'
VERIFIER_SHA = 'b77c32b3863b9464006ac1bb7f16c8f767113925d9142d77e4755f1ce365527e'
FORBIDDEN_OLD_FINAL = 'c6c8baab1de423e27740137330f8315796a7778e36735c93a0c87f2a56029471'
REPLIES = {
    'remove': b'remove from slot 0 returns: 0 (Ok)\n',
    'load': (APP + ': loaded to slot 0\n').encode(),
}
CAMERA = 'aura-camera-ui.service'
GUI = 'aura-avatar-ui.service'


class Hold(RuntimeError):
    """An unproved state: stop advancing, keep the original owner and evidence."""


def require(value, code):
    if not value:
        raise Hold(code)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True) + '\n').encode()


def sha(value):
    require(isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value), 'INVALID_SHA256')
    return value


def owner(value):
    require(isinstance(value, dict) and set(value) == {'pid', 'birth_ticks', 'command_sha256'}, 'OWNER_SHAPE')
    require(type(value['pid']) is int and value['pid'] > 0, 'OWNER_PID')
    require(isinstance(value['birth_ticks'], str) and re.fullmatch('[1-9][0-9]*', value['birth_ticks']), 'OWNER_BIRTH')
    sha(value['command_sha256'])
    return value


def require_no_owners(scan):
    require(scan['complete'] is True and not scan['unreadable'], 'OWNER_SCAN_INCOMPLETE')
    require(not scan['owners'], 'HARDWARE_OWNER_PRESENT')


def loaded_app(raw):
    """Parse the unchanged original client's six-column package table."""
    require(len(raw) <= 65536, 'PACKAGE_REPLY_OVERSIZE')
    lines = raw.decode('ascii', 'strict').splitlines()
    header = False
    names = set()
    active = []
    for line in lines:
        if not line.strip():
            continue
        if line.split()[0] == 'Accelerator':
            require(not header and line.split()[-1] == 'Active_slot', 'PACKAGE_HEADER')
            header = True
            continue
        fields = line.split()
        require(header and len(fields) == 6 and fields[0] not in names, 'PACKAGE_ROW')
        names.add(fields[0])
        require(fields[1] in {'PL_FLAT', 'XRT_FLAT', 'SIHA_PL_DFX', 'XRT_PL_DFX', 'XRT_AIE_DFX'}, 'PACKAGE_TYPE')
        slot = fields[-1]
        require(slot == '-1' or slot == '0,', 'UNEXPECTED_ACTIVE_SLOT')
        if slot == '0,':
            active.append(fields[0])
    require(header and APP in names and BENCHMARK in names and len(active) == 1, 'PACKAGE_ACTIVE_AMBIGUOUS')
    require(active[0] in {APP, BENCHMARK}, 'UNAPPROVED_LOADED_APP')
    return active[0]


def verify_platform(value, app):
    """Use dynamic overlay identity and a paired ZOCL parent/child tree."""
    require(value['firmware'] == app + '.bit.bin', 'FIRMWARE_IDENTITY')
    require(value['fpga_state'] == 'operating', 'FPGA_NOT_OPERATING')
    require(value['vart'] == 'firmware: /lib/firmware/xilinx/' + app + '/' + app + '.xclbin\n', 'VART_PAIRING')
    overlays = value['overlays']
    require(len(overlays) == 1 and overlays[0]['name'].startswith(app + '_image_')
            and overlays[0]['status'] == 'applied', 'DYNAMIC_OVERLAY_PAIRING')
    render, links = value['render'], value['zocl_links']
    require(len(render) == 1 and links and not value['unexpected_zocl_links'], 'ZOCL_RENDER_SHAPE')
    device = render[0]['device']
    require(device.startswith('/sys/devices/') and sum(p == device for p in links) == 1
            and all(p == device or p.startswith(device + '/') for p in links), 'ZOCL_PARENT_CHILD_PAIRING')
    sha(value['fdt_sha256'])  # Measured actual value; no old hash or required hash change.


def verify_unloaded(value):
    require(value['firmware'] is None and not value['overlays'] and not value['render']
            and not value['zocl_links'] and not value['unexpected_zocl_links'], 'PLATFORM_NOT_UNLOADED')


def verify_job(state, invocation, stdout, stderr, action):
    require(bool(re.fullmatch('[0-9a-f]{32}', invocation)) and state.get('InvocationID') == invocation, 'JOB_INVOCATION_CHANGED')
    needed = {'MainPID': '0', 'ActiveState': 'active', 'SubState': 'exited', 'Job': '',
              'ExecMainCode': '1', 'ExecMainStatus': '0', 'Result': 'success'}
    require(all(state.get(k) == v for k, v in needed.items()), 'JOB_NOT_CONFIRMED_SUCCESS')
    require(int(state.get('ExecMainPID', '0')) > 0
            and int(state.get('ExecMainExitTimestampMonotonic', '0')) > int(state.get('ExecMainStartTimestampMonotonic', '0')) > 0,
            'JOB_COMPLETION_TIMESTAMPS')
    require(len(stdout) <= 65536 and not stderr, 'JOB_STDERR_OR_OVERSIZE')
    if action in REPLIES:
        require(stdout == REPLIES[action], 'ORIGINAL_REPLY_NOT_EXACT')
    elif action == 'list':
        return loaded_app(stdout)


def verify_idstop(report, boot, manifest_sha):
    require(report.get('boot_id') == boot and report.get('manifest_sha256') == manifest_sha
            and report.get('identity_stop_passed') is True, 'IDSTOP_REPORT_PROVENANCE')
    require(all(report.get(k) is False for k in ('ARM_sent', 'COMMIT_sent', 'BIND_sent', 'REFERENCE_sent')), 'IDSTOP_MOTION_REQUEST')
    after = report.get('after_stop') or {}
    require(type(after.get('flags')) is int and after['flags'] == 0
            and type(after.get('lease_left_ms')) is int and after['lease_left_ms'] == 0, 'IDSTOP_OUTPUT_NOT_DISABLED')


def verify_final_pointer(raw, consumed, predecessor):
    """A pointer gate only. The original reader/bootstrap still validates/restores it."""
    require(digest(raw) != FORBIDDEN_OLD_FINAL, 'CONSUMED_C6C8_FINAL_FORBIDDEN')
    require(not consumed, 'CONSUMED_FINAL_POINTER')
    doc = json.loads(raw)
    seed = doc.get('seed') or {}
    require(doc.get('schema') == 'aura-native-protection-checkpoint-2'
            and doc.get('scope') == 'final_quiescent_before_native_owner_close'
            and seed.get('purpose') == 'final_quiescent_business_checkpoint'
            and seed.get('checkpoint_kind') == 1 and seed.get('fenced') == 0, 'ORIGINAL_FINAL_REQUIRED')
    prior = predecessor['camera_owner']
    owner(prior)
    require(seed.get('boot_id') == predecessor['boot_id'] and seed.get('source_pid') == prior['pid']
            and seed.get('source_birth_ticks') == int(prior['birth_ticks']), 'FINAL_POINTER_WRONG_PREDECESSOR')
    return digest(raw)


def verify_bootstrap_handoff(handoff, gate, boot, contract_sha):
    require(handoff.get('mode') in {'native_new_kernel_boot', 'native_exact_same_boot'}, 'ORIGINAL_BOOTSTRAP_HANDOFF_MISSING')
    require(gate['boot_id'] == boot and gate['contract_sha256'] == contract_sha
            and handoff.get('seed_sha256') == gate['checkpoint_sha256'], 'ORIGINAL_CAMERA_USED_DIFFERENT_FINAL')
    prior = gate['predecessor']['camera_owner']
    require(handoff.get('source_pid') == prior['pid']
            and str(handoff.get('source_birth_ticks')) == prior['birth_ticks'], 'ORIGINAL_BOOTSTRAP_SOURCE_OWNER_CHANGED')
    if handoff['mode'] == 'native_new_kernel_boot':
        require(handoff.get('current_boot') == boot and handoff.get('source_boot') == gate['predecessor']['boot_id'], 'ORIGINAL_NEW_BOOT_ARCHIVE_PROVENANCE')


def make_binding(selected, boot, current_owner, run_pin, approved_sources):
    owner(current_owner)
    require(selected['source_sha256'] == approved_sources, 'SELECTED_SOURCE_MAP_CHANGED')
    result = copy.deepcopy(selected)
    result.update(board_boot_id=boot, camera_pid=current_owner['pid'], camera_start_ticks=current_owner['birth_ticks'],
                  camera_cmdline_sha256=current_owner['command_sha256'], camera_config=run_pin['path'])
    existing = result['source_sha256'].get(run_pin['path'])
    require(existing is None or existing == run_pin['sha256'], 'RUN_CONFIG_PIN_CONFLICT')
    result['source_sha256'][run_pin['path']] = sha(run_pin['sha256'])
    return result


def config_patch(startup, ui, binding_pin):
    """Only the selected spec and its existing startup component pin may change."""
    changed_ui = copy.deepcopy(ui)
    changed_ui['board_business']['face_readback'] = dict(binding_pin)
    ui_bytes = encoded(changed_ui)
    changed_startup = copy.deepcopy(startup)
    require('config/board_avatar_gtk.json' in startup['component_sha256'], 'UI_PIN_MISSING')
    changed_startup['component_sha256']['config/board_avatar_gtk.json'] = digest(ui_bytes)
    return ui_bytes, encoded(changed_startup)


def gui_projection(state):
    """Export fixed booleans/counters only; discard all names, text and IDs."""
    pair, display = state.get('character_pair') or {}, state.get('avatar_display') or {}
    hf, pan, biz = (state.get('handsfree_dialogue') or {}, state.get('manual_pan') or {}, state.get('board_business') or {})
    clock = biz.get('clock') or {}
    return dict(sequence=state.get('sequence'), main=state.get('ui_page') == 'main', idle=state.get('phase') == 'IDLE',
                playing=state.get('playing'), pair_ready=pair.get('state') == 'READY',
                production_selected=pair.get('production_selected'), fallback_allowed=pair.get('fallback_allowed'),
                visible=display.get('visible'), frames=display.get('frames'),
                listening=hf.get('enabled'), microphone=hf.get('microphone_open'), listening_state=hf.get('state'),
                started=biz.get('started'), closed=biz.get('closed'), writer=(biz.get('writer') or {}).get('held'),
                clock_anchored=clock.get('anchored'), clock_same_boot=clock.get('same_boot'),
                faults=(state.get('runtime_faults') or {}).get('count'), following=pan.get('automatic_following'),
                pan_locked=pan.get('state') in {'FAULT', 'UNAVAILABLE'} and pan.get('readback') is None and pan.get('pulse_us') is None)


def verify_ready(first, last, listening_enabled):
    require(type(listening_enabled) is bool, 'LISTENING_PREFERENCE_SHAPE')
    for value in (first, last):
        require(all(value.get(k) is True for k in ('main', 'idle', 'pair_ready', 'production_selected', 'visible',
                                                  'started', 'writer', 'clock_anchored', 'clock_same_boot', 'pan_locked')), 'GUI_NOT_READY_OR_AXIS_NOT_LOCKED')
        require(all(value.get(k) is False for k in ('playing', 'fallback_allowed', 'closed', 'following')), 'GUI_UNSAFE_STATE')
        require(type(value.get('faults')) is int and value['faults'] == 0, 'GUI_RUNTIME_FAULT')
        require(value.get('listening') is listening_enabled, 'LISTENING_PREFERENCE_NOT_PRESERVED')
        if not listening_enabled:
            require(value.get('microphone') is False and value.get('listening_state') == 'PAUSED', 'GUI_NOT_PAUSED')
        else:
            require(value.get('listening_state') in {'WAITING_SERVICE', 'WAITING_SPEECH', 'COOLDOWN'}, 'GUI_LISTENING_NOT_IDLE')
    require(type(first.get('sequence')) is int and type(last.get('sequence')) is int and last['sequence'] > first['sequence'], 'GUI_API_NOT_ADVANCING')
    require(type(first.get('frames')) is int and type(last.get('frames')) is int and last['frames'] > first['frames'], 'AVATAR_NOT_ADVANCING')
