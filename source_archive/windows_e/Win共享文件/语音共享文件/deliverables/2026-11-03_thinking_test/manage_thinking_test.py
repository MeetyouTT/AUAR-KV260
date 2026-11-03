"""Scoped, reversible temporary thinking test; all model requests remain board-owned."""
from datetime import datetime, timezone
import argparse
import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import uuid

TASK = Path(__file__).resolve().parent
REGISTRY = TASK.parent/'2026-11-02_5090_deployment/CHAT_COORDINATION.json'
PHASE = TASK/'DEVICE_MAINTENANCE.json'


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def save(path, value):
    raw = (json.dumps(value, ensure_ascii=False, indent=2)+'\n').encode()
    temporary = path.with_name(path.name+'.part-'+uuid.uuid4().hex)
    with temporary.open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('action', choices=('claim', 'inspect', 'stop', 'apply', 'start', 'ready', 'verify', 'on', 'off', 'status', 'release'))
args = parser.parse_args()

if args.action == 'claim':
    assert not PHASE.exists()
    original = REGISTRY.read_bytes()
    registry = json.loads(original)
    previous = registry['board_maintenance_owner']
    assert previous['permission_active'] is False and not previous.get('maintenance_holder_active_work')
    assert previous.get('pending_calls_or_observers', 0) == 0 and previous.get('unknown_operations_remaining', 0) == 0
    operation = uuid.uuid4().hex
    (TASK/'CHAT_COORDINATION.before.json').write_bytes(original)
    phase = dict(schema='aura-temporary-thinking-test-maintenance-1', permission_active=True,
        operator_session_id=operation, thread_id=None, title='当前用户对话｜模型思考模式临时测试',
        authorization_source='Direct human request in the current chat',
        user_request='把模型的思考模式作为测试选项暂时开启',
        created_utc=datetime.now(timezone.utc).isoformat(),
        scope=['One board dialogue source plus existing startup pin', 'Normal guarded GUI stop/start',
               'Volatile current-boot thinking selection', 'Public synthetic checks; preserve paused listening'],
        transaction='/home/root/aura-5090-recovery-20261102-a6d4a069/thinking-test-'+operation,
        camera_or_motion_changes=False, private_store_operations=0)
    save(PHASE, phase)
    registry['board_maintenance_owner'] = dict(phase, maintenance_holder_active_work=True,
        phase_receipt=str(PHASE), pending_calls_or_observers=0, unknown_operations_remaining=0)
    assert REGISTRY.read_bytes() == original
    save(REGISTRY, registry)
    print(json.dumps(dict(status='SCOPED_MAINTENANCE_CLAIMED', operation_id=operation)))
    raise SystemExit(0)

phase = read(PHASE)
if args.action == 'release':
    original = REGISTRY.read_bytes()
    registry = json.loads(original)
    assert registry['board_maintenance_owner']['operator_session_id'] == phase['operator_session_id']
    assert read(TASK/'ON.json')['status'] == 'THINKING_TEST_ON'
    assert read(TASK/'VERIFY.json')['status'] == 'THINKING_TEST_ON'
    assert read(TASK/'PUBLIC_PERSONA_PROBE.json')['board_result']['status'] == 'LIVE_PERSONA_THINKING_MODEL_CHECKS_PASSED'
    verified = read(TASK/'VERIFY.json')
    phase.update(permission_active=False, status='DEPLOYED_VERIFIED_THINKING_TEST_ON_SCOPE_CLOSED',
        closed_utc=datetime.now(timezone.utc).isoformat(), pending_calls_or_observers=0,
        unknown_operations_remaining=0, background_observers=0,
        board_boot_id=verified['board_boot_id'], startup_sha256=verified['startup_sha256'],
        gui_owner=verified['gui_owner'], gui_children=verified['gui_children'],
        camera_owner=read(TASK/'INSPECT.json')['camera_owner'], current_state=verified['current_state'],
        result_receipt=str(TASK/'RESULT.json'))
    save(PHASE, phase)
    registry['board_maintenance_owner'] = dict(phase, maintenance_holder_active_work=False,
        phase_receipt=str(PHASE), result_receipt=str(TASK/'ON.json'))
    registry['temporary_model_thinking_test'] = dict(enabled=True, lifetime='current board boot only',
        board_boot_id=verified['board_boot_id'], observed_utc=phase['closed_utc'],
        receipt=str(TASK/'RESULT.json'), user_request=phase['user_request'], switch_script=str(TASK/'switch_thinking_test.ps1'))
    assert REGISTRY.read_bytes() == original
    save(REGISTRY, registry)
    print(json.dumps(dict(status=phase['status'], permission_active=False)))
    raise SystemExit(0)

registry = read(REGISTRY)
if args.action not in ('on', 'off', 'status'):
    assert phase['permission_active']
    assert registry['board_maintenance_owner']['operator_session_id'] == phase['operator_session_id']
    assert registry['board_maintenance_owner']['permission_active']
elif registry['board_maintenance_owner']['permission_active']:
    assert registry['board_maintenance_owner'].get('operator_session_id') == phase['operator_session_id']

payload = dict(action=args.action, baseline=read(TASK/'BASELINE.json'),
    operation_id=phase['operator_session_id'], transaction=phase['transaction'], candidate=read(TASK/'CANDIDATE.json'))
if (TASK/'INSPECT.json').exists(): payload['fresh'] = read(TASK/'INSPECT.json')
if (TASK/'APPLY.json').exists(): payload['expected_startup_sha256'] = read(TASK/'APPLY.json')['startup_sha256']
if args.action == 'apply':
    payload['candidate_base64'] = base64.b64encode((TASK/'candidate'/payload['candidate']['path']).read_bytes()).decode()
source = 'P = '+repr(payload)+'\n'+(TASK/'device_action.py').read_text(encoding='utf-8')
compile(source, 'recorded-thinking-action', 'exec')
attempt = uuid.uuid4().hex[:12]
record = TASK/(args.action.upper()+'-'+attempt)
save(record.with_suffix('.intent.json'), dict(action=args.action, single_submission=True,
    source_sha256=hashlib.sha256(source.encode()).hexdigest(), host_utc=datetime.now(timezone.utc).isoformat()))
helper = TASK.parent/'2026-10-18_board_dialogue/board_ssh.py'
spec = importlib.util.spec_from_file_location('verified_board_transport', helper)
transport = importlib.util.module_from_spec(spec)
spec.loader.exec_module(transport)
try:
    raw = transport.ssh('python3 -B -', source, timeout=45)
    result = json.loads(raw)
except Exception as error:
    save(record.with_suffix('.error.json'), dict(action=args.action, error_class=type(error).__name__, detail=str(error)[:1500]))
    raise
save(record.with_suffix('.result.json'), result)
save(TASK/(args.action.upper()+'.json'), result)
print(json.dumps(result, ensure_ascii=False))
