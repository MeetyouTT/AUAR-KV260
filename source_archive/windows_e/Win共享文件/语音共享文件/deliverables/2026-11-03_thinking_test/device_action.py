"""Executed once over verified SSH, with a host-recorded action payload."""
import base64
import hashlib
import http.client
import json
import os
from pathlib import Path
import subprocess
import sys
import time

# P is supplied by manage_thinking_test.py before this source.
ACTION = P['action']
BASE = P['baseline']
STARTUP = Path(BASE['startup_path'])
TX = Path(P['transaction'])
FLAG = Path('/run/aura-dialogue-thinking-test.json')
PROPS = 'MainPID,ActiveState,SubState,Job,Restart,KillMode,SendSIGKILL,TimeoutStopUSec,Result,ExecMainStatus'
ORIGINAL_PROPS = dict(Restart='no', KillMode='mixed', SendSIGKILL='yes', TimeoutStopUSec='25s')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def unit(name):
    r = subprocess.run(['systemctl', 'show', name, '--property='+PROPS],
                       capture_output=True, text=True, timeout=5)
    assert r.returncode == 0
    return dict(line.split('=', 1) for line in r.stdout.splitlines() if '=' in line)


def owner(pid):
    root = Path('/proc')/str(pid)
    return dict(pid=int(pid), birth_ticks=root.joinpath('stat').read_text().rsplit(')', 1)[1].split()[19],
                command_sha256=sha(root.joinpath('cmdline').read_bytes()))


def get(host, port, path):
    c = http.client.HTTPConnection(host, port, timeout=4)
    try:
        c.request('GET', path)
        r = c.getresponse()
        raw = r.read(2097153)
        assert r.status == 200 and len(raw) <= 2097152
        return json.loads(raw)
    finally:
        c.close()


def current_state():
    value = get('127.0.0.1', 8783, '/api/state')
    hands, pan = value.get('handsfree_dialogue') or {}, value.get('manual_pan') or {}
    readback = pan.get('readback') or {}
    speaker = (value.get('board_business') or {}).get('speaker') or {}
    return dict(ui_page=value.get('ui_page'), phase=value.get('phase'),
        pair_ready=(value.get('character_pair') or {}).get('state') == 'READY',
        listening_enabled=hands.get('enabled'), microphone_open=hands.get('microphone_open'),
        handsfree_state=hands.get('state'), playing=bool(value.get('playing')),
        pending_job=bool(value.get('pending_job')), speaker_busy=bool(speaker.get('active') or speaker.get('queued_or_active')),
        follow=pan.get('automatic_following'), axis_output_active=readback.get('active'),
        axis_output_armed=readback.get('armed'), runtime_fault_count=(value.get('runtime_faults') or {}).get('count'))


def paused_idle(value):
    assert value['listening_enabled'] is False and value['microphone_open'] is False
    assert not value['playing'] and not value['pending_job'] and not value['speaker_busy']
    assert value['follow'] is False and value['axis_output_active'] is False and value['axis_output_armed'] is False


def model_ready():
    value = get('192.168.50.1', 8797, '/health')
    backend = value['backend']
    assert value['ok'] and value['role'] == 'model_inference_only'
    assert backend['model'] == 'aura-qwen3.8-27b-abliterated:iq4_xs'
    assert backend['tts_ready'] and backend['num_step'] == 16
    assert not value['active'] and value['pending'] == 0


def saved_pause():
    assert json.loads(Path('/home/root/.local/share/aura-board-business/listening_preference.json').read_bytes()) == dict(version=1, enabled=False)


def create(path, raw):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def durable_replace(path, raw, expected):
    assert path.read_bytes() == expected and not path.is_symlink()
    mode = path.stat().st_mode & 0o777
    temporary = path.with_name(path.name+'.thinking-'+P['operation_id'])
    create(temporary, raw)
    os.chmod(temporary, mode)
    assert path.read_bytes() == expected
    os.replace(temporary, path)
    parent = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(parent)
    finally:
        os.close(parent)


def camera(expected=None):
    value = unit('aura-camera-ui.service')
    assert value['ActiveState'] == 'active' and value['SubState'] == 'running' and not value['Job']
    actual = owner(int(value['MainPID']))
    if expected is not None:
        assert actual == expected
    return actual


def source_check(expected_startup):
    raw = STARTUP.read_bytes()
    assert sha(raw) == expected_startup
    cfg = json.loads(raw)
    aura = Path(cfg['runtime'])/'aura'
    assert len(cfg['component_sha256']) == 380
    assert all(sha((aura/key).read_bytes()) == digest for key, digest in cfg['component_sha256'].items())
    return raw, cfg, aura


def properties(value):
    return {key: value[key] for key in ORIGINAL_PROPS}


assert os.geteuid() == 0
actual_boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
if ACTION not in ('off', 'status'):
    assert actual_boot == BASE['boot_id']
