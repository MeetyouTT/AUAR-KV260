"""Strict serialized native protection state; no model or service operations.

Production uses a hash-pinned final quiescent checkpoint. A legacy health
observation is not an exact shutdown checkpoint and is deliberately insufficient
for automatically resuming recovery. Maintenance seeds are a separate scope.
"""
import ctypes as C
import hashlib
import json
import math
import os
from pathlib import Path
import time
import uuid


PHASES = ('RUNNING', 'COOLDOWN', 'PROBATION', 'LATCHED')
REASONS = (None, 'unsafe_or_unknown_completion', 'recovery_budget_exhausted',
           'completed_hardcap_only', 'primary_overrun_after_fault', 'primary_overrun_during_probation')
FEATURE_COUNTERS = ('requests', 'execution_attempts', 'completed', 'features_returned',
                    'deferred', 'slot_denials', 'expired_after_admission')


def integer(value, name, *, maximum=2**64-1):
    if type(value) is not int or not 0 <= value <= maximum:
        raise ValueError('Invalid native protection integer: ' + name)
    return value


def digest(value, name):
    if not isinstance(value, str) or len(value) != 64 or any(c not in '0123456789abcdef' for c in value):
        raise ValueError('Pinned lowercase SHA256 required: ' + name)
    return value


def _boot(value):
    if not isinstance(value, str) or str(uuid.UUID(value)) != value:
        raise ValueError('Canonical kernel boot ID required')
    return value


def isolated_maintenance_seed(*, boot_id, captured_mono_ns, production_snapshot_sha256):
    """A new *test* counter domain, never a production recovery operation."""
    _boot(boot_id);integer(captured_mono_ns, 'captured_mono_ns')
    digest(production_snapshot_sha256, 'production_snapshot_sha256')
    recovery = []
    for _ in range(2):
        recovery.append(dict(enabled=1, phase=0, reason=0, probe_successes=0,
            attempt_count=0, history_opaque=0, opaque_attempt_count=0,
            cooldown_until_ns=0, fault_primary_calls=0, fault_primary_overruns=0,
            faults=0, attempts=0, recoveries=0, observed_ns=captured_mono_ns,
            attempt_times_ns=[0, 0]))
    return dict(abi_version=2, purpose='isolated_model_equivalence', fenced=0,
        checkpoint_kind=0,
        captured_mono_ns=captured_mono_ns, primary_calls=0, primary_period_overruns=0,
        last_primary_ns=0, source_pid=0, source_birth_ticks=0, boot_id=boot_id,
        source_manifest_sha256=production_snapshot_sha256,
        parent_snapshot_sha256=production_snapshot_sha256,
        admissions=[0]*3, overruns=[0]*3, completed=[0]*3,
        native_failures=[0]*3, not_submitted=[0]*3, disabled=[0]*3, recovery=recovery)


