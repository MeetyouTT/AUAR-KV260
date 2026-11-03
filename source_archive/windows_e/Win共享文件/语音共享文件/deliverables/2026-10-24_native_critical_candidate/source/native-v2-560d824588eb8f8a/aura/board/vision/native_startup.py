"""Explicit camera startup/shutdown wiring for the native candidate."""
import hashlib
import json
from pathlib import Path

from board.vision.native_binding import NativeContext
from board.vision.native_protection import (consume_checkpoint, digest, load_business_checkpoint,
    checkpoint_document, write_checkpoint, FEATURE_COUNTERS)
from board.vision.native_schedule import NativeDpuSchedule
from board.vision.native_yolo import NativeYoloOwner


def configuration(config):
    value = config.get('native_execution')
    if value is None:return None
    keys = {'library','library_sha256','seed','source_manifest','source_manifest_sha256',
            'source_unit_sha256','checkpoint_output'}
    if not isinstance(value,dict) or set(value) != keys:
        raise ValueError('Explicit complete native execution configuration required')
    for name in ('library_sha256','source_manifest_sha256','source_unit_sha256'):
        digest(value[name],name)
    for name in ('library','source_manifest','checkpoint_output'):
        path = Path(value[name])
        if not path.is_absolute() or path.is_symlink() or path.resolve() != path:
            raise ValueError('Explicit nonredirecting native path required: '+name)
    if config.get('detector_backend') != 'dpu_yolox':
        raise ValueError('Native execution requires the original YOLO DPU owner')
    if config.get('optional_admission_floor_ms') != 30:
        raise ValueError('Native execution preserves the conservative 30ms admission floor')
    if not config.get('yunet_dpu_recovery') or not config.get('sface_dpu_recovery'):
        raise ValueError('Independent native recovery policies are mandatory')
    for task in ('yunet','sface'):
        limit = config.get(task+'_slot_wait_ms',0)
        if type(limit) is not int or not 0<=limit<=100:
            raise ValueError('Native notification waits remain in 0..100ms')
    return value


def verify_runtime_manifest(native, root):
    path = Path(native['source_manifest'])
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != native['source_manifest_sha256']:
        raise ValueError('Native runtime manifest SHA mismatch')
    value = json.loads(raw)
    if value.get('schema') != 'aura-native-python-source-2' or not isinstance(value.get('files'),dict):
        raise ValueError('Native runtime source manifest schema differs')
    root = Path(root).resolve()
    actual = {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest()
              for p in root.rglob('*.py') if not p.is_symlink()}
    if actual != value['files']:
        raise ValueError('Native camera source closure differs from the pinned manifest')


def preflight(config, *, boot_id, root):
    native = configuration(config)
    if native is None:return None
    verify_runtime_manifest(native,root)
    loaded = load_business_checkpoint(native['seed'],boot_id=boot_id)
    if loaded['document']['source_unit_sha256'] != native['source_unit_sha256']:
        raise ValueError('Predecessor unit provenance differs')
    return loaded


def attach(config, state, original, loaded):
    """Run after original fixed-input YOLO checks, before any business worker."""
    native = configuration(config)
    if native is None:raise ValueError('Native attachment not configured')
    if loaded is None:raise ValueError('Validated exact native checkpoint required before attachment')
    context = NativeContext(original,native['library'],native['library_sha256'])
    try:
        context.restore_seed(loaded['seed'])
        consume_checkpoint(loaded)
        context.adopt_yolo()
        aux = loaded['auxiliary']
        schedule = NativeDpuSchedule(context,
            yunet_slot_wait_ms=config.get('yunet_slot_wait_ms',0),
            sface_slot_wait_ms=config.get('sface_slot_wait_ms',0),
            inherited_optional=aux.get('inherited_optional'),
            inherited_sface_counters=aux['sface_counters'],
            diagnostics=state.pipeline_metrics.optional_diagnostics)
        schedule.protection_handoff = dict(mode='native_exact_same_boot',
            seed_sha256=loaded['sha256'],source_pid=loaded['seed']['source_pid'],
            source_birth_ticks=loaded['seed']['source_birth_ticks'],
            counter_scope='exact sealed native predecessor counters plus current execution',
            first_use=True)
        owner = NativeYoloOwner(original,context,schedule)
        owner.pipeline_metrics = state.pipeline_metrics
        return owner,schedule
    except BaseException as original_error:
        if context.quarantined:
            # The native call or its Python bookkeeping may have completed;
            # retaining the original owner is part of that uncertain outcome.
            context._retain(original, original_error, 'native startup failed after uncertain operation')
        else:
            try:
                context.close()
            except BaseException as close_error:
                # Cleanup refusal/unknown outcome must not replace the actual
                # startup failure or lose its sole owner/lifecycle references.
                context._retain(original, original_error, close_error,
                    'native startup cleanup was not confirmed')
        raise


def shutdown(config, state, owner):
    """Call only after camera/identity workers joined and their runners closed."""
    native = configuration(config)
    if native is None:return None
    counters = getattr(state.dpu_schedule,'inherited_sface_counters',{})
    if state.identity is not None:
        health = state.identity.health()
        current = health.get('feature_inference') or {}
        if all(name in current for name in FEATURE_COUNTERS):counters=current
    if not all(name in counters for name in FEATURE_COUNTERS):
        raise RuntimeError('Final SFace counters unavailable; refusing a partial native checkpoint')
    seed = owner.native_context.checkpoint(native['source_manifest_sha256'])
    snapshot = owner.native_context.snapshot()
    document = checkpoint_document(snapshot,native_seed=seed,
        source_unit_sha256=native['source_unit_sha256'],sface_counters=counters,
        inherited_optional={task:state.dpu_schedule.optional_status(task) for task in ('yunet','sface')})
    try:
        return write_checkpoint(native['checkpoint_output'],document)
    finally:
        owner.close()