expected_startup = P.get('expected_startup_sha256', BASE['startup_sha256'])
out = dict(action=ACTION, board_boot_id=actual_boot, board_monotonic=time.monotonic(),
           private_store_reads=0, microphone_enable_calls=0, movement_commands=0)

if ACTION in ('off', 'status'):
    # Disabling the volatile selection never rewrites a later deployment.
    # It also remains usable after reboot, when /run has already reset it.
    selected = None
    if os.path.lexists(FLAG):
        assert not FLAG.is_symlink()
        with FLAG.open('rb') as stream:
            raw = stream.read(1025)
        assert len(raw) <= 1024
        selected = json.loads(raw)
        assert selected == dict(version=1, enabled=True, board_boot_id=actual_boot, num_predict=192)
        if ACTION == 'off':
            FLAG.unlink()
            selected = None
    out.update(status='THINKING_TEST_ON' if selected else 'THINKING_TEST_OFF',
        options=dict(think=True, num_predict=192) if selected else {},
        flag_path=str(FLAG), lifetime='current board boot only', source_or_service_mutations=0)

elif ACTION == 'inspect':
    raw, cfg, aura = source_check(expected_startup)
    gu = unit('aura-avatar-ui.service')
    assert gu['ActiveState'] == 'active' and gu['SubState'] == 'running' and not gu['Job']
    assert properties(gu) == ORIGINAL_PROPS
    # Bind both live GUI lifetimes, rather than relying on a saved PID.
    main = owner(int(gu['MainPID']))
    children = Path('/proc')/gu['MainPID']/'task'/gu['MainPID']/'children'
    child_owners = [owner(int(pid)) for pid in children.read_text().split()]
    assert child_owners
    state = current_state()
    paused_idle(state)
    saved_pause()
    model_ready()
    assert not os.path.lexists(FLAG)
    out.update(status='FRESH_IDLE_RECONCILED', startup_sha256=sha(raw), runtime_source_root=str(aura),
        gui_owner=main, gui_children=child_owners, camera_owner=camera(), current_state=state,
        all380_actual_bytes_match=True, original_gui_properties=properties(gu))

elif ACTION == 'stop':
    E = P['fresh']
    source_check(expected_startup)
    assert camera(E['camera_owner']) == E['camera_owner']
    gu = unit('aura-avatar-ui.service')
    assert owner(int(gu['MainPID'])) == E['gui_owner'] and properties(gu) == ORIGINAL_PROPS and not gu['Job']
    assert all(owner(child['pid']) == child for child in E['gui_children'])
    paused_idle(current_state())
    saved_pause()
    model_ready()
    assert not TX.exists() and TX.parent.is_dir() and TX.parent.resolve() == TX.parent
    TX.mkdir(mode=0o700)
    create(TX/'before.json', (json.dumps(E, sort_keys=True, indent=2)+'\n').encode())
    override = Path('/run/systemd/system/aura-avatar-ui.service.d')/('zzzzzz-thinking-'+P['operation_id']+'.conf')
    guard = b'[Service]\nKillMode=process\nSendSIGKILL=no\nTimeoutStopSec=infinity\n'
    override.parent.mkdir(parents=True, exist_ok=True)
    create(override, guard)
    subprocess.run(['systemctl', 'daemon-reload'], check=True, timeout=6, capture_output=True)
    protected = unit('aura-avatar-ui.service')
    assert protected['KillMode'] == 'process' and protected['SendSIGKILL'] == 'no' and protected['TimeoutStopUSec'] == 'infinity'
    assert owner(int(protected['MainPID'])) == E['gui_owner']
    create(TX/'stop-intent.json', b'{"single_normal_stop":true,"force_kill":false}\n')
    subprocess.run(['systemctl', 'stop', '--no-block', 'aura-avatar-ui.service'], check=True, timeout=6, capture_output=True)
    until = time.monotonic()+14
    while time.monotonic() < until:
        gu = unit('aura-avatar-ui.service')
        if gu['MainPID'] == '0' and gu['ActiveState'] == 'inactive' and not gu['Job']:
            break
        time.sleep(.3)
    assert gu['MainPID'] == '0' and gu['ActiveState'] == 'inactive' and gu['SubState'] == 'dead' and not gu['Job']
    assert gu['Result'] == 'success' and gu['ExecMainStatus'] == '0'
    for previous in [E['gui_owner']]+E['gui_children']:
        path = Path('/proc')/str(previous['pid'])
        assert not path.exists() or owner(previous['pid']) != previous
    camera(E['camera_owner'])
    assert override.read_bytes() == guard
    override.unlink()
    subprocess.run(['systemctl', 'daemon-reload'], check=True, timeout=6, capture_output=True)
    assert properties(unit('aura-avatar-ui.service')) == ORIGINAL_PROPS
    out.update(status='GUI_NORMAL_STOPPED', forced_action=False, camera_unchanged=True, original_gui_properties_restored=True)
    create(TX/'stop-result.json', (json.dumps(out)+'\n').encode())