def make_native_seed(values, seed_type, recovery_type):
    """Build the fixed C ABI only after explicit scope and range validation."""
    if not isinstance(values, dict) or values.get('abi_version') != 2:
        raise ValueError('Native seed schema mismatch')
    purpose = values.get('purpose')
    if purpose not in ('final_quiescent_business_checkpoint', 'isolated_model_equivalence',
                        'validated_new_kernel_boot'):
        raise ValueError('Explicit native seed purpose required')
    if purpose == 'isolated_model_equivalence':
        digest(values.get('parent_snapshot_sha256'), 'parent_snapshot_sha256')
    result = seed_type()
    result.abi_version, result.struct_size = 2, C.sizeof(seed_type)
    result.checkpoint_kind = 1 if purpose == 'final_quiescent_business_checkpoint' else 0
    if values.get('checkpoint_kind') != result.checkpoint_kind:
        raise ValueError('Health prefix or mismatched checkpoint kind cannot authorize execution')
    for name in ('fenced', 'captured_mono_ns', 'primary_calls', 'primary_period_overruns',
                 'last_primary_ns', 'source_pid', 'source_birth_ticks'):
        maximum = 2**32-1 if name == 'source_pid' else 2**64-1
        setattr(result, name, integer(values[name], name, maximum=maximum))
    if result.fenced or not result.captured_mono_ns:
        raise ValueError('Unconfirmed completion or missing capture time')
    result.boot_id = _boot(values['boot_id']).encode()
    result.source_manifest_sha256 = digest(values['source_manifest_sha256'], 'source_manifest_sha256').encode()
    if purpose == 'final_quiescent_business_checkpoint' and not (result.source_pid and result.source_birth_ticks):
        raise ValueError('Business history requires predecessor provenance')
    if purpose != 'final_quiescent_business_checkpoint' and (result.source_pid or result.source_birth_ticks):
        raise ValueError('Fresh/maintenance counter domains cannot impersonate a predecessor')
    for name in ('admissions', 'overruns', 'completed', 'native_failures', 'not_submitted', 'disabled'):
        items = values[name]
        if not isinstance(items, list) or len(items) != 3:
            raise ValueError('Exactly three native task counters required: ' + name)
        for i, item in enumerate(items):
            getattr(result, name)[i] = integer(item, name, maximum=1 if name == 'disabled' else 2**64-1)
    states = values['recovery']
    if not isinstance(states, list) or len(states) != 2:
        raise ValueError('Independent YuNet/SFace recovery states required')
    for i, state in enumerate(states):
        target = result.recovery[i]
        for name, field in recovery_type._fields_:
            if name == 'reserved':continue
            if name == 'attempt_times_ns':
                times = state[name]
                if not isinstance(times, list) or len(times) != 2:
                    raise ValueError('Fixed two-entry recovery history required')
                for j, value in enumerate(times):target.attempt_times_ns[j] = integer(value, name)
            else:
                maximum = 2**32-1 if field is C.c_uint32 else 2**64-1
                setattr(target, name, integer(state[name], name, maximum=maximum))
        if (target.enabled not in (0,1) or not 0 <= target.phase <= 3 or not 0 <= target.reason <= 5 or
                target.attempt_count > 2 or target.history_opaque not in (0,1)):
            raise ValueError('Invalid native recovery enum or history count')
        if target.history_opaque and (target.phase != 3 or not result.disabled[i+1]):
            raise ValueError('Opaque legacy history must remain disabled and LATCHED')
    if purpose != 'final_quiescent_business_checkpoint':
        if (result.primary_calls or result.primary_period_overruns or result.last_primary_ns or
                any(values[name][i] for name in ('admissions','overruns','completed','native_failures',
                    'not_submitted','disabled') for i in range(3)) or
                any(s['phase'] or s['faults'] or s['attempts'] or s['recoveries'] or
                    s['attempt_count'] or s['history_opaque'] for s in states)):
            raise ValueError('Fresh/maintenance seed cannot discard or replay prior faults')
    return result


def _read_pinned(pin):
    if not isinstance(pin, dict) or set(pin) != {'path', 'sha256'}:
        raise ValueError('Hash-pinned native checkpoint required')
    path = Path(pin['path'])
    if not path.is_absolute() or path.is_symlink() or path.resolve() != path:
        raise ValueError('Native checkpoint path redirects')
    raw = path.read_bytes()
    if len(raw) > 262144 or hashlib.sha256(raw).hexdigest() != digest(pin['sha256'], 'checkpoint SHA'):
        raise ValueError('Native checkpoint hash mismatch')
    return path, json.loads(raw)