elif ACTION == 'apply':
    gu = unit('aura-avatar-ui.service')
    assert gu['MainPID'] == '0' and gu['ActiveState'] == 'inactive' and not gu['Job']
    assert properties(gu) == ORIGINAL_PROPS
    camera(P['fresh']['camera_owner'])
    saved_pause()
    raw, cfg, aura = source_check(expected_startup)
    path = aura/P['candidate']['path']
    before = path.read_bytes()
    after = base64.b64decode(P['candidate_base64'], validate=True)
    assert sha(before) == P['candidate']['before_sha256'] and sha(after) == P['candidate']['after_sha256']
    compile(after, str(path), 'exec')
    create(TX/'board_dialogue.before.py', before)
    create(TX/'startup.before.json', raw)
    cfg['component_sha256'][P['candidate']['path']] = sha(after)
    updated = (json.dumps(cfg, ensure_ascii=False, indent=2)+'\n').encode()
    create(TX/'apply-intent.json', (json.dumps(dict(before=sha(raw), after=sha(updated)))+'\n').encode())
    durable_replace(path, after, before)
    durable_replace(STARTUP, updated, raw)
    source_check(sha(updated))
    out.update(status='ONE_SOURCE_AND_PIN_APPLIED', startup_sha256=sha(updated), source_sha256=sha(after),
               changed_components=1, retained_components=379, default_thinking_enabled=False)
    create(TX/'apply-result.json', (json.dumps(out)+'\n').encode())

elif ACTION == 'start':
    source_check(expected_startup)
    camera(P['fresh']['camera_owner'])
    saved_pause()
    model_ready()
    gu = unit('aura-avatar-ui.service')
    assert gu['MainPID'] == '0' and gu['ActiveState'] == 'inactive' and not gu['Job']
    assert properties(gu) == ORIGINAL_PROPS
    create(TX/'start-intent.json', b'{"single_normal_start":true,"saved_listening_enabled":false}\n')
    subprocess.run(['systemctl', 'start', '--no-block', 'aura-avatar-ui.service'], check=True, timeout=6, capture_output=True)
    out.update(status='GUI_NORMAL_START_SUBMITTED', gui_unit=unit('aura-avatar-ui.service'))

elif ACTION == 'ready':
    assert sha(STARTUP.read_bytes()) == expected_startup
    until = time.monotonic()+20
    state = None
    while True:
        gu = unit('aura-avatar-ui.service')
        try:
            state = current_state()
        except (OSError, http.client.HTTPException):
            state = None
        if (gu['ActiveState'] == 'active' and gu['SubState'] == 'running' and not gu['Job']
                and state is not None and state['pair_ready']):
            break
        if time.monotonic() >= until or gu['ActiveState'] in ('failed', 'inactive'):
            break
        time.sleep(2)
    out.update(status='GUI_READY' if state is not None and state['pair_ready'] and gu['ActiveState']=='active' else 'GUI_STARTING',
               gui_unit=gu, current_state=state)

elif ACTION in ('verify', 'on'):
    raw, cfg, aura = source_check(expected_startup)
    camera(P['fresh']['camera_owner'])
    sys.path.insert(0, str(aura))
    from board.runtime.board_dialogue import dialogue_thinking_test_options
    if ACTION in ('verify', 'on'):
        state = current_state()
        paused_idle(state)
        saved_pause()
        gu = unit('aura-avatar-ui.service')
        assert gu['ActiveState'] == 'active' and gu['SubState'] == 'running' and not gu['Job']
        assert properties(gu) == ORIGINAL_PROPS
        assert owner(int(gu['MainPID'])) != P['fresh']['gui_owner']
        assert state['pair_ready'] and state['runtime_fault_count'] == 0
        model_ready()
        children = Path('/proc')/gu['MainPID']/'task'/gu['MainPID']/'children'
        out.update(gui_owner=owner(int(gu['MainPID'])),
                   gui_children=[owner(int(pid)) for pid in children.read_text().split()], current_state=state,
                   all380_actual_bytes_match=True, camera_unchanged=True, original_gui_properties_restored=True)
    selected = dict(version=1, enabled=True, board_boot_id=BASE['boot_id'], num_predict=192)
    if ACTION == 'on':
        assert not os.path.lexists(FLAG)
        create(FLAG, (json.dumps(selected)+'\n').encode())
    elif ACTION == 'off':
        if os.path.lexists(FLAG):
            assert not FLAG.is_symlink() and json.loads(FLAG.read_bytes()) == selected
            FLAG.unlink()
    options = dialogue_thinking_test_options(BASE['boot_id'])
    if ACTION == 'on':
        assert options == dict(think=True, num_predict=192)
    elif ACTION == 'off':
        assert options == {}
    out.update(status='THINKING_TEST_ON' if options else 'THINKING_TEST_OFF', options=options,
               lifetime='current board boot only', flag_path=str(FLAG), startup_sha256=sha(raw))
else:
    raise ValueError('Unsupported recorded action')

print(json.dumps(out))