def load_business_checkpoint(pin, *, boot_id, now_ns=None):
    """Read/validate only. Source-owner shutdown is separately verified below."""
    path, document = _read_pinned(pin)
    if document.get('schema') != 'aura-native-protection-checkpoint-2':
        raise ValueError('Legacy health-only seed lacks exact native recovery/checkpoint history')
    if document.get('scope') != 'final_quiescent_before_native_owner_close':
        raise ValueError('Final quiescent checkpoint scope required')
    seed, auxiliary = document['seed'], document['auxiliary']
    if (seed.get('purpose') != 'final_quiescent_business_checkpoint' or
            seed.get('checkpoint_kind') != 1 or seed['boot_id'] != _boot(boot_id)):
        raise ValueError('Business checkpoint boot or counter domain differs')
    now = time.monotonic_ns() if now_ns is None else now_ns
    if not 0 < integer(seed['captured_mono_ns'], 'captured_mono_ns') <= now:
        raise ValueError('Checkpoint capture lies outside current monotonic domain')
    if any(integer(v, 'pending_result_tokens') for v in auxiliary['pending_result_tokens']):
        raise ValueError('Pending Python result confirmation must finish before checkpoint')
    if auxiliary['active'] or auxiliary['primary_waiting'] or auxiliary['fenced']:
        raise ValueError('Native checkpoint owner was not safely idle')
    digest(document['source_unit_sha256'], 'source_unit_sha256')
    counters = auxiliary['sface_counters']
    if set(counters) != set(FEATURE_COUNTERS):raise ValueError('Complete SFace counters required')
    for name, value in counters.items():integer(value, 'sface.'+name)
    if not counters['features_returned'] <= counters['completed'] <= counters['execution_attempts'] <= counters['requests']:
        raise ValueError('Inconsistent SFace checkpoint counters')
    # Static validation must finish before checked_backend creates the original
    # YOLO owner or runs its startup references. The C layer rechecks its own
    # stricter policy/clock constraints later, before any gate can execute.
    from board.vision.native_binding import Seed, Recovery
    make_native_seed(seed, Seed, Recovery)
    source = Path('/proc') / str(integer(seed['source_pid'], 'source_pid')) / 'stat'
    if source.exists():
        birth = int(source.read_text().rsplit(')',1)[1].split()[19])
        if birth == seed['source_birth_ticks']:
            raise ValueError('Predecessor still alive; second native owner forbidden')
    marker = path.with_name(path.name+'.native-consumed-'+pin['sha256'])
    if marker.exists():raise ValueError('Native checkpoint was already consumed; refusing history reset')
    return dict(seed=seed, auxiliary=auxiliary, document=document, marker=str(marker), sha256=pin['sha256'])


def consume_checkpoint(loaded):
    """Call after confirmed native restore, before any adoption or worker."""
    marker = Path(loaded['marker'])
    fd = os.open(str(marker), os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_CLOEXEC|os.O_NOFOLLOW, 0o600)
    try:
        raw = (loaded['sha256']+'\n').encode()
        if os.write(fd, raw) != len(raw):raise OSError('Incomplete native checkpoint consumption marker')
        os.fsync(fd)
    finally:os.close(fd)


def checkpoint_document(state, *, native_seed, source_unit_sha256, sface_counters,
                        inherited_optional=None):
    """Serialize only a confirmed idle native owner after business workers stop."""
    if (state['active'] or state['primary_waiting'] or state['fenced'] or
            any(state['pending_result_tokens']) or not state['seed_loaded'] or not state['quiesced']):
        raise ValueError('Cannot checkpoint a busy, pending or fenced owner')
    seed = dict(native_seed)
    if seed.get('purpose') != 'final_quiescent_business_checkpoint' or seed.get('abi_version') != 2:
        raise ValueError('Atomic native checkpoint is required')
    if seed['source_pid'] != os.getpid():raise ValueError('Native checkpoint belongs to another process')
    return {'schema':'aura-native-protection-checkpoint-2',
        'scope':'final_quiescent_before_native_owner_close', 'seed':seed,
        'source_unit_sha256':digest(source_unit_sha256,'source_unit_sha256'),
        'auxiliary':{'active':0,'primary_waiting':0,'fenced':0,'pending_result_tokens':[0]*3,
            'sface_counters':{name:integer(sface_counters[name],name) for name in FEATURE_COUNTERS},
            'inherited_optional':inherited_optional or {}}}


def write_checkpoint(path, document):
    path = Path(path)
    if not path.is_absolute() or path.is_symlink() or path.resolve() != path:
        raise ValueError('Explicit nonredirecting checkpoint output required')
    raw = (json.dumps(document,sort_keys=True,separators=(',',':'))+'\n').encode()
    if len(raw)>262144:raise ValueError('Native checkpoint exceeds bound')
    temporary = path.with_name(path.name+'.partial-'+str(os.getpid()))
    fd = os.open(str(temporary),os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_CLOEXEC|os.O_NOFOLLOW,0o600)
    try:
        if os.write(fd,raw)!=len(raw):raise OSError('Incomplete native checkpoint write')
        os.fsync(fd)
    finally:os.close(fd)
    os.replace(str(temporary),str(path))
    return {'path':str(path),'sha256':hashlib.sha256(raw).hexdigest()}
